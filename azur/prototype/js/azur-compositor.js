/* AZUR — room compositor.
   Draws one view of the room from its rendered light passes (WebGL2): decodes each pass back to linear light,
   mixes them with the time-of-day weights, applies depth-based parallax and an AgX-style tone curve so the
   result matches the Blender stills. Falls back to the pre-graded beauty plate, and to a plain <img> without WebGL.

   scene3 adds three things on top:
   - the jerseys sway: a smooth displacement field per garment (built here from the rendered id mask) bends the
     plate around each hook, driven by the rail's pendulums (setSway)
   - hover outlines: glow.png holds the bed, the rail and the magazine as white glows (R, G, B), faded in by setGlow
   - times of day: morning, evening and night are rectangles rendered over the day passes (passes.json 'states');
     setState copies them into the day textures (and puts the day pixels back when the state ends)

   Round 4 (lighter): the passes are mixed and tone-mapped into one texture only when the light changes (a few times a
   minute as the clock moves), not every frame; each frame then reads that one texture, shifted by parallax and sway.
   The sign's glow (neon_glow.webp, a smooth bloom made offline from the neon pass) is added in that mix. Views that
   are not on screen give their pass textures back to the GPU and upload them again when they are needed. */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const PASSES = ['sky', 'sunLow', 'sunHigh', 'neon', 'lamp', 'ceiling', 'street', 'spot'];
  const REQUIRED = PASSES.slice(0, 7);          // 'spot' (ceiling spot on the rail) exists from scene2 on
  const MD_MAX = 2600;          // plate pixels across the canvas the middle copies (2400 wide) serve; above: full plates
  const FILES = { sky: 'sky', sunLow: 'sun_low', sunHigh: 'sun_high', neon: 'neon', lamp: 'lamp', ceiling: 'ceiling', street: 'street', spot: 'spot' };
  const KEY_OF = Object.fromEntries(Object.entries(FILES).map(([k, f]) => [f, k]));
  const MAX_SWAY = 6;

  const VERT = `#version 300 es
  in vec2 aPos; out vec2 vUv;
  void main() { vUv = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5); gl_Position = vec4(aPos, 0.0, 1.0); }`;

  const COMMON = `
  vec3 dec(sampler2D t, vec2 uv, float s) {
    vec3 e = texture(t, uv).rgb;
    if (s < 0.0) return (exp(e * 8.9873218) - 1.0) / (-8000.0 * s);   // log curve (render_queue.LOG_K 8000: ln 8001)
    vec3 y = min(pow(e, vec3(2.2)), vec3(0.995));
    return (y / (1.0 - y)) / s;
  }`;

  // the light mix: all passes -> one tone-mapped picture (rendered into a texture when the light changes)
  const MIX_FRAG = `#version 300 es
  precision highp float;
  in vec2 vUv; out vec4 outColor;
  uniform sampler2D tSky, tSunLow, tSunHigh, tNeon, tLamp, tCeiling, tStreet, tSpot, tNeonGlow;
  uniform vec3 wSky, wSunLow, wSunHigh, wNeon, wLamp, wCeiling, wStreet, wSpot;
  uniform float sSky, sSunLow, sSunHigh, sNeon, sLamp, sCeiling, sStreet, sSpot, sNeonGlow, uGlowGain;
  uniform float uExposure, uContrast, uSat;
  ${COMMON}
  // AgX (approximation by B. Wrensch), close to Blender's AgX view transform
  vec3 agxCurve(vec3 x) {
    vec3 x2 = x * x; vec3 x4 = x2 * x2;
    return 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
  }
  vec3 agx(vec3 v) {
    const mat3 m = mat3(0.842479062253094, 0.0423282422610123, 0.0423756549057051,
                        0.0784335999999992, 0.878468636469772, 0.0784336,
                        0.0792237451477643, 0.0791661274605434, 0.879142973793104);
    const mat3 mi = mat3(1.19687900512017, -0.0528968517574562, -0.0529716355144438,
                         -0.0980208811401368, 1.15190312990417, -0.0980434501171241,
                         -0.0990297440797205, -0.0989611768448433, 1.15107367264116);
    const float lo = -12.47393, hi = 4.026069;
    v = m * max(v, vec3(1e-10));
    v = clamp(log2(v), lo, hi);
    v = (v - lo) / (hi - lo);
    v = agxCurve(v);
    // "Medium High Contrast" look
    float l = dot(v, vec3(0.2126, 0.7152, 0.0722));
    v = pow(max(v, vec3(0.0)), vec3(1.18 * uContrast));
    v = l + (1.08 * uSat) * (v - l);
    return mi * v;
  }
  void main() {
    vec2 uv = vec2(vUv.x, 1.0 - vUv.y);                   // framebuffer rows run bottom-up: store the plate top-down
    vec3 lin = dec(tSky, uv, sSky) * wSky + dec(tSunLow, uv, sSunLow) * wSunLow + dec(tSunHigh, uv, sSunHigh) * wSunHigh
             + dec(tNeon, uv, sNeon) * wNeon + dec(tLamp, uv, sLamp) * wLamp + dec(tCeiling, uv, sCeiling) * wCeiling
             + dec(tStreet, uv, sStreet) * wStreet + dec(tSpot, uv, sSpot) * wSpot;
    if (uGlowGain > 0.0) lin += dec(tNeonGlow, uv, sNeonGlow) * wNeon * uGlowGain;   // the sign's soft glow
    outColor = vec4(clamp(agx(lin * exp2(uExposure)), 0.0, 1.0), 1.0);
  }`;

  // every frame: the mixed picture, shifted by parallax and sway, plus hover, window and outlines
  const FRAG = `#version 300 es
  precision highp float;
  in vec2 vUv; out vec4 outColor;
  uniform sampler2D tLit, tDepth, tBeauty, tIds, tWin, tVideo, tGlow, tSwayA, tSwayB;
  uniform float uHover, uHoverAmt, uHasIds;              // garment under the pointer (slot + 1), fades in
  uniform float uWinAmt, uHasWin;                        // outdoor clip behind the window glass
  uniform vec4 uWinBox, uVidMap; uniform vec3 uVidGrade;
  uniform vec4 uMap;          // plate uv = uMap.xy + vUv * uMap.zw
  uniform vec2 uParallax;     // uv shift at depth 0 relative to the focus plane
  uniform float uFocus, uMode, uDim, uHasDepth;
  uniform vec3 uGrade;        // beauty mode only: rough time-of-day grade
  uniform vec3 uGlowAmt; uniform float uHasGlow;         // hover outlines: bed, rail, magazine
  uniform float uHasSway, uTime; uniform vec2 uPlatePx;
  uniform vec4 uSwayHook[${MAX_SWAY}];                   // per garment: hook (plate uv), swing angle (rad), ripple (px)
  // where the plate moves under a swinging garment (rotation about its hook, a ripple running down the cloth)
  vec2 sway(vec2 uv) {
    vec4 wa = texture(tSwayA, uv); vec4 wb = texture(tSwayB, uv);
    float w[6] = float[6](wa.r, wa.g, wa.b, wa.a, wb.r, wb.g);
    float sum = w[0] + w[1] + w[2] + w[3] + w[4] + w[5];
    if (sum < 0.002) return vec2(0.0);
    vec2 d = vec2(0.0);
    for (int i = 0; i < ${MAX_SWAY}; i++) {
      if (w[i] < 0.002) continue;
      vec4 h = uSwayHook[i];
      vec2 p = (uv - h.xy) * uPlatePx;
      float c = cos(h.z), s = sin(h.z);
      vec2 r = vec2(p.x * c - p.y * s, p.x * s + p.y * c) - p;
      float below = max(p.y, 0.0);
      r.x += h.w * sin(below * 0.018 - uTime * 3.1 + float(i) * 1.7) * min(1.0, below / 200.0);
      d += w[i] * r;
    }
    return d / max(sum, 1.0) / uPlatePx;
  }
  void main() {
    vec2 uv = uMap.xy + vUv * uMap.zw;
    float d = uHasDepth > 0.5 ? texture(tDepth, uv).r : uFocus;
    uv += uParallax * (d - uFocus);
    vec2 guv = uv;
    if (uHasSway > 0.5) uv -= sway(uv);
    vec3 c = uMode < 0.5 ? texture(tLit, uv).rgb : texture(tBeauty, uv).rgb * uGrade;
    if (uHasWin > 0.5 && uWinAmt > 0.001) {              // the street outside, seen through the glass
      float m = texture(tWin, uv).r * uWinAmt;
      vec2 wv = (uv - uWinBox.xy) / max(uWinBox.zw - uWinBox.xy, vec2(1e-4));
      vec3 vid = texture(tVideo, uVidMap.xy + clamp(wv, 0.0, 1.0) * uVidMap.zw).rgb * uVidGrade;
      c = mix(c, vid, m * 0.93);
    }
    if (uHasIds > 0.5 && uHoverAmt > 0.001) {            // the garment under the pointer lifts a little in light
      float id = floor(texture(tIds, uv).r * 255.0 / 32.0 + 0.5);
      float on = 1.0 - step(0.5, abs(id - uHover));
      c = c * (1.0 + 0.16 * uHoverAmt * on) + 0.014 * uHoverAmt * on;
    }
    c = clamp(c * uDim, 0.0, 1.0);
    if (uHasGlow > 0.5) {                                // white outline of what the pointer is on (screen blend)
      float g = clamp(dot(texture(tGlow, guv).rgb, uGlowAmt), 0.0, 1.0);
      c = 1.0 - (1.0 - c) * (1.0 - g * vec3(0.97, 0.99, 1.0));
    }
    outColor = vec4(c, 1.0);
  }`;

  function loadImage(src) {
    return new Promise((res) => {
      const im = new Image();
      im.decoding = 'async';
      im.onload = () => res(im); im.onerror = () => res(null);
      im.src = A.url(src);
    });
  }

  class Compositor {
    constructor(canvas) {
      this.canvas = canvas;
      this.gl = null;
      try { this.gl = canvas.getContext('webgl2', { antialias: false, premultipliedAlpha: false, preserveDrawingBuffer: true }); } catch (e) { this.gl = null; }
      this.view = null; this.mode = 'none';
      this.map = [0, 0, 1, 1]; this.parallax = [0, 0]; this.pan = 0.5; this.overscan = 0.03;
      this.dim = 1; this.cache = {};
      this.glow = [0, 0, 0]; this.swayHooks = new Float32Array(MAX_SWAY * 4); this.swayOn = false; this.time = 0;
      this.state = 'day';
      if (this.gl) this.init();
    }
    get ok() { return !!this.gl; }

    init() {
      const gl = this.gl;
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
      const program = (frag, units, names) => {
        const p = gl.createProgram();
        gl.attachShader(p, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, frag));
        gl.bindAttribLocation(p, 0, 'aPos'); gl.linkProgram(p);
        if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
        const u = {}; gl.useProgram(p);
        for (const n of units.concat(names)) u[n] = gl.getUniformLocation(p, n);
        units.forEach((n, i) => gl.uniform1i(u[n], i));
        return { p, u, units };
      };
      this.mixP = program(MIX_FRAG, ['tSky', 'tSunLow', 'tSunHigh', 'tNeon', 'tLamp', 'tCeiling', 'tStreet', 'tSpot', 'tNeonGlow'],
        ['wSky', 'wSunLow', 'wSunHigh', 'wNeon', 'wLamp', 'wCeiling', 'wStreet', 'wSpot',
         'sSky', 'sSunLow', 'sSunHigh', 'sNeon', 'sLamp', 'sCeiling', 'sStreet', 'sSpot', 'sNeonGlow', 'uGlowGain',
         'uExposure', 'uContrast', 'uSat']);
      this.drawP = program(FRAG, ['tLit', 'tDepth', 'tBeauty', 'tIds', 'tWin', 'tVideo', 'tGlow', 'tSwayA', 'tSwayB'],
        ['uMap', 'uParallax', 'uFocus', 'uMode', 'uDim', 'uHasDepth', 'uGrade',
         'uHover', 'uHoverAmt', 'uHasIds', 'uWinAmt', 'uHasWin', 'uWinBox', 'uVidMap', 'uVidGrade',
         'uGlowAmt', 'uHasGlow', 'uHasSway', 'uTime', 'uPlatePx', 'uSwayHook']);
      this.prog = this.drawP.p; this.u = this.drawP.u;
      const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      this.blank = this.texture(null);
      this.lit = null; this.litKey = ''; this.fbo = gl.createFramebuffer();
      this.hover = 0; this.hoverAmt = 0; this.winAmt = 0; this.video = null; this.videoTex = null;
      this.recent = [];                                   // views whose passes are on the GPU, most recent last
    }

    texture(img, nearest) {
      const gl = this.gl; const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, nearest ? gl.NEAREST : gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, nearest ? gl.NEAREST : gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      if (img) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
      return t;
    }
    dataTexture(w, h, data) {
      const gl = this.gl, t = this.texture(null);
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);
      return t;
    }

    /* Load a view. Resolves to 'passes', 'beauty' or 'none'. Textures are cached per view.
       With low-resolution copies (passes.json _lo, published builds) those come first and the full plates follow. */
    async load(key, meta, activate = true) {
      const base = A.config.assetBase + key + '/';   // loadImage() turns these into real URLs (A.url)
      if (this.cache[key]) {
        if (activate) { this.view = this.cache[key]; this.mode = this.view.mode; }
        await this.cache[key].ready;
        this.touch(this.cache[key]);                   // its passes back on the GPU if they were given back
        return this.cache[key].mode;
      }
      const v = { key, mode: 'none', tex: {}, scales: {}, size: null, beautyImg: null, imgs: {}, state: 'day', meta };
      this.cache[key] = v;
      let done; v.ready = new Promise(r => { done = r; });
      const scales = (meta && meta[key]) || {};
      const have = REQUIRED.every(p => scales[FILES[p]]);
      // a chosen garment's view ('rail@2') shares depth, garment ids and window mask with its view ('rail')
      const baseKey = key.split('@')[0], baseDir = A.config.assetBase + baseKey + '/';
      const vc = A.config.views[baseKey] || {};
      const wantIds = vc.ids !== false && vc.masks !== false, wantWin = vc.window !== false && vc.masks !== false;
      const s3 = !!A.config.scene3;
      const [depth, ids, win, masks, glow] = await Promise.all([
        loadImage(baseDir + 'depth.png'),
        key.includes('@') || !wantIds ? null : loadImage(baseDir + 'ids.png'),
        wantWin ? loadImage(baseDir + 'window.png') : null,
        s3 ? loadImage(baseDir + 'masks.png') : null,
        s3 ? loadImage(baseDir + 'glow.png') : null]);
      if (have && this.gl) {
        const lo = meta && meta._lo && !key.includes('@');
        const list = PASSES.filter(p => scales[FILES[p]]);
        const imgs = await Promise.all(list.map(p => loadImage(base + (lo ? 'lo/' : '') + FILES[p] + '.webp')));
        if (imgs.every(Boolean)) {
          list.forEach((p, i) => { v.tex[p] = this.texture(imgs[i]); v.scales[p] = scales[FILES[p]]; v.imgs[p] = imgs[i]; });
          v.size = [imgs[0].naturalWidth, imgs[0].naturalHeight]; v.mode = 'passes';
          v.texW = imgs[0].naturalWidth; v.texH = imgs[0].naturalHeight; v.version = 1;
          v.list = list; v.base = base; v.tier = lo ? 'lo' : 'full';
          if (lo) v.upgrade = () => this.upgrade(v);
          if (scales.neon_glow) {                      // the sign's soft glow (small, smooth: no low copy)
            const g = await loadImage(base + 'neon_glow.webp');
            if (g) { v.tex.neonGlow = this.texture(g); v.scales.neonGlow = scales.neon_glow; }
          }
        }
      }
      if (ids && this.gl) v.ids = this.texture(ids, true);
      v.idsImg = ids; v.masksImg = masks; v.masksDay = masks;
      if (glow && this.gl) { v.glow = v.glowDay = this.texture(glow); }
      const winBox = win && this.gl ? Compositor.maskBox(win) : null;   // no window in this view (the phone rail): no video
      if (winBox) { v.win = this.texture(win); v.winBox = winBox; }
      const vd = this.viewsData && this.viewsData[baseKey];
      v.platePx = (vd && vd.res) || v.size;            // full plate size (the textures may be the low-resolution copies)
      if (v.mode === 'none') {
        const b = await loadImage(base + 'beauty.webp');
        if (b) { v.beautyImg = b; v.size = [b.naturalWidth, b.naturalHeight]; v.mode = 'beauty'; if (this.gl) v.tex.beauty = this.texture(b); }
      }
      v.depth = depth && this.gl ? this.texture(depth) : null;
      if (!v.platePx) v.platePx = v.size;
      if (activate) { this.view = v; this.mode = v.mode; }
      done();
      if (this.state !== 'day') await this.applyState(v, this.state);
      this.touch(v);
      return v.mode;
    }

    /* GPU memory: only the views used last keep their pass textures (A.config.gpuViews, 2); the others give them back
       and upload them again from their images (and their time-of-day patches) when they are needed. */
    touch(v) {
      if (!this.gl || v.mode !== 'passes') return;
      if (v.evicted) this.restore(v);
      this.recent = this.recent.filter(x => x !== v); this.recent.push(v);
      let over = this.recent.length - (A.config.gpuViews || 2);
      for (const old of this.recent.slice()) {                // least recently used first, never the one on screen
        if (over <= 0) break;
        if (old === this.view || old === v) continue;
        this.evict(old); this.recent = this.recent.filter(x => x !== old); over--;
      }
    }
    evict(v) {
      const gl = this.gl;
      PASSES.forEach(p => { if (v.tex[p]) { gl.deleteTexture(v.tex[p]); v.tex[p] = null; } });
      v.evicted = true;
    }
    restore(v) {
      PASSES.forEach(p => { if (v.imgs[p]) v.tex[p] = this.texture(v.imgs[p]); });
      if (v.patched && v.patchImgs) {
        const k = v.texW / ((v.patched.res && v.patched.res[0]) || v.platePx[0]);
        v.patched.passes.forEach((f, j) => { const p = KEY_OF[f]; if (v.tex[p]) v.patched.rects.forEach((r, i) => this.putPatch(v.tex[p], v.patchImgs[j][i], r, k)); });
      }
      v.evicted = false; v.version = (v.version || 0) + 1;
    }
    putPatch(tex, img, r, k) {
      const gl = this.gl;
      const x = Math.round(r[0] * k), y = Math.round(r[1] * k), w = Math.round((r[2] - r[0]) * k), h = Math.round((r[3] - r[1]) * k);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      if (Math.abs(k - 1) < 1e-3 && img.naturalWidth === w && img.naturalHeight === h) {
        gl.texSubImage2D(gl.TEXTURE_2D, 0, x, y, gl.RGBA, gl.UNSIGNED_BYTE, img);
      } else {
        const c = Compositor.scratch(w, h); const g = c.getContext('2d');
        g.clearRect(0, 0, w, h); g.drawImage(img, 0, 0, w, h);
        gl.texSubImage2D(gl.TEXTURE_2D, 0, x, y, gl.RGBA, gl.UNSIGNED_BYTE, c);
      }
    }

    /* Plate pixels the canvas shows across its width (cover fit and overscan included). */
    platePxNeeded() { return this.canvas.width / Math.max(this.map[2], 1e-3); }

    /* Swap a view's low-resolution passes for sharper ones (idle time after the first frames): the middle copies
       (passes.json _md, 2400 wide) unless the canvas shows more plate pixels than those have, then the full plates. */
    async upgrade(v, tier) {
      v.upgrade = null;
      const list = v.list, base = v.base;
      tier = tier || ((v.meta && v.meta._md || []).includes(v.key) && this.platePxNeeded() < MD_MAX ? 'md' : 'full');
      if (tier === v.tier) return;
      v.tier = tier;
      const imgs = await Promise.all(list.map(p => loadImage(base + (tier === 'md' ? 'md/' : '') + FILES[p] + '.webp')));
      if (!imgs.every(Boolean)) return;
      const gl = this.gl;
      v.chain = (v.chain || Promise.resolve()).then(async () => {
        if (v.tier !== tier) return;                   // a sharper tier was asked for meanwhile
        list.forEach((p, i) => {
          if (v.tex[p]) { gl.bindTexture(gl.TEXTURE_2D, v.tex[p]); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, imgs[i]); }
          v.imgs[p] = imgs[i];
        });
        v.texW = imgs[0].naturalWidth; v.texH = imgs[0].naturalHeight; v.version = (v.version || 0) + 1;
        const st = v.state; v.state = 'day'; v.patched = null; v.patchImgs = null;   // the full plates carry no patches yet
        if (st !== 'day') await this.applyStateNow(v, st);
      });
      await v.chain;
      this.onChange && this.onChange();
    }

    /* ---------------------------------------------------------------- times of day (scene3) */
    /* The state every loaded view should show; returns once the active view shows it. */
    async setState(state) {
      this.state = state;
      const jobs = Object.values(this.cache).map(v => v.ready.then(() => this.applyState(v, state)));
      await Promise.all(jobs);
    }
    applyState(v, state) {                       // one change at a time per view
      v.chain = (v.chain || Promise.resolve()).then(() => this.applyStateNow(v, state)).catch(e => console.warn(e));
      return v.chain;
    }
    async applyStateNow(v, state) {
      if (!this.gl || v.mode !== 'passes' || v.state === state) return;
      const info = v.meta && v.meta.states && v.meta.states[v.key];
      const gl = this.gl, kOf = st => v.texW / ((st && st.res && st.res[0]) || v.platePx[0]);
      const want = state !== 'day' && info && info[state] && info[state].rects.length ? info[state] : null;
      // load what the new state needs before touching the textures, so a view never shows half of it
      let patches = null;
      if (want) {
        const dir = A.config.assetBase + v.key + '/' + state + '/';
        patches = await Promise.all(want.passes.map(f => Promise.all(want.rects.map((_, i) => loadImage(dir + f + '_' + i + '.webp')))));
        if (patches.some(arr => arr.some(x => !x))) patches = null;
      }
      const night = state === 'night';
      const [masksN, glowN] = A.config.scene3 && night && !v.masksNight
        ? await Promise.all([loadImage(A.config.assetBase + v.key.split('@')[0] + '/masks_night.png'), loadImage(A.config.assetBase + v.key.split('@')[0] + '/glow_night.png')]) : [null, null];
      if (v.state === state) return;            // another call got there first
      const put = (tex, img, r, k) => this.putPatch(tex, img, r, k);
      // the previous state's rectangles go back to day
      if (v.patched) {
        const { rects, passes } = v.patched, k = kOf(v.patched);
        passes.forEach(f => {
          const p = KEY_OF[f], day = v.imgs[p]; if (!day || !v.tex[p]) return;
          rects.forEach(r => {
            const x = Math.round(r[0] * k), y = Math.round(r[1] * k), w = Math.round((r[2] - r[0]) * k), h = Math.round((r[3] - r[1]) * k);
            const c = Compositor.scratch(w, h); const g = c.getContext('2d');
            g.clearRect(0, 0, w, h); g.drawImage(day, x, y, w, h, 0, 0, w, h);
            gl.bindTexture(gl.TEXTURE_2D, v.tex[p]); gl.texSubImage2D(gl.TEXTURE_2D, 0, x, y, gl.RGBA, gl.UNSIGNED_BYTE, c);
          });
        });
        v.patched = null; v.patchImgs = null;
      }
      if (want && patches) {
        const k = kOf(want);
        want.passes.forEach((f, j) => { const p = KEY_OF[f]; if (v.tex[p]) want.rects.forEach((r, i) => put(v.tex[p], patches[j][i], r, k)); });
        v.patched = want; v.patchImgs = patches;
      }
      v.version = (v.version || 0) + 1;
      if (masksN) v.masksNight = masksN;
      if (glowN) v.glowNight = this.texture(glowN);
      // night outlines only when the night picture is really there (its patches loaded), so dots and image agree
      const nightShown = night && !!v.patched;
      v.masksImg = nightShown && v.masksNight ? v.masksNight : v.masksDay;
      v.masksData = null;
      v.glow = nightShown && v.glowNight ? v.glowNight : v.glowDay;
      v.state = state;
    }
    static scratch(w, h) {
      const c = Compositor._scratch || (Compositor._scratch = document.createElement('canvas'));
      if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
      return c;
    }

    /* ---------------------------------------------------------------- swaying garments (scene3) */
    /* Smooth weights per garment from the id mask (two RGBA textures, quarter size): 1 on the garment, fading out
       a little beyond its edge, so the plate bends instead of tearing where a garment moves. */
    buildSway(v, n) {
      if (!this.gl || !v.idsImg || v.swayA) return;
      const im = v.idsImg, W = Math.max(64, Math.round(im.naturalWidth / 4)), H = Math.max(36, Math.round(im.naturalHeight / 4));
      const c = document.createElement('canvas'); c.width = W; c.height = H;
      const g = c.getContext('2d', { willReadFrequently: true }); g.imageSmoothingEnabled = false; g.drawImage(im, 0, 0, W, H);
      const src = g.getImageData(0, 0, W, H).data;
      const out = [new Uint8Array(W * H * 4), new Uint8Array(W * H * 4)];
      const m = new Float32Array(W * H), t = new Float32Array(W * H);
      const r = Math.max(2, Math.round(W / 220));             // ~11 plate pixels at 2400 wide
      const boxH = (a, b, rad) => { for (let y = 0; y < H; y++) { let s = 0; const o = y * W;
        for (let x = -rad; x <= rad; x++) s += a[o + Math.min(W - 1, Math.max(0, x))];
        for (let x = 0; x < W; x++) { b[o + x] = s / (2 * rad + 1); s += a[o + Math.min(W - 1, x + rad + 1)] - a[o + Math.max(0, x - rad)]; } } };
      const boxV = (a, b, rad) => { for (let x = 0; x < W; x++) { let s = 0;
        for (let y = -rad; y <= rad; y++) s += a[Math.min(H - 1, Math.max(0, y)) * W + x];
        for (let y = 0; y < H; y++) { b[y * W + x] = s / (2 * rad + 1); s += a[Math.min(H - 1, y + rad + 1) * W + x] - a[Math.max(0, y - rad) * W + x]; } } };
      for (let k = 0; k < Math.min(n, MAX_SWAY); k++) {
        const id = (k + 1) * 32;
        for (let i = 0; i < W * H; i++) m[i] = Math.abs(src[i * 4] - id) < 16 ? 1 : 0;
        boxH(m, t, r); boxV(t, m, r);                           // dilate a little (values > 0 near the garment) ...
        for (let i = 0; i < W * H; i++) m[i] = Math.min(1, m[i] * 2);
        boxH(m, t, r); boxV(t, m, r);                           // ... then soften
        const o = out[k >> 2], ch = k & 3;
        for (let i = 0; i < W * H; i++) o[i * 4 + ch] = Math.round(m[i] * 255);
      }
      v.swayA = this.dataTexture(W, H, out[0]); v.swayB = this.dataTexture(W, H, out[1]);
    }
    /* hooks: per garment [u, v] of its hook in plate uv; angles in radians; ripple in plate pixels */
    setSway(hooks, angles, ripple) {
      const a = this.swayHooks; let on = false;
      for (let i = 0; i < MAX_SWAY; i++) {
        const h = hooks[i];
        a[i * 4] = h ? h[0] : -10; a[i * 4 + 1] = h ? h[1] : -10; a[i * 4 + 2] = angles[i] || 0; a[i * 4 + 3] = ripple[i] || 0;
        if (Math.abs(angles[i] || 0) > 2e-5 || Math.abs(ripple[i] || 0) > 0.02) on = true;
      }
      this.swayOn = on;
    }
    setGlow(rgb) { this.glow = rgb; }

    /* Cover-fit the plate into the canvas; pan (0..1) chooses which part shows when the plate is wider. */
    layout(w, h, dpr) {
      const c = this.canvas;
      const W = Math.round(w * dpr), H = Math.round(h * dpr);
      if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
      this.cssW = w; this.cssH = h;
      if (!this.view || !this.view.size) return;
      const [pw, ph] = this.view.size; const pa = pw / ph, ca = w / h;
      let zx = 1, zy = 1;
      if (ca > pa) zy = pa / ca; else zx = ca / pa;
      const os = 1 / (1 + this.overscan); zx *= os; zy *= os;
      const ox = (1 - zx) * this.pan, oy = (1 - zy) * 0.5;
      this.map = [ox, oy, zx, zy];
      // a bigger window (full screen, a large display) than the middle copies serve: the full plates
      if (this.view.tier === 'md' && this.platePxNeeded() > MD_MAX) this.upgrade(this.view, 'full');
    }

    /* Plate uv (0..1 from the top-left) + depth value -> CSS pixels, including the current parallax. */
    toScreen(u, v, d) {
      const [ox, oy, zx, zy] = this.map;
      const f = this.focus || 0.6;
      const pu = u - this.parallax[0] * (d - f), pv = v - this.parallax[1] * (d - f);
      return [(pu - ox) / zx * this.cssW, (pv - oy) / zy * this.cssH];
    }
    /* CSS pixels -> plate uv (no parallax). */
    toPlate(x, y) { const [ox, oy, zx, zy] = this.map; return [ox + x / this.cssW * zx, oy + y / this.cssH * zy]; }
    /* Scale from plate fraction to CSS pixels (horizontal). */
    get pxPerPlateX() { return this.cssW / this.map[2]; }
    get pxPerPlateY() { return this.cssH / this.map[3]; }

    /* The passes -> one tone-mapped texture (plate size), again only when the light, the state or the textures changed:
       the clock moves the light slowly, so this runs a few times a minute instead of every frame. */
    mix(state) {
      const gl = this.gl, v = this.view, W = state.weights;
      const vc = A.config.views[v.key.split('@')[0]] || {};      // per-view art direction (the bed corner gets less window light)
      const night = A.app && A.app.dayState === 'night' && vc.exposureNight != null;   // his room at night: the hallway light
      const exp = state.exposure + (night ? vc.exposureNight : (vc.exposure || 0));
      const q = x => Math.round(x * 400) / 400;
      const key = [v.key, v.version || 0, v.texW, q(exp), q(state.contrast || 1), q(state.saturation || 1), A.config.neonGlow,
        ...PASSES.map(p => (W[p] || [0, 0, 0]).map(q).join(','))].join('|');
      if (key === this.litKey && this.lit) return;
      const w = v.texW, h = v.texH || v.size[1];
      if (!this.lit || this.litW !== w || this.litH !== h) {
        if (this.lit) gl.deleteTexture(this.lit);
        this.lit = this.texture(null); gl.bindTexture(gl.TEXTURE_2D, this.lit);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); this.litW = w; this.litH = h;
      }
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.lit, 0);
      gl.viewport(0, 0, w, h);
      const P = this.mixP, u = P.u; gl.useProgram(P.p);
      PASSES.forEach((p, i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, v.tex[p] || this.blank); });
      gl.activeTexture(gl.TEXTURE8); gl.bindTexture(gl.TEXTURE_2D, v.tex.neonGlow || this.blank);
      const cap = p => p[0].toUpperCase() + p.slice(1);
      PASSES.forEach(p => {
        const on = v.tex[p] && (p !== 'spot' || W.spot);
        gl.uniform3fv(u['w' + cap(p)], on ? W[p] : [0, 0, 0]); gl.uniform1f(u['s' + cap(p)], v.scales[p] || 1);
      });
      gl.uniform1f(u.sNeonGlow, v.scales.neonGlow || 1);
      gl.uniform1f(u.uGlowGain, v.tex.neonGlow ? (A.config.neonGlow == null ? 1 : A.config.neonGlow) : 0);
      gl.uniform1f(u.uExposure, exp); gl.uniform1f(u.uContrast, state.contrast || 1); gl.uniform1f(u.uSat, state.saturation || 1);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.useProgram(this.drawP.p);
      this.litKey = key;
    }

    render(state) {
      const gl = this.gl; if (!gl || !this.view) return;
      const v = this.view, u = this.u;
      if (v.mode === 'passes') { if (v.evicted) this.restore(v); this.mix(state); }
      gl.useProgram(this.drawP.p);
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      const bind = (unit, tex) => { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex || this.blank); };
      bind(0, v.mode === 'passes' ? this.lit : null); bind(1, v.depth); bind(2, v.tex.beauty); bind(3, v.ids); bind(4, v.win);
      bind(6, v.glow); bind(7, v.swayA); bind(8, v.swayB);
      // outdoor clip: upload the current frame while it plays (a paused clip keeps its last upload)
      const vid = this.video, vidOk = vid && vid.readyState >= 2 && v.win && this.winAmt > 0.001;
      if (vidOk) {
        if (!this.videoTex) this.videoTex = this.texture(null);
        gl.activeTexture(gl.TEXTURE5); gl.bindTexture(gl.TEXTURE_2D, this.videoTex);
        const t = vid.currentTime;
        if (t !== this.videoAt || !this.videoUp) {
          try { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, vid); this.videoAt = t; this.videoUp = true; } catch (e) { }
        }
      } else bind(5, null);
      gl.uniform1f(u.uHasWin, vidOk ? 1 : 0); gl.uniform1f(u.uWinAmt, this.winAmt);
      if (vidOk) {
        const b = v.winBox, vw = vid.videoWidth, vh = vid.videoHeight;
        if (this.clipBox) { gl.uniform4fv(u.uWinBox, this.clipBox); gl.uniform4fv(u.uVidMap, [0, 0, 1, 1]); }   // rendered for this window
        else {   // footage: cover the window box with it (box measured in plate pixels)
          gl.uniform4fv(u.uWinBox, b);
          const ba = ((b[2] - b[0]) * v.size[0]) / ((b[3] - b[1]) * v.size[1]), va = vw / vh;
          let mw = 1, mh = 1; if (ba > va) mh = va / ba; else mw = ba / va;
          gl.uniform4fv(u.uVidMap, [(1 - mw) / 2, (1 - mh) * 0.35, mw, mh]);
        }
        gl.uniform3fv(u.uVidGrade, this.videoGrade || [1, 1, 1]);
      }
      gl.uniform1f(u.uHasIds, v.ids ? 1 : 0); gl.uniform1f(u.uHover, this.hover); gl.uniform1f(u.uHoverAmt, this.hoverAmt);
      const glowOn = !!v.glow && (this.glow[0] + this.glow[1] + this.glow[2]) > 0.002;
      gl.uniform1f(u.uHasGlow, glowOn ? 1 : 0); gl.uniform3fv(u.uGlowAmt, this.glow);
      const swayOn = !!v.swayA && this.swayOn;
      gl.uniform1f(u.uHasSway, swayOn ? 1 : 0);
      if (swayOn) { gl.uniform4fv(u.uSwayHook, this.swayHooks); gl.uniform1f(u.uTime, this.time); gl.uniform2fv(u.uPlatePx, v.platePx || v.size || [1, 1]); }
      gl.uniform4fv(u.uMap, this.map);
      gl.uniform2fv(u.uParallax, this.parallax);
      gl.uniform1f(u.uFocus, this.focus || 0.6);
      gl.uniform1f(u.uHasDepth, v.depth ? 1 : 0);
      gl.uniform1f(u.uDim, this.dim);
      gl.uniform1f(u.uMode, v.mode === 'passes' ? 0 : 1);
      if (v.mode !== 'passes') gl.uniform3fv(u.uGrade, Compositor.beautyGrade(state));
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    /* Bounding box (plate uv) of the white area of a mask image, e.g. the window opening; null when there is none. */
    static maskBox(img) {
      const w = 160, h = Math.max(1, Math.round(160 * img.naturalHeight / img.naturalWidth));
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h).data; let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (d[(j * w + i) * 4] > 100) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (j < y0) y0 = j; if (j > y1) y1 = j; }
      return x1 < 0 ? null : [x0 / w, y0 / h, (x1 + 1) / w, (y1 + 1) / h];
    }

    /* Without passes the golden-hour beauty plate is graded towards the time of day (approximation). */
    static beautyGrade(s) {
      const b = Math.pow(2, (s.exposure - 2.65) * -0.55);
      const sk = s.sky; const sum = sk[0] + sk[1] + sk[2] + 0.001;
      const day = Math.min(1, sum / 2.6);
      const k = 0.28 + 0.72 * day;
      const tint = [sk[0] / sum * 3, sk[1] / sum * 3, sk[2] / sum * 3];
      const t = (x, i) => Math.max(0.05, k * (0.65 + 0.35 * tint[i]) * Math.min(1.2, b * 1.0));
      return [t(0, 0), t(0, 1), t(0, 2)];
    }

    snapshotInto(ctx2d) {
      if (!this.gl) return false;
      const c = ctx2d.canvas; c.width = this.canvas.width; c.height = this.canvas.height;
      ctx2d.drawImage(this.canvas, 0, 0); return true;
    }
  }

  A.Compositor = Compositor;
})();
