/* AZUR room: browser regression test of the built page (tools/build_artifact.py -> azur/.cache/publish).
   Serves the package itself, opens it in headless Chromium (desktop and phone) and walks the paths that broke before:
   product view open/close (button, ×, Escape), the 3D jersey redrawing for every jersey, the drop card, jersey links.

   Usage:  node azur/tools/test_room.cjs [publishDir] [screenshotDir]
   Env:    PLAYWRIGHT=<path to the playwright module>  CHROMIUM=<path to chrome>   (defaults: the cloud container's)
   Exit code 1 when a check fails. */
const http = require('http'), fs = require('fs'), path = require('path');
const pw = require(process.env.PLAYWRIGHT || (fs.existsSync('/opt/node-tools/node_modules/playwright') ? '/opt/node-tools/node_modules/playwright' : 'playwright'));
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, '..', '.cache', 'publish'));
const SHOTS = process.argv[3] || null;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.webp': 'image/webp',
  '.png': 'image/png', '.mp4': 'video/mp4', '.webm': 'video/webm', '.glb': 'model/gltf-binary' };

function serve() {
  const page = '<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'
    + fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8') + '</body></html>';
  const srv = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    if (u === '/' || u === '/_test.html') { res.writeHead(200, { 'Content-Type': 'text/html' }); return res.end(page); }
    const f = path.join(ROOT, path.normalize(u).replace(/^(\.\.[/\\])+/, ''));
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
  });
  return new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv)));
}

