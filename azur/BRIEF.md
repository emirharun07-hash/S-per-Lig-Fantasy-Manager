# AZUR — immersive football bedroom (brief v2, condensed)

Owner: the AZUR store (azurclothing.com, Shopify, EUR, Germany). The full brief lives in the owner's prompt; this file keeps what a resumed session needs.

## Idea

The homepage is a real childhood football bedroom. The jerseys hanging on a clothing rail are the product catalogue; the environment is the interface. "A kid who has not made it yet, but fully believes he will." Emotional reference: Kylian Mbappé's childhood bedroom, a wall nearly covered with posters of one idol in a white kit. Never depict a real person; posters use CC0 photos or original renders.

THE ROOM IS THE MEMORY · THE POSTERS ARE THE HEROES · THE BOOTS ARE THE WORK · THE TROPHY IS THE PROOF · THE JERSEYS ARE THE DREAM · THE COVERED JERSEY IS WHAT COMES NEXT · AZUR IS THE PRESENT.

## Fixed decisions

- Accent: Azur Electric, used only as an accent (neon, focus ring, labels, hairlines). Glow #16B8FF (light only), Highlight #8DEBFF (reflections, night text), Ink #0A6A9A (accent text on light surfaces), Night #07131D (label surfaces after dark). The room keeps its own warm, natural colours.
- Photorealistic room built in 3D (Blender + Cycles). A flat CSS/SVG illustration was rejected.
- Customer-facing copy in German. Prices "64,99 €". Microcopy: "Wähle ein Trikot" / "Tippe auf ein Trikot", "Ansehen", "Trikot ansehen", "Größe wählen", "In den Warenkorb", "Zurück ins Zimmer", "Nächster Drop", "Benachrichtige mich".
- Products: the live Shopify jerseys (Berlin 030, Frankfurt 069, Brasilien, Deutschland, Türkei). The 6th hanger holds a covered "Nächster Drop" garment bag that opens the drop e-mail sign-up.
- Logo: the brush signature from the live theme (`assets/logo/azur-logo-*.webp`, from theme "Azur Drops + Teaser"), rendered as an LED neon-flex sign.
- Prototype in plain JavaScript + CSS (no React) so it carries over into a Shopify section.
- Day/night follows the visitor's local time, continuously interpolated (dawn, morning, day, golden hour, sunset, blue hour, night, deep night). Light is rendered as separate passes and mixed in the browser.
- Camera, motion and layout values live in one scene config; the owner may change camera and motion later.

## Shopify facts (for Phase 2)

- Live theme: "Azur Drops + Teaser" (custom). It already has `sections/drops.liquid` + `snippets/signup-form.liquid` (customer form, tags `newsletter, drops`, double opt-in note), a page "Drops" (handle `drops`, currently unpublished), `snippets/logo.liquid`, and self-hosted Archivo fonts. Reuse these instead of building new ones.
- Storefront is password-protected; read theme files through the Admin API.
- Work on a duplicate theme, never on the live one directly. Ask the owner where the theme code should live before Phase 2.

## Process rules from the owner

- Give a rough time estimate before each work package.
- Keep background work running; if the session is interrupted, resume unfinished work as soon as possible (see `STATUS.md`).
- Phase 2 (Shopify) only after explicit approval of the prototype.
