/* AZUR — app: views, camera moves, pointer, phones, window, header, loop.
   Desktop starts in the room (establishing shot). A click on a jersey opens its product view right away (half the
   page the jersey to turn and zoom, half the page to buy); hovering shows a small label. The bed and the rail light
   up in white when the pointer is on them and take the camera there; white dots invite the click. The magazine on
   the duvet opens ANSTOSS. Phones start at the rail and swipe along it. The room follows the visitor's clock:
   light passes mix by the hour, and the things in the room change with the time of day (scene3). */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const $ = (s, r = document) => r.querySelector(s);
  const fetchJSON = url => fetch(url, { cache: 'no-cache' }).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const getJSON = p => (A.config.inline && A.config.inline[p]) ? Promise.resolve(A.config.inline[p]) : fetchJSON(A.url(p));
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

      // scene3: the room through the day, jerseys on real hangers, hover outlines; scene2: jerseys in the renders
      const exists = b => (cfg.inline && cfg.inline[b + 'passes.json']) ? Promise.resolve(true)
        : fetch(A.url(b + 'passes.json'), { cache: 'no-cache' }).then(r => r.ok).catch(() => false);
      const s3 = cfg.scene3Base || 'assets/scene3/views/', s2 = cfg.scene2Base || 'assets/scene2/views/';
      if (cfg.useScene3 !== false && await exists(s3)) { cfg.assetBase = s3; cfg.plateGarments = true; cfg.scene3 = true; }
      else if (cfg.useScene2 !== false && await exists(s2)) { cfg.assetBase = s2; cfg.plateGarments = true; }
      this.root.classList.toggle('is-scene3', !!cfg.scene3);
      this.plate = !!cfg.plateGarments;
      this.root.classList.toggle('is-plate', this.plate);
      const base = cfg.assetBase;
      [this.views, this.passes, A.sprites, this.moves] = await Promise.all([getJSON(base + 'views.json'), getJSON(base + 'passes.json'),
        this.plate ? Promise.resolve({}) : getJSON(base + 'sprites.json'), getJSON(base.replace(/views\/$/, 'moves/') + 'moves.json')]);
      this.moveFrames = {};
      this.outside = this.plate ? await getJSON(base.replace(/views\/$/, 'outside/') + 'outside.json') : {};   // round 4: the boy outside
      this.comp = new A.Compositor(this.canvas);
      this.comp.viewsData = this.views; this.comp.onChange = () => this.kick();
      this.root.classList.toggle('no-webgl', !this.comp.ok);
      this.glowAmt = [0, 0, 0]; this.region = null;
      this.dayState = cfg.scene3 ? this.stateNow() : 'day';
      this.comp.state = this.dayState; this.root.dataset.state = this.dayState;
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
      if ('IntersectionObserver' in window) new IntersectionObserver(([en]) => {
        this.offscreen = !en.isIntersecting;
        if (this.video && this.offscreen && !this.video.paused) this.video.pause();
        if (!this.offscreen) this.kick();
      }).observe(this.root);
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
      const up = v => v && v.upgrade && v.upgrade();
      setTimeout(() => up(this.comp.view), 900);                   // published builds start on smaller copies
      // other views load in the background so camera moves never wait (each view is 8 textures: phones load on demand,
      // desktops skip the phone plate)
      if (!this.isMobile) setTimeout(() => Object.keys(cfg.views).forEach(k => k !== start && k !== 'rail_m' && this.comp.load(k, this.passes, false).then(() => { this.loadDepth(k); setTimeout(() => up(this.comp.cache[k]), 1500); })), 2500);
      setTimeout(() => this.preloadMoves(), 6000);
      this.handleHash();
      window.addEventListener('hashchange', () => this.handleHash());    // links inside the page (#bett, #anstoss, a jersey)
    }

    /* ---------------------------------------------------------------- times of day (scene3) */
    stateNow() {
      const o = A.light.overrides, d = new Date();
      const h = o && o.timeHours != null ? o.timeHours : d.getHours() + d.getMinutes() / 60;
      const list = A.config.dayStates || []; let st = list.length ? list[list.length - 1].state : 'day';
      list.forEach(e => { if (h >= e.from) st = e.state; });
      return st;
    }
    /* The room changes while it is open (or the design panel's clock moves): the change crossfades. */
    async changeState(st) {
      if (!A.config.scene3 || st === this.dayState || this.stateBusy) return;
      this.stateBusy = true; this.dayState = st; this.root.dataset.state = st;
      const fade = !this.reduced && !this.busy && this.comp.ok && this.root.classList.contains('is-ready');
      if (fade) {
        this.comp.render(this.light); this.comp.snapshotInto(this.snapCtx);
        Object.assign(this.snap.style, { transform: '', filter: '', opacity: '1' }); this.snap.hidden = false;
      }
      await this.comp.setState(st);
      this.comp.render(this.light); this.placeChrome(); this.setTease(); this.kick();
      if (fade) { await this.snap.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 900, easing: 'ease-in-out' }).finished.catch(() => { }); this.snap.hidden = true; }
      this.stateBusy = false;
    }

    /* The line under the bed view: at night the magazine has slid off the duvet onto the floor. */
    setTease() {
      const c = A.config.copy, night = A.config.scene3 && this.dayState === 'night';
      if (this.tease) this.tease.textContent = night && c.bedTeaseNight ? c.bedTeaseNight : c.bedTease;
    }

    applyPalette() {
      if (A.config.shopify) return;                   // the theme CSS carries palette A, scoped to the room
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
      this.useClip(key);
      const v = this.viewData(key);
      const mode = await this.comp.load(key, this.passes);
      if (this.comp.view && !this.comp.view.size && v.res) this.comp.view.size = v.res.slice();   // plate not rendered yet: keep its geometry
      this.root.dataset.view = key; this.root.dataset.mode = mode;
      this.fallbackImg.hidden = !(mode === 'beauty' && !this.comp.ok);
      if (!this.comp.ok && mode === 'beauty') this.fallbackImg.src = A.url(A.config.assetBase + key + '/beauty.webp');
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
      if (this.busy) {                     // a flight is on: the newest wish waits for it to land (the magazine asked
        this.nextGo = to; await this.flight;   // for mid-flight, a chip clicked during a move); older wishes are dropped
        if (this.nextGo !== to) return;
        this.nextGo = null; return this.go(to, opts);
      }
      if (to === this.viewKey) { if (opts.select != null) this.select(opts.select); return; }
      const fromBase = this.viewKey.split('@')[0];
      if (this.plate && this.viewKey.includes('@') && to !== fromBase && !to.startsWith(fromBase + '@')) {
        this.rail.setSelected(-1); this.root.classList.remove('has-selection');
        await this.go(fromBase);                                   // hang the garment back first
        return this.go(to, opts);
      }
      this.busy = true; this.hideHint();
      let land; this.flight = new Promise(r => { land = r; });
      try { await this.fly(to, opts); }
      finally {                                       // a failed load must never leave the room stuck in flight
        this.busy = false; land();
        this.root.classList.remove('is-loading', 'is-flying'); this.layer.classList.remove('is-moving');
      }
      if (opts.select != null) setTimeout(() => this.select(opts.select), this.reduced ? 0 : 120);
      this.kick();
    }

    /* The camera move itself (go() keeps one at a time). */
    async fly(to, opts) {
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
    }

    /* ---------------------------------------------------------------- pre-rendered camera moves (scene/render_moves.py)
       Each move has a 'day' set (golden hour, f###.webp) and a 'night' set (n###.webp). The player grades the day
       frames toward the clock and lays the night frames over them by how dark it is, like the passes compositor.
       Only the sets the current light needs are downloaded. Phones (rail_m) keep the fake move. */
    moveMix() {
      const s = this.light, w = Math.max(0, Math.min(1, (s.night - 0.08) / 0.7));
      // scene3: the evening has its own flights (golden hour, the school bag back on the floor)
      const base = A.config.scene3 && this.dayState === 'evening' ? 'evening' : 'day';
      return { night: w, day: w < 0.98, nightOn: w > 0.02, base };
    }
    baseFrames(name, mix) { return this.moveFramesFor(name, mix.base) || (mix.base !== 'day' ? this.moveFramesFor(name, 'day') : null); }
    moveFramesFor(name, variant) {
      const m = this.moves && this.moves[name]; if (!m || !(m.variants || ['day']).includes(variant)) return null;
      const key = name + ':' + variant;
      if (!this.moveFrames[key]) {
        const base = A.config.assetBase.replace(/views\/$/, 'moves/') + name + '/', pre = { night: 'n', evening: 'e' }[variant] || 'f';
        const img = src => { const im = new Image(); im.decoding = 'async'; im.src = src; return im; };
        if (m.atlas) {      // published build (tools/build_artifact.py): frames stacked in a few vertical strips
          const per = m.atlas.per, strips = Array.from({ length: Math.ceil(m.frames / per) }, (_, s) => img(A.url(`${base}${pre}_s${s}.webp`)));
          this.moveFrames[key] = Array.from({ length: m.frames }, (_, i) => {
            const s = Math.floor(i / per), inStrip = Math.min(per, m.frames - s * per), im = strips[s];
            return { im, get w() { return im.naturalWidth; }, get h() { return im.naturalHeight / inStrip; }, get y() { return (i % per) * this.h; } };
          });
        } else this.moveFrames[key] = Array.from({ length: m.frames }, (_, i) => {
          const im = img(A.url(base + pre + String(i).padStart(3, '0') + '.webp'));
          return { im, y: 0, get w() { return im.naturalWidth; }, get h() { return im.naturalHeight; } };
        });
      }
      return this.moveFrames[key];
    }
    preloadMoves() {
      const mix = this.moveMix(), base = A.config.assetBase;
      Object.keys(this.moves || {}).forEach(name => {
        if (this.isMobile !== name.startsWith('rail_m-')) return;
        if (mix.day) this.baseFrames(name, mix); if (mix.nightOn) this.moveFramesFor(name, 'night');
        const m = this.moves[name]; [m.from_, m.to].forEach(v => { if (A.sprites && A.sprites[v]) new Image().src = A.url(base + v + '/drop.webp'); });
      });
    }
    findMove(from, to) {
      const mix = this.moveMix();
      const ready = name => {
        const need = [];
        if (mix.day) need.push(this.baseFrames(name, mix));
        if (mix.nightOn) need.push(this.moveFramesFor(name, 'night'));
        if (mix.night > 0.5 && !need[need.length - 1]) return false;            // a golden-hour flight into a night room would jar
        const sets = need.filter(Boolean);
        return sets.length > 0 && sets.every(f => f.every(F => F.im.complete && F.im.naturalWidth));
      };
      if (ready(`${from}-${to}`)) return { name: `${from}-${to}`, reverse: false };
      if (ready(`${to}-${from}`)) return { name: `${to}-${from}`, reverse: true };
      return null;
    }
    async playMove(mv, to) {
      const mix = this.moveMix(), m = this.moves[mv.name];
      const day = mix.day && this.baseFrames(mv.name, mix), night = mix.nightOn && this.moveFramesFor(mv.name, 'night');
      const n = m.frames, fps = m.fps || 30;
      const c = this.snap, ctx = this.snapCtx, dpr = Math.min(window.devicePixelRatio || 1, 2);
      const W = this.stage.clientWidth, H = this.stage.clientHeight;
      c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
      // day frames are golden hour: multiply toward the clock (same grade as the beauty fallback)
      const g = A.config.scene3 ? [1, 1, 1] : A.Compositor.beautyGrade(this.light), gmax = Math.max(1, g[0], g[1], g[2]);   // scene3 frames match their time of day
      const mul = `rgb(${g.map(x => Math.round(Math.min(1, x / gmax) * 255)).join(',')})`;
      const nb = 0.8 + 0.2 * Math.min(1, (this.light.lamp ? (this.light.lamp[0] || this.light.lamp) : 0) / 0.85);
      c.style.filter = gmax > 1 ? `brightness(${(1 + (gmax - 1) * (1 - mix.night)).toFixed(3)})` : '';
      const pan = this.comp.pan, os = 1 / (1 + (this.comp.overscan || 0));
      const cover = F => {          // F: one frame (an image, or a slice of a strip); same fit, pan and overscan as the plates
        const ia = F.w / F.h, ca = c.width / c.height;
        let sw = F.w, sh = F.h;
        if (ca > ia) sh = sw / ca; else sw = sh * ca;
        sw *= os; sh *= os;
        return [(F.w - sw) * pan, (F.h - sh) / 2, sw, sh, 0, 0, c.width, c.height];
      };
      const blit = F => { const q = cover(F); ctx.drawImage(F.im, q[0], q[1] + F.y, q[2], q[3], q[4], q[5], q[6], q[7]); };
      const draw = k => {
        ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
        if (day) {
          blit(day[k]);
          if (mul !== 'rgb(255,255,255)') { ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = mul; ctx.fillRect(0, 0, c.width, c.height); ctx.globalCompositeOperation = 'source-over'; }
        }
        if (night) {
          ctx.globalAlpha = day ? mix.night : 1;
          ctx.filter !== undefined && nb < 0.999 && (ctx.filter = `brightness(${nb.toFixed(3)})`);
          blit(night[k]);
          if (ctx.filter !== undefined) ctx.filter = 'none';
          ctx.globalAlpha = 1;
        }
      };
      const idx = k => mv.reverse ? n - 1 - k : k;
      // garments fly along: the frames are rendered without them, the live garment layer follows the projected
      // hangers frame by frame (moves.json track). Older moves without a track hide the garments instead.
      const tr = !this.plate && m.track && m.track.length === n ? m.track : null;
      const ref = (day || night)[0], iw = ref.w, ih = ref.h;
      const cv = cover(ref).map(x => x);   // [sx, sy, sw, sh, ...] in image pixels
      const proxy = { cssW: W, cssH: H, toScreen: (u, v) => [(u * iw - cv[0]) / cv[2] * W, (v * ih - cv[1]) / cv[3] * H] };
      const sb = v => A.sprites && A.sprites[v] && A.sprites[v].drop && A.sprites[v].drop.box;
      const sA = sb(m.from_), sB = sb(m.to);
      const dropAt = j => {
        const b = tr[j].drop; if (!b) return null;
        const t = j / (n - 1), a0 = tr[0].drop, b0 = tr[n - 1].drop;
        return b.map((x, q) => x + (sA && a0 ? (1 - t) * (sA[q] - a0[q]) : 0) + (sB && b0 ? t * (sB[q] - b0[q]) : 0));
      };
      const dropSrc = j => { const v = j / (n - 1) < 0.5 ? m.from_ : m.to; return sb(v) ? A.url(A.config.assetBase + v + '/drop.webp') : null; };
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
      const s3 = !!A.config.scene3;                  // scene3: outlines and white dots replace the drawn hotspots
      this.bedSvg.style.display = this.viewKey === 'room' && !s3 ? '' : 'none';
      const magOn = !s3 && this.viewKey === 'bed' && !!this.mag && !!(this.views.bed && this.views.bed.magazine);
      this.magSvg.style.display = magOn ? '' : 'none'; this.magGlint.classList.toggle('is-on', magOn);
      if (!magOn) this.magLabel.classList.remove('is-on');
      this.tease.classList.toggle('is-on', this.viewKey === 'bed');
      this.setRegion(null);
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
      if (i < 0) this.drop.close();                                   // the drop card goes with its selection (no view change here)
      if (i >= 0 && this.viewKey !== railKey) await this.go(railKey);      // another one is out: hang it back first
      if (i >= 0 && railKey === 'rail_m') { const sp = this.panFor(i); if (sp != null) await this.panTo(sp); }   // phones: centre it first
      await this.go(target);
      if (i >= 0 && this.viewKey === target) { this.rail.setSelected(i); this.root.classList.add('has-selection'); }
      this.kick();
    }
    panTo(target, ms = 320) {
      return new Promise(res => {
        const p0 = this.pan, t0 = performance.now();
        const step = now => {
          const t = this.reduced ? 1 : Math.min(1, (now - t0) / ms), e = t * t * (3 - 2 * t);
          this.pan = p0 + (target - p0) * e; this.snapPan = this.pan; this.kick();
          if (t < 1) requestAnimationFrame(step); else { this.snapPan = target; res(); }
        };
        requestAnimationFrame(step);
      });
    }
    /* Garment under a stage point (scene2): reads the rendered id mask of the current view. -1 = none. */
    garmentAt(x, y) {
      const cv = this.comp.view; if (!this.plate || !cv) return -1;
      // a posed view (rail@i) reads its rail's mask for the garments still hanging; the posed one is found by its box
      const posed = cv.key.includes('@'), v = posed ? this.comp.cache[cv.key.split('@')[0]] : cv;
      if (posed) {
        const sel = this.rail.selected, p = this.rail.px && this.rail.px[sel];
        if (p && x > p.x - p.w * 0.62 && x < p.x + p.w * 0.62 && y > p.y - p.h * 0.05 && y < p.y + p.h * 1.15) return sel;
      }
      if (!v || !v.idsImg) return -1;
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
      const p = A.products[i]; if (!p) return;
      this.rail.kickGarment(i, A.config.motion.sway.clickKick);
      if (p.type === 'product' && this.plate) {                    // straight to the product view
        this.hideHint();
        if (this.rail.selected >= 0 && !this.viewKey.includes('@')) {   // the drop card was open: it closes behind the product
          this.rail.setSelected(-1); this.root.classList.remove('has-selection'); this.drop.close();
        }
        return this.openProduct(i);
      }
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
    /* "Weiter umsehen" after the bag: back to the rail, where everything waves once. */
    async keepLooking() {
      if (this.isMobile) { if (this.viewKey !== 'rail_m') await this.go('rail_m'); }
      else if (this.viewKey === 'bed') await this.go('room');
      setTimeout(() => { this.rail.wave(); this.kick(); }, 250);
    }
    afterProductClose() { const s = this.rail.selected; if (s >= 0) this.rail.items[s].hit.focus({ preventScroll: true }); }
    setWorldDim(d = 1, blur = 0) {
      // the old layered rail dimmed the room behind a chosen jersey; the rendered room never stays blurred
      if (!this.plate && this.rail.selected >= 0 && d === 1) { d = A.config.motion.select.dimRoom; blur = A.config.motion.select.blurRoom; }
      this.dimTarget = d;
      this.canvas.style.filter = blur ? `blur(${blur}px)` : '';
      this.fallbackImg.style.filter = this.canvas.style.filter;
      this.kick();
    }
    /* the sports bag (cart) shows once something is in it */
    setCartCount(n) {
      this.cartCount = n;
      if (this.bagBtn) { this.bagBtn.hidden = !(n > 0); const c = this.bagBtn.querySelector('.azur-head__count'); if (c) c.textContent = n; }
    }
    bumpCart() {
      if (!this.bagBtn) return;
      this.bagBtn.animate([{ transform: 'translateY(0) rotate(0)' }, { transform: 'translateY(-5px) rotate(-8deg)', offset: 0.35 },
        { transform: 'translateY(0) rotate(4deg)', offset: 0.7 }, { transform: 'none' }], { duration: 620, easing: 'ease-out' });
    }

    /* ---------------------------------------------------------------- depth (same values the shader sees) */
    encDepth(metres) { return lin2srgb(Math.max(0, Math.min(1, (DEPTH.far - metres) / (DEPTH.far - DEPTH.near)))); }
    async loadDepth(key) {
      if (this.depthMaps[key] !== undefined) return;
      this.depthMaps[key] = null;
      const im = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.onerror = () => r(null); i.src = A.url(A.config.assetBase + key.split('@')[0] + '/depth.png'); });
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
      // header over the room: nothing but the sports bag (once something is in it) and three glowing dots for the menu;
      // the logo only shows, dimmed, behind the product view and the magazine (it takes you back into the room)
      const head = $('.azur-head');
      this.bagBtn = head && head.querySelector('.azur-head__bag');
      if (this.bagBtn && !A.config.shopify) this.bagBtn.addEventListener('click', () => this.shop.toggleCart());   // Shopify: the theme's drawer ([data-cart-open])
      this.setCartCount(A.store && A.store.cartCount || 0);
      // Shopify: the theme's cart drawer rewrites every [data-cart-count] (the bag's too) when lines change there;
      // the bag follows that number, and the cart is asked again when the visitor comes back to the tab
      const cnt = this.bagBtn && this.bagBtn.querySelector('.azur-head__count');
      if (cnt && 'MutationObserver' in window) new MutationObserver(() => {
        const n = parseInt(cnt.textContent, 10) || 0; if (n !== this.cartCount) { this.cartCount = n; this.bagBtn.hidden = !(n > 0); }
      }).observe(cnt, { childList: true, characterData: true, subtree: true });
      if (A.config.shopify) document.addEventListener('visibilitychange', () => {
        if (document.hidden) return;
        const root = (window.Shopify && Shopify.routes && Shopify.routes.root) || '/';
        fetch(root + 'cart.js', { headers: { Accept: 'application/json' } }).then(r => r.json()).then(c => this.setCartCount(c.item_count)).catch(() => { });
      });
      this.menuBtn = head && head.querySelector('.azur-head__dots'); this.menu = head && head.querySelector('.azur-menu');
      if (this.menuBtn && this.menu) {
        this.menuBtn.addEventListener('click', e => { e.stopPropagation(); this.toggleMenu(); });
        document.addEventListener('click', e => { if (!this.menu.hidden && !e.target.closest('.azur-menu, .azur-head__dots')) this.toggleMenu(false); });
      }
      const ghost = $('.azur-ghost');
      if (ghost) {   // it shows above the product view and the magazine (appended to <body>): it must live there too
        const wrap = ghost.parentElement && ghost.parentElement.tagName === 'NAV' ? ghost.parentElement : ghost;
        if (wrap.parentElement !== document.body) document.body.appendChild(wrap);
      }
      if (ghost) ghost.addEventListener('click', e => {
        e.preventDefault();
        if (this.shop.pdp.classList.contains('is-on')) this.shop.close();
        if (this.mag && this.mag.isOpen) this.mag.close();
      });
      document.querySelectorAll('.azur-head [data-go], [data-azur-go]').forEach(a => a.addEventListener('click', e => {
        e.preventDefault(); const t = a.dataset.go || a.dataset.azurGo;
        this.toggleMenu(false);
        if (A.config.shopify) this.root.scrollIntoView({ behavior: this.reduced ? 'auto' : 'smooth' });
        if (t === 'rail') this.go(this.isMobile ? 'rail_m' : 'rail'); else if (t === 'mag') this.openMag(); else this.go(t);
      }));
      // scene3: white dots on what can be visited from here (bed, rail, magazine); hover lights its outline
      this.dotBox = document.createElement('div'); this.dotBox.className = 'azur-dots'; this.layer.after(this.dotBox);
      this.dots = {};
      [['bed', c.goBed], ['rail', c.goRail], ['mag', c.magSpot]].forEach(([t, label]) => {
        const b = document.createElement('button'); b.type = 'button'; b.className = 'azur-dot azur-dot--' + t; b.dataset.target = t;
        b.setAttribute('aria-label', label); b.hidden = true;
        b.addEventListener('click', e => { e.stopPropagation(); this.goTarget(t); });
        b.addEventListener('pointerenter', () => this.setRegion(t, true)); b.addEventListener('pointerleave', () => this.setRegion(null));
        b.addEventListener('focus', () => this.setRegion(t, true)); b.addEventListener('blur', () => this.setRegion(null));
        this.dotBox.appendChild(b); this.dots[t] = b;
      });
      this.goLabel = document.createElement('p'); this.goLabel.className = 'azur-bedlabel azur-golabel'; this.goLabel.setAttribute('aria-hidden', 'true');
      this.dotBox.appendChild(this.goLabel);
      this.chips = $('.azur-views');
      this.chips.addEventListener('click', e => {
        const b = e.target.closest('button[data-view]'); if (!b) return;
        let v = b.dataset.view; if (v === 'rail' && this.isMobile) v = 'rail_m';
        if (!this.plate) this.select(-1);
        this.go(v);
      });
      this.hint = $('.azur-hint'); this.hint.textContent = this.isMobile ? c.hintMobile : c.hintDesktop;
      this.tease = $('.azur-tease'); this.setTease();
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
      // behind the window glass (the compositor masks it in). Round 4: for each window a clip rendered from that camera, a
      // boy running past on the lawn with his ball (outside/<view>.mp4); it rests on its first frame (nobody there) and
      // plays now and then. Older sets: real footage of the Bolzplatz across the street on a loop.
      if (this.plate && this.comp.ok) {
        const mk = (files, loop) => {
          const vid = document.createElement('video');
          Object.assign(vid, { muted: true, loop, playsInline: true, preload: 'none' });   // fetched when a window shows it
          vid.setAttribute('muted', ''); vid.setAttribute('playsinline', ''); vid.setAttribute('aria-hidden', 'true');
          files.forEach(([f, t]) => { const so = document.createElement('source'); so.src = A.url(f); so.type = t; vid.appendChild(so); });
          Object.assign(vid.style, { position: 'absolute', width: '2px', height: '2px', opacity: '0', pointerEvents: 'none', left: '0', top: '0' });
          this.root.appendChild(vid); return vid;
        };
        const ob = A.config.assetBase.replace(/views\/$/, 'outside/');
        this.clips = {};
        Object.entries(this.outside || {}).forEach(([k, c]) => {
          if (!c || !c.box) return;
          const vid = this.clips[k] = mk([[ob + k + '.webm', 'video/webm'], [ob + k + '.mp4', 'video/mp4']], false);
          vid.addEventListener('ended', () => this.clipEnded(vid));
        });
        if (Object.keys(this.clips).length) { this.useClip(this.viewKey || 'room'); this.scheduleClip(6000 + Math.random() * 6000); }
        else {
          const ob2 = A.config.outsideBase || 'assets/scene2/outside/';      // the same footage for every scene set
          this.comp.video = this.video = mk([[ob2 + 'bolzplatz.webm', 'video/webm'], [ob2 + 'bolzplatz.mp4', 'video/mp4']], true);
        }
      }
      this.initSound();
      // the neighbour's kid crosses the park outside the window now and then
      this.windowEl = $('.azur-window');
      this.kidTrack = $('.azur-kid-track');
      this.kidTrack.addEventListener('animationend', e => { if (e.target === this.kidTrack) this.kidTrack.classList.remove('is-run', 'is-back'); });
      this.scheduleKid(5000 + Math.random() * 5000);
    }
    /* ---------------------------------------------------------------- outside the window (round 4) */
    useClip(key) {        // the clip made for this view's window (none for the phones' rail and the bed)
      if (!this.clips) return;
      const k = (key || '').split('@')[0], vid = this.clips[k] || null, c = this.outside && this.outside[k];
      if (this.video && this.video !== vid && !this.video.loop && !this.video.paused) { this.video.pause(); this.video.currentTime = 0; }
      this.video = vid; this.comp.video = vid; this.comp.clipBox = vid ? c.box : null; this.comp.videoUp = false;
      if (vid && vid.preload !== 'auto') { vid.preload = 'auto'; vid.load(); }
    }
    scheduleClip(ms) {
      clearTimeout(this.clipTimer);
      this.clipTimer = setTimeout(() => this.playClip(), ms);
    }
    playClip() {
      const vid = this.video, c = this.comp;
      const quiet = !vid || vid.loop || this.reduced || document.hidden || this.offscreen || this.busy || c.winAmt < 0.5
        || (this.mag && this.mag.isOpen) || this.shop.pdp.classList.contains('is-on');
      if (quiet) { this.scheduleClip(9000 + Math.random() * 6000); return; }      // not now: look again soon
      vid.currentTime = 0;
      vid.play().then(() => {
        const k = Object.keys(this.clips).find(x => this.clips[x] === vid), kick = this.outside[k] && this.outside[k].kick;
        if (kick != null) setTimeout(() => { if (!vid.paused) this.kickSound(1); }, Math.max(0, kick - vid.currentTime) * 1000);
      }).catch(() => this.scheduleClip(20000));
      this.kick();
    }
    clipEnded(vid) {      // back on the empty lawn until the next time
      vid.pause(); vid.currentTime = 0; this.comp.videoUp = false; this.kick();
      this.scheduleClip(25000 + Math.random() * 45000);
    }

    /* Sound (round 4): a ball kicked outside, quiet and muffled by the window. Browsers allow sound only after the
       visitor's first click, tap or key; the speaker in the header switches it off (remembered). Now and then, while it
       is light outside, someone kicks a ball out of sight too. */
    initSound() {
      try { this.soundOn = localStorage.getItem('azur-sound') !== 'off'; } catch (e) { this.soundOn = true; }
      const btn = $('.azur-head__sound');
      const sync = () => { if (!btn) return; btn.setAttribute('aria-pressed', String(this.soundOn)); btn.setAttribute('aria-label', this.soundOn ? 'Ton aus' : 'Ton an'); };
      if (btn) {
        btn.hidden = false; sync();
        btn.addEventListener('click', e => {
          e.stopPropagation(); this.soundOn = !this.soundOn; sync(); this.unlockAudio();
          try { localStorage.setItem('azur-sound', this.soundOn ? 'on' : 'off'); } catch (err) { }
          if (this.soundOn) this.kickSound(0.6);
        });
      }
      const unlock = () => this.unlockAudio();
      ['pointerdown', 'keydown', 'touchstart'].forEach(ev => document.addEventListener(ev, unlock, { once: true, passive: true }));
      const far = () => {
        this.farTimer = setTimeout(far, 45000 + Math.random() * 75000);
        if (!document.hidden && !this.offscreen && this.light && this.light.window > 0.6 && !(this.video && !this.video.paused)) this.kickSound(0.45);
      };
      this.farTimer = setTimeout(far, 30000 + Math.random() * 40000);
    }
    unlockAudio() {
      if (!this.soundOn) return;
      try {
        this.audio = this.audio || new (window.AudioContext || window.webkitAudioContext)();
        if (this.audio.state === 'suspended') this.audio.resume();
      } catch (e) { }
    }
    kickSound(vol) {
      const ac = this.audio; if (!this.soundOn || !ac || ac.state !== 'running') return;
      const t = ac.currentTime + 0.01, out = ac.createGain(); out.gain.value = 0.2 * vol;
      const lp = ac.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2400;      // through the window
      out.connect(lp); lp.connect(ac.destination);
      const o = ac.createOscillator(), g = ac.createGain(); o.type = 'sine';           // the thump of the ball
      o.frequency.setValueAtTime(165, t); o.frequency.exponentialRampToValueAtTime(52, t + 0.13);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(1, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
      o.connect(g); g.connect(out); o.start(t); o.stop(t + 0.22);
      const len = Math.floor(ac.sampleRate * 0.05), buf = ac.createBuffer(1, len, ac.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3);  // the slap of the boot
      const n = ac.createBufferSource(); n.buffer = buf;
      const bp = ac.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1400; bp.Q.value = 0.9;
      const ng = ac.createGain(); ng.gain.value = 0.7; n.connect(bp); bp.connect(ng); ng.connect(out); n.start(t);
      const dl = ac.createDelay(); dl.delayTime.value = 0.11; const eg = ac.createGain(); eg.gain.value = 0.16;   // off the house fronts
      lp.connect(dl); dl.connect(eg); eg.connect(ac.destination);
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
      this.placeDots();
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

    /* ---------------------------------------------------------------- scene3: outlines, dots, menu */
    toggleMenu(on) {
      if (!this.menu) return;
      const open = on == null ? this.menu.hidden : on;
      this.menu.hidden = !open; this.menuBtn.setAttribute('aria-expanded', String(open));
      this.root.classList.toggle('menu-open', open);
      if (open) { const f = this.menu.querySelector('a, button'); if (f) f.focus({ preventScroll: true }); }
    }
    targets() { return A.config.scene3 ? (A.config.targets[this.viewKey.split('@')[0]] || []) : []; }
    /* Which outline region (bed, rail, magazine) is at a stage point: masks.png R, G, B (half size). */
    regionAt(x, y) {
      const cv = this.comp.view, t = this.targets(); if (!cv || !cv.masksImg || !t.length) return null;
      const d = this.masksData(cv); if (!d) return null;
      let [u, w] = this.comp.toPlate(x, y);
      const dep = this.depthAt(u, w), f = this.comp.focus || 0.6;
      u += this.parallax[0] * (dep - f); w += this.parallax[1] * (dep - f);
      const px = Math.floor(u * d.w), py = Math.floor(w * d.h);
      if (px < 0 || py < 0 || px >= d.w || py >= d.h) return null;
      const i = (py * d.w + px) * 4, r = d.data[i], g = d.data[i + 1], b = d.data[i + 2];
      if (b > 127 && t.includes('mag')) return 'mag';
      if (r > 127 && t.includes('bed')) return 'bed';
      if (g > 127 && t.includes('rail')) return 'rail';
      return null;
    }
    masksData(cv) {
      if (cv.masksData) return cv.masksData;
      const im = cv.masksImg; if (!im || !im.naturalWidth) return null;
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
      const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
      const d = { w: c.width, h: c.height, data: g.getImageData(0, 0, c.width, c.height).data };
      // where each region's dot sits: the bed and the magazine at their middle, the rail near its top (the bar)
      d.anchors = {};
      ['bed', 'rail', 'mag'].forEach((t, ch) => {
        let n = 0, sx = 0, sy = 0, y0 = d.h, y1 = -1;
        for (let y = 0; y < d.h; y += 2) for (let x = 0; x < d.w; x += 2) if (d.data[(y * d.w + x) * 4 + ch] > 127) { n++; sx += x; sy += y; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        if (n < 12) return;
        let ax = sx / n, ay = t === 'rail' ? y0 + (y1 - y0) * 0.04 : sy / n;
        // snap onto the region (a concave shape's middle can fall outside it)
        let best = null, bd = 1e12;
        for (let y = 0; y < d.h; y += 2) for (let x = 0; x < d.w; x += 2) if (d.data[(y * d.w + x) * 4 + ch] > 127) {
          const dd = (x - ax) ** 2 + (y - ay) ** 2; if (dd < bd) { bd = dd; best = [x, y]; } }
        if (best) d.anchors[t] = [(best[0] + 0.5) / d.w, (best[1] + 0.5) / d.h];
      });
      cv.masksData = d; return d;
    }
    setRegion(t, fromDot) {
      if (t === this.region && !fromDot) return;
      this.region = t;
      this.stage.classList.toggle('is-going', !!t);
      const el = this.goLabel; if (!el) return;
      const c = A.config.copy, dot = t && this.dots[t];
      if (t && dot && !dot.hidden) {
        el.textContent = t === 'bed' ? c.goBed : t === 'rail' ? c.goRail : c.magSpot;
        el.style.left = dot.style.left; el.style.top = (parseFloat(dot.style.top) - 18) + 'px';
        el.classList.add('is-on');
      } else el.classList.remove('is-on');
      this.kick();
    }
    goTarget(t) {
      this.setRegion(null);
      const dot = this.dots[t], r = dot && dot.getBoundingClientRect(), focus = r && r.width ? [r.left + r.width / 2, r.top + r.height / 2] : null;
      if (t === 'bed') this.go('bed', { focus });
      else if (t === 'rail') this.go(this.isMobile ? 'rail_m' : 'rail', { focus });
      else if (t === 'mag') this.openMag();
    }
    placeDots() {
      if (!this.dots) return;
      const cv = this.comp.view, t = this.targets(), d = cv && cv.masksImg ? this.masksData(cv) : null;
      Object.entries(this.dots).forEach(([k, b]) => {
        const a = d && t.includes(k) && d.anchors[k];
        b.hidden = !a; if (!a) return;
        const p = this.comp.toScreen(a[0], a[1], this.depthAt(a[0], a[1]));
        const W = this.stage.clientWidth, H = this.stage.clientHeight;
        if (p[0] < 24 || p[1] < 24 || p[0] > W - 24 || p[1] > H - 24) { b.hidden = true; return; }
        b.style.left = p[0].toFixed(1) + 'px'; b.style.top = p[1].toFixed(1) + 'px';
      });
    }

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
          if (!e.target.closest('.azur-dot')) this.setRegion(this.rail.hover >= 0 ? null : this.regionAt(x, y));
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
      st.addEventListener('pointerleave', () => { this.parallaxTarget = [0, 0]; this.rail.pointerLeave(); this.setRegion(null); last = null; });
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
        if (e.target.closest('.azur-drop, .azur-info, .azur-views, .azur-head, .azur-panel, .azur-dot')) return;
        if (this.plate) {
          if (this.dragMoved || e.target.closest('.azur-bed')) return;
          const r = st.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, id = this.garmentAt(x, y);
          if (id >= 0) return this.onGarmentClick(id);
          const reg = this.regionAt(x, y);
          if (reg) return this.goTarget(reg);
          if (this.viewKey.includes('@') || this.rail.selected >= 0) this.select(-1);
          return;
        }
        if (e.target.closest('.azur-g, .azur-bed')) return;
        if (this.rail.selected >= 0) this.select(-1);
      });
    }

    bindKeys() {
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
          if (this.menu && !this.menu.hidden) { this.toggleMenu(false); return this.menuBtn.focus(); }
          if (this.shop.pdp.classList.contains('is-on')) return this.shop.close();
          if (this.shop.drawer && this.shop.drawer.classList.contains('is-on')) return this.shop.toggleCart(false);
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
      // a jersey's link opens its product view, as a click on it does (the rendered rooms); the drop goes to the rail
      if (i >= 0 && this.plate && A.products[i].type === 'product') this.openProduct(i);
      else if (i >= 0) this.go(this.isMobile ? 'rail_m' : 'rail', { select: i });
      else if (h === 'bett') this.go('bed');
      else if (h === 'anstoss') this.openMag();
      else if (h === 'azur-drop' && /customer_posted=true/.test(location.search)) this.drop.confirm('');   // back from Shopify's bot check
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
      if (document.hidden || this.offscreen) { requestAnimationFrame(tt => this.frame(tt)); return; }
      const cfg = A.config;
      // light: follow the clock (cheap, once a second) or the design panel
      if (t - this.lightAt > 1000 || this.lightDirty) {
        this.lightAt = t; this.lightDirty = false;
        this.light = A.light.current(); this.rail.applyLight(this.light); this.applyAmbient(); this.dirty = true;
        if (A.config.scene3) { const st = this.stateNow(); if (st !== this.dayState) this.changeState(st); }
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
      // phones drift all the time: 30 pictures a second are plenty for that slow sway (and kinder to the battery)
      const drift = pmove && (!this.isMobile || t - (this.driftAt || 0) > 31);
      if (drift) this.driftAt = t;
      if (drift || this.dirty) { this.rail.place(); this.placeChrome(); }
      const swaying = this.rail.step(dt, this.reduced);
      if (this.plate && A.config.scene3) this.applySway(t, swaying);
      if (this.dirty || drift) { this.comp.render(this.light); this.dirty = false; }
      requestAnimationFrame(tt => this.frame(tt));
    }

    /* scene2: the hovered garment brightens in the render; the outdoor video runs while it is light outside. */
    stepPlate(dt) {
      const c = this.comp, h = this.rail.hover;
      // hover outlines fade in and out
      const S = (A.config.outline || {}).strength || 0.9, ease = Math.min(1, dt * ((A.config.outline || {}).ease || 9));
      const want = ['bed', 'rail', 'mag'].map(k => this.region === k ? S : 0);
      let glowCh = false;
      want.forEach((w, k) => { const n = this.glowAmt[k] + (w - this.glowAmt[k]) * ease;
        if (Math.abs(n - w) < 2e-3) { if (this.glowAmt[k] !== w) glowCh = true; this.glowAmt[k] = w; } else { this.glowAmt[k] = n; glowCh = true; } });
      if (glowCh) { c.setGlow(this.glowAmt.slice()); this.dirty = true; }
      if (h >= 0) c.hover = h + 1;
      const target = h >= 0 && !this.viewKey.includes('@') ? 1 : 0;
      const ha = c.hoverAmt + (target - c.hoverAmt) * Math.min(1, dt * 9);
      if (Math.abs(ha - c.hoverAmt) > 1e-3) { c.hoverAmt = ha; this.dirty = true; } else c.hoverAmt = target;
      const vid = this.video, hasWin = c.view && c.view.win;
      const wa = hasWin ? Math.max(0, Math.min(1, (this.light.window - 0.35) / 0.5)) : 0;
      if (Math.abs(wa - c.winAmt) > 1e-3) { c.winAmt += (wa - c.winAmt) * Math.min(1, dt * 3); this.dirty = true; }
      if (!vid) return;
      const resting = (this.mag && this.mag.isOpen) || this.shop.pdp.classList.contains('is-on');   // the room rests behind the magazine and the product view
      if (!vid.loop) {                                          // round 4: the boy's clip plays when scheduled (playClip)
        if (!vid.paused) { if (resting || document.hidden || c.winAmt < 0.05) this.clipEnded(vid); else this.dirty = true; }
        return;
      }
      if (c.winAmt > 0.01 && !document.hidden && !resting) {
        if (vid.paused && !this.reduced) vid.play().catch(() => { });
        if (!vid.paused) this.dirty = true;                     // new video frames
      } else if (!vid.paused) vid.pause();
    }

    /* scene3: the rail's pendulums bend the rendered plate (compositor sway). Idle breathing renders at 30 fps,
       a swinging jersey at full rate; nothing moves behind the product view or the magazine. */
    applySway(t, swaying) {
      const cv = this.comp.view; if (!cv || !this.comp.ok) return;
      if (!cv.swayA && cv.idsImg && !cv.swayTried) {
        cv.swayTried = true;
        (window.requestIdleCallback || (f => setTimeout(f, 60)))(() => { this.comp.buildSway(cv, A.products.length); this.kick(); });
      }
      if (!cv.swayA) return;
      const covered = this.shop.pdp.classList.contains('is-on') || (this.mag && this.mag.isOpen) || this.busy;
      const v = this.viewData(this.viewKey), hooks = (v.slots || []).map(x => x && x.hook);
      this.comp.setSway(hooks, this.rail.swayAng || [], this.rail.swayRip || []);
      this.comp.time = t / 1000;
      const idle = !this.reduced && A.config.motion.sway.idleDeg > 0;
      // one render per frame: the frame loop draws once when dirty (drawing here as well doubled the work)
      if (!covered && (swaying || (idle && t - (this.swayAt || 0) > 33))) { this.swayAt = t; this.dirty = true; }
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
