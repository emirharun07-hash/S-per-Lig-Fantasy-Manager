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

## Next

The owner's PC is rendering scene2 (chosen-garment views, then moves room→rail / room→bed and the pulls, day + night).

1. When the PC is done: pull, test the full flow (room → click → move → pull → info; magazine), tune light, then
   `build_artifact.py` and publish to the same artifact URL.
2. Seen in testing: during room → bed the flying jerseys leave the frame at the top for a few frames (correct in 3D, can look odd); option: fade a garment once its hook leaves the frame.
4. Faster renders later: the owner's Mac (M5) via `azur/tools/render_on_mac.sh`, once git there uses a private GitHub login (the work account blocked uploads).
5. Phase 2 (Shopify theme) only after explicit approval.

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
