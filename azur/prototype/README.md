# AZUR room — prototype

Interactive homepage prototype (Phase 1). Plain JavaScript + CSS, no build step, no framework, so every file maps onto a Shopify theme asset later.

Live (private): https://claude.ai/artifact/B4j6WH1yNHNeEG6rJLJ2Sy

## Files

| File | Job | Shopify later |
|---|---|---|
| `index.html` | Page markup: header, stage, hidden crawlable product list, noscript list | `sections/azur-room.liquid` |
| `css/azur-room.css` | All styling; Azur Electric tokens on `:root` | `assets/azur-room.css` |
| `js/azur-config.js` | **Art direction**: palettes, views, motion values, light over the day, German copy | section settings + `locales/de.default.json` |
| `js/azur-data.js` | Products in the shape Shopify will print (id, handle, name, price, image, variants…) | Liquid loop over a collection |
| `js/azur-light.js` | Visitor's clock → light-pass weights; sunrise/sunset estimated for Germany, no geolocation | `assets/azur-light.js` |
| `js/azur-compositor.js` | WebGL2: mixes the rendered light passes, depth parallax, AgX-style tone curve; falls back to the beauty plate | `assets/azur-compositor.js` |
| `js/azur-rail.js` | Garments on the rail: springs, hook pendulum, hover label, the info line under a chosen jersey | `assets/azur-rail.js` |
| `js/azur-drop.js` | Covered "Nächster Drop" garment: e-mail sign-up + holographic confirmation | posts the live theme's `snippets/signup-form.liquid` (tags `newsletter, drops`) |
| `js/azur-shop.js` | Product page + cart (simulated) | real `templates/product.json` + Shopify cart |
| `js/azur-panel.js` | "Regie" design panel (key D). Prototype only | not shipped |
| `js/azur-app.js` | Views (room / rail / bed / rail_m), camera moves, pointer, phone swipe, window kid, loop | `assets/azur-room.js` |

## Rendered assets (`assets/views/`)

Produced by `../scene/render_queue.py` from the Blender scene:

- `views.json`: where hangers, rail, window and bed sit on screen for each view (projected from 3D)
- `<view>/beauty.webp`: golden-hour plate (fallback, and what shows while passes are missing)
- `<view>/{sky,sun_low,sun_high,neon,lamp,ceiling,street}.webp` + `passes.json`: light passes, each rendered alone in white light, stored with a Reinhard curve (`lin = (y / (1 - y)) / scale`, `y = enc^2.2`)
- `<view>/depth.png`: depth for parallax (near = white)
- `hanger.webp`, `<view>/drop.webp`, `sprites.json`: hanger and covered-garment layers

Camera moves (`assets/moves/<move>/f###.webp` golden hour, `n###.webp` night, `moves.json`; from `../scene/render_moves.py`) replace the fake pans automatically once all frames of the needed set exist. The player grades the day frames toward the clock and lays the night frames over them by how dark it is; only the sets the current light needs are downloaded. Phones keep the fake pan.

`../tools/clean_sprite.py <view>` removes stray specks from a drop sprite and corrects its box (the queue runs it automatically).

## Changing things

- Motion feel: `AZUR.config.motion` (springs, pendulum, hover/select amounts, pan timing).
- Light at a given hour: `AZUR.config.daylight` keys (pass weights, exposure, garment grading).
- A garment's place: comes from the 3D scene; re-run `render_queue.py` after moving hangers in `build_room.py`.
- Products: `azur-data.js` (in Shopify: the collection).

## Local test

```bash
cd azur/prototype && python3 -m http.server 8765 &
sh azur/tools/mkdev.sh                     # wraps index.html into _dev.html
node azur/tools/prototype_shots.cjs out/   # headless screenshots (Chromium with --no-proxy-server)
```
