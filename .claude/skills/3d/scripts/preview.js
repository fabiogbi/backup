#!/usr/bin/env node
// Converte SVG/HTML em PNG com Playwright para conferir o resultado visualmente.
// Uso: node preview.js entrada.(svg|html) saida.png [largura altura] [--wait ms] [--scale 2]
const path = require('path');
const fs = require('fs');

let chromium;
try { ({ chromium } = require('playwright')); }
catch { console.error('Playwright não encontrado (npm i playwright). Pré-visualização indisponível.'); process.exit(2); }

(async () => {
  const args = process.argv.slice(2);
  const opt = (name, def) => { const i = args.indexOf(name); if (i < 0) return def; const v = args[i + 1]; args.splice(i, 2); return Number(v); };
  const wait = opt('--wait', 300);
  const scale = opt('--scale', 1);
  const [input, output, w, h] = args;
  if (!input || !output) { console.error('Uso: node preview.js entrada.svg saida.png [largura altura] [--wait ms] [--scale 2]'); process.exit(1); }

  let width = Number(w) || 0, height = Number(h) || 0;
  if (input.endsWith('.svg') && (!width || !height)) {
    const src = fs.readFileSync(input, 'utf8');
    const vb = src.match(/viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)/);
    const mw = src.match(/<svg[^>]*\swidth="([\d.]+)/), mh = src.match(/<svg[^>]*\sheight="([\d.]+)/);
    width = width || Number(mw?.[1] || vb?.[1] || 800);
    height = height || Number(mh?.[1] || vb?.[2] || 800);
  }
  width = width || 1280; height = height || 800;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: scale });
  await page.goto('file://' + path.resolve(input));
  await page.waitForTimeout(wait);
  await page.screenshot({ path: output, clip: { x: 0, y: 0, width, height } });
  await browser.close();
  console.log(`ok: ${output} (${width}x${height}@${scale}x)`);
})();
