/* AZUR — app: views, camera moves, pointer, phones, window, header, loop.
   Desktop starts in the room (establishing shot). Clicking a jersey there moves the camera to the rail and opens
   that jersey in one step. The bed has its own view (easter egg to come). Phones start at the rail and swipe along it.
   Camera moves are faked from stills for now (zoom, drift, blur); real pre-rendered moves can replace go() later. */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const $ = (s, r = document) => r.querySelector(s);
  const fetchJSON = url => fetch(url, { cache: 'no-cache' }).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const lin2srgb = c => c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  const DEPTH = { near: 0.4, far: 6.5 };

  class App {
    async init() {
      const cfg = A.config;
      this.root = $('#azur'); this.stage = $('.azur-stage'); this.world = $('.azur-world');
      this.canvas = $('.azur-canvas'); this.fallbackImg = $('.azur-fallback'); this.layer = $('.azur-layer');
      this.snap = $('.azur-snap'); this.snapCtx = this.snap.getContext('2d');
      this.reducedQuery = matchMedia('(prefers-reduced-motion: reduce)');
      this.reduced = this.reducedQuery.matches;
      this.isMobile = matchMedia(cfg.mobileQuery).matches;
      this.root.classList.toggle('is-mobile', this.isMobile);
      this.applyPalette();

      // scene2: the jerseys are real 3D garments inside the renders (owner feedback: they looked pasted in)
      if (cfg.useScene2 !== false) {
        const s2 = cfg.scene2Base || 'assets/scene2/views/';
        const ok = await fetch(s2 + 'passes.json', { cache: 'no-cache' }).then(r => r.ok).catch(() => false);
        if (ok) { cfg.assetBase = s2; cfg.plateGarments = true; }
      }
      this.plate = !!cfg.plateGarments;
      this.root.classList.toggle('is-plate', this.plate);
      const base = cfg.assetBase;
      [this.views, this.passes, A.sprites, this.moves] = await Promise.all([fetchJSON(base + 'views.json'), fetchJSON(base + 'passes.json'), fetchJSON(base + 'sprites.json'),
        fetchJSON(base.replace(/views\/$/, 'moves/') + 'moves.json')]);
      this.moveFrames = {};
      this.comp = new A.Compositor(this.canvas);
      this.root.classList.toggle('no-webgl', !this.comp.ok);
      this.rail = new A.Rail(this.layer, A.products, this);
      this.drop = new A.Drop(this.layer, this);
      this.shop = new A.Shop(this);
      this.mag = A.Mag ? new A.Mag(this) : null;
      this.depthMaps = {};
      this.parallax = [0, 0]; this.parallaxTarget = [0, 0];
      this.pan = 0.5; this.panVel = 0;
      this.light = A.light.current();
      this.buildChrome();
      this.bindPointer(); this.bindKeys();
      window.addEventListener('resize', () => this.resize());
      document.addEventListener('visibilitychange', () => { if (!document.hidden) this.kick(); });
      this.reducedQuery.addEventListener && this.reducedQuery.addEventListener('change', e => { this.reduced = e.matches; });
      if (A.Panel) this.panel = new A.Panel(this);

      const start = this.isMobile ? cfg.startView.mobile : cfg.startView.desktop;
      await this.enterView(start);
      this.root.classList.add('is-ready');
      this.lastT = performance.now(); this.lightAt = 0; this.running = true;
      this.light = A.light.current(); this.rail.applyLight(this.light); this.applyAmbient();
      requestAnimationFrame(t => this.frame(t));
      setTimeout(() => this.showHint(), this.reduced ? 200 : 1600);
      // other views load in the background so camera moves never wait (each view is 8 textures: phones load on demand,
      // desktops skip the phone plate)
      if (!this.isMobile) setTimeout(() => Object.keys(cfg.views).forEach(k => k !== start && k !== 'rail_m' && this.comp.load(k, this.passes, false).then(() => this.loadDepth(k))), 2500);
      setTimeout(() => this.preloadMoves(), 6000);
      this.handleHash();
    }

    applyPalette() {
      const p = A.config.palettes[A.config.palette], r = document.documentElement.style;
      r.setProperty('--glow', p.glow); r.setProperty('--highlight', p.highlight); r.setProperty('--ink', p.ink); r.setProperty('--night', p.night);
    }

    /* ---------------------------------------------------------------- views */
    /* View data; a chosen-garment view ('rail@2') is its rail view with that garment where the pull move left it. */
    viewData(key) {
      if (this.views[key]) return this.views[key];
      const [base, idx] = key.split('@'), bv = this.views[base] || {};
      if (idx == null) return bv;
      const mv = this.moves && this.moves[`${base}-${key}`], last = mv && mv.track && mv.track[mv.track.length - 1];
      const slots = (bv.slots || []).slice();
      if (last && last.slots && last.slots[+idx]) slots[+idx] = last.slots[+idx];
      return Object.assign({}, bv, { slots });
    }

    async enterView(key) {
      const prevBase = (this.viewKey || '').split('@')[0];
      this.viewKey = key;
      const v = this.viewData(key);
      const mode = await this.comp.load(key, this.passes);
      if (this.comp.view && !this.comp.view.size && v.res) this.comp.view.size = v.res.slice();   // plate not rendered yet: keep its geometry
      this.root.dataset.view = key; this.root.dataset.mode = mode;
      this.fallbackImg.hidden = !(mode === 'beauty' && !this.comp.ok);
      if (!this.comp.ok && mode === 'beauty') this.fallbackImg.src = A.config.assetBase + key + '/beauty.webp';
      this.root.classList.toggle('is-missing', mode === 'none');
      await this.loadDepth(key);
      const slots = v.slots || [];
      const avgDepth = slots.length ? slots.reduce((s, x) => s + x.depth, 0) / slots.length : 2.5;
      this.comp.focus = this.encDepth(avgDepth);
      if (!(key.startsWith('rail_m') && prevBase === 'rail_m')) this.pan = key.startsWith('rail_m') ? 0.38 : 0.5;
      this.rail.layout(key, v, this.comp);
      this.rail.setSelected(-1); this.rail.setHover(-1);
      this.drop.close();
      this.updateChips();
      this.resize();
    }

    /* Fake camera move: the current frame pushes toward the target and blurs, the next view settles in. */
    async go(to, opts = {}) {
      if (this.busy) return;
      if (to === this.viewKey) { if (opts.select != null) this.select(opts.select); return; }
      const fromBase = this.viewKey.split('@')[0];
      if (this.plate && this.viewKey.includes('@') && to !== fromBase && !to.startsWith(fromBase + '@')) {
        this.rail.setSelected(-1); this.root.classList.remove('has-selection');
        await this.go(fromBase);                                   // hang the garment back first
        return this.go(to, opts);
      }
      this.busy = true; this.hideHint();
      const m = A.config.motion.pan, from = this.viewKey;
      const back = to === 'room';
      const focus = opts.focus || [this.stage.clientWidth / 2, this.stage.clientHeight / 2];
      const slow = setTimeout(() => this.root.classList.add('is-loading'), 250);   // a view not loaded yet (phones load on demand)
      await this.comp.load(to, this.passes, false);
      clearTimeout(slow); this.root.classList.remove('is-loading');
      const mv = this.findMove(from, to);
      if (mv && !this.reduced) {
        await this.playMove(mv, to);
      } else if (!this.reduced && from.split('@')[0] === to.split('@')[0]) {
        // a garment taken off / put back without rendered frames yet: a short crossfade
        this.comp.render(this.light); this.comp.snapshotInto(this.snapCtx);
        Object.assign(this.snap.style, { transform: '', filter: '', opacity: '1' }); this.snap.hidden = false;
        await this.enterView(to); this.comp.render(this.light);
        await this.snap.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 380, easing: 'ease-out' }).finished.catch(() => { });
        this.snap.hidden = true;
      } else if (this.reduced) {
        await this.enterView(to);
        this.world.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 260 });
      } else {
        this.comp.render(this.light);
        this.comp.snapshotInto(this.snapCtx);
        this.snap.hidden = false;
        const W = this.stage.clientWidth, H = this.stage.clientHeight;
        const ox = (focus[0] / W * 100).toFixed(1) + '% ' + (focus[1] / H * 100).toFixed(1) + '%';
        this.snap.style.transformOrigin = ox;
        const z = back ? 1 / m.zoom : m.zoom;
        const drift = (back ? -1 : 1) * m.drift * W * (focus[0] / W - 0.5);
        const out = this.snap.animate([
          { transform: 'none', filter: 'blur(0px)', opacity: 1 },
          { transform: `translate3d(${-drift}px,0,0) scale(${z})`, filter: `blur(${m.blurPx}px)`, opacity: 1, offset: 0.75 },
          { transform: `translate3d(${-drift * 1.2}px,0,0) scale(${z * (back ? 0.96 : 1.04)})`, filter: `blur(${m.blurPx * 1.4}px)`, opacity: 0 }
        ], { duration: m.outMs + m.inMs * 0.45, easing: 'cubic-bezier(.55,0,.6,1)', fill: 'forwards' });
        this.layer.classList.add('is-moving');
        await new Promise(r => setTimeout(r, m.outMs * 0.55));
        await this.enterView(to);
        const zin = back ? 1.22 : 0.86;
        await this.world.animate([
          { transform: `scale(${zin}) translate3d(${drift * 0.6}px,0,0)`, filter: `blur(${m.blurPx}px)`, opacity: 0 },
          { transform: 'none', filter: 'blur(0px)', opacity: 1 }
        ], { duration: m.inMs, easing: 'cubic-bezier(.16,.8,.25,1)' }).finished.catch(() => { });
        out.cancel(); this.snap.hidden = true;
        this.layer.classList.remove('is-moving');
      }
      this.busy = false;
      if (opts.select != null) setTimeout(() => this.select(opts.select), this.reduced ? 0 : 120);
      this.kick();
    }

    /* ---------------------------------------------------------------- pre-rendered camera moves (scene/render_moves.py)
       Each move has a 'day' set (golden hour, f###.webp) and a 'night' set (n###.webp). The player grades the day
       frames toward the clock and lays the night frames over them by how dark it is, like the passes compositor.
       Only the sets the current light needs are downloaded. Phones (rail_m) keep the fake move. */
    moveMix() {
      const s = this.light, w = Math.max(0, Math.min(1, (s.night - 0.08) / 0.7));
      return { night: w, day: w < 0.98, nightOn: w > 0.02 };
    }
    moveFramesFor(name, variant) {
      const m = this.moves && this.moves[name]; if (!m || !(m.variants || ['day']).includes(variant)) return null;
      const key = name + ':' + variant;
      if (!this.moveFrames[key]) {
        const base = A.config.assetBase.replace(/views\/$/, 'moves/') + name + '/', pre = variant === 'night' ? 'n' : 'f';
        this.moveFrames[key] = Array.from({ length: m.frames }, (_, i) => { const im = new Image(); im.decoding = 'async'; im.src = base + pre + String(i).padStart(3, '0') + '.webp'; return im; });
      }
      return this.moveFrames[key];
    }
    preloadMoves() {
      const mix = this.moveMix(), base = A.config.assetBase;
      Object.keys(this.moves || {}).forEach(name => {
        if (this.isMobile !== name.startsWith('rail_m-')) return;
        if (mix.day) this.moveFramesFor(name, 'day'); if (mix.nightOn) this.moveFramesFor(name, 'night');
        const m = this.moves[name]; [m.from_, m.to].forEach(v => { if (A.sprites && A.sprites[v]) new Image().src = base + v + '/drop.webp'; });
      });
    }
    findMove(from, to) {
      const mix = this.moveMix();
      const ready = name => {
        const need = [];
        if (mix.day) need.push(this.moveFramesFor(name, 'day'));
        if (mix.nightOn) need.push(this.moveFramesFor(name, 'night'));
        if (mix.night > 0.5 && !need[need.length - 1]) return false;            // a golden-hour flight into a night room would jar
        const sets = need.filter(Boolean);
        return sets.length > 0 && sets.every(f => f.every(im => im.complete && im.naturalWidth));
      };
      if (ready(`${from}-${to}`)) return { name: `${from}-${to}`, reverse: false };
      if (ready(`${to}-${from}`)) return { name: `${to}-${from}`, reverse: true };
      return null;
    }
    async playMove(mv, to) {
      const mix = this.moveMix(), m = this.moves[mv.name];
      const day = mix.day && this.moveFramesFor(mv.name, 'day'), night = mix.nightOn && this.moveFramesFor(mv.name, 'night');
      const n = m.frames, fps = m.fps || 30;
      const c = this.snap, ctx = this.snapCtx, dpr = Math.min(window.devicePixelRatio || 1, 2);
      const W = this.stage.clientWidth, H = this.stage.clientHeight;
      c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
      // day frames are golden hour: multiply toward the clock (same grade as the beauty fallback)
      const g = A.Compositor.beautyGrade(this.light), gmax = Math.max(1, g[0], g[1], g[2]);
      const mul = `rgb(${g.map(x => Math.round(Math.min(1, x / gmax) * 255)).join(',')})`;
      const nb = 0.8 + 0.2 * Math.min(1, (this.light.lamp ? (this.light.lamp[0] || this.light.lamp) : 0) / 0.85);
      c.style.filter = gmax > 1 ? `brightness(${(1 + (gmax - 1) * (1 - mix.night)).toFixed(3)})` : '';
      const cover = im => {
        const ia = im.naturalWidth / im.naturalHeight, ca = c.width / c.height;
        let sw = im.naturalWidth, sh = im.naturalHeight, sx = 0, sy = 0;
        if (ca > ia) { sh = sw / ca; sy = (im.naturalHeight - sh) / 2; } else { sw = sh * ca; sx = (im.naturalWidth - sw) / 2; }
        return [sx, sy, sw, sh, 0, 0, c.width, c.height];
      };
      const draw = k => {
        ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
        if (day) {
          ctx.drawImage(day[k], ...cover(day[k]));
          if (mul !== 'rgb(255,255,255)') { ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = mul; ctx.fillRect(0, 0, c.width, c.height); ctx.globalCompositeOperation = 'source-over'; }
        }
        if (night) {
          ctx.globalAlpha = day ? mix.night : 1;
          ctx.filter !== undefined && nb < 0.999 && (ctx.filter = `brightness(${nb.toFixed(3)})`);
          ctx.drawImage(night[k], ...cover(night[k]));
          if (ctx.filter !== undefined) ctx.filter = 'none';
          ctx.globalAlpha = 1;
        }
      };
      const idx = k => mv.reverse ? n - 1 - k : k;
      // garments fly along: the frames are rendered without them, the live garment layer follows the projected
      // hangers frame by frame (moves.json track). Older moves without a track hide the garments instead.
      const tr = !this.plate && m.track && m.track.length === n ? m.track : null;
      const ref = (day || night)[0], iw = ref.naturalWidth, ih = ref.naturalHeight;
      const cv = cover(ref).map(x => x);   // [sx, sy, sw, sh, ...] in image pixels
      const proxy = { cssW: W, cssH: H, toScreen: (u, v) => [(u * iw - cv[0]) / cv[2] * W, (v * ih - cv[1]) / cv[3] * H] };
      const sb = v => A.sprites && A.sprites[v] && A.sprites[v].drop && A.sprites[v].drop.box;
      const sA = sb(m.from_), sB = sb(m.to);
      const dropAt = j => {
        const b = tr[j].drop; if (!b) return null;
        const t = j / (n - 1), a0 = tr[0].drop, b0 = tr[n - 1].drop;
        return b.map((x, q) => x + (sA && a0 ? (1 - t) * (sA[q] - a0[q]) : 0) + (sB && b0 ? t * (sB[q] - b0[q]) : 0));
      };
      const dropSrc = j => { const v = j / (n - 1) < 0.5 ? m.from_ : m.to; return sb(v) ? A.config.assetBase + v + '/drop.webp' : null; };
      const fly = k => { if (tr) { const j = idx(k); this.rail.fly(tr[j], proxy, dropAt(j), dropSrc(j)); } };
      // the first frame is the current camera: fade it in
      draw(idx(0)); c.style.transform = ''; c.hidden = false;
      if (tr) { this.world.insertBefore(c, this.layer); c.style.zIndex = '0'; this.root.classList.add('is-flying'); fly(0); }
      else this.layer.classList.add('is-moving');
      await c.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 160, easing: 'ease-out', fill: 'forwards' }).finished.catch(() => { });
      await new Promise(res => {
        const t0 = performance.now();
        const tick = now => {
          const k = Math.max(0, Math.min(n - 1, Math.floor((now - t0) / 1000 * fps)));   // rAF time can precede t0
          draw(idx(k)); fly(k);
          if (k < n - 1) requestAnimationFrame(tick); else res();
        };
        requestAnimationFrame(tick);
      });
      await this.enterView(to);
      this.comp.render(this.light);
      c.getAnimations().forEach(a => a.cancel());
      this.root.classList.remove('is-flying');
      await c.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 280, easing: 'ease-out' }).finished.catch(() => { });
      c.hidden = true; c.style.filter = ''; c.style.zIndex = ''; this.layer.classList.remove('is-moving');
      if (c.parentNode !== this.stage || c.previousElementSibling !== this.world) this.world.after(c);
    }

    updateChips() {
      this.chips.querySelectorAll('button').forEach(b => {
        const vk = this.viewKey.split('@')[0];
        const on = b.dataset.view === vk || (b.dataset.view === 'rail' && vk === 'rail_m');
        b.setAttribute('aria-current', on ? 'true' : 'false');
      });
      this.bedSvg.style.display = this.viewKey === 'room' ? '' : 'none';
      const magOn = this.viewKey === 'bed' && !!this.mag && !!(this.views.bed && this.views.bed.magazine);
      this.magSvg.style.display = magOn ? '' : 'none'; this.magGlint.classList.toggle('is-on', magOn);
      if (!magOn) this.magLabel.classList.remove('is-on');
      this.tease.classList.toggle('is-on', this.viewKey === 'bed');
    }

    /* ---------------------------------------------------------------- selection + products */
    select(i) {
      if (this.plate) return this.selectPlate(i);
      if (i >= 0 && this.viewKey === 'room') {
        const rect = this.rail.garmentRect(i);
        return this.go(this.isMobile ? 'rail_m' : 'rail', { select: i, focus: rect ? [rect.left + rect.width / 2, rect.top + rect.height * 0.4] : null });
      }
      this.hideHint();
      this.rail.setSelected(i);
      this.snapPan = null;
      const sel = i >= 0 && A.products[i];
      this.setWorldDim(sel ? A.config.motion.select.dimRoom : 1, sel ? A.config.motion.select.blurRoom : 0);
      this.root.classList.toggle('has-selection', !!sel);
      if (i < 0) this.drop.close();
      this.kick();
    }
    async selectPlate(i) {
      const railKey = this.isMobile ? 'rail_m' : 'rail';
      this.hideHint();
      if (i >= 0 && this.viewKey === 'room') {
        const rect = this.rail.garmentRect(i);
        return this.go(railKey, { select: i, focus: rect ? [rect.left + rect.width / 2, rect.top + rect.height * 0.4] : null });
      }
      if (this.busy) return;
      let target = i >= 0 ? `${railKey}@${i}` : railKey;
      const ps = this.passes && this.passes[target];
      if (i >= 0 && !(ps && Object.keys(ps).length >= 7)) target = railKey;   // pose not rendered yet: select on the rail as it hangs
      if (this.viewKey === target && (target.includes('@') || this.rail.selected === i)) return;
      this.rail.setSelected(-1); this.rail.setHover(-1); this.root.classList.remove('has-selection');
      if (i >= 0 && this.viewKey !== railKey) await this.go(railKey);      // another one is out: hang it back first
      await this.go(target);
      if (i >= 0 && this.viewKey === target) { this.rail.setSelected(i); this.root.classList.add('has-selection'); }
      this.kick();
    }
    /* Garment under a stage point (scene2): reads the rendered id mask of the current view. -1 = none. */
    garmentAt(x, y) {
      const v = this.comp.view; if (!this.plate || !v || !v.idsImg) return -1;
      if (!v.idsData) {
        const im = v.idsImg, c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
        const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
        v.idsData = { w: c.width, h: c.height, data: g.getImageData(0, 0, c.width, c.height).data };
      }
      const d = v.idsData, [ox, oy, zx, zy] = this.comp.map;
      let u = ox + x / this.comp.cssW * zx, w = oy + y / this.comp.cssH * zy;
      const dep = this.depthAt(u, w), f = this.comp.focus || 0.6;      // the same parallax shift the shader applies
      u += this.parallax[0] * (dep - f); w += this.parallax[1] * (dep - f);
      const px = Math.floor(u * d.w), py = Math.floor(w * d.h);
      if (px < 0 || py < 0 || px >= d.w || py >= d.h) return -1;
      const id = Math.round(d.data[(py * d.w + px) * 4] / 32);
      return id >= 1 && id <= A.products.length ? id - 1 : -1;
    }
    onGarmentClick(i) {
      if (this.dragMoved) return;
      if (this.viewKey !== 'room' && this.rail.selected === i) return this.select(-1);
      this.select(i);
    }
    onHover(i) {
      if (i >= 0) this.hideHint();
      if (this.plate && i >= 0 && !this.isMobile) {
        const k = (this.viewKey === 'room' ? 'rail' : this.viewKey.split('@')[0]) + '@' + i;
        if (!this.comp.cache[k] && this.passes[k] && Object.keys(this.passes[k]).length >= 7) this.comp.load(k, this.passes, false);
      }
      this.stage.classList.toggle('is-pointing', i >= 0);
      this.kick();
    }
    /* ANSTOSS: from anywhere, walk to the bed first, then the magazine opens out of its place on the duvet. */
    async openMag() {
      if (!this.mag || this.mag.isOpen) return;
      if (this.viewKey !== 'bed') {
        if (!this.plate) this.select(-1);
        const r = this.bedPoly.getBoundingClientRect();
        await this.go('bed', this.viewKey === 'room' && r.width ? { focus: [r.left + r.width / 2, r.top + r.height / 2] } : {});
        this.placeChrome();
      }
      const r = this.magSvg.style.display !== 'none' ? this.magPoly.getBoundingClientRect() : null;
      this.mag.open(r && r.width > 2 ? r : null);
    }
    showOnRail(i) {
      if (this.plate) return this.select(i);
      this.go(this.isMobile ? 'rail_m' : 'rail', { select: i });
    }
    openProduct(i) {
      const p = A.products[i]; if (!p) return;
      this.shop.open(p, this.rail.garmentRect(i));
    }
    afterProductClose() { const s = this.rail.selected; if (s >= 0) this.rail.items[s].hit.focus({ preventScroll: true }); }
    setWorldDim(d = 1, blur = 0) {
      if (this.rail.selected >= 0 && d === 1) { d = A.config.motion.select.dimRoom; blur = A.config.motion.select.blurRoom; }
      this.dimTarget = d;
      this.canvas.style.filter = blur ? `blur(${blur}px)` : '';
      this.fallbackImg.style.filter = this.canvas.style.filter;
      this.kick();
    }
    setCartCount(n) { if (this.cartBtn) this.cartBtn.querySelector('span').textContent = n; }
    bumpCart() { this.cartBtn.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.12)' }, { transform: 'scale(1)' }], { duration: 420 }); }

    /* ---------------------------------------------------------------- depth (same values the shader sees) */
    encDepth(metres) { return lin2srgb(Math.max(0, Math.min(1, (DEPTH.far - metres) / (DEPTH.far - DEPTH.near)))); }
    async loadDepth(key) {
      if (this.depthMaps[key] !== undefined) return;
      this.depthMaps[key] = null;
      const im = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = A.config.assetBase + key + '/depth.png'; });
      if (!im) return;
      const c = document.createElement('canvas'); const w = 200, h = Math.round(200 * im.naturalHeight / im.naturalWidth);
      c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(im, 0, 0, w, h);
      this.depthMaps[key] = { w, h, data: x.getImageData(0, 0, w, h).data };
    }
    depthAt(u, v, metres) {
      if (metres != null) return this.encDepth(metres);
      const d = this.depthMaps[this.viewKey];
      if (!d) return this.comp.focus || 0.6;
      const x = Math.max(0, Math.min(d.w - 1, Math.round(u * (d.w - 1)))), y = Math.max(0, Math.min(d.h - 1, Math.round(v * (d.h - 1))));
      return d.data[(y * d.w + x) * 4] / 255;
    }

    /* ---------------------------------------------------------------- chrome: header, view chips, hint, bed, window */
    buildChrome() {
      const c = A.config.copy;
      const head = $('.azur-head');
      this.cartBtn = head.querySelector('.azur-head__cart');
      this.cartBtn.addEventListener('click', () => this.shop.toggleCart());
      head.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => {
        e.preventDefault(); const t = a.dataset.go;
        if (t === 'rail') this.go(this.isMobile ? 'rail_m' : 'rail'); else if (t === 'mag') this.openMag(); else this.go(t);
      }));
      this.chips = $('.azur-views');
      this.chips.addEventListener('click', e => {
        const b = e.target.closest('button[data-view]'); if (!b) return;
        let v = b.dataset.view; if (v === 'rail' && this.isMobile) v = 'rail_m';
        if (!this.plate) this.select(-1);
        this.go(v);
      });
      this.hint = $('.azur-hint'); this.hint.textContent = this.isMobile ? c.hintMobile : c.hintDesktop;
      this.tease = $('.azur-tease'); this.tease.textContent = c.bedTease;
      // bed hotspot (room view)
      this.bedSvg = $('.azur-bed');
      this.bedPoly = this.bedSvg.querySelector('polygon');
      const goBed = () => { if (!this.plate) this.select(-1); const r = this.bedPoly.getBoundingClientRect(); this.go('bed', { focus: [r.left + r.width / 2, r.top + r.height / 2] }); };
      this.bedSvg.querySelector('a').addEventListener('click', e => { e.preventDefault(); goBed(); });
      this.bedSvg.querySelector('a').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goBed(); } });
      this.bedLabel = $('.azur-bedlabel');
      const showBed = on => {
        if (on) { const r = this.bedPoly.getBoundingClientRect(), s = this.stage.getBoundingClientRect();
          this.bedLabel.style.left = (r.left - s.left + r.width / 2) + 'px'; this.bedLabel.style.top = (Math.max(r.top - s.top, 60) + 10) + 'px'; }
        this.bedLabel.classList.toggle('is-on', on);
      };
      this.bedSvg.querySelector('a').addEventListener('pointerenter', () => showBed(true));
      this.bedSvg.querySelector('a').addEventListener('pointerleave', () => showBed(false));
      this.bedSvg.querySelector('a').addEventListener('focus', () => showBed(true));
      this.bedSvg.querySelector('a').addEventListener('blur', () => showBed(false));
      // the ANSTOSS magazine on the duvet (bed view) opens the brand story + lookbook
      this.magSvg = $('.azur-magspot'); this.magPoly = this.magSvg.querySelector('polygon');
      this.magLabel = $('.azur-maglabel'); this.magLabel.textContent = c.magSpot; this.magGlint = $('.azur-magglint');
      const ma = this.magSvg.querySelector('a');
      ma.addEventListener('click', e => { e.preventDefault(); this.openMag(); });
      ma.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.openMag(); } });
      const showMag = on => {
        if (on) { const r = this.magPoly.getBoundingClientRect(), s = this.stage.getBoundingClientRect();
          this.magLabel.style.left = (r.left - s.left + r.width / 2) + 'px'; this.magLabel.style.top = (r.bottom - s.top + 10) + 'px'; }
        this.magLabel.classList.toggle('is-on', on);
      };
      ['pointerenter', 'focus'].forEach(ev => ma.addEventListener(ev, () => showMag(true)));
      ['pointerleave', 'blur'].forEach(ev => ma.addEventListener(ev, () => showMag(false)));
      // scene2: real footage of the Bolzplatz across the street plays behind the window glass (the compositor masks it)
      if (this.plate && this.comp.ok) {
        const vid = document.createElement('video');
        Object.assign(vid, { muted: true, loop: true, playsInline: true, preload: 'auto' });
        vid.setAttribute('muted', ''); vid.setAttribute('playsinline', ''); vid.setAttribute('aria-hidden', 'true');
        const ob = A.config.assetBase.replace(/views\/$/, 'outside/');
        [['bolzplatz.webm', 'video/webm'], ['bolzplatz.mp4', 'video/mp4']].forEach(([f, t]) => {
          const so = document.createElement('source'); so.src = ob + f; so.type = t; vid.appendChild(so); });
        Object.assign(vid.style, { position: 'absolute', width: '2px', height: '2px', opacity: '0', pointerEvents: 'none', left: '0', top: '0' });
        this.root.appendChild(vid); this.comp.video = vid; this.video = vid;
      }
      // the neighbour's kid crosses the park outside the window now and then
      this.windowEl = $('.azur-window');
      this.kidTrack = $('.azur-kid-track');
      this.kidTrack.addEventListener('animationend', e => { if (e.target === this.kidTrack) this.kidTrack.classList.remove('is-run', 'is-back'); });
      this.scheduleKid(5000 + Math.random() * 5000);
    }
    scheduleKid(ms) {
      clearTimeout(this.kidTimer);
      this.kidTimer = setTimeout(() => { this.runKid(); this.scheduleKid(22000 + Math.random() * 38000); }, ms);
    }
    runKid() {
      const t = this.kidTrack, w = this.windowEl;
      if (!t || this.reduced || document.hidden || w.hidden || !(+w.style.opacity > 0.2) || t.classList.contains('is-run')) return;
      const far = Math.random();            // further away: smaller, higher in the window, slower across it
      t.style.setProperty('--kid-s', (6 + far * 4).toFixed(1) + 's');
      t.style.setProperty('--kid-h', (0.15 - far * 0.05).toFixed(3));
      t.style.setProperty('--kid-y', (7 + far * 6).toFixed(1) + '%');
      t.classList.toggle('is-back', Math.random() < 0.5);
      void t.offsetWidth; t.classList.add('is-run');
    }

    placeChrome() {
      const comp = this.comp, v = this.views[this.viewKey] || {}, vc = A.config.views[this.viewKey] || {};
      // bed hotspot
      if (this.viewKey === 'room' && vc.bedHotspot) {
        const W = this.stage.clientWidth, H = this.stage.clientHeight;
        this.bedSvg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        const pts = vc.bedHotspot.map(([u, w]) => comp.toScreen(u, w, this.depthAt(u, Math.min(0.99, w))));
        this.bedPoly.setAttribute('points', pts.map(p => p.map(n => n.toFixed(1)).join(',')).join(' '));
      }
      // magazine hotspot + a slow glint on its cover (bed view)
      if (this.viewKey === 'bed' && v.magazine && this.magSvg) {
        const W = this.stage.clientWidth, H = this.stage.clientHeight;
        this.magSvg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        const cu = v.magazine.reduce((a, p) => a + p[0], 0) / 4, cw = v.magazine.reduce((a, p) => a + p[1], 0) / 4, d = this.depthAt(cu, cw);
        const pts = v.magazine.map(([u, w]) => comp.toScreen(u, w, d));
        this.magPoly.setAttribute('points', pts.map(p => p.map(n => n.toFixed(1)).join(',')).join(' '));
        const g = comp.toScreen(cu, cw, d);
        this.magGlint.style.transform = `translate3d(${g[0].toFixed(1)}px, ${g[1].toFixed(1)}px, 0)`;
      }
      // window: clip a small exterior layer to the glass so the kid stays behind it
      const win = v.window;
      if (win && win.every(p => p[0] > -0.3 && p[0] < 1.3) && !this.isMobileView()) {
        const d = this.depthAt((win[0][0] + win[2][0]) / 2, (win[0][1] + win[2][1]) / 2);
        const pts = win.map(([u, w]) => comp.toScreen(u, w, d));
        const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
        const x0 = Math.min(...xs), y0 = Math.min(...ys), x1 = Math.max(...xs), y1 = Math.max(...ys);
        const el = this.windowEl;
        el.hidden = false;
        el.style.transform = `translate3d(${x0.toFixed(1)}px, ${y0.toFixed(1)}px, 0)`;
        el.style.width = (x1 - x0) + 'px'; el.style.height = (y1 - y0) + 'px';
        el.style.clipPath = `polygon(${pts.map(p => `${(p[0] - x0).toFixed(1)}px ${(p[1] - y0).toFixed(1)}px`).join(',')})`;
        el.style.setProperty('--wh', (y1 - y0) + 'px');
      } else this.windowEl.hidden = true;
    }
    isMobileView() { return this.viewKey === 'rail_m'; }

    /* phones: the pan value that puts garment i in the middle of the screen, and the garment nearest the middle */
    panSpan() { return this.stage.clientWidth * (1 / this.comp.map[2] - 1) || 1; }
    panFor(i) {
      const p = this.rail.px && this.rail.px[i]; if (!p) return null;
      return Math.max(0, Math.min(1, this.pan + (p.x - this.stage.clientWidth / 2) / this.panSpan()));
    }
    nearestGarment() {
      const px = this.rail.px || [], mid = this.stage.clientWidth / 2;
      let best = -1, bd = 1e9;
      px.forEach((p, i) => { if (p && Math.abs(p.x - mid) < bd) { bd = Math.abs(p.x - mid); best = i; } });
      return best;
    }

    showHint() {
      if (this.hintDone) return;
      const p = this.rail.px && this.rail.px.filter(Boolean);
      if (p && p.length) {
        const x = (p[0].x + p[p.length - 1].x) / 2, y = Math.max(...p.map(q => q.y + q.h)) + 18;
        this.hint.style.transform = `translate3d(${x.toFixed(0)}px, ${Math.min(y, this.stage.clientHeight - 70).toFixed(0)}px, 0) translateX(-50%)`;
      }
      this.hint.classList.add('is-on');
      this.hintTimer = setTimeout(() => this.hideHint(), 11000);
    }
    hideHint() { if (this.hintDone) return; this.hintDone = true; this.hint.classList.remove('is-on'); clearTimeout(this.hintTimer); }

    /* ---------------------------------------------------------------- pointer, swipe, keys */
    bindPointer() {
      const st = this.stage;
      let last = null, down = null;
      st.addEventListener('pointermove', e => {
        const r = st.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
        const now = performance.now();
        const vx = last ? (x - last.x) / Math.max(8, now - last.t) * 1000 : 0;
        last = { x, y, t: now };
        if (e.pointerType !== 'touch') {
          this.parallaxTarget = [(x / r.width - 0.5) * 2, (y / r.height - 0.5) * 2];
          this.rail.pointerMove(x, y, vx);
        }
        if (down && this.viewKey === 'rail_m') {
          const dx = x - down.x;
          if (Math.abs(dx) > 6) this.dragMoved = true;
          const span = this.panSpan(), raw = down.pan - dx / span;
          // rubber band past the ends
          this.pan = Math.max(-0.05, Math.min(1.05, raw < 0 ? raw * 0.25 : raw > 1 ? 1 + (raw - 1) * 0.25 : raw));
          this.panVel = -vx / span;
          this.rail.panImpulse(vx);
          this.kick();
        }
      });
      st.addEventListener('pointerleave', () => { this.parallaxTarget = [0, 0]; this.rail.pointerLeave(); last = null; });
      st.addEventListener('pointerdown', e => {
        if (e.target.closest('.azur-drop, .azur-info, .azur-views, .azur-head')) return;
        const r = st.getBoundingClientRect();
        down = { x: e.clientX - r.left, pan: this.pan }; this.dragMoved = false;
        this.dragging = true; this.snapPan = null; this.panVel = 0;
      });
      window.addEventListener('pointerup', () => { down = null; this.dragging = false; setTimeout(() => { this.dragMoved = false; }, 0); });
      window.addEventListener('pointercancel', () => { down = null; this.dragging = false; this.dragMoved = false; });
      // phones: tilt the room very slightly with a slow drift instead of a pointer
      if (this.isMobile) this.parallaxTarget = [0, 0];
      // click on the empty room deselects
      st.addEventListener('click', e => {
        if (e.target.closest('.azur-drop, .azur-info, .azur-views, .azur-head, .azur-panel')) return;
        if (this.plate) {
          if (this.dragMoved || e.target.closest('.azur-bed')) return;
          const r = st.getBoundingClientRect(), id = this.garmentAt(e.clientX - r.left, e.clientY - r.top);
          if (id >= 0) return this.onGarmentClick(id);
          if (this.viewKey.includes('@')) this.select(-1);
          return;
        }
        if (e.target.closest('.azur-g, .azur-bed')) return;
        if (this.rail.selected >= 0) this.select(-1);
      });
    }

    bindKeys() {
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
          if (this.shop.pdp.classList.contains('is-on')) return this.shop.close();
          if (this.shop.drawer.classList.contains('is-on')) return this.shop.toggleCart(false);
          if (this.drop.card.classList.contains('is-on')) { this.drop.hideCard(); return this.select(-1); }
          if (this.rail.selected >= 0) return this.select(-1);
          if (this.viewKey !== 'room' && !this.isMobile) return this.go('room');
        }
      });
    }

    handleHash() {
      const h = decodeURIComponent(location.hash.slice(1));
      if (!h) return;
      const i = A.products.findIndex(p => p.handle === h);
      if (i >= 0) this.go(this.isMobile ? 'rail_m' : 'rail', { select: i });
      else if (h === 'bett') this.go('bed');
      else if (h === 'anstoss') this.openMag();
    }

    /* ---------------------------------------------------------------- loop */
    resize() {
      const w = this.stage.clientWidth, h = this.stage.clientHeight, dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.comp.pan = this.pan;
      this.comp.layout(w, h, dpr);
      this.rail.place(); this.placeChrome();
      this.dirty = true; this.kick();
    }
    kick() { this.dirty = true; }

    frame(t) {
      const dt = Math.min(0.05, (t - this.lastT) / 1000); this.lastT = t;
      if (document.hidden) { requestAnimationFrame(tt => this.frame(tt)); return; }
      const cfg = A.config;
      // light: follow the clock (cheap, once a second) or the design panel
      if (t - this.lightAt > 1000 || this.lightDirty) {
        this.lightAt = t; this.lightDirty = false;
        this.light = A.light.current(); this.rail.applyLight(this.light); this.applyAmbient(); this.dirty = true;
      }
      // parallax eases toward the pointer; phones drift very slowly so the room still feels spatial
      const vc = cfg.views[this.viewKey] || {}, k = this.reduced ? 0 : (vc.parallax || 0.01) * cfg.motion.intensity;
      let tx = this.parallaxTarget[0], ty = this.parallaxTarget[1];
      if (this.isMobile && !this.reduced) { const s = t / 1000; tx = Math.sin(s * 0.21) * 0.6; ty = Math.sin(s * 0.17) * 0.3; }
      const e = cfg.motion.parallaxEase;
      const nx = this.parallax[0] + (-tx * k - this.parallax[0]) * e, ny = this.parallax[1] + (-ty * k * 0.6 - this.parallax[1]) * e;
      const pmove = Math.abs(nx - this.parallax[0]) + Math.abs(ny - this.parallax[1]) > 1e-6;
      this.parallax = [nx, ny]; this.comp.parallax = this.parallax;
      // phones: momentum after a swipe along the rail, then the rail settles with a garment in the middle
      if (this.viewKey === 'rail_m' && !this.dragging) {
        const W = this.stage.clientWidth;
        if (Math.abs(this.panVel) > 0.05 && !this.reduced && this.pan >= 0 && this.pan <= 1) {
          const p = this.pan + this.panVel * dt, c = Math.max(0, Math.min(1, p));
          if (c !== p) this.panVel *= -0.25;                      // soft stop at the ends
          this.pan = c; this.panVel *= Math.pow(0.05, dt); this.snapPan = null;
          this.rail.panImpulse(-this.panVel * W); this.dirty = true;
        } else {
          this.panVel = 0;
          if (this.snapPan == null) this.snapPan = this.panFor(this.rail.selected >= 0 ? this.rail.selected : this.nearestGarment());
          const d = this.snapPan == null ? 0 : this.snapPan - this.pan;
          if (Math.abs(d) > 2e-4) {
            const step = this.reduced ? d : d * Math.min(1, dt * 7);
            this.pan += step; this.rail.panImpulse(-(step / Math.max(dt, 1e-3)) * W * 0.6); this.dirty = true;
          }
        }
      }
      if (this.comp.pan !== this.pan) { this.comp.pan = this.pan; this.comp.layout(this.stage.clientWidth, this.stage.clientHeight, Math.min(window.devicePixelRatio || 1, 2)); this.dirty = true; }
      // selection dims the room smoothly
      const dT = this.dimTarget == null ? 1 : this.dimTarget;
      if (Math.abs(this.comp.dim - dT) > 0.002) { this.comp.dim += (dT - this.comp.dim) * Math.min(1, dt * 6); this.dirty = true; }
      if (this.plate) this.stepPlate(dt);
      if (pmove || this.dirty) { this.rail.place(); this.placeChrome(); }
      this.rail.step(dt, this.reduced);
      if (this.dirty || pmove) { this.comp.render(this.light); this.dirty = false; }
      requestAnimationFrame(tt => this.frame(tt));
    }

    /* scene2: the hovered garment brightens in the render; the outdoor video runs while it is light outside. */
    stepPlate(dt) {
      const c = this.comp, h = this.rail.hover;
      if (h >= 0) c.hover = h + 1;
      const target = h >= 0 && !this.viewKey.includes('@') ? 1 : 0;
      const ha = c.hoverAmt + (target - c.hoverAmt) * Math.min(1, dt * 9);
      if (Math.abs(ha - c.hoverAmt) > 1e-3) { c.hoverAmt = ha; this.dirty = true; } else c.hoverAmt = target;
      const vid = this.video, hasWin = c.view && c.view.win;
      const wa = hasWin ? Math.max(0, Math.min(1, (this.light.window - 0.35) / 0.5)) : 0;
      if (Math.abs(wa - c.winAmt) > 1e-3) { c.winAmt += (wa - c.winAmt) * Math.min(1, dt * 3); this.dirty = true; }
      if (!vid) return;
      if (c.winAmt > 0.01 && !document.hidden && !(this.mag && this.mag.isOpen)) {   // the room rests while the magazine is open
        if (vid.paused && !this.reduced) vid.play().catch(() => { });
        if (!vid.paused) this.dirty = true;                     // new video frames
      } else if (!vid.paused) vid.pause();
    }

    /* UI follows the room's light: labels switch to night styling after dusk. */
    applyAmbient() {
      const s = this.light, r = this.root;
      r.style.setProperty('--night-amt', s.night.toFixed(3));
      r.classList.toggle('is-night', s.night > 0.5);
      const kid = this.windowEl;
      if (kid) kid.style.opacity = Math.max(0, Math.min(1, (s.window - 0.45) * 2)).toFixed(2);
      if (this.comp) {   // outdoor footage follows the daylight a little (it was filmed on a bright afternoon)
        const sk = s.sky, g = c => Math.min(1.05, 0.2 + 0.85 * c);   // dusk turns the footage dark and blue
        const warm = Array.isArray(s.sunLow) ? Math.min(1, (s.sunLow[0] || 0)) : 0;
        this.comp.videoGrade = [g(sk[0]) * (1 + 0.06 * warm), g(sk[1]) * (0.98 - 0.02 * warm), g(sk[2]) * (0.95 - 0.1 * warm)];
      }
      if (this.panel) this.panel.sync(s);
    }
  }

  A.App = App;
  const boot = () => { A.app = new App(); A.app.init().catch(err => { console.error(err); document.documentElement.classList.add('azur-error'); }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
