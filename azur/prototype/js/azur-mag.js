/* AZUR — "ANSTOSS", the football magazine left on the duvet (bed view easter egg): brand story and lookbook as a
   flip book. Desktops see two-page spreads turning on the spine, phones one page at a time. Lookbook pages lead to the
   jersey on the rail, the drop page to the covered garment. Brand copy is the shop's own "Über Azur" text. */
(function () {
  const A = window.AZUR = window.AZUR || {};
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const firstSentence = s => (String(s).match(/^[^.]+\./) || [s])[0];

  class Mag {
    constructor(app) {
      this.app = app; this.n = 0; this.isOpen = false;
      const c = A.config.copy.mag;
      this.el = document.createElement('section');
      this.el.className = 'azur-mag'; this.el.setAttribute('role', 'dialog'); this.el.setAttribute('aria-modal', 'true');
      this.el.setAttribute('aria-label', c.label); this.el.hidden = true;
      this.el.innerHTML = `
        <div class="azur-mag__scrim" data-act="close"></div>
        <div class="azur-mag__stage"><div class="azur-mag__book"></div></div>
        <div class="azur-mag__bar">
          <button class="azur-mag__arrow" type="button" data-act="prev" aria-label="${c.prev}">←</button>
          <span class="azur-mag__count" aria-live="polite"></span>
          <button class="azur-mag__arrow" type="button" data-act="next" aria-label="${c.next}">→</button>
          <button class="azur-mag__close" type="button" data-act="close">${c.close}</button>
        </div>`;
      document.body.appendChild(this.el);
      this.stage = this.el.querySelector('.azur-mag__stage');
      this.book = this.el.querySelector('.azur-mag__book');
      this.count = this.el.querySelector('.azur-mag__count');
      this.pages = this.buildPages();
      this.bind();
    }

    /* ------------------------------------------------------------ content: cover, editorial, photo, 5 jerseys, drop, back */
    buildPages() {
      const c = A.config.copy.mag, prods = A.products.filter(p => p.type === 'product');
      const foot = (n, label) => `<p class="mp__foot"><span>${label}</span><span>${n}</span></p>`;
      const pages = [];
      pages.push(`
        <div class="mp mp--cover">
          <img class="mp__photo" src="${A.url('assets/mag/cover.webp')}" alt="${c.coverAlt}" loading="lazy">
          <p class="mp__mast" aria-label="ANSTOSS">ANSTOSS</p>
          <p class="mp__issue">${c.issue}</p>
          <p class="mp__lines">${c.coverLines.map(l => `<span>${l}</span>`).join('')}</p>
          <p class="mp__sticker">${c.coverSticker}</p>
        </div>`);
      pages.push(`
        <div class="mp mp--text">
          <p class="mp__kicker">${c.editorialKicker}</p>
          <h2 class="mp__head">${c.editorialHead}</h2>
          <p class="mp__lead">${c.editorialLead}</p>
          ${c.about.map(t => `<p class="mp__body">${t}</p>`).join('')}
          <p class="mp__sign">${c.sign}<span>${c.signNote}</span></p>
          <div class="mp__toc"><p class="mp__kicker">${c.tocKicker}</p><ol>
            ${prods.map((p, k) => `<li><button type="button" data-act="goto" data-p="${3 + k}"><span>${esc(p.name)}</span><span>${4 + k}</span></button></li>`).join('')}
            <li><button type="button" data-act="goto" data-p="${3 + prods.length}"><span>${c.dropHead}</span><span>${4 + prods.length}</span></button></li>
          </ol></div>
          ${foot(2, 'ANSTOSS 01')}
        </div>`);
      pages.push(`
        <div class="mp mp--photo">
          <img class="mp__photo" src="${A.url('assets/mag/story.webp')}" alt="${c.storyAlt}" loading="lazy">
          <p class="mp__quote">${c.storyQuote}</p>
          ${foot(3, 'ANSTOSS 01')}
        </div>`);
      prods.forEach((p, k) => {
        const i = A.products.indexOf(p);
        pages.push(`
        <div class="mp mp--look" style="--acc:${p.accent || '#0A6A9A'}">
          <p class="mp__kicker">${c.lookKicker} · ${String(k + 1).padStart(2, '0')}/${String(prods.length).padStart(2, '0')}</p>
          <div class="mp__shot"><img src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy"></div>
          <h3 class="mp__name">${esc(p.name)}</h3>
          <p class="mp__desc">${esc(firstSentence(p.description))}</p>
          <p class="mp__price">${A.formatPrice ? A.formatPrice(p.price) : p.price + ' €'} <span>${esc(p.fit || '')}</span></p>
          <p class="mp__acts">
            <button type="button" data-act="rail" data-i="${i}">${c.toRail}</button>
            <a href="${esc(p.productUrl)}" target="_blank" rel="noopener">${c.toShop} <span aria-hidden="true">↗</span></a>
          </p>
          ${foot(4 + k, c.lookKicker)}
        </div>`);
      });
      const di = A.products.findIndex(p => p.type === 'drop');
      pages.push(`
        <div class="mp mp--drop">
          <p class="mp__kicker">${c.dropKicker}</p>
          <h3 class="mp__head">${c.dropHead}</h3>
          <p class="mp__body">${c.dropText}</p>
          ${di >= 0 ? `<p class="mp__acts"><button type="button" data-act="rail" data-i="${di}">${c.toDrop}</button></p>` : ''}
          ${foot(4 + prods.length, 'ANSTOSS 01')}
        </div>`);
      pages.push(`
        <div class="mp mp--back">
          <img class="mp__logo" src="${A.url('assets/brand/azur-logo-paper.webp')}" alt="AZUR" loading="lazy">
          <p class="mp__bye">${c.bye}</p>
          <p class="mp__credits">${c.credits}</p>
        </div>`);
      return pages;
    }

    /* Desktop: sheet k carries page 2k on its front and 2k+1 on its back; the cover sits alone on the right and the
       back cover alone on the left. Phones: one sheet per page, the turned sheet flies off to the left. */
    layout() {
      const W = innerWidth, H = innerHeight, single = W < 760 || W < H * 0.95;
      const barH = 64, ph0 = Math.min(H - barH - (single ? 72 : 96), 820), ratio = 0.72;
      let ph = ph0, pw = ph * ratio;
      const maxW = single ? W - 32 : W * 0.92;
      if ((single ? pw : pw * 2) > maxW) { pw = single ? maxW : maxW / 2; ph = pw / ratio; }
      this.book.style.setProperty('--pw', pw.toFixed(1) + 'px'); this.book.style.setProperty('--ph', ph.toFixed(1) + 'px');
      this.book.style.setProperty('--fs', (pw / 420).toFixed(3));
      if (single === this.single && this.sheets) return this.place(true);
      this.single = single; this.el.classList.toggle('is-single', single);
      const P = this.pages, sheets = [];
      if (single) P.forEach(p => sheets.push([p, '<div class="mp mp--blank"></div>']));
      else for (let k = 0; k < P.length; k += 2) sheets.push([P[k], P[k + 1] || '<div class="mp mp--blank"></div>']);
      this.book.innerHTML = sheets.map(([f, b], k) => `
        <div class="azur-mag__sheet" data-k="${k}">
          <div class="azur-mag__face azur-mag__face--front">${f}</div>
          <div class="azur-mag__face azur-mag__face--back">${b}</div>
        </div>`).join('');
      this.sheets = [...this.book.querySelectorAll('.azur-mag__sheet')];
      // keep the reader on the same page when the layout switches
      const page = this.page != null ? this.page : 0;
      this.n = single ? Math.min(page, P.length - 1) : Math.ceil(page / 2);
      this.place(true);
    }

    get max() { return this.single ? this.sheets.length - 1 : this.sheets.length; }

    place(instant) {
      const S = this.sheets, n = this.n, single = this.single;
      if (instant) this.book.classList.add('is-instant');
      S.forEach((s, k) => {
        const flipped = k < n;
        s.classList.toggle('is-flipped', flipped);
        s.style.zIndex = flipped ? k + 1 : S.length - k + 1;
      });
      // the closed book sits centred (cover or back cover alone), open spreads centre on the spine
      const shift = single ? 0 : n === 0 ? -0.5 : n === S.length ? 0.5 : 0;
      this.book.style.setProperty('--shift', shift);
      // only the visible pages take focus / reach screen readers
      const vis = single ? [[n, 'front']] : [[n - 1, 'back'], [n, 'front']];
      S.forEach((s, k) => s.querySelectorAll('.azur-mag__face').forEach(f => {
        const on = vis.some(([vk, side]) => vk === k && f.classList.contains('azur-mag__face--' + side));
        f.inert = !on; f.setAttribute('aria-hidden', on ? 'false' : 'true');
      }));
      this.page = single ? n : Math.max(0, n * 2 - 1);
      const total = this.pages.length, c = A.config.copy.mag;
      const label = single ? `${n + 1} / ${total}` : n === 0 ? c.coverWord : n === S.length ? c.backWord : `${n * 2}–${n * 2 + 1} / ${total}`;
      this.count.textContent = label;
      this.el.querySelector('[data-act="prev"]').disabled = n <= 0;
      this.el.querySelector('[data-act="next"]').disabled = n >= this.max;
      if (instant) { void this.book.offsetWidth; this.book.classList.remove('is-instant'); }
    }

    turn(d) {
      const n = Math.max(0, Math.min(this.max, this.n + d));
      if (n === this.n) return;
      const lo = Math.min(n, this.n), hi = Math.max(n, this.n), turning = this.sheets.slice(lo, hi);
      this.n = n; this.place(false);
      turning.forEach((s, j) => {                                 // the turning sheets stay on top while they move
        s.style.zIndex = this.sheets.length + 5 + (d > 0 ? turning.length - j : j);
        s.classList.add('is-turning'); clearTimeout(s._t); s._t = setTimeout(() => s.classList.remove('is-turning'), 900);
      });
      if (this.el.contains(document.activeElement) && document.activeElement.disabled || !this.el.contains(document.activeElement))
        this.el.querySelector(n >= this.max ? '[data-act="prev"]' : '[data-act="next"]').focus({ preventScroll: true });
      clearTimeout(this.zt); this.zt = setTimeout(() => this.place(true), this.app.reduced ? 0 : 760);
    }

    goto(page) { this.turn((this.single ? page : Math.ceil(page / 2)) - this.n); }

    /* The masthead and the jersey names fill their line exactly, whatever font the browser ends up with. */
    fit() {
      this.book.querySelectorAll('.mp__mast, .mp__head, .mp__name').forEach(el => {
        el.style.fontSize = ''; el.style.whiteSpace = el.classList.contains('mp__mast') ? '' : 'nowrap';
        const w = el.clientWidth, sw = el.scrollWidth; el.style.whiteSpace = '';
        if (sw > w && w > 0) el.style.fontSize = (parseFloat(getComputedStyle(el).fontSize) * w / sw * 0.98).toFixed(1) + 'px';
      });
    }

    /* ------------------------------------------------------------ open / close */
    open(fromRect) {
      if (this.isOpen) return;
      this.isOpen = true; this.returnFocus = document.activeElement;
      this.n = 0; this.page = 0;                                   // a magazine picked up again starts at its cover
      this.el.hidden = false; this.layout(); this.fit();
      this.app.root.classList.add('is-reading');
      requestAnimationFrame(() => this.el.classList.add('is-on'));
      if (fromRect && !this.app.reduced) {
        const b = this.stage.getBoundingClientRect();
        const dx = fromRect.left + fromRect.width / 2 - (b.left + b.width / 2), dy = fromRect.top + fromRect.height / 2 - (b.top + b.height / 2);
        const s = Math.max(0.08, fromRect.width / Math.max(1, b.width));
        this.stage.animate([{ transform: `translate(${dx}px, ${dy}px) scale(${s}) rotate(-24deg)`, opacity: 0.4 },
                            { transform: 'none', opacity: 1 }], { duration: 720, easing: 'cubic-bezier(.16,.84,.3,1)' });
      }
      setTimeout(() => this.el.querySelector('[data-act="next"]').focus({ preventScroll: true }), 60);
      this.app.setWorldDim(0.55, 4);
    }
    close(then) {
      if (!this.isOpen) return;
      this.isOpen = false; this.el.classList.remove('is-on'); this.app.root.classList.remove('is-reading');
      this.app.setWorldDim(1, 0);
      setTimeout(() => { if (!this.isOpen) this.el.hidden = true; if (then) then(); }, this.app.reduced ? 0 : 360);
      if (!then && this.returnFocus && this.returnFocus.focus) this.returnFocus.focus({ preventScroll: true });
    }

    bind() {
      this.el.addEventListener('click', e => {
        const a = e.target.closest('[data-act]');
        if (a) {
          const act = a.dataset.act;
          if (act === 'close') return this.close();
          if (act === 'prev') return this.turn(-1);
          if (act === 'next') return this.turn(1);
          if (act === 'goto') return this.goto(+a.dataset.p);
          if (act === 'rail') { const i = +a.dataset.i; return this.close(() => this.app.showOnRail(i)); }
        }
        if (e.target.closest('a, button')) return;
        const face = e.target.closest('.azur-mag__face');        // tap the right page to turn on, the left one to turn back
        if (!face || this.dragged) return;
        const r = this.book.getBoundingClientRect(), mid = r.left + r.width * (this.single ? 0.3 : 0.5);   // spine
        this.turn(e.clientX >= mid ? 1 : -1);
      });
      document.addEventListener('keydown', e => {                   // capture: the room's own Escape (back to the room) must not fire
        if (!this.isOpen) return;
        if (e.key === 'Escape') { e.stopPropagation(); this.close(); }
        else if (e.key === 'ArrowRight') { e.preventDefault(); this.turn(1); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); this.turn(-1); }
        else if (e.key === 'Tab') {                              // keep focus inside the open magazine
          const f = [...this.el.querySelectorAll('button:not([disabled]), a[href]')].filter(x => !x.closest('[inert]'));
          if (!f.length) return;
          if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
          else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
        }
      }, true);
      let x0 = null;
      this.stage.addEventListener('pointerdown', e => { x0 = e.clientX; this.dragged = false; });
      this.stage.addEventListener('pointerup', e => {
        if (x0 == null) return; const dx = e.clientX - x0; x0 = null;
        if (Math.abs(dx) > 40) { this.dragged = true; this.turn(dx < 0 ? 1 : -1); setTimeout(() => { this.dragged = false; }, 0); }
      });
      window.addEventListener('resize', () => { if (this.isOpen) { this.layout(); this.fit(); } });
    }
  }

  A.Mag = Mag;
})();
