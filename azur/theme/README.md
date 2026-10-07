# AZUR theme files (Phase 2)

Files for the Shopify theme **"Azur Zimmer (Entwurf)"** (`gid://shopify/OnlineStoreTheme/208669016403`, a copy of
the live theme "Azur Drops + Teaser"). Only these files are added or changed in the copy; everything else stays the
live theme's.

| File | What |
|---|---|
| `sections/azur-room.liquid` | the room as the first homepage section (markup, products from Shopify, settings) |
| `snippets/azur-room-data.liquid` | views / light passes / camera moves (generated) |
| `assets/azur-room.js`, `assets/azur-room.css` | the room (generated from `azur/prototype/js`, `azur/prototype/css`) |
| `assets/azur-martian-mono.woff2`, `assets/azur-caveat.woff2` | self-hosted fonts (SIL OFL) |
| `templates/index.json` | homepage: room, then the existing sections (the old campaign hero is disabled, not deleted) |
| `files/` + `files.json` | renders, half-size copies, jersey models (GLB) and move strips for Content > Files (`azr2-…`, round 3), fetched by Shopify from this repo |

Editable in the theme editor (section "AZUR Zimmer"): products per hook, drop text, care note, free shipping from (€),
the menu behind the three dots, and the ANSTOSS pages as blocks "Heftseite" (no blocks = the default issue).

Rebuild after changing the prototype: `python3 azur/tools/build_artifact.py` (packs the move strips, half-size copies), then
`python3 azur/tools/build_theme.py`. Test locally: `python3 azur/tools/theme_harness.py` (http://127.0.0.1:8770/).
