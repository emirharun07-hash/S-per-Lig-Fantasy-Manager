"""Local stand-in for the Shopify storefront, to test the room section before it goes into the draft theme.

    python3 azur/tools/theme_harness.py [port]      -> http://127.0.0.1:8770/

Renders sections/azur-room.liquid with python-liquid (Shopify filters stubbed), wraps it in the live theme's page
structure (announcement bar, overlay header, #inhalt, cart drawer) with the live theme's CSS (fetched into
azur/.cache/theme_live/azur.css), serves the renders under /files/ with their Shopify Files names, and answers
POST /cart/add.js and POST /contact like Shopify does (enough for the room's cart and drop sign-up).
"""
import http.server, json, os, re, socketserver, sys
from liquid import Environment, DictLoader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'theme')
PROTO = os.path.join(ROOT, 'prototype')
LIVE = os.path.join(ROOT, '.cache', 'theme_live')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8770

PRODUCTS = [  # as Shopify's Liquid product objects would show them (ids and handles from the shop)
    (10885924946259, 'frankfurt-trikot-azur-collection', 'Frankfurt 069 Trikot', 6499, 'frankfurt', [55081072722259, 55081072755027, 55081072787795, 55081072820563]),
    (10886281167187, 'berlin-trikot-azur-collection', 'Berlin 030 Trikot', 6499, 'berlin', [55083930026323, 55083930059091, 55083930091859, 55083930124627]),
    (10876882387283, 'brasilien-trikot-azur-collection', 'Brasilien Trikot', 5499, 'brasilien', [1, 2, 3, 4]),
    (10876882190675, 'deutschland-trikot-azur-collection', 'Deutschland Trikot', 5499, 'deutschland', [5, 6, 7, 8]),
    (10876882026835, 'turkei-trikot-azur-collection', 'Türkei Trikot', 5499, 'tuerkei', [9, 10, 11, 12]),
]


def product(pid, handle, title, price, img, vids):
    return {'id': pid, 'handle': handle, 'title': title, 'price': price, 'url': '/products/' + handle,
            'description': f'<p>{title}. Polokragen, Azur-Signatur auf der Brust.</p>',
            'featured_image': {'url': f'/proto/assets/products/{img}.webp', 'aspect_ratio': 0.9},
            'variants': [{'id': v, 'title': s, 'available': s != 'XL'} for v, s in zip(vids, ['S', 'M', 'L', 'XL'])]}


def render_section():
    src = open(os.path.join(THEME, 'sections', 'azur-room.liquid')).read()
    schema = json.loads(re.search(r'{% schema %}(.*?){% endschema %}', src, re.S).group(1))
    src = re.sub(r'{% schema %}.*?{% endschema %}', '', src, flags=re.S)
    env = Environment(loader=DictLoader({'azur-room-data': open(os.path.join(THEME, 'snippets', 'azur-room-data.liquid')).read()}))
    env.filters['asset_url'] = lambda v: '/theme/assets/' + v
    env.filters['file_url'] = lambda v: '/files/' + v + '?v=1'
    env.filters['json'] = lambda v: json.dumps(v, ensure_ascii=False)
    env.filters['stylesheet_tag'] = lambda v: f'<link href="{v}" rel="stylesheet" type="text/css" media="all" />'
    env.filters['image_url'] = lambda v, width=None: (v or {}).get('url', '')
    settings = {s['id']: s.get('default') for s in schema['settings'] if 'id' in s}
    for i, p in enumerate(PRODUCTS, 1): settings[f'product_{i}'] = product(*p)
    ctx = {'section': {'settings': settings, 'id': 'room'}, 'shop': {'name': 'Azur'}, 'cart': {'currency': {'iso_code': 'EUR'}},
           'settings': {'shipping_cost': 'in Deutschland 1,99 €, ab 90 € kostenlos'}}
    return env.from_string(src).render(**ctx)


