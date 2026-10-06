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
| Light passes + parallax layers | Pending: render after the camera is chosen |
| Interactive prototype (Artifact) | Pending |

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

## Next

1. Owner reviews camera presets A–F and the bed-layout proposal.
2. Build the interactive prototype with the current still as a placeholder plate (camera-agnostic scene config).
3. After the camera is chosen: render the light passes (dawn, day, golden hour, blue hour/night + neon, desk lamp, ceiling, street lamp) and parallax layers for desktop and mobile cameras.

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

Headless Chromium for looking at web references needs the proxy CA key:
`--ignore-certificate-errors-spki-list=$(openssl x509 -in /root/.ccr/agent-proxy-ca.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64)`
plus `proxy: { server: $HTTPS_PROXY }` and the full Chromium build at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
