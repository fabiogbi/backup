/*
 * Persistência local (IndexedDB). Os dados ficam no aparelho e sobrevivem
 * a fechar o app. Não depende de rede.
 */
const DB = (() => {
  const NOME = 'inventario-cego';
  const VERSAO = 1;
  let conexao = null;

  function abrir() {
    if (conexao) return conexao;
    conexao = new Promise((resolve, reject) => {
      const req = indexedDB.open(NOME, VERSAO);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('itens')) db.createObjectStore('itens', { keyPath: 'codigo' });
        if (!db.objectStoreNames.contains('leituras')) db.createObjectStore('leituras', { keyPath: 'id', autoIncrement: true });
        if (!db.objectStoreNames.contains('config')) db.createObjectStore('config', { keyPath: 'chave' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => { conexao = null; reject(req.error); };
    });
    return conexao;
  }

  // Executa uma única requisição dentro de uma transação e devolve seu resultado.
  async function executar(store, modo, fn) {
    const db = await abrir();
    return new Promise((resolve, reject) => {
      const t = db.transaction(store, modo);
      const req = fn(t.objectStore(store));
      t.oncomplete = () => resolve(req ? req.result : undefined);
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error);
    });
  }

  return {
    open: abrir,

    // Substitui a base inteira em uma só transação.
    async salvarItens(itens) {
      const db = await abrir();
      return new Promise((resolve, reject) => {
        const t = db.transaction('itens', 'readwrite');
        const st = t.objectStore('itens');
        st.clear();
        for (const it of itens) st.put(it);
        t.oncomplete = () => resolve(itens.length);
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      });
    },
    listarItens: () => executar('itens', 'readonly', st => st.getAll()),
    apagarItens: () => executar('itens', 'readwrite', st => st.clear()),

    async listarLeituras() {
      const lista = await executar('leituras', 'readonly', st => st.getAll());
      return lista.sort((a, b) => a.id - b.id);
    },
    addLeitura: leitura => executar('leituras', 'readwrite', st => st.add(leitura)),

    // Grava várias leituras em uma transação e devolve os ids gerados.
    async addLeituras(lista) {
      const db = await abrir();
      return new Promise((resolve, reject) => {
        const t = db.transaction('leituras', 'readwrite');
        const st = t.objectStore('leituras');
        const ids = lista.map(l => st.add(l));
        t.oncomplete = () => resolve(ids.map(r => r.result));
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      });
    },
    removerLeitura: id => executar('leituras', 'readwrite', st => st.delete(id)),
    apagarLeituras: () => executar('leituras', 'readwrite', st => st.clear()),

    async getConfig(chave) {
      const r = await executar('config', 'readonly', st => st.get(chave));
      return r ? r.valor : null;
    },
    setConfig: (chave, valor) => executar('config', 'readwrite', st => st.put({ chave, valor })),
  };
})();