(async () => {
  const srv = await serve(), url = `http://127.0.0.1:${srv.address().port}/_test.html`;
  const exe = process.env.CHROMIUM || ['/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '/opt/pw-browsers/chromium'].find(p => fs.existsSync(p));
  const b = await pw.chromium.launch({ executablePath: exe, args: ['--no-proxy-server', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const logs = []; let fails = 0;
  const ok = (name, cond, s) => { if (!cond) fails++; logs.push((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : ' ' + JSON.stringify(s))); };
  const mk = async (vp, mobile) => {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 1, isMobile: !!mobile, hasTouch: !!mobile }); const p = await ctx.newPage();
    p.on('pageerror', e => { fails++; logs.push(`FAIL page error: ${e.message}`); });
    p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) logs.push('console: ' + m.text()); });
    return p;
  };
  const st = p => p.evaluate(() => { const a = AZUR.app, s = a.shop; return { view: a.viewKey, pdp: s.pdp.classList.contains('is-on'), prod: s.product && s.product.key,
    sel: a.rail.selected, hover: a.rail.hover, hasSel: a.root.classList.contains('has-selection'), drop: a.drop.el.classList.contains('is-on'),
    label: a.rail.label.classList.contains('is-on'), hash: location.hash, dim: a.dimTarget }; });
  const find = (p, i) => p.evaluate(i => { const a = AZUR.app, W = a.stage.clientWidth, H = a.stage.clientHeight; let n = 0, sx = 0, sy = 0;
    for (let y = 0; y < H; y += 6) for (let x = 0; x < W; x += 6) if (a.garmentAt(x, y) === i) { n++; sx += x; sy += y; }
    return n ? [Math.round(sx / n), Math.round(sy / n)] : null; }, i);
  const keyOf = (p, i) => p.evaluate(i => AZUR.products[i].key, i);
  const dropIdx = p => p.evaluate(() => AZUR.products.findIndex(x => x.type === 'drop'));
  const shot = (p, name, loc) => SHOTS && (loc ? p.locator(loc).screenshot({ path: path.join(SHOTS, name) }) : p.screenshot({ path: path.join(SHOTS, name) }));
  const click = async (p, i) => { const pt = await find(p, i); if (!pt) return false; await p.mouse.move(pt[0] - 12, pt[1], { steps: 2 }); await p.mouse.move(pt[0], pt[1], { steps: 3 }); await p.mouse.click(pt[0], pt[1]); return true; };
  try {
    let p = await mk({ width: 1440, height: 810 });
    await p.goto(url); await p.waitForFunction(() => window.AZUR && AZUR.app && AZUR.app.running, null, { timeout: 30000 }); await p.waitForTimeout(3000);
    const D = await dropIdx(p), n = await p.evaluate(() => AZUR.products.length);
    // every jersey from the room: its product view opens, its own model draws, the view closes again
    await p.evaluate(() => { const v = AZUR.app.shop.viewer; if (v) { v._n = 0; const d = v.draw.bind(v); v.draw = () => { v._n++; d(); }; } });
    for (let i = 0; i < n; i++) {
      if (i === D) continue;
      const k = await keyOf(p, i);
      if (!await click(p, i)) { ok(`room: ${k} found under the pointer`, false, {}); continue; }
      await p.waitForFunction(() => AZUR.app.shop.pdp.classList.contains('has-model'), null, { timeout: 15000 }).catch(() => {});
      const n0 = await p.evaluate(() => AZUR.app.shop.viewer._n);       // the idle turn keeps drawing (slow software GL: give it time)
      await p.waitForFunction(n0 => AZUR.app.shop.viewer._n > n0, n0, { timeout: 4000 }).catch(() => {});
      const v = await p.evaluate(() => { const v = AZUR.app.shop.viewer; return { url: (v.url || '').split('/').pop(), draws: v._n, model: AZUR.app.shop.pdp.classList.contains('has-model') }; });
      const s = await st(p);
      ok(`room: ${k} opens with its own 3D model, which keeps drawing`, s.pdp && s.prod === k && v.model && v.url.startsWith(k + '.') && v.draws > n0, { s, v, n0 });
      await shot(p, `pdp_${k}.png`, '.azur-pdp__stage');
      await p.keyboard.press('Escape'); await p.waitForTimeout(700);
      const s2 = await st(p); ok(`room: Escape closes ${k}`, !s2.pdp && s2.dim === 1 && !s2.hash, s2);
    }
    // on the rail: Escape closes the product view only; the × closes it
    await p.evaluate(() => AZUR.app.go('rail')); await p.waitForTimeout(2500);
    await click(p, 3); await p.waitForTimeout(1200);
    let s = await st(p); ok('rail: click opens the product view, link in the address', s.pdp && s.hash.length > 1, s);
    await p.keyboard.press('Escape'); await p.waitForTimeout(1200);
    s = await st(p); ok('rail: Escape closes it and stays on the rail', !s.pdp && s.view === 'rail', s);
    await click(p, 1); await p.waitForTimeout(1200); await p.click('.azur-pdp__x'); await p.waitForTimeout(700);
    s = await st(p); ok('rail: × closes the product view', !s.pdp && s.dim === 1, s);
    // the drop card: opens, others still answer to hover, a click on one opens it, × and Escape close the card
    if (D >= 0) {
      await click(p, D); await p.waitForTimeout(1500);
      s = await st(p); ok('drop: card opens', s.drop && s.sel === D && s.hasSel, s);
      await shot(p, 'drop_card.png');
      const pt = await find(p, 2); await p.mouse.move(pt[0] - 15, pt[1], { steps: 2 }); await p.mouse.move(pt[0], pt[1], { steps: 3 }); await p.waitForTimeout(300);
      s = await st(p); ok('drop: another jersey still answers to hover', s.hover === 2 && s.label, s);
      await p.mouse.click(pt[0], pt[1]); await p.waitForTimeout(1200);
      s = await st(p); ok('drop: a click on it opens its product view and closes the card', s.pdp && !s.drop && s.sel === -1 && !s.hasSel, s);
      if (s.pdp) { await p.click('.azur-pdp__back'); await p.waitForTimeout(700); }
      await click(p, D); await p.waitForTimeout(1500); await p.click('.azur-drop__close'); await p.waitForTimeout(500);
      s = await st(p); ok('drop: × closes the card', !s.drop && s.sel === -1, s);
      await click(p, D); await p.waitForTimeout(1500); await p.keyboard.press('Escape'); await p.waitForTimeout(500);
      s = await st(p); ok('drop: Escape closes the card', !s.drop && s.sel === -1, s);
    }
    await p.keyboard.press('Escape'); await p.waitForTimeout(2500);
    s = await st(p); ok('Escape on the rail goes back to the room', s.view === 'room', s);
    // links
    const h = await p.evaluate(() => AZUR.products[0].handle);
    await p.evaluate(h => { location.hash = h; }, h); await p.waitForTimeout(1200);
    s = await st(p); ok('in-page jersey link opens its product view', s.pdp, s);
    await p.click('.azur-pdp__x'); await p.waitForTimeout(600);
    await p.close(); p = await mk({ width: 1440, height: 810 });
    await p.goto(url + '#' + h); await p.waitForFunction(() => window.AZUR && AZUR.app && AZUR.app.running, null, { timeout: 30000 }); await p.waitForTimeout(1500);
    s = await st(p); ok('page opened with a jersey link shows its product view', s.pdp && s.sel === -1, s);
    // rapid open/close, then the viewer still works
    for (const i of [3, 0, 3, 4, 3, 1]) { await p.evaluate(i => AZUR.app.openProduct(i), i); await p.waitForTimeout(120); await p.evaluate(() => AZUR.app.shop.close()); }
    await p.evaluate(() => AZUR.app.openProduct(4)); await p.waitForTimeout(2500);
    const vs = await p.evaluate(() => { const v = AZUR.app.shop.viewer; return { url: (v.url || '').split('/').pop(), running: v.running, parts: v.parts.length, model: AZUR.app.shop.pdp.classList.contains('has-model') }; });
    const k4 = await keyOf(p, 4);
    ok('rapid open/close: the last jersey opened is the one shown', vs.url.startsWith(k4 + '.') && vs.running && vs.parts > 0 && vs.model, vs);
    await p.close();
    // phone
    p = await mk({ width: 390, height: 844 }, true);
    await p.goto(url); await p.waitForFunction(() => window.AZUR && AZUR.app && AZUR.app.running, null, { timeout: 30000 }); await p.waitForTimeout(3000);
    s = await st(p); ok('phone: starts at the rail', s.view === 'rail_m', s);
    const pt = await find(p, 3); if (pt) await p.mouse.click(pt[0], pt[1]); await p.waitForTimeout(2000);
    s = await st(p); ok('phone: tap opens the product view', s.pdp, s);
    await shot(p, 'phone_pdp.png');
    if (s.pdp) { await p.click('.azur-pdp__x'); await p.waitForTimeout(700); }
    s = await st(p); ok('phone: × closes it', !s.pdp, s);
    await p.close();

    // cart (prototype cart): size, add, free-shipping hint, keep looking, the bag in the header, removing a line
    p = await mk({ width: 1440, height: 810 });
    await p.goto(url); await p.waitForFunction(() => window.AZUR && AZUR.app && AZUR.app.running, null, { timeout: 30000 }); await p.waitForTimeout(2000);
    await p.evaluate(() => { try { localStorage.removeItem('azur-cart'); } catch (e) { } AZUR.app.shop.cart = []; AZUR.app.shop.renderCart(); });
    let bag = await p.evaluate(() => !document.querySelector('.azur-head__bag').hidden);
    ok('cart: the bag is hidden while the cart is empty', !bag, { bag });
    await p.evaluate(() => AZUR.app.openProduct(0)); await p.waitForTimeout(900);
    let add = await p.evaluate(() => document.querySelector('.azur-pdp__add').disabled);
    ok('cart: add button waits for a size', add, { add });
    await p.click('.azur-size >> nth=1'); await p.click('.azur-pdp__add'); await p.waitForTimeout(700);
    let c = await p.evaluate(() => ({ lines: AZUR.app.shop.cart.length, after: !document.querySelector('.azur-pdp__after').hidden,
      ship: document.querySelector('.azur-pdp__ship').textContent, bag: !document.querySelector('.azur-head__bag').hidden,
      count: document.querySelector('.azur-head__count').textContent }));
    ok('cart: added, free-shipping hint shown, bag visible with the count', c.lines === 1 && c.after && /€|kostenlos|Versand/i.test(c.ship) && c.bag && c.count === '1', c);
    await p.waitForTimeout(1300);
    const lay = await p.evaluate(() => [...document.querySelectorAll('.azur-pdp__info > *:not([hidden])')]
      .map(e => ({ c: e.className, h: Math.round(e.getBoundingClientRect().height), want: e.scrollHeight })).filter(x => x.h < x.want * 0.8));   // tight display type overflows its box a little on purpose
    ok('cart: nothing in the product column is squeezed after adding', lay.length === 0, lay);
    await shot(p, 'pdp_added.png');
    await p.click('.azur-pdp__after [data-act="more"]'); await p.waitForTimeout(900);
    s = await st(p); ok('cart: "keep looking" closes the product view', !s.pdp && s.dim === 1, s);
    await p.click('.azur-head__bag'); await p.waitForTimeout(500);
    let dr = await p.evaluate(() => AZUR.app.shop.drawer.classList.contains('is-on'));
    ok('cart: the bag opens the cart', dr, { dr });
    await p.click('.azur-cart [data-remove="0"]'); await p.waitForTimeout(300);
    c = await p.evaluate(() => ({ lines: AZUR.app.shop.cart.length, empty: !!document.querySelector('.azur-cart__empty'), bag: !document.querySelector('.azur-head__bag').hidden }));
    ok('cart: a line can be removed, the empty bag hides', c.lines === 0 && c.empty && !c.bag, c);
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
    dr = await p.evaluate(() => AZUR.app.shop.drawer.classList.contains('is-on'));
    ok('cart: Escape closes the cart', !dr, { dr });
    // menu behind the three dots
    await p.click('.azur-head__dots'); await p.waitForTimeout(300);
    let m = await p.evaluate(() => !document.querySelector('.azur-menu').hidden);
    ok('menu: the dots open it', m, { m });
    await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    m = await p.evaluate(() => !document.querySelector('.azur-menu').hidden);
    ok('menu: Escape closes it', !m, { m });
    // view chips
    for (const v of ['bed', 'rail', 'room']) {
      await p.click(`.azur-views button[data-view="${v}"]`); await p.waitForTimeout(2600);
      s = await st(p); ok(`chips: ${v}`, s.view === v, s);
    }
    // the magazine: opens from the bed, turns, closes with Escape, the room is not dimmed afterwards
    await p.evaluate(() => AZUR.app.openMag()); await p.waitForTimeout(3500);
    let mg = await p.evaluate(() => ({ open: AZUR.app.mag && AZUR.app.mag.isOpen, view: AZUR.app.viewKey, n: AZUR.app.mag && AZUR.app.mag.n }));
    ok('magazine: opens (from the bed)', mg.open && mg.view === 'bed', mg);
    await p.click('.azur-mag [data-act="next"]'); await p.waitForTimeout(900);
    mg = await p.evaluate(() => ({ n: AZUR.app.mag.n }));
    ok('magazine: turns a page', mg.n === 1, mg);
    await shot(p, 'magazine.png');
    await p.keyboard.press('Escape'); await p.waitForTimeout(800);
    mg = await p.evaluate(() => ({ open: AZUR.app.mag.isOpen, view: AZUR.app.viewKey, dim: AZUR.app.dimTarget, cls: document.documentElement.className }));
    ok('magazine: Escape closes it, stays at the bed, room not dimmed', !mg.open && mg.view === 'bed' && mg.dim === 1 && !/azur-mag-open/.test(mg.cls), mg);
    // a look page leads to its product view
    await p.evaluate(() => AZUR.app.openMag()); await p.waitForTimeout(1200);
    const lookBtn = await p.evaluate(() => { const b = document.querySelector('.azur-mag [data-act="product"]'); return b ? +b.dataset.i : -1; });
    if (lookBtn >= 0) {
      await p.evaluate(() => document.querySelector('.azur-mag [data-act="product"]').click()); await p.waitForTimeout(1500);
      s = await st(p); mg = await p.evaluate(() => AZUR.app.mag.isOpen);
      ok('magazine: a look page opens that jersey\'s product view', s.pdp && !mg, { s, mg });
      await p.click('.azur-pdp__x'); await p.waitForTimeout(700);
      s = await st(p); ok('magazine: after that product view the room is back to normal', !s.pdp && s.dim === 1, s);
    }
    // times of day: switching the clock changes the room state without errors
    for (const h of [7.2, 12.5, 18.5, 23.5]) {
      await p.evaluate(h => { AZUR.light.overrides.timeHours = h; AZUR.app.lightDirty = true; }, h);
      await p.waitForFunction(() => !AZUR.app.stateBusy && AZUR.app.dayState === AZUR.app.stateNow(), null, { timeout: 8000 }).catch(() => {});
      const ds = await p.evaluate(() => ({ state: AZUR.app.dayState, want: AZUR.app.stateNow(), busy: !!AZUR.app.stateBusy, dataset: AZUR.app.root.dataset.state }));
      ok(`clock ${h}: the room follows (${ds.want})`, !ds.busy && ds.state === ds.want && ds.dataset === ds.want, ds);
    }
  } catch (e) { fails++; logs.push('FAIL exception: ' + e.message.split('\n')[0]); }
  console.log(logs.join('\n')); console.log(fails ? `${fails} failed` : 'all passed');
  await b.close(); srv.close(); process.exit(fails ? 1 : 0);
})();
