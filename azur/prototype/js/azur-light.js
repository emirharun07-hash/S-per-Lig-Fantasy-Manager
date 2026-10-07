/* AZUR — light over the day.
   Turns the visitor's local clock into weights for the rendered light passes, continuously interpolated.
   No geolocation: sunrise and sunset are estimated for a Germany-typical location and the current date,
   and the configured day (keys in AZUR.config.daylight) is stretched to match them. */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const C = () => A.config;

  // reference day the keys were authored for (approx. late September in Germany)
  const REF = { sunrise: 7.2, noon: 13.4, sunset: 19.6 };

  function dayOfYear(d) { return Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 864e5); }

  /* Simplified NOAA solar calculation; returns local clock hours. */
  function sunTimes(date, lat, lon) {
    const n = dayOfYear(date);
    const g = 2 * Math.PI / 365 * (n - 1);
    const eq = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
    const decl = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g);
    const la = lat * Math.PI / 180;
    const cosH = (Math.cos(90.833 * Math.PI / 180) / (Math.cos(la) * Math.cos(decl))) - Math.tan(la) * Math.tan(decl);
    const ha = Math.acos(Math.max(-1, Math.min(1, cosH))) * 180 / Math.PI;
    const tz = -date.getTimezoneOffset();                    // minutes east of UTC
    const noon = (720 - 4 * lon - eq + tz) / 60;
    return { sunrise: noon - ha * 4 / 60, noon, sunset: noon + ha * 4 / 60 };
  }

  /* Map real clock hours onto the reference day (piecewise linear through sunrise, noon, sunset). */
  function toReference(h, st) {
    const a = [0, st.sunrise, st.noon, st.sunset, 24];
    const b = [0, REF.sunrise, REF.noon, REF.sunset, 24];
    for (let i = 0; i < 4; i++) {
      if (h <= a[i + 1]) return b[i] + (h - a[i]) / (a[i + 1] - a[i]) * (b[i + 1] - b[i]);
    }
    return h;
  }

  const smooth = t => t * t * (3 - 2 * t);
  const asVec = v => Array.isArray(v) ? v : [v, v, v];
  const mix = (a, b, t) => a + (b - a) * t;
  const mix3 = (a, b, t) => [mix(a[0], b[0], t), mix(a[1], b[1], t), mix(a[2], b[2], t)];

  function stateAt(hRef) {
    const keys = C().daylight;
    let i = 0;
    while (i < keys.length - 2 && keys[i + 1].h <= hRef) i++;
    const k0 = keys[i], k1 = keys[i + 1];
    const t = smooth(Math.max(0, Math.min(1, (hRef - k0.h) / (k1.h - k0.h))));
    return {
      sky: mix3(asVec(k0.sky), asVec(k1.sky), t),
      sunLow: mix3(asVec(k0.sunLow), asVec(k1.sunLow), t),
      sunHigh: mix3(asVec(k0.sunHigh), asVec(k1.sunHigh), t),
      neon: mix(k0.neon, k1.neon, t),
      lamp: mix(k0.lamp, k1.lamp, t),
      ceiling: mix(k0.ceiling, k1.ceiling, t),
      street: mix(k0.street, k1.street, t),
      exposure: mix(k0.exposure, k1.exposure, t),
      window: mix(k0.window, k1.window, t),
      garment: mix3(k0.garment, k1.garment, t),
      hRef
    };
  }

  function srgbToLinear(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function hexToLinear(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(v => srgbToLinear(v / 255));
  }

  /* Design-panel overrides (multipliers) live here; the app writes into it. */
  const overrides = {
    timeHours: null, exposure: 0, sky: 1, sun: 1, neon: 1, lamp: 1, ceiling: 1, street: 1,
    warmth: 0, contrast: 1, saturation: 1, window: 1
  };

  function current(date) {
    date = date || new Date();
    const cfg = C();
    const st = sunTimes(date, cfg.location.lat, cfg.location.lon);
    let h = overrides.timeHours != null ? overrides.timeHours : date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
    if (!isFinite(h)) h = 13;                       // browser clock unavailable: a calm daytime room
    const s = stateAt(overrides.timeHours != null ? h : toReference(h, st));
    const o = overrides;
    const warm = [1 + o.warmth * 0.18, 1 + o.warmth * 0.02, 1 - o.warmth * 0.2];
    const glow = hexToLinear(cfg.palettes[cfg.palette].glow);
    s.weights = {
      sky: s.sky.map((v, i) => v * o.sky * warm[i]),
      sunLow: s.sunLow.map((v, i) => v * o.sun * warm[i]),
      sunHigh: s.sunHigh.map((v, i) => v * o.sun * warm[i]),
      neon: glow.map(v => v * s.neon * o.neon),
      lamp: cfg.lampTint.map(v => v * s.lamp * o.lamp),
      ceiling: cfg.ceilingTint.map(v => v * s.ceiling * o.ceiling),
      street: cfg.streetTint.map(v => v * s.street * o.street)
    };
    s.exposure += o.exposure;
    s.contrast = o.contrast; s.saturation = o.saturation;
    s.window *= o.window;
    s.clockHours = h; s.sun = st;
    s.night = Math.max(0, Math.min(1, (3.2 - (s.sky[0] + s.sky[1] + s.sky[2])) / 3.0)) ** 2;
    s.phase = phaseName(s.hRef);
    return s;
  }

  function phaseName(h) {
    if (h < 5.2 || h >= 23) return 'Tiefe Nacht';
    if (h < 6.6) return 'Morgendämmerung';
    if (h < 10) return 'Morgen';
    if (h < 16) return 'Tag';
    if (h < 19) return 'Goldene Stunde';
    if (h < 20.2) return 'Sonnenuntergang';
    if (h < 21.2) return 'Blaue Stunde';
    return 'Nacht';
  }

  A.light = { current, sunTimes, overrides, hexToLinear, srgbToLinear };
})();
