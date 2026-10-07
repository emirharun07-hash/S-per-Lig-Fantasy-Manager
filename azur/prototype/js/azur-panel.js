/* AZUR — prototype-only art direction panel. Not part of the customer site.
   Opens from the small "Regie" button (or the D key). Every control writes into AZUR.config / AZUR.light.overrides. */
(function () {
  const A = window.AZUR = window.AZUR || {};

  const SLIDERS = [
    ['Licht', [
      ['exposure', 'Helligkeit (Blenden)', -2, 2, 0.05, 0],
      ['contrast', 'Kontrast', 0.7, 1.4, 0.01, 1],
      ['saturation', 'Sättigung', 0.5, 1.5, 0.01, 1],
      ['warmth', 'Wärme', -1, 1, 0.01, 0],
      ['window', 'Fenster', 0, 2, 0.01, 1],
      ['sky', 'Tageslicht', 0, 2, 0.01, 1],
      ['sun', 'Sonne', 0, 2, 0.01, 1],
      ['neon', 'Neon', 0, 3, 0.01, 1],
      ['lamp', 'Schreibtischlampe', 0, 3, 0.01, 1],
      ['ceiling', 'Deckenlicht', 0, 3, 0.01, 1],
      ['street', 'Straßenlaterne', 0, 3, 0.01, 1]
    ]],
    ['Bewegung', [
      ['m:intensity', 'Animation', 0, 2, 0.01, 1],
      ['m:interaction', 'Trikot-Reaktion', 0, 2, 0.01, 1],
      ['m:parallax', 'Parallaxe', 0, 3, 0.01, 1]
    ]]
  ];

  class Panel {
    constructor(app) {
      this.app = app; this.baseParallax = {};
      Object.entries(A.config.views).forEach(([k, v]) => { this.baseParallax[k] = v.parallax; });
      const btn = document.createElement('button');
      btn.className = 'azur-regie'; btn.type = 'button'; btn.textContent = 'Regie';
      btn.setAttribute('aria-expanded', 'false'); btn.title = 'Prototyp-Regler (Taste D)';
      document.body.appendChild(btn);
      const el = document.createElement('aside');
      el.className = 'azur-panel'; el.setAttribute('aria-label', 'Prototyp-Regler'); el.hidden = true;
      const pal = Object.entries(A.config.palettes).map(([k, p]) => `<option value="${k}" ${k === A.config.palette ? 'selected' : ''}>${k} · ${p.name}</option>`).join('');
      el.innerHTML = `
        <header><strong>Regie</strong><span>nur im Prototyp</span></header>
        <section>
          <h3>Tageszeit</h3>
          <label class="azur-panel__row azur-panel__check"><input type="checkbox" id="azp-live" checked> Echte Uhrzeit des Besuchers</label>
          <label class="azur-panel__row"><span>Uhrzeit <output id="azp-time-out"></output></span><input type="range" id="azp-time" min="0" max="24" step="0.05"></label>
          <p class="azur-panel__phase" id="azp-phase"></p>
          <div class="azur-panel__presets">
            ${[['Morgen', 7.5], ['Mittag', 12.5], ['Goldene Stunde', 18.4], ['Blaue Stunde', 20.6], ['Nacht', 23]].map(([n, h]) => `<button type="button" data-h="${h}">${n}</button>`).join('')}
          </div>
        </section>
        <section>
          <h3>Farbsystem</h3>
          <select id="azp-palette">${pal}</select>
        </section>
        ${SLIDERS.map(([title, rows]) => `<section><h3>${title}</h3>${rows.map(([k, l, mi, ma, st, d]) => `
          <label class="azur-panel__row"><span>${l} <output data-for="${k}">${d}</output></span>
          <input type="range" data-k="${k}" min="${mi}" max="${ma}" step="${st}" value="${d}"></label>`).join('')}</section>`).join('')}
        <section>
          <h3>Ansicht</h3>
          <div class="azur-panel__presets">
            <button type="button" data-view="room">Zimmer</button><button type="button" data-view="rail">Ständer</button>
            <button type="button" data-view="bed">Bett</button><button type="button" data-view="rail_m">Handy-Ständer</button>
          </div>
          <label class="azur-panel__row azur-panel__check"><input type="checkbox" id="azp-reduced"> Reduzierte Bewegung testen</label>
          <p class="azur-panel__info" id="azp-info"></p>
        </section>
        <footer><button type="button" id="azp-reset">Zurücksetzen</button></footer>`;
      document.body.appendChild(el);
      this.el = el; this.btn = btn;
      btn.addEventListener('click', () => this.toggle());
      document.addEventListener('keydown', e => { if ((e.key === 'd' || e.key === 'D') && !e.target.closest('input, textarea, select')) this.toggle(); });
      this.bind();
    }

    toggle(on) {
      const open = on == null ? this.el.hidden : on;
      this.el.hidden = !open; this.btn.setAttribute('aria-expanded', String(open));
    }

    bind() {
      const o = A.light.overrides, el = this.el, app = this.app;
      const live = el.querySelector('#azp-live'), time = el.querySelector('#azp-time');
      live.addEventListener('change', () => { o.timeHours = live.checked ? null : +time.value; app.lightDirty = true; });
      time.addEventListener('input', () => { live.checked = false; o.timeHours = +time.value; app.lightDirty = true; });
      el.querySelectorAll('[data-h]').forEach(b => b.addEventListener('click', () => { live.checked = false; time.value = b.dataset.h; o.timeHours = +b.dataset.h; app.lightDirty = true; }));
      el.querySelector('#azp-palette').addEventListener('change', e => { A.config.palette = e.target.value; app.applyPalette(); app.lightDirty = true; });
      el.querySelectorAll('input[data-k]').forEach(inp => inp.addEventListener('input', () => {
        const k = inp.dataset.k, v = +inp.value;
        el.querySelector(`output[data-for="${k}"]`).textContent = v.toFixed(2);
        if (k === 'm:intensity') A.config.motion.intensity = v;
        else if (k === 'm:interaction') A.config.interactionStrength = v;
        else if (k === 'm:parallax') Object.keys(A.config.views).forEach(vk => { A.config.views[vk].parallax = this.baseParallax[vk] * v; });
        else o[k] = v;
        app.lightDirty = true;
      }));
      el.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => { app.select(-1); app.go(b.dataset.view); }));
      el.querySelector('#azp-reduced').addEventListener('change', e => { app.reduced = e.target.checked || app.reducedQuery.matches; });
      el.querySelector('#azp-reset').addEventListener('click', () => {
        Object.assign(o, { timeHours: null, exposure: 0, sky: 1, sun: 1, neon: 1, lamp: 1, ceiling: 1, street: 1, warmth: 0, contrast: 1, saturation: 1, window: 1 });
        el.querySelectorAll('input[data-k]').forEach(inp => {
          const row = SLIDERS.flatMap(s => s[1]).find(r => r[0] === inp.dataset.k); inp.value = row[5];
          el.querySelector(`output[data-for="${inp.dataset.k}"]`).textContent = row[5];
        });
        A.config.motion.intensity = 1; A.config.interactionStrength = 1;
        Object.keys(A.config.views).forEach(vk => { A.config.views[vk].parallax = this.baseParallax[vk]; });
        live.checked = true; app.lightDirty = true;
      });
    }

    sync(s) {
      if (this.el.hidden) return;
      const h = s.clockHours, hh = Math.floor(h), mm = Math.floor((h - hh) * 60);
      this.el.querySelector('#azp-time-out').textContent = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
      if (A.light.overrides.timeHours == null) this.el.querySelector('#azp-time').value = h.toFixed(2);
      const sr = s.sun, f = x => `${String(Math.floor(x)).padStart(2, '0')}:${String(Math.floor((x % 1) * 60)).padStart(2, '0')}`;
      this.el.querySelector('#azp-phase').textContent = `${s.phase} · Sonnenaufgang ${f(sr.sunrise)} · Untergang ${f(sr.sunset)}`;
      const modes = { passes: 'Lichtvarianten (live gemischt)', beauty: 'Vorschaubild (Lichtvarianten rendern noch)', none: 'Bilder fehlen noch' };
      this.el.querySelector('#azp-info').textContent = `Ansicht: ${this.app.viewKey} · ${modes[this.app.root.dataset.mode] || ''}`;
    }
  }

  A.Panel = Panel;
})();
