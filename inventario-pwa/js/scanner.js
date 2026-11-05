/*
 * Leitura de códigos de barras pela câmera usando ZXing (vendor/zxing.min.js).
 * Funciona em iOS (Safari/PWA) e Android (Chrome), pois não depende da API
 * BarcodeDetector, que não existe no Safari.
 */
const Scanner = (() => {
  let leitor = null;

  function formatos() {
    const F = ZXing.BarcodeFormat;
    return [F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E, F.CODE_128, F.CODE_39, F.ITF];
  }

  /**
   * @param {HTMLVideoElement} video
   * @param {(codigo: string) => void} aoLer
   * @returns {Promise<void>} resolve quando a câmera abre; rejeita com mensagem amigável
   */
  async function iniciar(video, aoLer) {
    if (typeof ZXing === 'undefined') throw new Error('Biblioteca de leitura não carregou. Recarregue o app.');
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Câmera indisponível. O app precisa de HTTPS. Use o campo para digitar o código.');
    }
    parar();

    const dicas = new Map();
    dicas.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, formatos());
    dicas.set(ZXing.DecodeHintType.TRY_HARDER, true);
    leitor = new ZXing.BrowserMultiFormatReader(dicas);

    const restricoes = {
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    };

    try {
      // Erros de "nenhum código neste frame" chegam ao callback e são ignorados.
      await leitor.decodeFromConstraints(restricoes, video, (resultado) => {
        if (resultado) aoLer(resultado.getText());
      });
    } catch (e) {
      parar();
      const nome = e && e.name;
      if (nome === 'NotAllowedError' || nome === 'SecurityError') {
        throw new Error('Permissão de câmera negada. iPhone: Ajustes › Safari › Câmera. Android: Configurações do Chrome › Permissões do site.');
      }
      if (nome === 'NotFoundError' || nome === 'OverconstrainedError') {
        throw new Error('Nenhuma câmera traseira encontrada neste aparelho.');
      }
      throw new Error('Não foi possível iniciar a câmera: ' + (e && e.message ? e.message : e));
    }
  }

  function parar() {
    if (leitor) {
      try { leitor.reset(); } catch (e) { /* já parado */ }
      leitor = null;
    }
  }

  return { iniciar, parar };
})();