PAGE = """<!doctype html><html lang="de" class="js"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>Harness</title>
<link rel="stylesheet" href="/live/azur.css">
<script>window.Shopify = { routes: { root: '/' } };</script>
</head><body class="template-index">
<div class="shopify-section"><div class="announcement" style="min-height:var(--bar-h);display:grid;place-items:center;background:#121212;color:#f3f0ea;font-size:.75rem">Kostenloser Versand ab 90 €</div></div>
<div class="shopify-section section-header"><header class="header header--overlay" data-header>
  <div class="header__bar wrap" style="display:flex;justify-content:space-between;align-items:center;height:var(--header-h);padding:0 var(--gutter)">
    <nav><a href="#">Berlin 030</a> &nbsp; <a href="#">Frankfurt 069</a> &nbsp; <a href="#">Shop</a></nav>
    <a class="header__logo" href="/"><img class="logo--ink" src="/theme_live_assets/azur-logo-ink.webp" alt="AZUR" style="height:28px;width:auto"><img class="logo--paper" src="/theme_live_assets/azur-logo-paper.webp" alt="" style="height:28px;width:auto;display:none"></a>
    <a class="header__cart" href="/cart" data-cart-open>Warenkorb <span data-cart-count>0</span></a>
  </div></header></div>
<main id="inhalt" tabindex="-1">
  <div class="shopify-section section-azur-room">__SECTION__</div>
  <div class="shopify-section"><section style="padding:4rem 2rem;min-height:70vh"><h2>Trikots</h2><p>Die bisherigen Startseiten-Bereiche folgen hier.</p></section></div>
</main>
<div class="drawer" id="cart" data-drawer hidden><div class="drawer__scrim" data-cart-close></div>
  <div class="drawer__panel" style="background:#f3f0ea;padding:2rem;width:min(26rem,100vw);margin-left:auto;height:100%"><h2>Warenkorb</h2><p data-cart-lines></p><button data-cart-close>Schließen</button></div></div>
<script>
  // stand-in for the theme's azur.js: the header cart link opens the drawer and shows what /cart/add.js received
  document.addEventListener('click', e => {
    const o = e.target.closest('[data-cart-open]'), c = e.target.closest('[data-cart-close]'), d = document.querySelector('[data-drawer]');
    if (o) { e.preventDefault(); d.hidden = false; d.classList.add('is-open'); document.querySelector('[data-cart-lines]').textContent = JSON.stringify(window.__cart || []); }
    if (c) { d.hidden = true; d.classList.remove('is-open'); }
  });
</script>
</body></html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    cart = []

    def translate_path(self, path):
        path = path.split('?')[0]
        if path.startswith('/theme/assets/azur-logo'): return os.path.join(PROTO, 'assets', 'brand', path[14:])
        if path.startswith('/theme/'): return os.path.join(THEME, path[7:])
        if path.startswith('/proto/'): return os.path.join(PROTO, path[7:])
        if path.startswith('/live/'): return os.path.join(LIVE, path[6:])
        if path.startswith('/theme_live_assets/'): return os.path.join(PROTO, 'assets', 'brand', path[19:])
        if path.startswith('/files/'): return FILES.get(path[7:], '/nonexistent')
        return super().translate_path(path)

    def do_GET(self):
        if self.path.split('?')[0] in ('/', '/index.html'):
            body = PAGE.replace('__SECTION__', render_section()).encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers()
            self.wfile.write(body); return
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); raw = self.rfile.read(n)
        if self.path.startswith('/cart/add.js'):
            items = json.loads(raw or b'{}').get('items', [])
            Handler.cart += items
            body = json.dumps({'items': items}).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json')
        elif self.path.startswith('/contact'):
            open(os.path.join(LIVE, 'last_contact_post.txt'), 'wb').write(raw)
            body = b'<html>ok</html>'; self.send_response(200); self.send_header('Content-Type', 'text/html')
        else:
            body = b'{}'; self.send_response(404)
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a): pass


def files_map():
    out = {}
    for e in json.load(open(os.path.join(THEME, 'files.json'))):
        u = e['url'].split('/azur/', 1)[1]
        from urllib.parse import unquote
        out[e['filename']] = os.path.join(ROOT, unquote(u))
    return out


FILES = files_map()
if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', PORT), Handler) as s:
        print(f'harness on http://127.0.0.1:{PORT}/', flush=True); s.serve_forever()
