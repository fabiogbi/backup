/*
 * Núcleo do inventário (sem DOM): leitura da base CSV, conciliação
 * contagem x sistema, KPIs e geração do relatório HTML.
 * Funciona no navegador (window.Core) e no Node (module.exports) para testes.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Core = api;
})(typeof self !== 'undefined' ? self : globalThis, function () {
  'use strict';

  // Nomes de coluna aceitos (sem acento, minúsculos, espaços viram "_").
  const ALIAS = {
    codigo: ['codigo', 'ean', 'sku', 'cod', 'codigo_barras', 'barcode', 'gtin'],
    descricao: ['descricao', 'produto', 'nome', 'item', 'descr'],
    saldo: ['saldo', 'quantidade', 'qtd', 'qtde', 'estoque', 'saldo_sistema'],
    custo: ['custo', 'custo_unitario', 'valor_unitario', 'preco_custo', 'custo_medio'],
    local: ['local', 'endereco', 'localizacao', 'setor', 'area', 'deposito'],
  };

  const STATUS = {
    OK: 'OK',
    FALTA: 'FALTA',
    SOBRA: 'SOBRA',
    NAO_CONTADO: 'NAO_CONTADO',
    NAO_CADASTRADO: 'NAO_CADASTRADO',
  };

  const STATUS_LABEL = {
    OK: 'Conforme',
    FALTA: 'Falta',
    SOBRA: 'Sobra',
    NAO_CONTADO: 'Não contado',
    NAO_CADASTRADO: 'Não cadastrado',
  };

  const NF = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
  const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  const fmtNum = n => NF.format(Number.isFinite(n) ? n : 0);
  const fmtBRL = n => BRL.format(Number.isFinite(n) ? n : 0);
  const fmtPct = n => `${(Number.isFinite(n) ? n : 0).toFixed(2).replace('.', ',')}%`;
  const r2 = n => Math.round(n * 100) / 100;

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  const normCabecalho = s => String(s ?? '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .trim().toLowerCase().replace(/[\s-]+/g, '_');

  /* ---------- Leitura de CSV ---------- */

  function detectarSeparador(linha) {
    const cont = { ';': 0, ',': 0, '\t': 0 };
    let aspas = false;
    for (const c of linha) {
      if (c === '"') aspas = !aspas;
      else if (!aspas && c in cont) cont[c]++;
    }
    return Object.keys(cont).reduce((a, b) => (cont[b] > cont[a] ? b : a), ';');
  }

  function parseDelimitado(texto, sep) {
    const linhas = [];
    let linha = [];
    let campo = '';
    let aspas = false;
    for (let i = 0; i < texto.length; i++) {
      const c = texto[i];
      if (aspas) {
        if (c === '"') {
          if (texto[i + 1] === '"') { campo += '"'; i++; } else aspas = false;
        } else campo += c;
      } else if (c === '"') {
        aspas = true;
      } else if (c === sep) {
        linha.push(campo); campo = '';
      } else if (c === '\n' || c === '\r') {
        if (c === '\r' && texto[i + 1] === '\n') i++;
        linha.push(campo); linhas.push(linha);
        linha = []; campo = '';
      } else {
        campo += c;
      }
    }
    if (campo !== '' || linha.length) { linha.push(campo); linhas.push(linha); }
    return linhas.filter(l => l.some(c => String(c).trim() !== ''));
  }

  // Aceita "1.234,56", "1234.56", "R$ 10,00", "1234".
  function parseNumero(valor) {
    if (valor === null || valor === undefined) return null;
    let s = String(valor).replace(/R\$/gi, '').replace(/\s/g, '');
    if (s === '') return null;
    if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
    else if ((s.match(/\./g) || []).length > 1) s = s.replace(/\./g, '');
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }

  /**
   * Converte o texto de um CSV na base de itens.
   * @returns {{itens: Array, erros: string[], avisos: string[]}}
   */
  function parseBase(texto) {
    const limpo = String(texto ?? '').replace(/^﻿/, '');
    const primeira = limpo.split(/\r?\n/)[0] || '';
    const linhas = parseDelimitado(limpo, detectarSeparador(primeira));
    const erros = [];
    const avisos = [];

    if (!linhas.length) return { itens: [], erros: ['Arquivo vazio.'], avisos };

    const cab = linhas[0].map(normCabecalho);
    const idx = {};
    for (const campo of Object.keys(ALIAS)) {
      idx[campo] = cab.findIndex(c => ALIAS[campo].includes(c));
    }

    const faltando = ['codigo', 'saldo'].filter(c => idx[c] < 0);
    if (faltando.length) {
      return {
        itens: [],
        erros: [`Colunas obrigatórias não encontradas: ${faltando.join(', ')}. Cabeçalho lido: ${cab.join(' | ')}`],
        avisos,
      };
    }

    const mapa = new Map();
    for (let r = 1; r < linhas.length; r++) {
      const l = linhas[r];
      const num = r + 1;
      const get = campo => (idx[campo] >= 0 ? String(l[idx[campo]] ?? '') : '');

      const codigo = get('codigo').trim().replace(/\s+/g, '');
      if (!codigo) { erros.push(`Linha ${num}: código vazio.`); continue; }

      const rawSaldo = get('saldo').trim();
      const saldo = rawSaldo === '' ? 0 : parseNumero(rawSaldo);
      if (saldo === null) { erros.push(`Linha ${num}: saldo inválido ("${rawSaldo}").`); continue; }

      const rawCusto = get('custo').trim();
      let custo = 0;
      if (rawCusto !== '') {
        const c = parseNumero(rawCusto);
        if (c === null) avisos.push(`Linha ${num}: custo inválido ("${rawCusto}"), usado 0.`);
        else custo = c;
      }

      if (mapa.has(codigo)) {
        avisos.push(`Linha ${num}: código ${codigo} duplicado; mantida a primeira ocorrência.`);
        continue;
      }

      mapa.set(codigo, {
        codigo,
        descricao: get('descricao').trim() || '(sem descrição)',
        saldo,
        custo,
        local: get('local').trim() || 'Sem local',
      });
    }

    return { itens: [...mapa.values()], erros, avisos };
  }

  /* ---------- Conciliação ---------- */

  function somarLeituras(leituras) {
    const m = new Map();
    for (const l of leituras) m.set(l.codigo, (m.get(l.codigo) || 0) + l.qtd);
    return m;
  }

  /**
   * Cruza a base com as leituras. Retorna uma linha por item da base
   * e uma linha por código lido que não existe na base.
   */
  function conciliar(itens, leituras) {
    const contado = somarLeituras(leituras.filter(l => l.qtd > 0));
    const linhas = [];
    const codigosBase = new Set();

    for (const it of itens) {
      codigosBase.add(it.codigo);
      const qtd = contado.get(it.codigo) || 0;
      const diferenca = qtd - it.saldo;
      let status;
      if (diferenca === 0) status = STATUS.OK;
      else if (qtd === 0) status = STATUS.NAO_CONTADO;
      else status = diferenca < 0 ? STATUS.FALTA : STATUS.SOBRA;

      linhas.push({
        codigo: it.codigo,
        descricao: it.descricao,
        local: it.local,
        saldo: it.saldo,
        contado: qtd,
        diferenca,
        custo: it.custo,
        valorSistema: r2(it.saldo * it.custo),
        valorContado: r2(qtd * it.custo),
        valorDiferenca: r2(diferenca * it.custo),
        status,
        naoCadastrado: false,
      });
    }

    for (const [codigo, qtd] of contado) {
      if (codigosBase.has(codigo)) continue;
      linhas.push({
        codigo,
        descricao: '(não cadastrado)',
        local: 'Não cadastrado',
        saldo: 0,
        contado: qtd,
        diferenca: qtd,
        custo: 0,
        valorSistema: 0,
        valorContado: 0,
        valorDiferenca: 0,
        status: STATUS.NAO_CADASTRADO,
        naoCadastrado: true,
      });
    }
    return linhas;
  }

  /* ---------- KPIs ---------- */

  function calcularKpis(linhas, leituras) {
    const soma = (arr, f) => arr.reduce((a, l) => a + f(l), 0);
    const base = linhas.filter(l => !l.naoCadastrado);
    const naoCad = linhas.filter(l => l.naoCadastrado);

    const totalItens = base.length;
    const itensOk = base.filter(l => l.status === STATUS.OK).length;
    const totalConsiderado = totalItens + naoCad.length;

    const faltas = soma(linhas, l => (l.diferenca < 0 ? -l.diferenca : 0));
    const sobras = soma(linhas, l => (l.diferenca > 0 ? l.diferenca : 0));
    const saldoTotal = soma(base, l => l.saldo);
    const contadoTotal = soma(linhas, l => l.contado);
    const variacao = faltas + sobras;
    const acuraciaQtd = saldoTotal > 0
      ? Math.max(0, 1 - variacao / saldoTotal) * 100
      : (variacao === 0 ? 100 : 0);

    const valorFaltas = soma(linhas, l => (l.valorDiferenca < 0 ? -l.valorDiferenca : 0));
    const valorSobras = soma(linhas, l => (l.valorDiferenca > 0 ? l.valorDiferenca : 0));

    // Tempo e produtividade
    let inicio = null;
    let fim = null;
    for (const l of leituras) {
      if (!l.ts) continue;
      if (inicio === null || l.ts < inicio) inicio = l.ts;
      if (fim === null || l.ts > fim) fim = l.ts;
    }
    const duracaoMin = inicio !== null && fim !== null ? (fim - inicio) / 60000 : 0;
    const leiturasPorHora = duracaoMin > 0 ? leituras.length / (duracaoMin / 60) : 0;

    // Por operador
    const opMap = new Map();
    for (const l of leituras) {
      const op = l.operador || '(sem operador)';
      if (!opMap.has(op)) opMap.set(op, { operador: op, leituras: 0, unidades: 0, codigos: new Set() });
      const o = opMap.get(op);
      o.leituras++;
      o.unidades += l.qtd;
      o.codigos.add(l.codigo);
    }
    const operadores = [...opMap.values()]
      .map(o => ({ operador: o.operador, leituras: o.leituras, unidades: o.unidades, codigos: o.codigos.size }))
      .sort((a, b) => b.leituras - a.leituras);

    // Por local
    const locMap = new Map();
    for (const l of linhas) {
      const k = l.local;
      if (!locMap.has(k)) {
        locMap.set(k, { local: k, itens: 0, ok: 0, faltas: 0, sobras: 0, valorDiferenca: 0, naoContados: 0 });
      }
      const g = locMap.get(k);
      g.itens++;
      if (l.status === STATUS.OK) g.ok++;
      if (l.status === STATUS.NAO_CONTADO) g.naoContados++;
      if (l.diferenca < 0) g.faltas += -l.diferenca;
      if (l.diferenca > 0) g.sobras += l.diferenca;
      g.valorDiferenca = r2(g.valorDiferenca + l.valorDiferenca);
    }
    const porLocal = [...locMap.values()]
      .map(g => ({ ...g, acuracia: g.itens ? (g.ok / g.itens) * 100 : 0 }))
      .sort((a, b) => a.acuracia - b.acuracia || a.local.localeCompare(b.local, 'pt-BR'));

    // Top divergências por impacto financeiro (ou quantidade, se não há custo)
    const top = linhas
      .filter(l => l.status !== STATUS.OK)
      .sort((a, b) => Math.abs(b.valorDiferenca) - Math.abs(a.valorDiferenca)
        || Math.abs(b.diferenca) - Math.abs(a.diferenca))
      .slice(0, 10);

    const codigosLidos = somarLeituras(leituras).size;

    return {
      totalItens,
      itensOk,
      itensDivergentes: totalItens - itensOk,
      naoContados: base.filter(l => l.status === STATUS.NAO_CONTADO).length,
      naoCadastrados: naoCad.length,
      acuraciaItens: totalConsiderado ? (itensOk / totalConsiderado) * 100 : 0,
      acuraciaQtd,
      saldoTotal,
      contadoTotal,
      diferencaLiquida: contadoTotal - saldoTotal,
      faltas,
      sobras,
      valorSistema: r2(soma(linhas, l => l.valorSistema)),
      valorContado: r2(soma(linhas, l => l.valorContado)),
      valorDiferencaLiquida: r2(soma(linhas, l => l.valorDiferenca)),
      valorFaltas: r2(valorFaltas),
      valorSobras: r2(valorSobras),
      totalLeituras: leituras.length,
      codigosLidos,
      inicio,
      fim,
      duracaoMin,
      leiturasPorHora,
      operadores,
      porLocal,
      top,
    };
  }

  /* ---------- Exportações ---------- */

  const csvCel = v => {
    const s = typeof v === 'number' ? String(v).replace('.', ',') : String(v ?? '');
    return /[;"\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  function conciliacaoCSV(linhas) {
    const cab = ['codigo', 'descricao', 'local', 'status', 'saldo_sistema', 'contado', 'diferenca', 'custo', 'valor_diferenca'];
    const corpo = linhas.map(l => [
      l.codigo, l.descricao, l.local, STATUS_LABEL[l.status], l.saldo, l.contado,
      l.diferenca, l.custo, l.valorDiferenca,
    ].map(csvCel).join(';'));
    return '﻿' + [cab.join(';'), ...corpo].join('\r\n');
  }

  function leiturasCSV(leituras) {
    const cab = ['id', 'ts_iso', 'data_hora', 'operador', 'codigo', 'quantidade', 'origem'];
    const corpo = leituras.map(l => [
      l.id, new Date(l.ts).toISOString(), new Date(l.ts).toLocaleString('pt-BR'),
      l.operador, l.codigo, l.qtd, l.origem,
    ].map(csvCel).join(';'));
    return '﻿' + [cab.join(';'), ...corpo].join('\r\n');
  }

  /**
   * Lê um CSV de leituras exportado por outro aparelho.
   * @returns {{leituras: Array, erros: string[]}}
   */
  function parseLeituras(texto) {
    const limpo = String(texto ?? '').replace(/^﻿/, '');
    const linhas = parseDelimitado(limpo, detectarSeparador(limpo.split(/\r?\n/)[0] || ''));
    if (!linhas.length) return { leituras: [], erros: ['Arquivo vazio.'] };

    const cab = linhas[0].map(normCabecalho);
    const iCod = cab.indexOf('codigo');
    const iQtd = cab.indexOf('quantidade');
    const iTs = cab.indexOf('ts_iso');
    const iOp = cab.indexOf('operador');
    const iOrig = cab.indexOf('origem');
    if (iCod < 0 || iQtd < 0 || iTs < 0) {
      return { leituras: [], erros: ['Arquivo não reconhecido. Use o CSV "Exportar leituras" gerado pelo app (colunas: codigo, quantidade, ts_iso).'] };
    }

    const leituras = [];
    const erros = [];
    for (let r = 1; r < linhas.length; r++) {
      const l = linhas[r];
      const num = r + 1;
      const codigo = String(l[iCod] ?? '').trim();
      const qtd = parseNumero(l[iQtd]);
      const ts = Date.parse(String(l[iTs] ?? '').trim());
      if (!codigo) { erros.push(`Linha ${num}: código vazio.`); continue; }
      if (qtd === null || qtd <= 0) { erros.push(`Linha ${num}: quantidade inválida.`); continue; }
      if (!Number.isFinite(ts)) { erros.push(`Linha ${num}: data inválida.`); continue; }
      leituras.push({
        codigo,
        qtd,
        operador: iOp >= 0 ? String(l[iOp] ?? '').trim() : '',
        ts,
        origem: iOrig >= 0 ? String(l[iOrig] ?? '').trim() || 'importado' : 'importado',
      });
    }
    return { leituras, erros };
  }

  // Assinatura para evitar importar a mesma leitura duas vezes.
  const chaveLeitura = l => `${l.ts}|${l.codigo}|${l.operador || ''}|${l.qtd}|${l.origem || ''}`;

  /* ---------- Relatório HTML ---------- */

  const CSS_RELATORIO = `
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2733;background:#f4f6f9}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
header{background:#1f4e79;color:#fff;padding:24px 16px}
header h1{margin:0 0 4px;font-size:22px}
header p{margin:0;opacity:.85}
h2{font-size:17px;margin:28px 0 10px;color:#1f4e79}
.meta{display:flex;flex-wrap:wrap;gap:8px 20px;margin:0 0 8px;color:#4a5866;font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.card{background:#fff;border:1px solid #dde3ea;border-radius:10px;padding:12px 14px}
.card .k{font-size:12px;color:#5b6876;text-transform:uppercase;letter-spacing:.03em}
.card .v{font-size:22px;font-weight:700;margin-top:4px}
.card .s{font-size:12px;color:#5b6876;margin-top:2px}
.card.destaque{border-color:#1f4e79}
.neg{color:#b42318}.pos{color:#1d7a3a}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dde3ea;border-radius:10px;overflow:hidden}
th,td{padding:7px 9px;border-bottom:1px solid #eef1f5;text-align:left;vertical-align:middle}
th{background:#eef3f8;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#3d4b5c}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.wrapt{overflow-x:auto}
.bar{background:#e4e9ef;border-radius:6px;height:10px;min-width:120px;overflow:hidden}
.bar span{display:block;height:100%;background:#1f7a8c}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.s-OK{background:#e3f5ea;color:#1d7a3a}
.s-FALTA{background:#fde8e6;color:#b42318}
.s-SOBRA{background:#fff3d6;color:#8a5a00}
.s-NAO_CONTADO{background:#eceff3;color:#3d4b5c}
.s-NAO_CADASTRADO{background:#efe6fb;color:#5b2d8e}
details{margin-top:12px}summary{cursor:pointer;font-weight:600;color:#1f4e79;margin-bottom:8px}
.vazio{color:#5b6876;padding:12px;background:#fff;border:1px dashed #cdd5df;border-radius:10px}
footer{margin-top:32px;color:#5b6876;font-size:12px}
@media print{body{background:#fff}header{-webkit-print-color-adjust:exact;print-color-adjust:exact}details{display:block}details>summary{display:none}.card,table{break-inside:avoid}}
`;

  function tabela(cabecalhos, linhasHtml) {
    if (!linhasHtml.length) return '<p class="vazio">Nenhum registro.</p>';
    const th = cabecalhos.map(([t, num]) => `<th${num ? ' class="n"' : ''}>${t}</th>`).join('');
    return `<div class="wrapt"><table><thead><tr>${th}</tr></thead><tbody>${linhasHtml.join('')}</tbody></table></div>`;
  }

  const badge = st => `<span class="badge s-${st}">${esc(STATUS_LABEL[st])}</span>`;
  const sinal = (n, fmt) => `<span class="${n < 0 ? 'neg' : n > 0 ? 'pos' : ''}">${fmt(n)}</span>`;

  function linhaItemHtml(l) {
    return `<tr>
      <td>${esc(l.codigo)}</td><td>${esc(l.descricao)}</td><td>${esc(l.local)}</td>
      <td class="n">${fmtNum(l.saldo)}</td><td class="n">${fmtNum(l.contado)}</td>
      <td class="n">${sinal(l.diferenca, fmtNum)}</td>
      <td class="n">${sinal(l.valorDiferenca, fmtBRL)}</td>
      <td>${badge(l.status)}</td></tr>`;
  }

  function cartao(rotulo, valor, sub = '', destaque = false) {
    return `<div class="card${destaque ? ' destaque' : ''}"><div class="k">${esc(rotulo)}</div>
      <div class="v">${valor}</div>${sub ? `<div class="s">${esc(sub)}</div>` : ''}</div>`;
  }

  function renderRelatorioHTML(ctx) {
    const k = ctx.kpis;
    const linhas = ctx.linhas || [];
    const geradoEm = (ctx.geradoEm instanceof Date ? ctx.geradoEm : new Date()).toLocaleString('pt-BR');
    const nome = ctx.nomeInventario || 'Inventário';
    const periodo = k.inicio && k.fim
      ? `${new Date(k.inicio).toLocaleString('pt-BR')} até ${new Date(k.fim).toLocaleString('pt-BR')}`
      : 'sem leituras';

    const cards = [
      cartao('Acuracidade (itens)', fmtPct(k.acuraciaItens), `${k.itensOk} de ${k.totalItens + k.naoCadastrados} itens conformes`, true),
      cartao('Acuracidade (quantidade)', fmtPct(k.acuraciaQtd), '1 − (faltas + sobras) ÷ saldo'),
      cartao('Itens divergentes', fmtNum(k.itensDivergentes), `de ${fmtNum(k.totalItens)} na base`),
      cartao('Não contados', fmtNum(k.naoContados), 'itens da base sem leitura'),
      cartao('Não cadastrados', fmtNum(k.naoCadastrados), 'códigos lidos fora da base'),
      cartao('Faltas (un.)', sinal(-k.faltas, fmtNum), ''),
      cartao('Sobras (un.)', sinal(k.sobras, fmtNum), ''),
      cartao('Diferença líquida (un.)', sinal(k.diferencaLiquida, fmtNum), `sistema ${fmtNum(k.saldoTotal)} · contado ${fmtNum(k.contadoTotal)}`),
      cartao('Valor do sistema', fmtBRL(k.valorSistema), ''),
      cartao('Valor contado', fmtBRL(k.valorContado), ''),
      cartao('Diferença financeira', sinal(k.valorDiferencaLiquida, fmtBRL), ''),
      cartao('Valor em falta', sinal(-k.valorFaltas, fmtBRL), ''),
      cartao('Valor em sobra', sinal(k.valorSobras, fmtBRL), ''),
      cartao('Leituras', fmtNum(k.totalLeituras), `${fmtNum(k.codigosLidos)} códigos distintos`),
      cartao('Tempo de contagem', fmtNum(k.duracaoMin) + ' min',
        k.duracaoMin >= 1 ? `${fmtNum(k.leiturasPorHora)} leituras/hora` : 'produtividade só com ≥ 1 min'),
      cartao('Operadores', fmtNum(k.operadores.length), ''),
    ].join('');

    const locais = tabela(
      [['Local'], ['Itens', 1], ['Conformes', 1], ['Acuracidade', 1], ['Faltas (un.)', 1], ['Sobras (un.)', 1], ['Não contados', 1], ['Dif. R$', 1], ['Gráfico']],
      k.porLocal.map(g => `<tr><td>${esc(g.local)}</td><td class="n">${fmtNum(g.itens)}</td>
        <td class="n">${fmtNum(g.ok)}</td><td class="n">${fmtPct(g.acuracia)}</td>
        <td class="n">${fmtNum(g.faltas)}</td><td class="n">${fmtNum(g.sobras)}</td>
        <td class="n">${fmtNum(g.naoContados)}</td><td class="n">${sinal(g.valorDiferenca, fmtBRL)}</td>
        <td><div class="bar"><span style="width:${Math.min(100, g.acuracia).toFixed(1)}%"></span></div></td></tr>`));

    const ops = tabela(
      [['Operador'], ['Leituras', 1], ['Unidades', 1], ['Códigos distintos', 1]],
      k.operadores.map(o => `<tr><td>${esc(o.operador)}</td><td class="n">${fmtNum(o.leituras)}</td>
        <td class="n">${fmtNum(o.unidades)}</td><td class="n">${fmtNum(o.codigos)}</td></tr>`));

    const top = tabela(
      [['Código'], ['Descrição'], ['Local'], ['Sistema', 1], ['Contado', 1], ['Dif.', 1], ['Dif. R$', 1], ['Status']],
      k.top.map(l => `<tr><td>${esc(l.codigo)}</td><td>${esc(l.descricao)}</td><td>${esc(l.local)}</td>
        <td class="n">${fmtNum(l.saldo)}</td><td class="n">${fmtNum(l.contado)}</td>
        <td class="n">${sinal(l.diferenca, fmtNum)}</td><td class="n">${sinal(l.valorDiferenca, fmtBRL)}</td>
        <td>${badge(l.status)}</td></tr>`));

    const cabItem = [['Código'], ['Descrição'], ['Local'], ['Sistema', 1], ['Contado', 1], ['Dif.', 1], ['Dif. R$', 1], ['Status']];
    const divergencias = linhas
      .filter(l => l.status !== STATUS.OK)
      .sort((a, b) => a.local.localeCompare(b.local, 'pt-BR') || a.codigo.localeCompare(b.codigo));
    const divHtml = tabela(cabItem, divergencias.map(linhaItemHtml));
    const todosHtml = tabela(cabItem, [...linhas].sort((a, b) => a.local.localeCompare(b.local, 'pt-BR') || a.codigo.localeCompare(b.codigo)).map(linhaItemHtml));

    return `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório de inventário – ${esc(nome)}</title>
<style>${CSS_RELATORIO}</style></head>
<body>
<header><div class="wrap" style="padding:0 0 0"><h1>Relatório de inventário cego</h1>
<p>${esc(nome)}</p></div></header>
<main class="wrap">
  <div class="meta">
    <span>Gerado em: ${esc(geradoEm)}</span>
    <span>Período de contagem: ${esc(periodo)}</span>
    <span>Base: ${esc(ctx.baseArquivo || '—')}${ctx.baseData ? ` (importada em ${esc(new Date(ctx.baseData).toLocaleString('pt-BR'))})` : ''}</span>
  </div>

  <h2>Indicadores (KPIs)</h2>
  <section class="cards">${cards}</section>

  <h2>Acuracidade por local</h2>
  ${locais}

  <h2>Desempenho por operador</h2>
  ${ops}

  <h2>Top 10 divergências (impacto financeiro)</h2>
  ${top}

  <h2>Todas as divergências (${fmtNum(divergencias.length)})</h2>
  ${divHtml}

  <details><summary>Inventário completo (${fmtNum(linhas.length)} linhas)</summary>
  ${todosHtml}</details>

  <footer>Regra de acuracidade: itens conformes ÷ (itens da base + códigos não cadastrados). Diferença = contado − saldo do sistema.
  Valores usam o custo unitário da base; itens sem custo entram com R$ 0,00.</footer>
</main>
</body></html>`;
  }

  return {
    ALIAS, STATUS, STATUS_LABEL,
    detectarSeparador, parseDelimitado, parseNumero, parseBase,
    somarLeituras, conciliar, calcularKpis,
    conciliacaoCSV, leiturasCSV, parseLeituras, chaveLeitura, renderRelatorioHTML,
    fmtNum, fmtBRL, fmtPct, esc,
  };
});
