/* AZUR — the garment rail.
   Every product hangs as its own layer on top of the rendered room, placed where the hangers are in the 3D scene
   (assets/views/views.json). Motion is physical: springs for lift, push and turn, a damped pendulum on each hook.
   Hover moves through the garments; a click turns one toward you and shows one quiet line underneath. */
(function () {
  const A = window.AZUR = window.AZUR || {};

  /* Stand-in while hanger.webp is not rendered: the scene's hanger drawn from its own geometry (millimetres,
     anchor = hook origin at 0,0; the wooden V sits behind the garment, only the hook shows above the collar). */
  const HANGER_FALLBACK = { w: 0.44, h: 0.166, anchor: [0.22, 0.096], src: 'data:image/svg+xml,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-220 -96 440 166">
      <path d="M-205 58 Q0 -36 205 58" fill="none" stroke="#6d4526" stroke-width="18" stroke-linecap="round"/>
      <path d="M-200 52 Q0 -40 200 52" fill="none" stroke="#a87a4c" stroke-width="5" stroke-linecap="round" opacity=".7"/>
      <path d="M0 6 V-44 C0 -60 7 -66 5 -78 C3 -89 -6 -93 -12 -88" fill="none" stroke="#9a9a96" stroke-width="5" stroke-linecap="round"/>
      <path d="M-1 4 V-44 C-1 -58 5 -65 3 -76" fill="none" stroke="#e6e6e2" stroke-width="1.6" stroke-linecap="round"/>
    </svg>`) };

  class Spring {
    constructor(v = 0) { this.v = v; this.t = v; this.vel = 0; }
    step(dt, k, c) { const a = k * (this.t - this.v) - c * this.vel; this.vel += a * dt; this.v += this.vel * dt; }
    snap() { this.v = this.t; this.vel = 0; }
    get moving() { return Math.abs(this.t - this.v) > 1e-4 || Math.abs(this.vel) > 1e-4; }
  }

  class Garment {
    constructor(product, index, rail) {
      this.p = product; this.i = index; this.rail = rail;
      this.lift = new Spring(); this.fwd = new Spring(); this.turn = new Spring(); this.push = new Spring(); this.tilt = new Spring();
      this.bright = new Spring(1);
      this.theta = 0; this.omega = 0; this.phase = index * 1.7;
      this.el = this.build();
    }
    build() {
      const p = this.p, cfg = A.config, el = document.createElement('li');
      el.className = 'azur-g' + (p.type === 'drop' ? ' azur-g--drop' : '');
      el.dataset.index = this.i;
      const label = p.type === 'drop' ? `${p.name}. ${p.description}` : `${p.name}, ${A.formatPrice(p.price)}`;
      el.innerHTML = `
        <div class="azur-g__shadow" aria-hidden="true"></div>
        <div class="azur-g__pivot">
          <img class="azur-g__hanger" alt="" aria-hidden="true" src="${A.sprites && A.sprites.hanger ? A.url(cfg.assetBase + 'hanger.webp') : HANGER_FALLBACK.src}">
          <div class="azur-g__body">
            ${p.type === 'drop' ? this.dropMarkup() : `
            <img class="azur-g__img" src="${p.image}" alt="" draggable="false">
            <div class="azur-g__tint" aria-hidden="true" style="-webkit-mask-image:url(${p.image});mask-image:url(${p.image})"></div>
            <div class="azur-g__glow" aria-hidden="true" style="-webkit-mask-image:url(${p.image});mask-image:url(${p.image})"></div>`}
          </div>
        </div>
        <button class="azur-g__hit" type="button" aria-label="${label}" data-index="${this.i}"></button>`;
      this.pivot = el.querySelector('.azur-g__pivot');
      this.body = el.querySelector('.azur-g__body');
      this.shadow = el.querySelector('.azur-g__shadow');
      this.hit = el.querySelector('.azur-g__hit');
      this.hanger = el.querySelector('.azur-g__hanger');
      this.hanger.addEventListener('error', () => { this.hanger.src = HANGER_FALLBACK.src; this.hangerFallback = true; this.rail.place(); }, { once: true });
      this.hangerFallback = !(A.sprites && A.sprites.hanger);
      return el;
    }
    dropMarkup() {
      return `<img class="azur-g__img azur-g__dropimg" alt="" draggable="false" hidden>
        <div class="azur-bag" aria-hidden="true">
          <span class="azur-bag__zip"></span>
          <img class="azur-bag__logo" src="${A.url('assets/brand/azur-logo-paper.webp')}" alt="">
          <span class="azur-bag__tag">Nächster<br>Drop</span>
        </div>`;
    }
    kick(impulse) { this.omega += impulse; }
  }

  class Rail {
    constructor(root, products, app) {
      this.app = app; this.root = root;
      this.list = document.createElement('ul');
      this.list.className = 'azur-rail'; this.list.setAttribute('aria-label', 'Trikots am Kleiderständer');
      root.appendChild(this.list);
      this.items = products.map((p, i) => new Garment(p, i, this));
      this.items.forEach(g => this.list.appendChild(g.el));
      this.hover = -1; this.selected = -1; this.view = null; this.geom = [];
      // scene2: the garments are part of the rendered room; this layer only keeps labels, info and keyboard targets
      this.plate = !!A.config.plateGarments;
      root.classList.toggle('is-plate', this.plate);
      this.pointer = { x: -1e4, y: -1e4, vx: 0, inside: false };
      this.t = 0; this.shadowStrength = 1;
      this.label = document.createElement('div'); this.label.className = 'azur-label'; this.label.setAttribute('aria-hidden', 'true');
      root.appendChild(this.label);
      this.info = document.createElement('div'); this.info.className = 'azur-info'; this.info.setAttribute('role', 'region'); this.info.setAttribute('aria-live', 'polite');
      root.appendChild(this.info);
      this.bind();
    }

    bind() {
      this.list.addEventListener('click', e => {
        const b = e.target.closest('.azur-g__hit'); if (!b) return;
        const i = +b.dataset.index;
        this.app.onGarmentClick(i);
      });
      this.list.addEventListener('focusin', e => {
        const b = e.target.closest('.azur-g__hit'); if (!b) return;
        this.setHover(+b.dataset.index, true);
      });
      this.list.addEventListener('focusout', () => { if (!this.pointer.inside) this.setHover(-1); });
      this.list.addEventListener('keydown', e => {
        const b = e.target.closest('.azur-g__hit'); if (!b) return;
        const i = +b.dataset.index;
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          const j = Math.max(0, Math.min(this.items.length - 1, i + (e.key === 'ArrowRight' ? 1 : -1)));
          this.items[j].hit.focus();
          if (this.selected >= 0 && this.view !== 'room') this.app.select(j);
        }
      });
      this.info.addEventListener('click', e => {
        const a = e.target.closest('[data-action]'); if (!a) return;
        e.preventDefault();
        if (a.dataset.action === 'view') this.app.openProduct(this.selected);
        if (a.dataset.action === 'back') this.app.select(-1);
      });
    }

    /* Place the garments for a view using the projected hanger positions. */
    layout(viewKey, viewData, comp) {
      this.view = viewKey; this.viewData = viewData; this.comp = comp;
      const cfg = A.config, vcfg = cfg.views[viewKey] || {};
      this.root.classList.toggle('is-room', viewKey === 'room');
      this.root.classList.toggle('is-mobile', viewKey === 'rail_m');
      const slots = (viewData && viewData.slots) || [];
      const sprite = (A.sprites && A.sprites[viewKey] && A.sprites[viewKey].drop) || null;
      this.geom = this.items.map((g, i) => {
        const s = slots[i]; if (!s) return null;
        return { hook: s.hook, top: s.top, bottom: s.bottom, depthM: s.depth, scale: vcfg.garmentScale || 1, sprite: g.p.type === 'drop' ? sprite : null };
      });
      // drop garment: use its own rendered sprite when this view has one
      const drop = this.items.find(g => g.p.type === 'drop');
      if (drop) {
        const img = drop.el.querySelector('.azur-g__dropimg'), bag = drop.el.querySelector('.azur-bag');
        const has = !!sprite;
        if (img) { img.hidden = !has; if (has) img.src = A.url(cfg.assetBase + viewKey + '/drop.webp'); }
        if (bag) bag.hidden = has;
        drop.hasSprite = has;
      }
      this.place();
    }

    /* During a pre-rendered camera move: place the garments for one frame of the flight. comp maps the frame's
       (u, v) to the screen; f holds that frame's projected slots, the neon and the drop bag's box. */
    fly(f, comp, dropBox, dropSrc) {
      this.comp = comp; this.viewData = { neon: f.neon };
      this.geom = this.items.map((g, i) => {
        const s = f.slots[i]; if (!s) return null;
        const drop = g.p.type === 'drop';
        if (drop && !dropBox) return null;
        return { hook: s.hook, top: s.top, bottom: s.bottom, depthM: s.depth, scale: 1, sprite: drop ? { box: dropBox } : null };
      });
      const drop = this.items.find(g => g.p.type === 'drop');
      if (drop && dropSrc) {
        const img = drop.el.querySelector('.azur-g__dropimg'), bag = drop.el.querySelector('.azur-bag');
        if (img && img.getAttribute('src') !== dropSrc) { img.src = dropSrc; img.hidden = false; if (bag) bag.hidden = true; }
      }
      this.place();
    }

    /* Recompute pixel geometry (call on resize / pan / parallax). */
    place() {
      const comp = this.comp; if (!comp || !comp.cssW) return;
      const depthAt = this.app.depthAt.bind(this.app);
      this.px = this.geom.map((g, i) => {
        if (!g) return null;
        const d = depthAt(g.top[0], g.top[1], g.depthM);
        const top = comp.toScreen(g.top[0], g.top[1], d);
        const bot = comp.toScreen(g.bottom[0], g.bottom[1], d);
        const hook = comp.toScreen(g.hook[0], g.hook[1], d);
        const h = Math.max(20, (bot[1] - top[1])) * g.scale;
        const it = this.items[i];
        let w = h * (it.p.imageAspect || 0.9);
        let ox = 0, oy = 0;
        if (g.sprite) {   // sprite box is in view-plate coordinates
          const b = g.sprite.box;
          const p0 = comp.toScreen(b[0], b[1], d), p1 = comp.toScreen(b[2], b[3], d);
          w = p1[0] - p0[0]; ox = p0[0] - top[0] + w / 2; oy = p0[1] - top[1];
          // the sprite swings around its own hook, which is not the centre of the box (the tag hangs to one side)
          const ax = Math.max(0.1, Math.min(0.9, (hook[0] - p0[0]) / Math.max(1, w)));
          return { x: top[0] + ox, y: top[1] + oy, h: p1[1] - p0[1], w, hook, ox: 0, oy: 0, ax, sprite: true, d };   // box centre / top
        }
        return { x: top[0], y: top[1], h, w, hook, ox, oy, sprite: false, d };
      });
      const cfg = A.config;
      this.items.forEach((g, i) => {
        const p = this.px[i]; g.el.hidden = !p; if (!p) return;
        g.el.style.zIndex = String(10 + i);
        g.el.style.width = p.w + 'px'; g.el.style.height = p.h + 'px';
        g.pivot.style.transformOrigin = p.sprite ? `${(p.ax * 100).toFixed(1)}% 0` : '';
        g.body.style.width = p.w + 'px'; g.body.style.height = p.h + 'px';
        if (g.hanger) {
          // exact size from the scene: metres times this garment's pixels per metre (garments are 0.74 m long)
          const k = p.h / 0.74, hs = A.sprites && A.sprites.hanger;
          const mpp = hs && hs.metres_per_px;
          const m = hs && !g.hangerFallback ? { w: hs.size[0] * mpp, h: hs.size[1] * mpp, anchor: [hs.anchor[0] * mpp, hs.anchor[1] * mpp] } : HANGER_FALLBACK;
          g.hanger.style.width = (m.w * k) + 'px';
          g.hanger.style.left = (p.w / 2 - m.anchor[0] * k) + 'px';
          // the anchor is the hook origin, 8 mm above the garment top; the hook rises above it
          g.hanger.style.top = (-(m.anchor[1] + 0.008) * k) + 'px';
          // the wooden bar sits inside the jersey: only the hook and the neck of the hanger show
          const cl = 0.035, below = 0.022;
          g.hanger.style.clipPath = `inset(0px ${((m.w - m.anchor[0] - cl) * k).toFixed(1)}px ${((m.h - m.anchor[1] - below) * k).toFixed(1)}px ${((m.anchor[0] - cl) * k).toFixed(1)}px)`;
          g.hanger.hidden = p.sprite;
        }
        // neon light falls on the garments from the sign: direction and strength by distance on screen
        const n = this.viewData && this.viewData.neon;
        if (n && !p.sprite) {
          const q = this.comp.toScreen(n[0], n[1], p.d);
          const dx = p.x - q[0], dy = p.y + p.h * 0.3 - q[1], dist = Math.hypot(dx, dy) / Math.max(1, this.comp.cssW);
          const ang = Math.round(Math.atan2(dx, -dy) * 180 / Math.PI), kk = Math.exp(-Math.pow(dist / 0.42, 2)).toFixed(2);
          if (g.glowKey !== ang + '|' + kk) { g.glowKey = ang + '|' + kk; g.el.style.setProperty('--g-glow-a', ang + 'deg'); g.el.style.setProperty('--g-glow-k', kk); }
        }
      });
    }

    setHover(i, fromKeyboard) {
      if (i === this.hover) return;
      const prev = this.hover; this.hover = i;
      const mi = A.config.motion.intensity * A.config.interactionStrength;
      const sw = this.plate && A.config.motion.sway ? A.config.motion.sway : A.config.motion.swing;   // scene3: the rendered jerseys swing
      if (prev >= 0 && this.items[prev]) this.items[prev].kick(sw.leaveKick * mi * (Math.random() > 0.5 ? 1 : -1));
      if (i >= 0 && this.items[i]) this.items[i].kick(-sw.hoverKick * mi * Math.sign(this.pointer.vx || 1));
      this.app.onHover(i, fromKeyboard);
      this.updateLabel();
    }

    setSelected(i) {
      this.selected = i;
      this.items.forEach((g, j) => g.el.classList.toggle('is-selected', j === i));
      if (i >= 0) this.items[i].kick(A.config.motion.swing.selectKick * A.config.motion.intensity);
      this.updateInfo();
      this.updateLabel();
    }

    /* Pointer from the app (CSS px inside the stage). Finds the garment under it along the rail. */
    pointerMove(x, y, vx) {
      this.pointer.x = x; this.pointer.y = y; this.pointer.vx = vx;
      if (!this.px || !this.px.length) return;
      if (this.plate) {             // exact garment shape from the rendered id mask
        const id = this.app.garmentAt(x, y);
        this.pointer.inside = id >= 0;
        const sw = A.config.motion.sway;                          // brushing past a jersey sets it swinging
        if (id >= 0 && sw && this.items[id]) this.items[id].omega += Math.max(-600, Math.min(600, vx)) * sw.brush * A.config.motion.intensity * A.config.interactionStrength;
        if (this.selected < 0 || this.view === 'room') this.setHover(id);
        return;
      }
      let best = -1, bestDist = 1e9;
      this.px.forEach((p, i) => {
        if (!p) return;
        const cx = p.x + this.items[i].push.v * p.w;
        const inBand = y > p.y - p.h * 0.12 && y < p.y + p.h * 1.02 && x > cx - p.w * 0.62 && x < cx + p.w * 0.62;
        if (!inBand) return;
        const dist = Math.abs(x - cx);
        if (dist < bestDist) { bestDist = dist; best = i; }
      });
      this.pointer.inside = best >= 0;
      // brushing past a garment near its hook makes it swing a little (digital wardrobe reference)
      const m = A.config.motion, mi = m.intensity * A.config.interactionStrength;
      this.px.forEach((p, i) => {
        if (!p) return;
        const near = Math.abs(x - p.x) < p.w * 0.6 && y > p.y - p.h * 0.2 && y < p.y + p.h;
        if (near) this.items[i].omega += vx * m.swing.impulse * mi;
      });
      if (this.selected < 0 || this.view === 'room') this.setHover(best);
    }
    pointerLeave() { this.pointer.inside = false; this.pointer.x = -1e4; if (this.selected < 0 || this.view === 'room') this.setHover(-1); }

    /* Pan velocity on phones: the whole rail swings against the motion. */
    panImpulse(v) {
      const m = A.config.motion; const mi = m.intensity * A.config.interactionStrength;
      this.items.forEach(g => g.omega -= v * m.swing.impulse * 0.9 * mi);
    }

    updateLabel() {
      const i = this.selected >= 0 && this.view !== 'room' ? -1 : this.hover;
      const el = this.label;
      if (i < 0 || !this.items[i] || !this.px || !this.px[i]) { el.classList.remove('is-on'); return; }
      const p = this.items[i].p;
      el.innerHTML = p.type === 'drop'
        ? `<span class="azur-label__name">${p.name}</span><span class="azur-label__meta">${p.description}</span><span class="azur-label__cta">Ansehen</span>`
        : `<span class="azur-label__name">${p.name}</span><span class="azur-label__meta">${A.formatPrice(p.price)}</span><span class="azur-label__cta">${A.config.copy.view}</span>`;
      el.classList.add('is-on');
      this.labelFor = i;
    }

    updateInfo() {
      const i = this.selected, el = this.info, c = A.config.copy;
      if (i < 0 || this.view === 'room') { el.classList.remove('is-on'); el.innerHTML = ''; return; }
      const p = this.items[i].p;
      if (p.type === 'drop') { el.classList.remove('is-on'); el.innerHTML = ''; this.app.drop.open(); return; }
      this.app.drop.close();
      const n = String(i + 1).padStart(2, '0');
      el.innerHTML = `
        <span class="azur-info__n">${n}</span>
        <span class="azur-info__name">${p.name}</span>
        <span class="azur-info__price">${A.formatPrice(p.price)}</span>
        <a class="azur-info__cta" href="${p.productUrl}" data-action="view">${c.viewJersey} <span aria-hidden="true">→</span></a>
        <button class="azur-info__back" type="button" data-action="back">${c.putBack}</button>`;
      el.classList.add('is-on');
    }

    /* A push on one jersey (a click, a hover): it swings, its neighbours a little (they touch on the rail). */
    kickGarment(i, degPerS) {
      const sw = A.config.motion.sway, g = this.items[i]; if (!g) return;
      const dir = Math.sign(this.pointer.vx || (Math.random() - 0.5)) || 1, mi = A.config.motion.intensity * A.config.interactionStrength;
      g.omega += degPerS * dir * mi;
      [i - 1, i + 1].forEach(j => { if (this.items[j]) this.items[j].omega += degPerS * dir * (sw ? sw.neighbour : 0.3) * mi; });
    }
    /* Everything on the rail waves once, left to right (after something went into the bag: there is more). */
    wave() {
      this.items.forEach((g, i) => setTimeout(() => this.kickGarment(i, (A.config.motion.sway || {}).hoverKick || 2), 90 * i));
    }
    /* scene3 pendulums: angle (rad) and cloth ripple (plate px) per garment for the compositor. Returns true while
       something swings (beyond the idle breathing). */
    stepSway(dt, reduced) {
      const sw = A.config.motion.sway, mi = A.config.motion.intensity * A.config.interactionStrength, n = this.items.length;
      if (!this.swayAng) { this.swayAng = new Array(n).fill(0); this.swayRip = new Array(n).fill(0); }
      let moving = false;
      this.items.forEach((g, i) => {
        if (reduced) { g.theta = 0; g.omega = 0; g.rip = 0; this.swayAng[i] = 0; this.swayRip[i] = 0; return; }
        const acc = -sw.stiffness * g.theta - sw.damping * g.omega;
        g.omega = Math.max(-40, Math.min(40, g.omega + acc * dt)); g.theta += g.omega * dt;
        if (Math.abs(g.theta) > sw.maxDeg) { g.theta = Math.sign(g.theta) * sw.maxDeg; g.omega *= -0.3; }
        const idle = sw.idleDeg * mi * Math.sin(this.t * 1.13 + g.phase) * (0.55 + 0.45 * Math.sin(this.t * 0.31 + g.phase * 2.3));
        const ripT = (i === this.hover ? sw.ripple : 0) + Math.min(sw.ripple * 1.5, Math.abs(g.omega) * 0.5);
        g.rip = (g.rip || 0) + (ripT * mi - (g.rip || 0)) * Math.min(1, dt * 3);
        this.swayAng[i] = (g.theta + idle) * Math.PI / 180; this.swayRip[i] = g.rip;
        if (Math.abs(g.omega) > 0.02 || Math.abs(g.theta) > 0.01 || g.rip > 0.05) moving = true;
      });
      return moving;
    }

    /* Physics + DOM transforms. Returns true while anything is still moving. */
    step(dt, reduced) {
      this.t += dt;
      if (this.plate) { const m = A.config.scene3 && A.config.motion.sway ? this.stepSway(dt, reduced) : false; this.positionOverlays(); return m; }
      const cfg = A.config, m = cfg.motion, mi = m.intensity * cfg.interactionStrength;
      const k = m.spring.stiffness, c = m.spring.damping;
      const h = this.hover, s = (this.view === 'room') ? -1 : this.selected;
      let moving = false;
      this.items.forEach((g, i) => {
        const p = this.px && this.px[i]; if (!p) return;
        // targets
        let lift = 0, fwd = 0, turn = 0, push = 0, tilt = 0, bright = 1;
        if (s >= 0) {
          if (i === s) { lift = m.select.lift; fwd = m.select.forward; turn = m.select.turnDeg; bright = 1.04; }
          else { const d = i - s; push = Math.sign(d) * m.select.push * Math.pow(m.hover.falloff, Math.abs(d) - 1); bright = 0.86; }
        } else if (h >= 0) {
          if (i === h) { lift = m.hover.lift; fwd = m.hover.forward; turn = m.hover.turnDeg; bright = m.hover.bright;
            tilt = m.hover.tiltDeg * Math.max(-1, Math.min(1, (this.pointer.x - p.x) / (p.w * 0.5))); }
          else { const d = i - h; push = Math.sign(d) * m.hover.neighbourPush * Math.pow(m.hover.falloff, Math.abs(d) - 1); }
        }
        g.lift.t = lift * mi; g.fwd.t = fwd * mi; g.turn.t = turn * Math.min(1, mi); g.push.t = push * mi; g.tilt.t = tilt * mi; g.bright.t = bright;
        if (reduced) { [g.lift, g.fwd, g.turn, g.push, g.tilt, g.bright].forEach(sp => sp.snap()); g.theta = 0; g.omega = 0; }
        else {
          [g.lift, g.fwd, g.turn, g.push, g.tilt, g.bright].forEach(sp => sp.step(dt, k, c));
          // damped pendulum on the hook (degrees)
          const sw = m.swing; const acc = -sw.stiffness * g.theta - sw.damping * g.omega;
          g.omega += acc * dt; g.theta += g.omega * dt;
          g.theta = Math.max(-sw.maxDeg, Math.min(sw.maxDeg, g.theta));
        }
        moving = moving || g.lift.moving || g.fwd.moving || g.turn.moving || g.push.moving || Math.abs(g.omega) > 0.02 || Math.abs(g.theta) > 0.02;
        const idle = reduced ? 0 : m.idle.swayDeg * Math.sin(this.t * 2 * Math.PI / m.idle.periodS + g.phase);
        const ang = g.theta + idle + g.tilt.v;
        const scale = 1 + g.fwd.v;
        const x = p.x + g.push.v * p.w, y = p.y - g.lift.v * p.h;
        g.el.style.transform = `translate3d(${(x - p.w / 2).toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
        g.pivot.style.transform = `rotate(${ang.toFixed(3)}deg) scale(${scale.toFixed(4)})`;
        const fan = p.sprite ? 0 : cfg.garments.fanDeg;
        g.body.style.transform = `perspective(${cfg.garments.perspective}px) rotateY(${(fan + g.turn.v).toFixed(2)}deg)`;
        g.body.style.filter = `brightness(${(g.bright.v).toFixed(3)})`;
        // the shadow on the wall separates as the garment comes forward
        const sh = cfg.garments.shadow, sep = 1 + g.fwd.v * 6 + g.lift.v * 4;
        g.shadow.style.transform = `translate3d(${(sh.x * p.h * sep).toFixed(1)}px, ${(sh.y * p.h * sep).toFixed(1)}px, 0) rotate(${(ang * 0.6).toFixed(2)}deg) scale(${(1 + g.fwd.v * 0.4).toFixed(3)})`;
        g.shadow.style.filter = `blur(${(sh.blur * p.h * sep).toFixed(1)}px)`;
        g.shadow.style.opacity = (sh.alpha * this.shadowStrength / Math.sqrt(sep)).toFixed(3);
        g.el.style.zIndex = String(i === s ? 60 : i === h ? 40 + i : 10 + i);
      });
      this.positionOverlays();
      return moving;
    }

    positionOverlays() {
      if (this.plate) return this.positionOverlaysPlate();
      const i = this.labelFor;
      if (this.label.classList.contains('is-on') && this.px && this.px[i]) {
        const p = this.px[i], g = this.items[i];
        const x = p.x + g.push.v * p.w + p.w * 0.34, y = p.y - g.lift.v * p.h + p.h * 0.1;
        this.label.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
      }
      const s = this.selected;
      if (s >= 0 && this.px && this.px[s]) {
        const p = this.px[s], g = this.items[s];
        const bottom = p.y - g.lift.v * p.h + p.h * (1 + g.fwd.v) + 14;
        const x = p.x + g.push.v * p.w;
        this.info.style.transform = `translate3d(${x.toFixed(1)}px, ${bottom.toFixed(1)}px, 0) translateX(-50%)`;
        this.app.drop.position(x, p.y + p.h * 0.18, p);
      }
    }

    positionOverlaysPlate() {
      const i = this.labelFor, H = this.app.stage.clientHeight;
      if (this.label.classList.contains('is-on') && this.px && this.px[i]) {
        const p = this.px[i];
        this.label.style.transform = `translate3d(${(p.x + p.w * 0.3).toFixed(1)}px, ${(p.y + p.h * 0.12).toFixed(1)}px, 0)`;
      }
      const s = this.selected;
      if (s >= 0 && this.px && this.px[s]) {
        const p = this.px[s];
        const bottom = Math.min(H - 96, p.y + p.h + 14), W = this.app.stage.clientWidth, half = this.info.offsetWidth / 2;
        const x = Math.max(16 + half, Math.min(W - 16 - half, p.x));      // the garment at the edge keeps its line on screen
        this.info.style.transform = `translate3d(${x.toFixed(1)}px, ${bottom.toFixed(1)}px, 0) translateX(-50%)`;
        this.app.drop.position(p.x, p.y + p.h * 0.18, p);
      }
    }

    /* Light the garments like the room around them (see daylight[].garment in the config). */
    applyLight(state) {
      const [b, warm, cool] = state.garment;
      const glow = A.config.palettes[A.config.palette].glow;
      this.root.style.setProperty('--g-bright', b.toFixed(3));
      this.root.style.setProperty('--g-warm', warm.toFixed(3));
      this.root.style.setProperty('--g-cool', cool.toFixed(3));
      this.root.style.setProperty('--g-neon', (Math.min(1, state.neon) * (0.15 + 0.6 * state.night)).toFixed(3));
      this.root.style.setProperty('--glow', glow);
      this.shadowStrength = 0.5 + 0.5 * (1 - state.night);
    }

    garmentRect(i) {
      if (this.plate) {
        const p = this.px && this.px[i]; if (!p) return null;
        const s = this.app.stage.getBoundingClientRect();
        return { left: s.left + p.x - p.w / 2, top: s.top + p.y, width: p.w, height: p.h, right: s.left + p.x + p.w / 2, bottom: s.top + p.y + p.h };
      }
      return this.items[i] && this.items[i].body.getBoundingClientRect();
    }
  }

  A.Rail = Rail;
})();
