/*
 * Controlador da interface: telas, contagem cega, importação da base,
 * relatório. Não exibe o saldo do sistema durante a contagem.
 */
(function () {
  'use strict';

  const $ = id => document.getElementById(id);
  const E = Core.esc;

  const S = {
    itens: new Map(),      // base carregada: codigo -> item
    leituras: [],          // todas as leituras (ordenadas por id)
    nomeInventario: '',
    operador: '',
    qtdPadrao: 1,
    base: null,            // { arquivo, data, total }
    ultimo: { cod: '', ts: 0 },
  };

  /* ---------- Feedback sonoro/tátil ---------- */

  let audio = null;
  function bip(freq, ms, vibra) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const o = audio.createOscillator();
      const g = audio.createGain();
      o.frequency.value = freq;
      g.gain.value = 0.15;
      o.connect(g); g.connect(audio.destination);
      o.start(); o.stop(audio.currentTime + ms / 1000);
    } catch (e) { /* som indisponível */ }
    if (vibra && navigator.vibrate) navigator.vibrate(vibra);
  }

  let toastTimer = null;
  function toast(msg, tipo) {
    const t = $('toast');
    t.textContent = msg;
    t.className = 'toast' + (tipo ? ' ' + tipo : '');
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
  }

  /* ---------- Navegação ---------- */

  function mostrarTela(nome) {
    if (nome !== 'contar') Scanner.parar();
    if (nome !== 'contar') pararCamera();
    document.querySelectorAll('.tela').forEach(s => { s.hidden = s.id !== 'tela-' + nome; });
    document.querySelectorAll('.nav button').forEach(b => {
      const ativo = b.dataset.tela === nome;
      b.classList.toggle('ativo', ativo);
      if (ativo) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    });
    if (nome === 'relatorio') renderKpisPrevia();
    if (nome === 'config') renderConfig();
  }

  /* ---------- Persistência de configuração ---------- */

  async function salvarSessao() {
    await DB.setConfig('sessao', {
      nomeInventario: S.nomeInventario,
      operador: S.operador,
      qtdPadrao: S.qtdPadrao,
    });
  }

  /* ---------- Base ---------- */

  // Lê o arquivo tentando UTF-8 e, se falhar, Windows-1252 (CSV do Excel brasileiro).
  function lerArquivo(arquivo) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => {
        const buf = r.result;
        try {
          resolve(new TextDecoder('utf-8', { fatal: true }).decode(buf));
        } catch (e) {
          resolve(new TextDecoder('windows-1252').decode(buf));
        }
      };
      r.onerror = () => reject(r.error);
      r.readAsArrayBuffer(arquivo);
    });
  }

  async function importarBase(arquivo) {
    const texto = await lerArquivo(arquivo);
    const { itens, erros, avisos } = Core.parseBase(texto);

    const boxErros = $('erros-base');
    const msgs = [...erros.map(e => ({ t: 'erro', m: e })), ...avisos.map(a => ({ t: 'aviso', m: a }))];
    boxErros.innerHTML = msgs.slice(0, 30)
      .map(x => `<div class="${x.t}">${E(x.m)}</div>`).join('') +
      (msgs.length > 30 ? `<div class="aviso">… e mais ${msgs.length - 30} mensagens.</div>` : '');

    if (!itens.length) {
      toast('Base não importada. Veja os erros abaixo.', 'erro');
      return;
    }

    await DB.salvarItens(itens);
    S.itens = new Map(itens.map(i => [i.codigo, i]));
    S.base = { arquivo: arquivo.name, data: Date.now(), total: itens.length };
    await DB.setConfig('base', S.base);
    renderConfig();
    toast(`Base importada: ${itens.length} itens.`, 'ok');
  }

  async function apagarBase() {
    if (!confirm('Apagar a base de itens? As leituras são mantidas.')) return;
    await DB.apagarItens();
    await DB.setConfig('base', null);
    S.itens = new Map();
    S.base = null;
    $('erros-base').innerHTML = '';
    renderConfig();
    toast('Base apagada.');
  }

  /* ---------- Contagem ---------- */

  async function registrarCodigo(bruto, daCamera) {
    const codigo = String(bruto || '').trim().replace(/\s+/g, '');
    if (!codigo) return;

    if (!S.operador) {
      bip(300, 250, 200);
      toast('Informe o operador antes de contar.', 'erro');
      $('operador').focus();
      return;
    }

    const agora = Date.now();
    // A câmera repete o mesmo código a cada frame: ignora repetições rápidas.
    if (daCamera && codigo === S.ultimo.cod && agora - S.ultimo.ts < 1500) return;
    S.ultimo = { cod: codigo, ts: agora };

    const qtd = S.qtdPadrao > 0 ? S.qtdPadrao : 1;
    const leitura = { codigo, qtd, operador: S.operador, ts: agora, origem: daCamera ? 'camera' : 'manual' };
    leitura.id = await DB.addLeitura(leitura);
    S.leituras.push(leitura);

    const naBase = S.itens.has(codigo);
    if (naBase) bip(1400, 80, 40);
    else bip(260, 300, [120, 80, 120]);

    mostrarUltima(codigo, qtd, naBase);
    renderLeituras();
  }

  // Mostra a descrição e o total registrado; nunca o saldo do sistema.
  function mostrarUltima(codigo, qtd, naBase) {
    const box = $('ultima');
    const item = S.itens.get(codigo);
    const totalCodigo = S.leituras.reduce((a, l) => (l.codigo === codigo ? a + l.qtd : a), 0);
    box.hidden = false;
    box.className = 'ultima ' + (naBase ? 'ok' : 'alerta');
    box.innerHTML = `
      <div class="ult-cod">${E(codigo)}</div>
      <div class="ult-desc">${naBase ? E(item.descricao) : '⚠ Código fora da base (registrado como não cadastrado)'}</div>
      <div class="ult-total">+${Core.fmtNum(qtd)} registrado · total deste código: ${Core.fmtNum(totalCodigo)}</div>`;
  }

  function renderLeituras() {
    const ul = $('lista-leituras');
    const ultimas = S.leituras.slice(-30).reverse();
    ul.innerHTML = ultimas.map(l => {
      const naBase = S.itens.has(l.codigo);
      return `<li>
        <div class="l-info">
          <strong>${E(l.codigo)}</strong>
          <span class="sub">${naBase ? E(S.itens.get(l.codigo).descricao) : 'não cadastrado'} · ${E(l.operador)} · ${new Date(l.ts).toLocaleTimeString('pt-BR')}</span>
        </div>
        <span class="l-qtd">+${Core.fmtNum(l.qtd)}</span>
        <button class="btn-x" data-id="${l.id}" aria-label="Remover leitura">✕</button>
      </li>`;
    }).join('') || '<li class="vazio">Nenhuma leitura ainda.</li>';

    const unidades = S.leituras.reduce((a, l) => a + l.qtd, 0);
    const codigos = new Set(S.leituras.map(l => l.codigo)).size;
    $('resumo-contagem').textContent = `${S.leituras.length} leituras · ${Core.fmtNum(unidades)} un. · ${codigos} códigos`;
  }

  async function removerLeitura(id) {
    await DB.removerLeitura(id);
    S.leituras = S.leituras.filter(l => l.id !== id);
    renderLeituras();
    $('ultima').hidden = true;
  }

  async function desfazerUltima() {
    const ultima = S.leituras[S.leituras.length - 1];
    if (!ultima) return toast('Nada para desfazer.');
    await removerLeitura(ultima.id);
    toast('Última leitura removida.');
  }

  /* ---------- Câmera ---------- */

  let cameraAtiva = false;

  async function alternarCamera() {
    if (cameraAtiva) return pararCamera();
    const video = $('video');
    video.hidden = false;
    try {
      await Scanner.iniciar(video, codigo => registrarCodigo(codigo, true));
      cameraAtiva = true;
      $('btn-camera').textContent = 'Parar câmera';
    } catch (e) {
      video.hidden = true;
      toast(e.message, 'erro');
    }
  }

  function pararCamera() {
    Scanner.parar();
    cameraAtiva = false;
    const v = $('video');
    if (v) { v.hidden = true; v.srcObject = null; }
    const b = $('btn-camera');
    if (b) b.textContent = 'Iniciar câmera';
  }

  /* ---------- Relatório ---------- */

  function gerarResultados() {
    const linhas = Core.conciliar([...S.itens.values()], S.leituras);
    const kpis = Core.calcularKpis(linhas, S.leituras);
    return { linhas, kpis };
  }

  function renderKpisPrevia() {
    const box = $('kpis-prev');
    if (!S.itens.size) {
      box.innerHTML = '<p class="vazio">Importe a base na aba Configurar para ver os indicadores.</p>';
      return;
    }
    const { kpis } = gerarResultados();
    const card = (k, v) => `<div class="kpi"><span>${k}</span><strong>${v}</strong></div>`;
    box.innerHTML = [
      card('Acuracidade itens', Core.fmtPct(kpis.acuraciaItens)),
      card('Acuracidade qtd.', Core.fmtPct(kpis.acuraciaQtd)),
      card('Divergentes', Core.fmtNum(kpis.itensDivergentes)),
      card('Não contados', Core.fmtNum(kpis.naoContados)),
      card('Não cadastrados', Core.fmtNum(kpis.naoCadastrados)),
      card('Dif. financeira', Core.fmtBRL(kpis.valorDiferencaLiquida)),
    ].join('');
  }

  function nomeArquivo(prefixo, ext) {
    const d = new Date();
    const p = n => String(n).padStart(2, '0');
    const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
    return `${prefixo}-${stamp}.${ext}`;
  }

  function baixar(blob, nome) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  let ultimoRelatorio = null;

  function gerarRelatorio() {
    if (!S.itens.size) return toast('Importe a base antes de gerar o relatório.', 'erro');
    const { linhas, kpis } = gerarResultados();
    const html = Core.renderRelatorioHTML({
      nomeInventario: S.nomeInventario,
      geradoEm: new Date(),
      baseArquivo: S.base && S.base.arquivo,
      baseData: S.base && S.base.data,
      kpis,
      linhas,
    });
    const nome = nomeArquivo('relatorio-inventario', 'html');
    ultimoRelatorio = new File([html], nome, { type: 'text/html' });
    baixar(ultimoRelatorio, nome);
    $('btn-compartilhar').hidden = !(navigator.canShare && navigator.canShare({ files: [ultimoRelatorio] }));
    toast('Relatório gerado.', 'ok');
  }

  async function compartilharRelatorio() {
    if (!ultimoRelatorio) return gerarRelatorio();
    try {
      await navigator.share({ files: [ultimoRelatorio], title: 'Relatório de inventário' });
    } catch (e) { /* cancelado pelo usuário */ }
  }

  function exportarConciliacao() {
    if (!S.itens.size) return toast('Importe a base antes.', 'erro');
    const { linhas } = gerarResultados();
    baixar(new Blob([Core.conciliacaoCSV(linhas)], { type: 'text/csv;charset=utf-8' }), nomeArquivo('conciliacao', 'csv'));
  }

  function exportarLeituras() {
    if (!S.leituras.length) return toast('Não há leituras.', 'erro');
    baixar(new Blob([Core.leiturasCSV(S.leituras)], { type: 'text/csv;charset=utf-8' }), nomeArquivo('leituras', 'csv'));
  }

  /* ---------- Configurar ---------- */

  function renderConfig() {
    $('nome-inv').value = S.nomeInventario;
    const info = $('info-base');
    if (S.base) {
      info.textContent = `${Core.fmtNum(S.base.total)} itens · ${S.base.arquivo} · importada em ${new Date(S.base.data).toLocaleString('pt-BR')}`;
    } else {
      info.textContent = 'Nenhuma base importada.';
    }
    $('resumo-config').textContent = `${S.leituras.length} leituras registradas neste aparelho.`;
  }

  async function importarLeituras(arquivo) {
    const texto = await lerArquivo(arquivo);
    const { leituras: recebidas, erros } = Core.parseLeituras(texto);
    const boxErros = $('erros-leituras');
    boxErros.innerHTML = erros.slice(0, 20).map(m => `<div class="erro">${E(m)}</div>`).join('');

    if (!recebidas.length) {
      toast(erros.length ? 'Nada importado. Veja os erros.' : 'Arquivo sem leituras.', 'erro');
      return;
    }

    const existentes = new Set(S.leituras.map(Core.chaveLeitura));
    const novas = recebidas.filter(l => {
      const k = Core.chaveLeitura(l);
      if (existentes.has(k)) return false;
      existentes.add(k);
      return true;
    });

    if (novas.length) {
      const ids = await DB.addLeituras(novas);
      novas.forEach((l, i) => { l.id = ids[i]; S.leituras.push(l); });
      S.leituras.sort((a, b) => a.id - b.id);
    }
    renderLeituras();
    renderConfig();
    toast(`${novas.length} leituras importadas, ${recebidas.length - novas.length} já existiam.`, 'ok');
  }

  async function apagarLeituras() {
    if (!confirm('Apagar TODAS as leituras deste aparelho? Esta ação não pode ser desfeita. Exporte antes se precisar.')) return;
    await DB.apagarLeituras();
    S.leituras = [];
    renderLeituras();
    renderConfig();
    $('ultima').hidden = true;
    toast('Leituras apagadas.');
  }

  /* ---------- Inicialização ---------- */

  function atualizarRede() {
    const p = $('status-rede');
    p.textContent = navigator.onLine ? 'Online' : 'Offline';
    p.className = 'pill ' + (navigator.onLine ? 'on' : 'off');
  }

  async function iniciar() {
    try {
      await DB.open();
    } catch (e) {
      toast('Armazenamento local indisponível neste navegador. Feche o modo privado.', 'erro');
      return;
    }

    const [itens, leituras, sessao, base] = await Promise.all([
      DB.listarItens(), DB.listarLeituras(), DB.getConfig('sessao'), DB.getConfig('base'),
    ]);

    itens.forEach(i => S.itens.set(i.codigo, i));
    S.leituras = leituras;
    if (sessao) {
      S.nomeInventario = sessao.nomeInventario || '';
      S.operador = sessao.operador || '';
      S.qtdPadrao = sessao.qtdPadrao || 1;
    }
    S.base = base;

    $('operador').value = S.operador;
    $('qtd-padrao').value = S.qtdPadrao;
    renderLeituras();
    renderConfig();

    // Eventos — Navegação
    document.querySelectorAll('.nav button').forEach(b =>
      b.addEventListener('click', () => mostrarTela(b.dataset.tela)));

    // Configurar
    $('nome-inv').addEventListener('change', e => { S.nomeInventario = e.target.value.trim(); salvarSessao(); });
    $('arquivo-base').addEventListener('change', async e => {
      const arq = e.target.files[0];
      e.target.value = '';
      if (!arq) return;
      try { await importarBase(arq); }
      catch (err) { toast('Falha ao ler o arquivo: ' + err.message, 'erro'); }
    });
    $('btn-apagar-base').addEventListener('click', apagarBase);
    $('btn-exportar-leituras').addEventListener('click', exportarLeituras);
    $('arquivo-leituras').addEventListener('change', async e => {
      const arq = e.target.files[0];
      e.target.value = '';
      if (!arq) return;
      try { await importarLeituras(arq); }
      catch (err) { toast('Falha ao importar: ' + err.message, 'erro'); }
    });
    $('btn-apagar-leituras').addEventListener('click', apagarLeituras);

    // Contar
    $('operador').addEventListener('change', e => { S.operador = e.target.value.trim(); salvarSessao(); });
    $('qtd-padrao').addEventListener('change', e => {
      const v = parseFloat(String(e.target.value).replace(',', '.'));
      S.qtdPadrao = v > 0 ? v : 1;
      e.target.value = S.qtdPadrao;
      salvarSessao();
    });
    $('btn-camera').addEventListener('click', alternarCamera);
    $('form-codigo').addEventListener('submit', e => {
      e.preventDefault();
      const campo = $('codigo');
      registrarCodigo(campo.value, false);
      campo.value = '';
      campo.focus();
    });
    $('btn-desfazer').addEventListener('click', desfazerUltima);
    $('lista-leituras').addEventListener('click', e => {
      const b = e.target.closest('button[data-id]');
      if (b) removerLeitura(Number(b.dataset.id));
    });

    // Relatório
    $('btn-gerar').addEventListener('click', gerarRelatorio);
    $('btn-compartilhar').addEventListener('click', compartilharRelatorio);
    $('btn-csv-conc').addEventListener('click', exportarConciliacao);

    window.addEventListener('online', atualizarRede);
    window.addEventListener('offline', atualizarRede);
    atualizarRede();

    // Tela inicial: contagem se já há operador, senão configurar.
    mostrarTela(S.itens.size ? 'contar' : 'config');

    if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
      navigator.serviceWorker.register('sw.js').catch(() => { /* offline indisponível */ });
    }
  }

  document.addEventListener('DOMContentLoaded', iniciar);
})();
