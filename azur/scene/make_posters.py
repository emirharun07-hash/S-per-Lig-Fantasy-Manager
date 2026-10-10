"""Round 6: the three wall posters (they replace the photo collage). Writes azur/assets/posters_r6/*.jpg.

  stadium.jpg  2:1 panorama, framed print   (CC0 photo assets/posters/p157.jpg)
  moment.jpg   square, taped                (CC0 photo assets/posters/p133.jpg: the keeper behind the net)
  trikot.jpg   5:7 graphic poster           (the AZUR Brasilien jersey on azure, a big 10)
  magazin.jpg  the ANSTOSS cover for the magazine on the bed, as the browser shows it (prototype/assets/mag/cover.webp
               with masthead, issue line, cover lines and sticker from azur-config.js copy.mag)

Type: Archivo / Archivo Narrow (SIL OFL), fetched from Google Fonts into .cache/fonts the first time. Run with
python3 azur/scene/make_posters.py; the JPGs are committed, so the scene build does not need the fonts."""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
A = os.path.join(ROOT, 'assets')
OUT = os.path.join(A, 'posters_r6')
FONTS = os.path.join(ROOT, '.cache', 'fonts')
FONT_URLS = {   # Google Fonts (css2 API), SIL Open Font License
    'Archivo-ExtraBold.ttf': 'https://fonts.gstatic.com/s/archivo/v25/k3k6o8UDI-1M0wlSV9XAw6lQkqWY8Q82sJaRE-NWIDdgffTTtDRp8A.ttf',
    'ArchivoNarrow-Bold.ttf': 'https://fonts.gstatic.com/s/archivonarrow/v35/tss5ApVBdCYD5Q7hcxTE1ArZ0Zz8oY2KRmwvKhhvy1aKpA.ttf',
}


def font(name, size):
    p = os.path.join(FONTS, name)
    if not os.path.exists(p):
        os.makedirs(FONTS, exist_ok=True)
        urllib.request.urlretrieve(FONT_URLS[name], p)
    return ImageFont.truetype(p, size)


def crop_to(im, aspect, cx=0.5, cy=0.5):
    """Largest crop of the given aspect (w/h) around (cx, cy) in image fractions."""
    w, h = im.size
    if w / h > aspect: cw, ch = round(h * aspect), h
    else: cw, ch = w, round(w / aspect)
    x0 = min(max(0, round(cx * w - cw / 2)), w - cw); y0 = min(max(0, round(cy * h - ch / 2)), h - ch)
    return im.crop((x0, y0, x0 + cw, y0 + ch))


def fit_text(draw, text, fnt_name, max_w, max_size, tracking=0.0):
    size = max_size
    while size > 8:
        f = font(fnt_name, size)
        w = sum(draw.textlength(ch, font=f) for ch in text) + tracking * size * (len(text) - 1)
        if w <= max_w: return f, w
        size -= 2
    return font(fnt_name, size), max_w


