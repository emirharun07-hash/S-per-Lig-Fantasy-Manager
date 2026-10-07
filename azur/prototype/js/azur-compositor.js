/* AZUR — room compositor.
   Draws one view of the room from its rendered light passes (WebGL2): decodes each pass back to linear light,
   mixes them with the time-of-day weights, applies depth-based parallax and an AgX-style tone curve so the
   result matches the Blender stills. Falls back to the pre-graded beauty plate, and to a plain <img> without WebGL. */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const PASSES = ['sky', 'sunLow', 'sunHigh', 'neon', 'lamp', 'ceiling', 'street'];
  const FILES = { sky: 'sky', sunLow: 'sun_low', sunHigh: 'sun_high', neon: 'neon', lamp: 'lamp', ceiling: 'ceiling', street: 'street' };

  const VERT = `#version 300 es
  in vec2 aPos; out vec2 vUv;
  void main() { vUv = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5); gl_Position = vec4(aPos, 0.0, 1.0); }`;

  const FRAG = `#version 300 es
  precision highp float;
  in vec2 vUv; out vec4 outColor;
  uniform sampler2D tSky, tSunLow, tSunHigh, tNeon, tLamp, tCeiling, tStreet, tDepth, tBeauty;
  uniform vec3 wSky, wSunLow, wSunHigh, wNeon, wLamp, wCeiling, wStreet;
  uniform float sSky, sSunLow, sSunHigh, sNeon, sLamp, sCeiling, sStreet;
  uniform vec4 uMap;          // plate uv = uMap.xy + vUv * uMap.zw
  uniform vec2 uParallax;     // uv shift at depth 0 relative to the focus plane
  uniform float uFocus, uExposure, uMode, uDim, uContrast, uSat, uHasDepth;
  uniform vec3 uGrade;        // beauty mode only: rough time-of-day grade

  vec3 dec(sampler2D t, vec2 uv, float s) {
    vec3 e = texture(t, uv).rgb;
    vec3 y = min(pow(e, vec3(2.2)), vec3(0.995));
    return (y / (1.0 - y)) / s;
  }
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
    vec2 uv = uMap.xy + vUv * uMap.zw;
    float d = uHasDepth > 0.5 ? texture(tDepth, uv).r : uFocus;
    uv += uParallax * (d - uFocus);
    vec3 c;
    if (uMode < 0.5) {
      vec3 lin = dec(tSky, uv, sSky) * wSky + dec(tSunLow, uv, sSunLow) * wSunLow + dec(tSunHigh, uv, sSunHigh) * wSunHigh
               + dec(tNeon, uv, sNeon) * wNeon + dec(tLamp, uv, sLamp) * wLamp + dec(tCeiling, uv, sCeiling) * wCeiling
               + dec(tStreet, uv, sStreet) * wStreet;
      c = agx(lin * exp2(uExposure));
    } else {
      c = texture(tBeauty, uv).rgb * uGrade;
    }
    outColor = vec4(clamp(c * uDim, 0.0, 1.0), 1.0);
  }`;

  function loadImage(src) {
    return new Promise((res) => {
      const im = new Image();
      im.decoding = 'async';
      im.onload = () => res(im); im.onerror = () => res(null);
      im.src = src;
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
      if (this.gl) this.init();
    }
    get ok() { return !!this.gl; }

    init() {
      const gl = this.gl;
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
      const p = gl.createProgram();
      gl.attachShader(p, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAG));
      gl.bindAttribLocation(p, 0, 'aPos'); gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
      this.prog = p; gl.useProgram(p);
      const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      this.u = {};
      const names = ['tSky', 'tSunLow', 'tSunHigh', 'tNeon', 'tLamp', 'tCeiling', 'tStreet', 'tDepth', 'tBeauty',
        'wSky', 'wSunLow', 'wSunHigh', 'wNeon', 'wLamp', 'wCeiling', 'wStreet',
        'sSky', 'sSunLow', 'sSunHigh', 'sNeon', 'sLamp', 'sCeiling', 'sStreet',
        'uMap', 'uParallax', 'uFocus', 'uExposure', 'uMode', 'uDim', 'uContrast', 'uSat', 'uHasDepth', 'uGrade'];
      for (const n of names) this.u[n] = gl.getUniformLocation(p, n);
      ['tSky', 'tSunLow', 'tSunHigh', 'tNeon', 'tLamp', 'tCeiling', 'tStreet', 'tDepth', 'tBeauty'].forEach((n, i) => gl.uniform1i(this.u[n], i));
      this.blank = this.texture(null);
    }

    texture(img) {
      const gl = this.gl; const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      if (img) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
      else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
      return t;
    }

    /* Load a view. Resolves to 'passes', 'beauty' or 'none'. Textures are cached per view. */
    async load(key, meta, activate = true) {
      const base = A.config.assetBase + key + '/';
      if (this.cache[key]) { if (activate) { this.view = this.cache[key]; this.mode = this.view.mode; } return this.cache[key].mode; }
      const scales = (meta && meta[key]) || {};
      const have = PASSES.every(p => scales[FILES[p]]);
      const v = { key, mode: 'none', tex: {}, scales: {}, size: null, beautyImg: null };
      const depth = await loadImage(base + 'depth.png');
      if (have && this.gl) {
        const imgs = await Promise.all(PASSES.map(p => loadImage(base + FILES[p] + '.webp')));
        if (imgs.every(Boolean)) {
          PASSES.forEach((p, i) => { v.tex[p] = this.texture(imgs[i]); v.scales[p] = scales[FILES[p]]; });
          v.size = [imgs[0].naturalWidth, imgs[0].naturalHeight]; v.mode = 'passes';
        }
      }
      if (v.mode === 'none') {
        const b = await loadImage(base + 'beauty.webp');
        if (b) { v.beautyImg = b; v.size = [b.naturalWidth, b.naturalHeight]; v.mode = 'beauty'; if (this.gl) v.tex.beauty = this.texture(b); }
      }
      v.depth = depth && this.gl ? this.texture(depth) : null;
      this.cache[key] = v;
      if (activate) { this.view = v; this.mode = v.mode; }
      return v.mode;
    }

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
    }

    /* Plate uv (0..1 from the top-left) + depth value -> CSS pixels, including the current parallax. */
    toScreen(u, v, d) {
      const [ox, oy, zx, zy] = this.map;
      const f = this.focus || 0.6;
      const pu = u - this.parallax[0] * (d - f), pv = v - this.parallax[1] * (d - f);
      return [(pu - ox) / zx * this.cssW, (pv - oy) / zy * this.cssH];
    }
    /* Scale from plate fraction to CSS pixels (horizontal). */
    get pxPerPlateX() { return this.cssW / this.map[2]; }
    get pxPerPlateY() { return this.cssH / this.map[3]; }

    render(state) {
      const gl = this.gl; if (!gl || !this.view) return;
      const v = this.view, u = this.u;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      const bind = (unit, tex) => { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex || this.blank); };
      PASSES.forEach((p, i) => bind(i, v.tex[p]));
      bind(7, v.depth); bind(8, v.tex.beauty);
      gl.uniform4fv(u.uMap, this.map);
      gl.uniform2fv(u.uParallax, this.parallax);
      gl.uniform1f(u.uFocus, this.focus || 0.6);
      gl.uniform1f(u.uHasDepth, v.depth ? 1 : 0);
      gl.uniform1f(u.uDim, this.dim);
      gl.uniform1f(u.uContrast, state.contrast || 1);
      gl.uniform1f(u.uSat, state.saturation || 1);
      gl.uniform1f(u.uMode, v.mode === 'passes' ? 0 : 1);
      if (v.mode === 'passes') {
        const W = state.weights;
        gl.uniform3fv(u.wSky, W.sky); gl.uniform3fv(u.wSunLow, W.sunLow); gl.uniform3fv(u.wSunHigh, W.sunHigh);
        gl.uniform3fv(u.wNeon, W.neon); gl.uniform3fv(u.wLamp, W.lamp); gl.uniform3fv(u.wCeiling, W.ceiling); gl.uniform3fv(u.wStreet, W.street);
        PASSES.forEach(p => gl.uniform1f(u['s' + p[0].toUpperCase() + p.slice(1)], v.scales[p]));
        gl.uniform1f(u.uExposure, state.exposure);
      } else {
        gl.uniform3fv(u.uGrade, Compositor.beautyGrade(state));
      }
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
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
