// Captura de pagina real para insert: print inteiro ou gravacao da rolagem.
// Quem chama e o capturar_pagina.py, que acha o Chrome e instala o
// puppeteer-core no cache da skill. Nao rode direto.
//
//   node pagina.js print  <chrome> <url> <saida.png> <desktop|celular> <espera_ms> <altura_max>
//   node pagina.js gravar <chrome> <url> <pasta> <segundos> <chaves t:y,...> <largura> <altura> <escala> <espera_ms>
//
// Por que existe, alem do modo rapido: pagina feita em JS (React, Next) sai em
// branco na captura de linha de comando do Chrome. Aqui a pagina carrega com
// rede ociosa, rola ate o fim para carregar imagem preguicosa, volta, esconde
// banner de cookie e so entao fotografa. Ja usado em anuncios reais.
const fs = require('fs');
const path = require('path');
const pp = require('puppeteer-core');

const UA_DESKTOP = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0 Safari/537.36';
const UA_CELULAR = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
const espera = ms => new Promise(r => setTimeout(r, ms));

async function abrir(chrome, url, viewport, ua, esperaMs) {
  const b = await pp.launch({ headless: true, executablePath: chrome, args: ['--no-sandbox', '--hide-scrollbars'] });
  const p = await b.newPage();
  await p.setUserAgent(ua);
  await p.setViewport(viewport);
  await p.goto(url, { waitUntil: 'networkidle2', timeout: 60000 }).catch(() => {});
  await espera(esperaMs);
  await p.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
    window.scrollTo(0, 0);
  });
  await p.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    const rx = /cookie|consent|onetrust|gdpr|privacy-banner|cc-banner|truste/i;
    document.querySelectorAll('body *').forEach(el => {
      const s = getComputedStyle(el);
      const id = (el.id || '') + ' ' + (typeof el.className === 'string' ? el.className : '');
      const txt = el.innerText || '';
      const fixo = s.position === 'fixed' || s.position === 'sticky';
      if (fixo && (rx.test(id) || (rx.test(txt) && txt.length < 900))) el.style.display = 'none';
    });
  });
  await espera(1500);
  return { b, p };
}

async function print(chrome, url, saida, modo, esperaMs, alturaMax) {
  const celular = modo === 'celular';
  const vp = celular ? { width: 430, height: 932, deviceScaleFactor: 3, isMobile: true, hasTouch: true }
                     : { width: 1440, height: 900, deviceScaleFactor: 2 };
  const { b, p } = await abrir(chrome, url, vp, celular ? UA_CELULAR : UA_DESKTOP, esperaMs);
  const h = await p.evaluate(() => document.documentElement.scrollHeight);
  const alt = Math.min(h, alturaMax);
  fs.mkdirSync(path.dirname(path.resolve(saida)), { recursive: true });
  await p.screenshot({ path: saida, clip: { x: 0, y: 0, width: vp.width, height: alt } });
  console.log(`${saida} ${vp.width}x${alt} (pagina tem ${h}px)`);
  await b.close();
}

async function gravar(chrome, url, pasta, seg, chaves, W, H, escala, esperaMs) {
  fs.mkdirSync(pasta, { recursive: true });
  const { b, p } = await abrir(chrome, url, { width: W, height: H, deviceScaleFactor: escala }, UA_DESKTOP, esperaMs);
  const K = chaves.split(',').map(c => c.split(':').map(Number));
  const ease = t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  const n = Math.round(seg * 30);
  console.log('altura da pagina', await p.evaluate(() => document.documentElement.scrollHeight));
  for (let i = 0; i < n; i++) {
    const t = i / 30;
    let y = K[K.length - 1][1];
    if (t <= K[0][0]) y = K[0][1];
    for (let k = 0; k < K.length - 1; k++) {
      if (t >= K[k][0] && t <= K[k + 1][0]) y = K[k][1] + (K[k + 1][1] - K[k][1]) * ease((t - K[k][0]) / (K[k + 1][0] - K[k][0]));
    }
    await p.evaluate(v => window.scrollTo(0, v), y);
    await espera(25);
    await p.screenshot({ path: path.join(pasta, `q${String(i).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 92 });
  }
  await b.close();
  console.log(`${n} quadros em ${pasta}`);
}

(async () => {
  const [modo, chrome, url, ...r] = process.argv.slice(2);
  if (modo === 'print') await print(chrome, url, r[0], r[1] || 'desktop', +(r[2] || 6000), +(r[3] || 6000));
  else if (modo === 'gravar') await gravar(chrome, url, r[0], +(r[1] || 12), r[2] || '0:0', +(r[3] || 1280), +(r[4] || 960), +(r[5] || 1.5), +(r[6] || 7000));
  else { console.error('modo desconhecido: ' + modo); process.exit(2); }
})().catch(e => { console.error(String(e && e.stack || e)); process.exit(1); });