def draw_tracked(draw, xy, text, f, fill, tracking=0.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking * f.size


def stadium():
    im = Image.open(os.path.join(A, 'posters', 'p157.jpg')).convert('RGB')
    im = crop_to(im, 2.0, cy=0.56).resize((2400, 1200), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.06).filter(ImageFilter.UnsharpMask(2, 60, 2))
    d = ImageDraw.Draw(im)
    f = font('ArchivoNarrow-Bold.ttf', 70)
    draw_tracked(d, (70, 1200 - 70 - 70), 'HEIMSPIEL', f, (255, 255, 255), tracking=0.18)
    d.rectangle((70, 1200 - 160, 70 + 120, 1200 - 152), fill=(255, 255, 255))
    return im


def moment():
    im = Image.open(os.path.join(A, 'posters', 'p133.jpg')).convert('RGB')
    im = crop_to(im, 1.0, cx=0.45).resize((1800, 1800), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.1)
    # the lower third darkens a little so the words read
    sh = Image.linear_gradient('L').resize((1800, 1800)).point(lambda v: min(140, max(0, v - 150) * 1.9))
    im = Image.composite(Image.new('RGB', im.size, (8, 16, 18)), im, sh)
    d = ImageDraw.Draw(im)
    word = 'ZU NULL.'
    f, w = fit_text(d, word, 'Archivo-ExtraBold.ttf', 1800 - 2 * 120, 330, tracking=0.02)
    draw_tracked(d, (120, 1800 - 110 - f.size * 1.05), word, f, (250, 244, 232), tracking=0.02)
    fs = font('ArchivoNarrow-Bold.ttf', 54)
    draw_tracked(d, (126, 1800 - 110 - f.size * 1.05 - 80), 'DIE NUMMER 1 HÄLT DICHT', fs, (255, 214, 92), tracking=0.16)
    return im


def trikot():
    W, H = 1715, 2400
    top, bot = (14, 125, 181), (7, 19, 29)          # Azur Ink toward Night
    g = Image.linear_gradient('L').resize((W, H))
    im = Image.composite(Image.new('RGB', (W, H), bot), Image.new('RGB', (W, H), top), g)
    d = ImageDraw.Draw(im, 'RGBA')
    for x in range(-H, W, 46):                       # fine diagonal pinstripes
        d.line((x, H, x + H, 0), fill=(255, 255, 255, 10), width=3)
    # the big 10 behind the jersey, outlined
    f10 = font('Archivo-ExtraBold.ttf', 1500)
    bb = d.textbbox((0, 0), '10', font=f10)
    tx, ty = (W - (bb[2] - bb[0])) / 2 - bb[0], H * 0.47 - (bb[3] - bb[1]) / 2 - bb[1]
    inner = Image.new('L', (W, H), 0); ImageDraw.Draw(inner).text((tx, ty), '10', font=f10, fill=255)
    outer = Image.new('L', (W, H), 0); ImageDraw.Draw(outer).text((tx, ty), '10', font=f10, fill=255, stroke_width=8, stroke_fill=255)
    ring = Image.composite(Image.new('L', (W, H), 0), outer, inner)      # the stroke only (PIL fills a stroke solid)
    im.paste((22, 184, 255), (0, 0), inner.point(lambda v: v * 30 // 255))
    im.paste((141, 235, 255), (0, 0), ring.point(lambda v: v * 150 // 255))
    d = ImageDraw.Draw(im, 'RGBA')
    # the jersey with a soft shadow
    j = Image.open(os.path.join(A, 'jerseys', 'brasilien.png')).convert('RGBA')
    jw = int(W * 0.66); j = j.resize((jw, int(j.height * jw / j.width)), Image.LANCZOS).rotate(-4, Image.BICUBIC, expand=True)
    jx, jy = (W - j.width) // 2, int(H * 0.50 - j.height / 2)
    shadow = Image.new('RGBA', j.size, (0, 0, 0, 0)); shadow.putalpha(j.getchannel('A').point(lambda a: a * 0.55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    im.paste((0, 0, 0), (jx + 30, jy + 42), shadow); im.paste(j, (jx, jy), j)
    # AZUR at the top, NR. 10 at the foot
    logo = Image.open(os.path.join(A, 'logo', 'azur-logo-paper.webp')).convert('RGBA')
    lw = int(W * 0.34); logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im.paste(logo, ((W - lw) // 2, 120), logo)
    d = ImageDraw.Draw(im)
    fn = font('Archivo-ExtraBold.ttf', 210)
    draw_tracked(d, (110, H - 110 - 210 * 1.02), 'NR. 10', fn, (245, 209, 48), tracking=0.01)
    fs = font('ArchivoNarrow-Bold.ttf', 58)
    t = 'TRIKOT-EDITION'
    tw = sum(d.textlength(ch, font=fs) for ch in t) + 0.2 * 58 * (len(t) - 1)
    draw_tracked(d, (W - 110 - tw, H - 110 - 58 * 1.25), t, fs, (235, 245, 250), tracking=0.2)
    return im


def magazin():
    PROTO = os.path.join(ROOT, 'prototype', 'assets', 'mag', 'cover.webp')
    im = Image.open(PROTO).convert('RGB')
    W, H = im.width * 2, im.height * 2
    im = im.resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 50, 2))
    d = ImageDraw.Draw(im)
    f, w = fit_text(d, 'ANSTOSS', 'ArchivoNarrow-Bold.ttf', W - 2 * 70, 300, tracking=0.0)
    d.text(((W - w) / 2, 40), 'ANSTOSS', font=f, fill=(255, 255, 255))
    fi = font('ArchivoNarrow-Bold.ttf', 30)
    t = 'AUSGABE 01 · DAS HEFT VON AZUR'
    tw = sum(d.textlength(ch, font=fi) for ch in t) + 0.24 * 30 * (len(t) - 1)
    draw_tracked(d, ((W - tw) / 2, 40 + f.size * 1.08), t, fi, (255, 255, 255), tracking=0.24)
    fl = font('Archivo-ExtraBold.ttf', 88)
    lines = ['ZWEI STÄDTE.', 'DREI LÄNDER.', 'EIN ZIMMER.']
    y = H - 70 - len(lines) * 88 * 1.0
    for ln in lines:
        d.text((60 + 3, y + 4), ln, font=fl, fill=(0, 0, 0))     # a soft drop shadow, as on the page
        d.text((60, y), ln, font=fl, fill=(255, 255, 255)); y += 88
    fsk = font('ArchivoNarrow-Bold.ttf', 34)
    st = 'MIT LOOKBOOK: ALLE TRIKOTS'
    sw = d.textlength(st, font=fsk)
    x0, y0 = W - 60 - sw - 36, int(H * 0.47)
    d.rectangle((x0, y0, x0 + sw + 36, y0 + 64), fill=(22, 184, 255))
    d.text((x0 + 18, y0 + 12), st, font=fsk, fill=(4, 18, 27))
    return im


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (('stadium', stadium), ('moment', moment), ('trikot', trikot), ('magazin', magazin)):
        fn().save(os.path.join(OUT, name + '.jpg'), quality=92)
        print('poster', name)
