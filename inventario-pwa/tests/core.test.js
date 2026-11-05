// Testes do núcleo (sem navegador). Rodar: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../js/core.js');

const BASE_CSV = [
  'codigo;descricao;saldo;custo;local',
  '1001;Arroz 5kg;10;20,00;Corredor A',
  '1002;Feijão 1kg;5;7,50;Corredor A',
  '1003;Óleo 900ml;4;6,00;Corredor B',
  '1004;Café 500g;3;18,70;Corredor B',
].join('\n');

const leitura = (codigo, qtd, extra = {}) => ({ codigo, qtd, operador: 'Ana', ts: 1_700_000_000_000, origem: 'manual', ...extra });

test('parseBase: separador ; , valores em formato brasileiro e acentos', () => {
  const { itens, erros } = Core.parseBase(BASE_CSV);
  assert.deepEqual(erros, []);
  assert.equal(itens.length, 4);
  assert.deepEqual(itens[0], { codigo: '1001', descricao: 'Arroz 5kg', saldo: 10, custo: 20, local: 'Corredor A' });
  assert.equal(itens[3].custo, 18.7);
});

test('parseBase: separador vírgula, BOM, aspas e cabeçalho com acento', () => {
  const csv = '﻿EAN,Descrição,Quantidade,Valor unitário,Endereço\n' +
    '7891000100103,"Arroz, tipo 1",12,"R$ 1.234,50",A-01\n';
  const { itens, erros } = Core.parseBase(csv);
  assert.deepEqual(erros, []);
  assert.equal(itens[0].codigo, '7891000100103');
  assert.equal(itens[0].descricao, 'Arroz, tipo 1');
  assert.equal(itens[0].saldo, 12);
  assert.equal(itens[0].custo, 1234.5);
  assert.equal(itens[0].local, 'A-01');
});

test('parseBase: exige colunas codigo e saldo', () => {
  const { itens, erros } = Core.parseBase('produto;preco\nArroz;10');
  assert.equal(itens.length, 0);
  assert.match(erros[0], /codigo, saldo/);
});

test('parseBase: linha com saldo inválido é rejeitada; duplicado gera aviso', () => {
  const csv = 'codigo;saldo\n1;10\n2;abc\n1;5\n';
  const { itens, erros, avisos } = Core.parseBase(csv);
  assert.equal(itens.length, 1);
  assert.equal(itens[0].saldo, 10);
  assert.match(erros[0], /Linha 3: saldo inválido/);
  assert.match(avisos[0], /duplicado/);
});

test('conciliar: classifica OK, FALTA, SOBRA, NAO_CONTADO e NAO_CADASTRADO', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const leituras = [
    leitura('1001', 10),   // OK
    leitura('1002', 3),    // FALTA (-2)
    leitura('1003', 6),    // SOBRA (+2)
    // 1004 não lido -> NAO_CONTADO
    leitura('9999', 2),    // NAO_CADASTRADO
  ];
  const linhas = Core.conciliar(itens, leituras);
  const st = Object.fromEntries(linhas.map(l => [l.codigo, l.status]));
  assert.equal(st['1001'], 'OK');
  assert.equal(st['1002'], 'FALTA');
  assert.equal(st['1003'], 'SOBRA');
  assert.equal(st['1004'], 'NAO_CONTADO');
  assert.equal(st['9999'], 'NAO_CADASTRADO');
  assert.equal(linhas.find(l => l.codigo === '1002').diferenca, -2);
  assert.equal(linhas.find(l => l.codigo === '1003').valorDiferenca, 12);
});

test('conciliar: soma várias leituras do mesmo código', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const leituras = [leitura('1001', 4), leitura('1001', 3, { operador: 'Bruno' }), leitura('1001', 3)];
  const l = Core.conciliar(itens, leituras).find(x => x.codigo === '1001');
  assert.equal(l.contado, 10);
  assert.equal(l.status, 'OK');
});

test('calcularKpis: acuracia, faltas/sobras e valores', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const leituras = [leitura('1001', 10), leitura('1002', 3), leitura('1003', 6), leitura('9999', 2)];
  const linhas = Core.conciliar(itens, leituras);
  const k = Core.calcularKpis(linhas, leituras);

  // Base 4 itens + 1 não cadastrado = 5 considerados; conformes = 1 (1001)
  assert.equal(k.totalItens, 4);
  assert.equal(k.itensOk, 1);
  assert.equal(k.naoCadastrados, 1);
  assert.equal(k.naoContados, 1);
  assert.ok(Math.abs(k.acuraciaItens - 20) < 1e-9);

  // Saldo 22 na base; faltas: 2 (1002) + 3 (1004 não contado); sobras: 2 (1003) + 2 (9999)
  assert.equal(k.saldoTotal, 22);
  assert.equal(k.faltas, 5);
  assert.equal(k.sobras, 4);
  assert.ok(Math.abs(k.acuraciaQtd - (1 - 9 / 22) * 100) < 1e-9);

  // Invariante: diferença líquida = soma das diferenças por item
  const somaDif = linhas.reduce((a, l) => a + l.diferenca, 0);
  assert.equal(k.diferencaLiquida, somaDif);
  assert.equal(k.totalLeituras, 4);
  assert.equal(k.codigosLidos, 4);
});

