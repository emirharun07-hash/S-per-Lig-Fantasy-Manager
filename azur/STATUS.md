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
| Views + light passes | **Rendering** via `scene/render_queue.py` (detached, resumable, commits every output): beauty plates, depth maps, hanger + drop sprites, 7 light passes for views room / rail / rail_m / bed |
| Interactive prototype | **Published**: https://claude.ai/artifact/B4j6WH1yNHNeEG6rJLJ2Sy (code in `prototype/`, config in `prototype/js/azur-config.js`) |
| Real camera moves | **Later (owner reminder)**: replace the fake pans (room → rail, room → bed) with pre-rendered flights |

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
- Bed: easter egg comes later; remind the owner of the ideas (magazine "ANSTOSS" opens the brand story / lookbook; or the drop sign-up; or atmosphere only).
- Overlapping jerseys are fine; details only on click.

## Next

1. Let the render queue finish (`tail azur/.cache/queue.log`). If it stopped: `sh azur/tools/start_queue.sh` or `setsid nohup python3 azur/scene/render_queue.py > azur/.cache/queue_run.txt 2>&1 &`. Finished outputs are skipped.
2. After new renders land: test in the headless browser (`azur/tools/prototype_shots.cjs`), tune `daylight` keys and garment grading, republish the artifact (same file path / URL above) with the new files under `assets/views/`.
3. Polish: drop sprite + hanger sprite alignment, window kid, mobile swipe feel, reduced motion. Scene: the duvet looks lumpy from the room camera (more smoothing / fewer self-collision artefacts), boots are placeholders.
4. Later: real camera flights, bed easter egg, Phase 2 (Shopify) only after explicit approval.

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

Local test of the prototype: `cd azur/prototype && python3 -m http.server 8765`, then `sh azur/tools/mkdev.sh` wraps index.html into `_dev.html`; run Chromium with `--no-proxy-server`.

Headless Chromium for looking at web references needs the proxy CA key:
`--ignore-certificate-errors-spki-list=$(openssl x509 -in /root/.ccr/agent-proxy-ca.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64)`
plus `proxy: { server: $HTTPS_PROXY }` and the full Chromium build at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
