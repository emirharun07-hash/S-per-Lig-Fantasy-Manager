/* AZUR — the jersey as a 3D model in the product view (scene/export_models.py: draped shell on its wooden hanger).
   A small GLB reader (positions, normals, UVs, base colour textures, node transforms) and a WebGL2 view of it:
   drag to turn, wheel or pinch to zoom, double click to reset; it sways a little until it is touched.
   Renders only while something moves. A 3D scan of a product can replace its GLB under the same name. */
(function () {
  const A = window.AZUR = window.AZUR || {};

  async function readGLB(url) {
    const res = await fetch(url); if (!res.ok) throw new Error('model ' + res.status);
    let buf;
    if (/\.json(\?|$)/.test(url)) {                // hosts that do not serve .glb get it base64-wrapped in JSON
      const b64 = (await res.json()).glb, bin = atob(b64), u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      buf = u8.buffer;
    } else buf = await res.arrayBuffer();
    const dv = new DataView(buf);
    if (dv.getUint32(0, true) !== 0x46546C67) throw new Error('not a GLB');
    let off = 12, json = null, bin = null;
    while (off + 8 <= buf.byteLength) {
      const len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true);
      if (type === 0x4E4F534A) json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, off + 8, len)));
      else if (type === 0x004E4942) bin = buf.slice(off + 8, off + 8 + len);
      off += 8 + len;
    }
    if (!json || !bin) throw new Error('GLB without data');
    return { json, bin };
  }

  /* ---------------------------------------------------------------- small matrix helpers (column-major) */
  const M = {
    id: () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    mul(a, b) { const o = new Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; },
    trs(t = [0, 0, 0], q = [0, 0, 0, 1], s = [1, 1, 1]) {
      const [x, y, z, w] = q, xx = x * x, yy = y * y, zz = z * z, xy = x * y, xz = x * z, yz = y * z, wx = w * x, wy = w * y, wz = w * z;
      return [(1 - 2 * (yy + zz)) * s[0], 2 * (xy + wz) * s[0], 2 * (xz - wy) * s[0], 0,
              2 * (xy - wz) * s[1], (1 - 2 * (xx + zz)) * s[1], 2 * (yz + wx) * s[1], 0,
              2 * (xz + wy) * s[2], 2 * (yz - wx) * s[2], (1 - 2 * (xx + yy)) * s[2], 0, t[0], t[1], t[2], 1];
    },
    persp(fovy, asp, n, f) { const t = 1 / Math.tan(fovy / 2); return [t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; },
    look(e, c, up) {
      const z = norm([e[0] - c[0], e[1] - c[1], e[2] - c[2]]), x = norm(cross(up, z)), y = cross(z, x);
      return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1];
    },
    apply(m, p) { return [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]]; }
  };
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

  const VS = `#version 300 es
  in vec3 aPos; in vec3 aNor; in vec2 aUv;
  uniform mat4 uVP, uModel; out vec3 vN; out vec2 vUv; out vec3 vW;
  void main() { vec4 w = uModel * vec4(aPos, 1.0); vW = w.xyz; vN = mat3(uModel) * aNor; vUv = aUv; gl_Position = uVP * w; }`;
  const FS = `#version 300 es
  precision highp float;
  in vec3 vN; in vec2 vUv; in vec3 vW; out vec4 o;
  uniform sampler2D tBase; uniform vec4 uBase; uniform float uHasTex; uniform vec3 uEye;
  void main() {
    vec3 base = uBase.rgb;
    if (uHasTex > 0.5) base *= pow(texture(tBase, vUv).rgb, vec3(2.2));
    vec3 n = normalize(vN), v = normalize(uEye - vW);
    if (dot(n, v) < 0.0) n = -n;                                  // the cloth is seen from both sides at the hem
    vec3 key = normalize(vec3(-0.45, 0.75, 0.75)), fill = normalize(vec3(0.8, 0.1, 0.45));
    float d1 = max(dot(n, key), 0.0), d2 = max(dot(n, fill), 0.0);
    float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0);
    vec3 amb = mix(vec3(0.07, 0.075, 0.09), vec3(0.30, 0.29, 0.28), n.y * 0.5 + 0.5);
    vec3 c = base * (amb + vec3(1.0, 0.96, 0.9) * d1 * 1.1 + vec3(0.62, 0.74, 0.95) * d2 * 0.4) + vec3(0.55, 0.72, 1.0) * rim * 0.16;
    c = c / (1.0 + c * 0.12);
    o = vec4(pow(c, vec3(1.0 / 2.2)), 1.0);
  }`;

  class Viewer {
    constructor(canvas, onReady) {
      this.canvas = canvas; this.onReady = onReady;
      this.gl = null;
      try { this.gl = canvas.getContext('webgl2', { antialias: true, alpha: true, premultipliedAlpha: true }); } catch (e) { }
      this.parts = []; this.cache = {};
      this.yaw = 0; this.pitch = 0.06; this.zoom = 1; this.vyaw = 0; this.touched = false; this.t0 = performance.now();
      if (this.gl) { this.init(); this.bind(); }
    }
    get ok() { return !!this.gl; }

    init() {
      const gl = this.gl, sh = (t, s) => { const x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x);
        if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; };
      const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FS));
      gl.bindAttribLocation(p, 0, 'aPos'); gl.bindAttribLocation(p, 1, 'aNor'); gl.bindAttribLocation(p, 2, 'aUv'); gl.linkProgram(p);
      this.prog = p; this.u = {};
      ['uVP', 'uModel', 'tBase', 'uBase', 'uHasTex', 'uEye'].forEach(n => { this.u[n] = gl.getUniformLocation(p, n); });
    }

    /* Show a product's model (cached per URL). Resolves true when it is on screen, false without a model. */
    async show(url) {
      this.url = url; this.parts = []; this.reset(true);
      if (!this.gl) return false;
      this.clear();                                    // never show the jersey that was open before
      try {
        // the promise is cached at once, so a second open while it loads waits for the same download
        const m = this.cache[url] || (this.cache[url] = readGLB(url).then(g => this.upload(g)));
        const parts = await m;
        if (this.url !== url) return false;            // another jersey was opened meanwhile
        this.parts = parts.list; this.bounds = parts.bounds;
        this.start(); return true;
      } catch (e) { delete this.cache[url]; return false; }
    }
    /* raf must be cleared too: kick() schedules nothing while it holds an id, and a cancelled frame never clears it */
    stop() { this.running = false; cancelAnimationFrame(this.raf); this.raf = 0; this.url = null; }
    clear() { const gl = this.gl; gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); }
    reset(instant) {
      this.touched = false; this.vyaw = 0; this.t0 = performance.now();
      if (instant) { this.yaw = 0; this.pitch = 0.06; this.zoom = 1; } else { this.resetFrom = [this.yaw, this.pitch, this.zoom]; this.resetT = performance.now(); }
      this.kick();
    }

    async upload({ json, bin }) {
      const gl = this.gl, acc = i => {
        const a = json.accessors[i], bv = json.bufferViews[a.bufferView];
        const C = { 5126: Float32Array, 5125: Uint32Array, 5123: Uint16Array, 5121: Uint8Array }[a.componentType];
        const n = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[a.type];
        return new C(bin, (bv.byteOffset || 0) + (a.byteOffset || 0), a.count * n);
      };
      const images = await Promise.all((json.images || []).map(im => {
        const bv = json.bufferViews[im.bufferView];
        const blob = new Blob([new Uint8Array(bin, bv.byteOffset || 0, bv.byteLength)], { type: im.mimeType });
        return createImageBitmap(blob).catch(() => null);
      }));
      const texOf = new Map();
      const texture = idx => {
        if (texOf.has(idx)) return texOf.get(idx);
        const tx = json.textures[idx] || {}, ext = tx.extensions || {};
        const src = tx.source != null ? tx.source : (ext.EXT_texture_webp || ext.KHR_texture_basisu || {}).source, img = images[src];   // WebP images come as EXT_texture_webp
        let t = null;
        if (img) {
          t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img); gl.generateMipmap(gl.TEXTURE_2D);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        }
        texOf.set(idx, t); return t;
      };
      const list = [], lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
      const visit = (ni, parent) => {
        const nd = json.nodes[ni];
        const local = nd.matrix ? nd.matrix.slice() : M.trs(nd.translation, nd.rotation, nd.scale);
        const world = M.mul(parent, local);
        if (nd.mesh != null) json.meshes[nd.mesh].primitives.forEach(pr => {
          const at = pr.attributes; if (at.POSITION == null) return;
          const pos = acc(at.POSITION), nor = at.NORMAL != null ? acc(at.NORMAL) : null, uv = at.TEXCOORD_0 != null ? acc(at.TEXCOORD_0) : null;
          for (let i = 0; i < pos.length; i += 3) { const w = M.apply(world, [pos[i], pos[i + 1], pos[i + 2]]); for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], w[k]); hi[k] = Math.max(hi[k], w[k]); } }
          const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
          const vb = (data, loc, size) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
            gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0); };
          vb(pos, 0, 3);
          if (nor) vb(nor, 1, 3); else { gl.disableVertexAttribArray(1); gl.vertexAttrib3f(1, 0, 0, 1); }
          if (uv) vb(uv, 2, 2); else { gl.disableVertexAttribArray(2); gl.vertexAttrib2f(2, 0, 0); }
          let count = pos.length / 3, type = null;
          if (pr.indices != null) {
            const ix = acc(pr.indices), b = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ix, gl.STATIC_DRAW);
            count = ix.length; type = ix instanceof Uint32Array ? gl.UNSIGNED_INT : ix instanceof Uint16Array ? gl.UNSIGNED_SHORT : gl.UNSIGNED_BYTE;
          }
          gl.bindVertexArray(null);
          const mat = pr.material != null ? json.materials[pr.material] : {}, pbr = mat.pbrMetallicRoughness || {};
          const bt = pbr.baseColorTexture;
          list.push({ vao, count, type, model: world, base: pbr.baseColorFactor || [1, 1, 1, 1], tex: bt ? texture(bt.index) : null });
        });
        (nd.children || []).forEach(c => visit(c, world));
      };
      const scene = json.scenes[json.scene || 0];
      (scene ? scene.nodes : json.nodes.map((_, i) => i)).forEach(n => visit(n, M.id()));
      const center = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
      const radius = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2;
      return { list, bounds: { center, radius } };
    }

    bind() {
      const c = this.canvas, pts = new Map();
      let last = null, pinch = null;
      c.addEventListener('pointerdown', e => {
        c.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
        this.touch(); this.vyaw = 0; last = { x: e.clientX, y: e.clientY, t: performance.now() };
        if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), z: this.zoom }; }
      });
      c.addEventListener('pointermove', e => {
        if (!pts.has(e.pointerId)) return;
        pts.set(e.pointerId, [e.clientX, e.clientY]);
        if (pts.size === 2 && pinch) {
          const [a, b] = [...pts.values()]; this.zoom = this.clampZoom(pinch.z * Math.hypot(a[0] - b[0], a[1] - b[1]) / Math.max(1, pinch.d));
        } else if (last) {
          const now = performance.now(), dx = e.clientX - last.x, dy = e.clientY - last.y;
          this.yaw += dx * 0.009; this.pitch = Math.max(-0.45, Math.min(0.6, this.pitch + dy * 0.006));
          this.vyaw = dx * 0.009 / Math.max(8, now - last.t) * 1000; last = { x: e.clientX, y: e.clientY, t: now };
        }
        this.kick();
      });
      const up = e => { if (!pts.delete(e.pointerId)) return; if (pts.size < 2) pinch = null; if (!pts.size) last = null; else { const p = [...pts.values()][0]; last = { x: p[0], y: p[1], t: performance.now() }; } };
      ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(ev => c.addEventListener(ev, up));
      c.addEventListener('wheel', e => { e.preventDefault(); this.touch(); this.zoom = this.clampZoom(this.zoom * Math.exp(-e.deltaY * 0.0016)); this.kick(); }, { passive: false });
      c.addEventListener('dblclick', () => this.reset(false));
      if ('ResizeObserver' in window) new ResizeObserver(() => this.kick()).observe(c);   // a still model redraws at the new size
      c.addEventListener('keydown', e => {
        const k = { ArrowLeft: [-0.25, 0], ArrowRight: [0.25, 0], '+': [0, 1.15], '-': [0, 1 / 1.15], '=': [0, 1.15] }[e.key];
        if (!k) return; e.preventDefault(); this.touch(); this.yaw += k[0]; if (k[1]) this.zoom = this.clampZoom(this.zoom * k[1]); this.kick();
      });
    }
    clampZoom(z) { return Math.max(1, Math.min(3.4, z)); }
    touch() { if (!this.touched) { this.touched = true; this.canvas.dispatchEvent(new CustomEvent('azur-touched', { bubbles: true })); } this.resetT = null; }

    start() { this.running = true; this.kick(); }
    kick() { if (!this.running || this.raf) return; this.raf = requestAnimationFrame(t => { this.raf = 0; this.frame(t); }); }

    frame(t) {
      if (!this.running || !this.parts.length) return;
      const reduced = A.app && A.app.reduced;
      let more = false;
      if (this.resetT != null) {                                   // ease back to the front
        const k = Math.min(1, (t - this.resetT) / 600), e = k * k * (3 - 2 * k), [y0, p0, z0] = this.resetFrom;
        this.yaw = y0 + (Math.round(y0 / (2 * Math.PI)) * 2 * Math.PI - y0) * e; this.pitch = p0 + (0.06 - p0) * e; this.zoom = z0 + (1 - z0) * e;
        if (k < 1) more = true; else { this.resetT = null; this.yaw = 0; this.t0 = t; }
      } else if (!this.touched && !reduced) {                      // shown on its hanger: a slow turn back and forth
        this.yaw = 0.42 * Math.sin((t - this.t0) / 1000 * 0.55); more = true;
      } else if (Math.abs(this.vyaw) > 0.01 && !reduced) {         // let go: it keeps turning a little
        this.yaw += this.vyaw / 60; this.vyaw *= 0.93; more = true;
      }
      this.draw();
      if (more) this.kick();
    }

    draw() {
      const gl = this.gl, c = this.canvas, dpr = Math.min(window.devicePixelRatio || 1, 2);
      const W = Math.round(c.clientWidth * dpr), H = Math.round(c.clientHeight * dpr);
      if (!W || !H) return;
      if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
      gl.viewport(0, 0, W, H); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE); gl.useProgram(this.prog);
      const { center, radius } = this.bounds, asp = W / H, fov = 0.52;
      // fit the jersey's height (and width on narrow screens), then zoom in toward its middle
      const fit = radius / Math.sin(fov / 2) * Math.max(1, 0.8 / asp) * 1.4, d = fit / this.zoom;   // room around it
      const cp = Math.cos(this.pitch), eye = [center[0] + d * cp * Math.sin(this.yaw), center[1] + d * Math.sin(this.pitch), center[2] + d * cp * Math.cos(this.yaw)];
      const vp = M.mul(M.persp(fov, asp, Math.max(0.01, d - radius * 2), d + radius * 3), M.look(eye, center, [0, 1, 0]));
      gl.uniformMatrix4fv(this.u.uVP, false, vp); gl.uniform3fv(this.u.uEye, eye); gl.uniform1i(this.u.tBase, 0);
      this.parts.forEach(p => {
        gl.uniformMatrix4fv(this.u.uModel, false, p.model);
        gl.uniform4fv(this.u.uBase, p.base); gl.uniform1f(this.u.uHasTex, p.tex ? 1 : 0);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, p.tex);
        gl.bindVertexArray(p.vao);
        if (p.type) gl.drawElements(gl.TRIANGLES, p.count, p.type, 0); else gl.drawArrays(gl.TRIANGLES, 0, p.count);
      });
      gl.bindVertexArray(null);
    }
  }

  A.Viewer = Viewer;
})();
