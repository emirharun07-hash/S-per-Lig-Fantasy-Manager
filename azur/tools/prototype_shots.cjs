const { chromium } = require('/opt/node-tools/node_modules/playwright');
const SPKI = process.env.CCR_SPKI;
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--no-proxy-server', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const out = process.argv[2] || '/tmp';
  const logs = [];
  async function run(name, vp, actions) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 1, isMobile: !!vp.mobile, hasTouch: !!vp.mobile });
    const p = await ctx.newPage();
    p.on('console', m => logs.push(`[${name}] ${m.type()}: ${m.text()}`));
    p.on('pageerror', e => logs.push(`[${name}] PAGEERROR: ${e.message}`));
    await p.goto('http://127.0.0.1:8765/_dev.html', { waitUntil: 'load' });
    await p.waitForTimeout(3500);
    await actions(p, name);
    await ctx.close();
  }
  await run('desk', { width: 1440, height: 810 }, async (p, n) => {
    await p.screenshot({ path: `${out}/${n}_1_room.png` });
    await p.mouse.move(560, 300); await p.waitForTimeout(150); await p.mouse.move(610, 330); await p.waitForTimeout(900);
    await p.screenshot({ path: `${out}/${n}_2_hover.png` });
    await p.mouse.click(610, 330); await p.waitForTimeout(2600);
    await p.screenshot({ path: `${out}/${n}_3_rail_selected.png` });
    const info = await p.$('.azur-info__cta'); if (info) { await info.click(); await p.waitForTimeout(1400); }
    await p.screenshot({ path: `${out}/${n}_4_pdp.png` });
  });
  await run('mobile', { width: 390, height: 844, mobile: true }, async (p, n) => {
    await p.screenshot({ path: `${out}/${n}_1_rail.png` });
  });
  console.log(logs.slice(0, 40).join('\n'));
  await b.close();
})();