test('calcularKpis: lista de operadores e por local', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const leituras = [
    leitura('1001', 10, { operador: 'Ana' }),
    leitura('1002', 5, { operador: 'Bruno', ts: 1_700_000_600_000 }),
  ];
  const k = Core.calcularKpis(Core.conciliar(itens, leituras), leituras);
  assert.equal(k.operadores.length, 2);
  assert.equal(k.operadores[0].operador, 'Ana');
  const corA = k.porLocal.find(g => g.local === 'Corredor A');
  assert.equal(corA.itens, 2);
  assert.equal(corA.ok, 2);
  assert.equal(corA.acuracia, 100);
  assert.equal(k.duracaoMin, 10);
});

test('calcularKpis: sem leituras não quebra e acuracia cai para 0', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const k = Core.calcularKpis(Core.conciliar(itens, []), []);
  assert.equal(k.naoContados, 4);
  assert.equal(k.acuraciaItens, 0);
  assert.equal(k.leiturasPorHora, 0);
});

test('renderRelatorioHTML: escapa conteúdo vindo da base', () => {
  const csv = 'codigo;descricao;saldo\n1;<img src=x onerror=alert(1)>;2\n';
  const { itens } = Core.parseBase(csv);
  const leituras = [leitura('1', 1)];
  const linhas = Core.conciliar(itens, leituras);
  const html = Core.renderRelatorioHTML({
    nomeInventario: 'Teste <b>',
    geradoEm: new Date(1_700_000_000_000),
    kpis: Core.calcularKpis(linhas, leituras),
    linhas,
  });
  assert.ok(!html.includes('<img src=x'));
  assert.ok(html.includes('&lt;img src=x'));
  assert.ok(html.includes('Teste &lt;b&gt;'));
  assert.ok(html.startsWith('<!doctype html>'));
  assert.ok(html.includes('Acuracidade (itens)'));
});

test('conciliacaoCSV: separador ponto e vírgula, decimal com vírgula', () => {
  const { itens } = Core.parseBase(BASE_CSV);
  const linhas = Core.conciliar(itens, [leitura('1002', 3)]);
  const csv = Core.conciliacaoCSV(linhas);
  const primeiraLinhaDados = csv.split('\r\n')[2];
  assert.ok(primeiraLinhaDados.startsWith('1002;Feijão 1kg;Corredor A;Falta;5;3;-2;7,5;'));
});

test('leiturasCSV -> parseLeituras: ida e volta preserva as leituras', () => {
  const origem = [
    { id: 1, codigo: '1001', qtd: 2, operador: 'Ana; Lima', ts: 1_700_000_000_123, origem: 'camera' },
    { id: 2, codigo: '9999', qtd: 1.5, operador: 'Bruno', ts: 1_700_000_060_000, origem: 'manual' },
  ];
  const { leituras, erros } = Core.parseLeituras(Core.leiturasCSV(origem));
  assert.deepEqual(erros, []);
  assert.equal(leituras.length, 2);
  assert.equal(leituras[0].operador, 'Ana; Lima');
  assert.equal(leituras[0].ts, 1_700_000_000_123);
  assert.equal(leituras[1].qtd, 1.5);
  // Chave de deduplicação estável entre importações
  assert.equal(Core.chaveLeitura(leituras[0]), Core.chaveLeitura({ ...origem[0] }));
});

test('parseLeituras: rejeita CSV que não é de leituras', () => {
  const { leituras, erros } = Core.parseLeituras(BASE_CSV);
  assert.equal(leituras.length, 0);
  assert.match(erros[0], /não reconhecido/);
});

test('parseLeituras: quantidade e data inválidas viram erro de linha', () => {
  const csv = 'id;ts_iso;operador;codigo;quantidade;origem\n1;2026-01-01T10:00:00.000Z;Ana;1;0;manual\n2;lixo;Ana;1;1;manual\n';
  const { leituras, erros } = Core.parseLeituras(csv);
  assert.equal(leituras.length, 0);
  assert.match(erros[0], /quantidade inválida/);
  assert.match(erros[1], /data inválida/);
});
