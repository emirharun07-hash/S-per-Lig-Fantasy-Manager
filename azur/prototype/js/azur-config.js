/* AZUR — scene configuration.
   Everything that is art direction lives here: palette, views, motion, light over the day, copy.
   The other scripts only read from AZUR.config, so motion and look can change without touching logic. */
window.AZUR = window.AZUR || {};

AZUR.config = {
  assetBase: 'assets/views/',

  /* Accent systems. A is the chosen one; the others stay switchable in the design panel. */
  palettes: {
    A: { name: 'Azur Electric',  glow: '#16B8FF', highlight: '#8DEBFF', ink: '#0A6A9A', night: '#07131D' },
    B: { name: 'Stadium Cobalt', glow: '#315CFF', highlight: '#A8C7FF', ink: '#2747D8', night: '#0A0D14' },
    C: { name: 'Acid Pitch',     glow: '#B7FF00', highlight: '#D9FF75', ink: '#466400', night: '#0B100A' },
    D: { name: 'Silver Neon',    glow: '#00E5FF', highlight: '#D7DCE2', ink: '#3D4651', night: '#090A0C' },
    E: { name: 'Night Claret',   glow: '#FF3568', highlight: '#FF8DA8', ink: '#C21A4C', night: '#12090D' },
    F: { name: 'Sunset Orange',  glow: '#FF7038', highlight: '#FFC36A', ink: '#A9441A', night: '#16100C' }
  },
  palette: 'A',

  /* Views = camera positions rendered in Blender (scene/render_queue.py). Positions of hangers, window and
     bed come from assets/views/views.json; the values here are art direction on top of that. */
  views: {
    room:   { label: 'Zimmer', parallax: 0.010, focus: 0.55, garmentScale: 1.0,
              bedHotspot: [[0.20, 0.83], [0.46, 0.79], [0.53, 1.0], [0.18, 1.0]] },
    rail:   { label: 'Ständer', parallax: 0.014, focus: 0.62, garmentScale: 1.0 },
    bed:    { label: 'Bett', parallax: 0.012, focus: 0.5, exposure: 0.5, masks: false },   // exposure: extra stops on top of the clock
    rail_m: { label: 'Ständer', parallax: 0.008, focus: 0.62, garmentScale: 1.0, swipe: true }
  },
  startView: { desktop: 'room', mobile: 'rail_m' },
  mobileQuery: '(max-width: 760px), (pointer: coarse) and (max-width: 1024px) and (orientation: portrait)',

  /* Garments on the rail. The 3D rail fans them 25° toward the window; CSS mirrors that. */
  garments: {
    fanDeg: 24,               // resting turn toward the window (matches FAN in build_room.py)
    perspective: 1400,        // px, CSS perspective of the garment layer
    hangerWidthM: 0.43,       // hanger shoulder width in metres (for sprite scaling)
    shadow: { x: -0.05, y: 0.035, blur: 0.06, alpha: 0.35 }   // fractions of garment height
  },

  /* Motion. All durations in ms, springs as stiffness/damping per second. Tweak freely. */
  motion: {
    intensity: 1.0,           // global multiplier (design panel)
    spring: { stiffness: 170, damping: 19 },          // lift, push, turn
    swing:  { stiffness: 38,  damping: 3.2, impulse: 0.012, maxDeg: 7, hoverKick: 9, leaveKick: 5, selectKick: 14 },   // pendulum on the hook (deg, deg/s)
    idle:   { swayDeg: 0.45, periodS: 6.5 },          // garments breathe a little
    hover:  { lift: 0.035, forward: 0.045, turnDeg: -9, tiltDeg: 1.4, bright: 1.07, neighbourPush: 0.16, falloff: 0.45 },
    select: { lift: 0.06, forward: 0.16, turnDeg: -24, push: 0.42, dimRoom: 0.62, blurRoom: 2.5 },
    labelDelay: 90,
    pan: { outMs: 520, inMs: 820, zoom: 1.32, blurPx: 14, drift: 0.04 },   // fake camera move between views
    parallaxEase: 0.06        // how fast the room follows the pointer
  },
  interactionStrength: 1.0,

  /* Light over the day. Each key: hour, then linear RGB weights for every rendered light pass.
     The browser mixes the passes (sky, sun_low, sun_high, neon, lamp, ceiling, street) with these weights.
     exposure is in stops (the approved stills use 2.65). neon is a scalar; its colour is the palette glow. */
  daylight: [
    { h: 0.0,  sky: [0.012, 0.016, 0.034], sunLow: 0, sunHigh: 0, neon: 1.05, lamp: 0.0,  ceiling: 0.0,  spot: 0.5, street: 0.3,  exposure: 3.0, window: 0.15, garment: [0.28, 0.0, 0.42] },
    { h: 5.2,  sky: [0.05, 0.065, 0.12],   sunLow: 0, sunHigh: 0, neon: 0.95, lamp: 0.0,  ceiling: 0.0,  spot: 0.35, street: 0.24, exposure: 2.95, window: 0.35, garment: [0.42, 0.0, 0.36] },
    { h: 6.4,  sky: [0.42, 0.46, 0.6],     sunLow: 0, sunHigh: 0, neon: 0.55, lamp: 0.0,  ceiling: 0.0,  spot: 0.25, street: 0.15, exposure: 2.8, window: 0.75, garment: [0.66, 0.02, 0.25] },
    { h: 8.5,  sky: [0.9, 0.9, 0.92],      sunLow: 0, sunHigh: [0.25, 0.24, 0.22], neon: 0.12, lamp: 0, ceiling: 0, spot: 0.3, street: 0, exposure: 2.75, window: 1, garment: [0.92, 0.0, 0.06] },
    { h: 12.5, sky: [1.0, 1.0, 1.0],       sunLow: 0, sunHigh: [0.75, 0.72, 0.66], neon: 0.08, lamp: 0, ceiling: 0, spot: 0.3, street: 0, exposure: 2.65, window: 1, garment: [0.98, 0.0, 0.0] },
    { h: 16.0, sky: [1.0, 0.97, 0.92],     sunLow: [0.35, 0.27, 0.18], sunHigh: [0.3, 0.27, 0.22], neon: 0.12, lamp: 0, ceiling: 0, spot: 0.35, street: 0, exposure: 2.65, window: 1, garment: [0.95, 0.12, 0.0] },
    { h: 18.4, sky: [1.0, 0.86, 0.72],     sunLow: [1.0, 0.6, 0.33], sunHigh: 0, neon: 0.35, lamp: 0, ceiling: 0, spot: 0.45, street: 0, exposure: 2.65, window: 1, garment: [0.92, 0.32, 0.0] },
    { h: 19.6, sky: [0.62, 0.45, 0.42],    sunLow: [0.85, 0.36, 0.14], sunHigh: 0, neon: 0.75, lamp: 0.25, ceiling: 0, spot: 0.6, street: 0, exposure: 2.85, window: 0.8, garment: [0.78, 0.4, 0.05] },
    { h: 20.6, sky: [0.17, 0.22, 0.42],    sunLow: 0, sunHigh: 0, neon: 1.0, lamp: 0.75, ceiling: 0.0, spot: 0.7, street: 0.15, exposure: 2.95, window: 0.55, garment: [0.48, 0.12, 0.3] },
    { h: 22.3, sky: [0.04, 0.055, 0.11],   sunLow: 0, sunHigh: 0, neon: 1.05, lamp: 0.85, ceiling: 0.0, spot: 0.7, street: 0.3, exposure: 3.0, window: 0.25, garment: [0.32, 0.04, 0.36] },
    { h: 24.0, sky: [0.012, 0.016, 0.034], sunLow: 0, sunHigh: 0, neon: 1.05, lamp: 0.0,  ceiling: 0.0,  spot: 0.5, street: 0.3,  exposure: 3.0, window: 0.15, garment: [0.28, 0.0, 0.42] }
  ],
  lampTint: [1.0, 0.62, 0.32],        // warm bulb in the desk lamp
  ceilingTint: [1.0, 0.86, 0.68],
  streetTint: [0.95, 0.84, 0.7],    // LED street lamp, slightly warm
  spotTint: [1.0, 0.82, 0.62],      // ceiling spot over the rail (scene2): warm, shows the jerseys
  /* Germany-typical sun times (shifted by season, see azur-light.js); no geolocation needed. */
  location: { lat: 51.2, lon: 10.4 },

  /* Labels and copy (customer facing = German). */
  copy: {
    hintDesktop: 'Wähle ein Trikot',
    hintMobile: 'Tippe auf ein Trikot',
    view: 'Ansehen',
    viewJersey: 'Trikot ansehen',
    putBack: 'Zurückhängen',
    backToRoom: 'Zurück ins Zimmer',
    room: 'Zimmer', rail: 'Ständer', bed: 'Bett',
    chooseSize: 'Größe wählen',
    addToCart: 'In den Warenkorb',
    added: 'Im Warenkorb',
    cart: 'Warenkorb', checkout: 'Zur Kasse', emptyCart: 'Dein Warenkorb ist leer.',
    total: 'Summe', inclVat: 'inkl. MwSt.',
    nav: ['Shop', 'Kollektion', 'Über uns'],
    dropTitle: 'Nächster Drop',
    dropText: 'Noch unter Verschluss.',
    dropPlaceholder: 'Deine E-Mail-Adresse',
    dropButton: 'Benachrichtige mich',
    dropLegal: 'Mit der Anmeldung erhältst du E-Mails von AZUR zu neuen Drops. Abmeldung jederzeit möglich.',
    dropDone: 'Du bist dabei.',
    dropDoneText: 'Wir melden uns, bevor der Drop live geht.',
    dropInvalid: 'Bitte gib eine gültige E-Mail-Adresse ein.',
    bedTease: 'Psst. Blätter mal im Heft auf der Decke.',
    magSpot: 'ANSTOSS lesen',
    mag: {
      label: 'ANSTOSS, Ausgabe 01. Das Heft von AZUR',
      prev: 'Zurückblättern', next: 'Weiterblättern', close: 'Heft zuklappen',
      coverWord: 'Titel', backWord: 'Rückseite',
      issue: 'Ausgabe 01 · Das Heft von AZUR',
      coverAlt: 'Zwei Kinder spielen Fußball im Morgennebel, einer im Fallrückzieher, einer im Tor.',
      coverLines: ['Zwei Städte.', 'Drei Länder.', 'Ein Zimmer.'],
      coverSticker: 'Mit Lookbook: alle Trikots',
      editorialKicker: 'Editorial',
      editorialHead: 'Anstoß.',
      editorialLead: 'Poster an der Wand, der Ball unterm Bett, das Trikot für morgen schon rausgelegt. So fängt es an.',
      about: ['Wir nehmen Farben und Zeichen von Ländern und Städten und setzen sie auf ein reduziertes Trikot.',
              'Embleme und die Azur-Signatur auf der Brust. Getragen auf dem Platz und danach.'],
      sign: 'Emir & Talha',
      signNote: 'Emir Kilic und Talha Zaffar, Gründer von AZUR',
      storyAlt: 'Ein Spieler im roten Shirt schießt einen Ball über eine sonnige Wiese.',
      storyQuote: 'Getragen auf dem Platz und danach.',
      lookKicker: 'Lookbook',
      tocKicker: 'In diesem Heft',
      toRail: 'Am Ständer ansehen', toShop: 'Im Shop',
      dropKicker: 'Vorschau',
      dropHead: 'Nächster Drop',
      dropText: 'Am Ständer hängt noch etwas unter der Hülle. Noch unter Verschluss. Trag dich ein, dann erfährst du es zuerst.',
      toDrop: 'Zur Hülle am Ständer',
      bye: 'Bis zum nächsten Anstoß.',
      credits: 'Fotos: sasint, Negative Space (CC0)'
    },
    roomHint: 'Klick auf den Ständer oder aufs Bett',
    prototypeNote: 'Prototyp · Warenkorb und Anmeldung sind simuliert'
  }
};

/* Paths are written as in the prototype ('assets/scene2/views/rail/sky.webp'). In Shopify the section sets
   AZUR.config.urlMap (renders in Content > Files, logos in the theme's assets) and AZUR.config.inline (the JSON). */
AZUR.url = p => (AZUR.config.urlMap ? AZUR.config.urlMap(p) : p);

