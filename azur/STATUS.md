# AZUR bedroom — status

Read this first when resuming work. The full creative brief is in `BRIEF.md`.

## Where we are

**Phase 1 (Claude Artifact prototype)**. Shopify implementation (Phase 2) starts only after explicit approval.

| Step | State |
|---|---|
| Palette chosen | Done: A, Azur Electric (Glow #16B8FF, Highlight #8DEBFF, Ink #0A6A9A, Night #07131D) |
| 3D toolchain | Done: Blender 5.0.1 via `pip install bpy==5.0.1` (Python 3.11), Cycles on CPU |
| Assets | Done: jerseys from Shopify, AZUR logo from the live theme, 23 CC0 poster photos, Poly Haven textures/models/HDRI |
| First still (golden hour) | Done: `renders/still_golden_hour.png`, approved as a direction on 2026-10-06 |
| Scene round 2 | Done: pillow, folded-back duvet, magazine, desk corner with lamp and chair, boots, training bag, medals, pennant, black garment bag with AZUR print and zip, flush ceiling light, neon double tubes for thick strokes |
| Camera options | Rendered: presets A–F plus bed detail G in `scene/build_room.py` (`CAMS`). Owner decides later; bed is out of frame in most angles, so a layout change (bed against the left poster wall) is proposed |
| Views + light passes | **Done** (04:32 UTC): beauty plates, depth maps, hanger + drop sprites, all 7 light passes for room / rail / rail_m / bed. Checked in the browser across the day and published (artifact version 8) |
| Interactive prototype | **Published**: https://claude.ai/artifact/B4j6WH1yNHNeEG6rJLJ2Sy (code in `prototype/`, config in `prototype/js/azur-config.js`) |
| Real camera moves | **Done and live** (artifact version 12, 09:20 UTC): room → rail and room → bed (and back), each with a day and a night set; garments fly along. Phones and rail ↔ bed keep the fake move |
| Bed fix | **Done in the scene, re-rendering**: the duvet looked lumpy and grey. Now it is simulated the way it happens (head edge pulled back on a hook, then let go): a thrown-back sky-blue duvet with soft folds, the white pillow free. Bed camera unchanged. Room and bed plates/passes are re-rendered with the new `.cache/azur_room.blend`; rail views do not show the bed and stay valid |

## Owner feedback on the first still (2026-10-06)

- Likes the idea and the first design. Posters, rail, window, ball, rug and trophy work well.
- The bed tells no story: fix it (crumpled duvet, pillow, things on the bed).
- Jerseys overlapping is fine: you hover through them, details only on click (small info with a link to the product).
- Garment bag: free to redesign. Logo correction in the neon: yes.
- Add more storytelling objects.
- Realistic style is right for now (may change later). The time of day must follow the visitor's clock.
- Camera may change later (bed barely visible, jerseys slightly too far). Keep the camera configurable or show several angles.
- Animation details may still change: build motion fully parameterised.
- Interaction inspiration accepted (see `refs/NOTES.md`).

## Owner decisions (2026-10-07, night)

- Start view: the room (camera B = view `room`). Clicking a jersey moves the camera to the rail (`rail`, closer and higher than C) and opens that jersey in one step. Clicking the bed moves to the bed view (`bed`).
- Fake camera moves for now; **real rendered moves must follow later**.
- Phones start at the rail (`rail_m`), swipe along it, garments swing with the swipe.
- Bed: easter egg comes later (decided 2026-10-07 afternoon, owner left it to us: the magazine, see below).
- Overlapping jerseys are fine; details only on click.

## Scene 2 (owner feedback 2026-10-07: jerseys looked pasted in)

- Jerseys are real 3D garments in the renders now: a thin fabric shell built from the shop's front and back photos
  (`jersey_mesh` in `build_room.py`), hooks only (the wooden bar sits inside). New: double window with mullion, gaskets,
  aluminium handles, roller-shutter cover and belt winder; linen curtain; lofted football boots; ceiling spot over the
  rail (its own light pass `spot`); magazine cover flat.
- Render set `prototype/assets/scene2/` (`AZUR_SET`, default scene2; old set stays in `assets/views` until scene2 is live):
  views room / rail / rail_m / bed with garments (beauty, depth, 8 passes), `ids.png` (which garment is where: hover and
  click), `window.png` (where the outside shows), chosen-garment views `rail@i` / `rail_m@i` (garment taken off the rail
  toward the camera, 8 passes each), moves room→rail / room→bed and pull moves `rail-rail@i`, day + night.
- Outside the window: real footage of kids playing on a Bolzplatz (Mixkit, free licence: https://mixkit.co/free-stock-video/young-boy-scoring-free-kick-goal-6652/),
  cut into a seamless 6.6 s loop: `prototype/assets/scene2/outside/bolzplatz.mp4`; shown through the window mask by the compositor.
- Rendering: the owner's PC (`powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1`, about 1.5 h).
  Views and passes took about 20 s per image; a chosen-garment view (beauty + 8 passes) about 2.5 min.
- Prototype scene2 mode (`cfg.plateGarments`, switched on when `assets/scene2/views/passes.json` exists): garments are in
  the plate; hover/click read `ids.png`; clicking takes the garment off the rail (`rail@i`, pull move when rendered, a
  crossfade otherwise; a garment whose `rail@i` is not rendered yet is selected on the rail as it hangs). The window
  video is graded by the sky colour and fades out after dusk; it pauses while the magazine is open.
- Bed easter egg: the magazine **ANSTOSS** on the duvet (`prototype/js/azur-mag.js`, copy in `azur-config.js` → `copy.mag`).
  Hotspot from `views.json` → `bed.magazine` (projected by `job_projections`), a small glint, label "ANSTOSS lesen".
  Opens a flip book: cover (CC0 photo "Children Football", sasint), editorial with the shop's own "Über Azur" text and a
  clickable contents list, photo page, one lookbook page per jersey ("Am Ständer ansehen" walks to it, "Im Shop" opens the
  product), the drop teaser (goes to the covered garment) and a back cover. Desktop: spreads turning on the spine; phones:
  one page at a time. Header "Über uns" and `#anstoss` open it too. Founder names (Impressum, unpublished) are left out on purpose.
- Publishing: `python3 azur/tools/build_artifact.py` assembles `azur/.cache/publish/` (page + `files.json`); move frames
  are packed into strips there (an artifact version holds at most 511 files).

## Phase 2: Shopify (started 2026-10-07 evening, owner approved: "Kannst du all das in Shopify reinmachen?")

- Draft theme **"Azur Zimmer (Entwurf)"** `gid://shopify/OnlineStoreTheme/208669016403` (copy of the live theme
  "Azur Drops + Teaser" `208428204371`, which stays untouched). Preview (logged into the admin, or after the storefront
  password): https://azurclothing.com/?preview_theme_id=208669016403 · editor:
  https://admin.shopify.com/store/5vpchz-hd/themes/208669016403/editor
- In the draft: `sections/azur-room.liquid` (room = first homepage section under the overlay header, products from the
  section settings, real cart via /cart/add.js + the theme drawer, drop sign-up via the customer form, tags newsletter,
  drops), `snippets/azur-room-data.liquid`, `assets/azur-room.js|css`, fonts, `templates/index.json` (room, then the
  existing sections; the campaign hero is disabled, not deleted). Source: `azur/theme/` (see its README).
- Renders: 226 files in Content > Files, names `azr1-…` (all READY). Shopify fetched them from this public repo.
- Not testable from the cloud: the storefront is password-protected. Local stand-in: `tools/theme_harness.py`.
- Publishing the draft (making it live) is the owner's step in the admin, after the preview looks right.

## Round 3 (owner feedback 2026-10-07 evening, after the Shopify draft): plan and decisions

Owner decisions: PDP shows a real 3D jersey in the browser (rotate + zoom; light model, own tiny WebGL viewer);
night = teen only suggested (body shape under the duvet, hair on the pillow, an arm out); after add-to-cart only the
free-shipping hint (real rule: free in DE from 90 €); the new minimal header only over the room (rest of the shop keeps
the theme header). Later the owner may deliver 3D scans of the jerseys: keep the jersey source swappable.
Renders run on the owner's PC through `render_on_windows.ps1 watch` (see "Round 3: where it stands").

Scene (build_room.py, new set `scene3`):
1. jerseys = cloth-simulated shell from the shop photos over a real wooden hanger (hook out of the collar)
2. rail no longer inside the desk; pens rest on the desk; neon sign cleaner (day: glass tubes, night: glow)
3. messy teen bed; time-of-day states as patches: night (sleeping teen), morning (crumpled duvet, alarm),
   day (tidier, kid outside), evening (school bag, books on the floor)
4. masks: object mask (bed / rail / magazine) for white hover outlines; clean plates without garments (sway)
5. renders 2400 px wide (1600 copies for small screens); less quantization (neon lossless)
6. export a light jersey model per product for the PDP viewer
Web: chips Bett | Zimmer | Ständer; white outline glow + white glint dots (bed, rail, magazine); jerseys sway (shader,
ids mask over the clean plate); click on a jersey opens the PDP at once (hover info stays); PDP 3D viewer + shop link;
shipping progress after add; header over the room: no logo (logo dimmed top-left only behind overlays), bag icon
(visible when the cart has items), other links behind three glowing white dots; magazine pages as data (Shopify
section blocks); fix the room staying blurred after closing the PDP (selection blur in plate mode).

## Round 3: where it stands (2026-10-07, 23:05 UTC)

Built and pushed:
- Scene `scene3` (build_room.py + garment.py): cloth-draped jerseys on wooden hangers, rail out of the desk (x 0.76–2.76),
  neon centred over it (x 1.76), messier duvet, pens resting on the desk, states tagged `azur_state`
  (morning: pyjama + phone; evening/night: school bag, exercise books, pencil case; night: duvet over a sleeping shape,
  a socked foot, the magazine slid onto the floor; hoodie over the chair always).
- Pipeline (render_queue.py): 2400×1350 plates (rail_m 1800×2000), 384 samples, encoding with more codes in the dark
  (ENC_REF 1.5, webp q94, neon q97), masks.png/glow.png (+ _night) for hover outlines, times of day as patches
  (`passes.json` → `states[view][state] = {rects, passes, res}`, files `<view>/<state>/<pass>_<n>.webp`, rendered
  only around the changed objects + sun shadows, compared with the kept day EXRs), no posed `@i` views, no pulls.
  render_moves.py: variants day (midday) / evening (golden hour) / night (lamp off), each with its state's objects.
  export_models.py: one GLB per jersey (shell + hanger + hook, ~250–310 KB). render_preview.py: quick looks.
- PC watch mode v2: `render_on_windows.ps1 watch` runs `tools/render_step.ps1` every 2 min (re-read each round),
  reports to `azur/render_status.json`, request fields `id, set, rebuild, redo, jobs`; a newer request stops a stale
  run. Scripts started by an old copy hand over to v2 by themselves (new window, old one closes).
- Web (prototype): white outlines + dots (bed, rail, magazine), swaying jerseys (pendulums bend the plate around the
  hooks), click → product view with the 3D jersey (azur-viewer.js), shipping progress after add + "Weiter umsehen",
  header = sports bag (when the cart has items) + three glowing dots, ghost logo behind overlays, states with crossfade,
  chips Bett | Zimmer | Ständer, magazine pages as data (Shopify blocks "Heftseite"), half-size first load (`_lo`).
- Shopify section updated (not yet pushed to the draft theme): new header, menu (link list), free shipping setting,
  magazine blocks, Files prefix `azr2-`.

Running: nothing since 01:18 local (the PC went to sleep during r3-1, after all day passes and stills). Request r3-5
waits on the branch (replaces r3-4, which never started): rebuild (cleanly draped jerseys, drop bag with more room, pens
in the cup instead of floating, hoodie shaped over the chair back, masks without the footballs), preview, models, all
plates, times of day, moves. Start on the PC: `git pull origin <branch>` then
`powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1 watch`.
Artifact version 17 (2026-10-08 ~03:20 UTC): round 3 interim with the PC's r3-1 plates (old pens/hoodie, no state
patches, no moves yet), jersey models exported in the cloud (GLBs base64-wrapped as .glb.json: artifacts do not serve .glb).

Bug round (2026-10-08 morning, owner: "the Deutschland jersey is buggy, once clicked I cannot get out or look at others"):
- 3D viewer froze after the first product view (stop() left a cancelled frame id, kick() then never drew again): every
  later jersey showed the first one opened. Fixed; canvas cleared before a new model, shared downloads, resize redraw.
- Drop card (Nächster Drop) did not close with its × or Escape on the rendered rail, and it sat over the jerseys left of
  the bag. Fixed (closes with its selection; placed right of the bag); hover keeps working while it is open.
- Product view: visible × button, Escape no longer also flies back to the room, page behind does not scroll; jersey
  links (#handle, also in-page) open the product view. Regression test: 16 checks (desktop + phone) pass.
- The Deutschland jersey itself was crumpled (rail plates and 3D model): a one-cell notch under the arm in its pattern
  got pulled shut by the outline relaxation and tangled the shell. garment.py closes such notches, and since the cloth
  solver is chaotic (one cell more or less tangled Berlin instead), every drape is now checked (width, depth, length)
  and re-run with a slightly different grid/pressure until it passes (`garment.RETRIES`, settings in `garment.TUNE`).
- Rail: jerseys 0.29 m apart, the drop bag at x 2.54 and narrower (0.58 m), turned a bit more: it hid half of Türkei.
  Checked with a cloud preview (960×540, 24 samples): all five jerseys visible, Deutschland clean, all drapes pass on
  the first try in the rebuilt scene.
- Artifact version 18 = these web fixes on the interim plates; version 19 adds the re-draped jersey models (cloud export).
- `node azur/tools/test_room.cjs [publishDir] [shotDir]`: browser regression test of the built page (desktop + phone,
  product views, 3D models, drop card, links, cart, menu, chips, magazine, times of day, keyboard, no WebGL).
- 08:10 UTC check (PC still silent): the add button collapsed to a 2 px line after adding (flex column squeezing) →
  fixed (artifact v20); the header bag now follows the theme drawer's cart count (artifact v21, theme harness checked).
- 09:10 UTC check (PC still silent): keyboard use fixed (focus back to the jersey after the product view, Tab trapped in
  it, hidden cart/drop panels inert); no-WebGL and reduced-motion paths checked; test now 54 checks (artifact v22).
- 10:10 UTC check (PC still silent): the room was composited twice per frame (sway + frame loop) → once; the room and
  its window video rest behind the product view (artifact v23). Phone swipe along the rail and the drop card checked.
- 11:10 UTC check (PC still silent): depth and window maps carried Blender's dither noise and did not compress
  (5.2 MB for all views); `scene/maps.py` tidies them (0.35 MB), the pipeline renders maps without dither and tidies
  them too. Phones no longer fetch or decode the window video (no window in that view). Data before the first
  picture: desktop 2.84 -> 1.54 MB, phone 3.60 -> 1.72 MB (artifact v24).
- 12:10 UTC check (PC still silent): accessibility audit (axe-core) of room, product view and magazine: only the
  dimmed logo outside a landmark → in a nav; it was also an invisible Tab stop (now hidden while unused) and, in the
  prototype page, sat under the product view so it could not be clicked (moved to <body> by the app). 0 violations
  now (artifact v25).
- 13:10 UTC check (PC still silent): responsive sweep over six screen sizes. On 320 px phones the product view ran
  past the screen (title's longest word) and the drop card stuck out 6 px; both fixed, Regie button off the chips
  (artifact v26). Landscape phone, tablets, laptop and wide screens were already fine.
- 14:10 UTC check (PC still silent): the Shopify build in the theme harness (desktop + phone): axe clean for our
  markup (the one finding is the harness's stand-in announcement bar), theme header hidden over the room, product
  view with 3D model and shop link, logo hides again after closing. Nothing to fix.
- 15:10 UTC check (PC still silent): dry run of the whole r3-5 pipeline in the cloud at tiny size (AZUR_QUEUE_FAST:
  all four views with passes, masks, ids, window, depth, beauty and the evening/night/morning patches; the camera moves
  room-rail and room-bed in day/evening/night; all preview shots): no errors. The page tested against that output for
  the first time with real state patches and moves: patches go in and out with the clock (night masks at night), the
  moves play both ways by day and by night, no errors. The PC run should go through.
- 16:10 UTC check (PC still silent): evening flights use their own frames; the clock changing while a flight starts
  (both use the snapshot canvas) ends consistent: right state, right view, snapshot gone, no errors.

Next: when the PC is done: check previews and plates, `AZUR_SET=scene3 python3 azur/tools/build_artifact.py`, publish the
artifact (same URL), `python3 azur/tools/build_theme.py`, commit `azur/theme`, fileCreate the `azr2-` files (two
batches), themeFilesUpsert into the draft theme 208669016403, test with `tools/theme_harness.py`.

## Rough timings (this machine: 4 CPU cores, no GPU)

- Preview render 960×540: about 1.5 min (incl. cloth simulation)
- Final render 1920×1080, 256 samples: about 16 min
- Full pass set (about 20–30 renders): 6–8 hours in the background

## How to resume

```bash
pip install bpy==5.0.1 pillow scikit-image imageio-ffmpeg
python3 azur/scene/fetch_assets.py            # Poly Haven assets into azur/.cache/ph
python3 azur/scene/build_room.py -- preview azur/renders/preview.png azur/.cache/azur_room.blend
python3 azur/scene/build_room.py -- final azur/renders/still.png '' A      # 4th arg: camera preset(s), e.g. A,B,F
```

Rendering on the owner's machines (estimates from Blender Open Data medians vs. tonight's cloud timings):
- PC: Ryzen 7 5800X + Radeon RX 6750 XT 12 GB (HIP): **measured 2026-10-07: rail plate 17.9 s (cloud CPU 545 s, about 30x)**.
  Full re-render of tonight's set would take about 20-25 min there. Set up and working (owner's PowerShell, private git identity).
  `powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1 [all|moves|queue]` (needs Git for Windows
  and a current AMD driver; untested so far). Preferred: private machine, so the GitHub login works.
- MacBook Air M5 (Metal, fanless, throttles under long load): full re-render ~60-90 min. `sh azur/tools/render_on_mac.sh`.
  Its git is tied to a work account, uploads failed on 2026-10-07.
- Cloud (4 Xeon vCPU, no GPU): full re-render ~8 h.
Both scripts install everything on the first run, render with `AZUR_GPU=1`, skip finished outputs and commit/push like
the cloud queue. Never render the same job on two machines at once. A local machine rebuilds the scene itself; the cloth
(duvet, scarf) may differ very slightly from the cloud build, so re-render whole views or whole move sets there.

Local test of the prototype: `cd azur/prototype && python3 -m http.server 8765`, then `sh azur/tools/mkdev.sh` wraps index.html into `_dev.html`; run Chromium with `--no-proxy-server`.

Headless Chromium for looking at web references needs the proxy CA key:
`--ignore-certificate-errors-spki-list=$(openssl x509 -in /root/.ccr/agent-proxy-ca.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64)`
plus `proxy: { server: $HTTPS_PROXY }` and the full Chromium build at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
