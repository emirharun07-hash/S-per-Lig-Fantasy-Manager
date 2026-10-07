/* AZUR — product page over the room and the cart.
   The product view opens over the room right from a click on a jersey: one half the jersey (a 3D model to turn and
   zoom, the shop photo until it is loaded or without WebGL), the other half to buy. After a size goes into the bag,
   the page shows how far it is to free shipping and offers to keep looking. Prototype: a simulated cart. Shopify
   (A.config.shopify): the real cart (/cart/add.js, /cart.js) and the theme's own cart drawer; checkout is Shopify's. */
(function () {
  const A = window.AZUR = window.AZUR || {};

  class Shop {
    constructor(app) {
      this.app = app; this.live = !!A.config.shopify; this.cart = this.live ? [] : this.load();
      const c = A.config.copy;
      this.pdp = document.createElement('section');
      this.pdp.className = 'azur-pdp'; this.pdp.setAttribute('role', 'dialog'); this.pdp.setAttribute('aria-modal', 'true'); this.pdp.setAttribute('aria-labelledby', 'azur-pdp-title');
      this.pdp.innerHTML = `
        <div class="azur-pdp__stage">
          <div class="azur-pdp__light" aria-hidden="true"></div>
          <img class="azur-pdp__img" alt="">
          <canvas class="azur-pdp__canvas" tabindex="0" aria-label="3D-Ansicht des Trikots: ziehen zum Drehen, scrollen zum Zoomen, Doppelklick setzt zurück"></canvas>
          <p class="azur-pdp__hint" aria-hidden="true"></p>
        </div>
        <div class="azur-pdp__info">
          <nav class="azur-pdp__crumbs" aria-label="Pfad"><button type="button" data-act="close">${c.room}</button><span aria-hidden="true">/</span><span>Trikots</span></nav>
          <h1 class="azur-pdp__title" id="azur-pdp-title"></h1>
          <p class="azur-pdp__price"></p>
          <p class="azur-pdp__fit"></p>
          <p class="azur-pdp__desc"></p>
          <fieldset class="azur-pdp__sizes">
            <legend>${c.chooseSize}</legend>
            <div class="azur-pdp__sizerow"></div>
          </fieldset>
          <button class="azur-pdp__add" type="button" data-act="add" disabled>${c.chooseSize}</button>
          <p class="azur-pdp__error" role="alert" hidden></p>
          <div class="azur-pdp__after" role="status" hidden>
            <p class="azur-pdp__ship"></p>
            <div class="azur-pdp__bar" aria-hidden="true"><i></i></div>
            <div class="azur-pdp__acts2">
              <button type="button" data-act="more">${c.keepLooking}</button>
              <button type="button" data-act="cart">${c.toCart}</button>
            </div>
          </div>
          <ul class="azur-pdp__facts">
            <li>${A.store.shipping}</li>
            <li>${A.store.care}</li>
          </ul>
          ${this.live ? `<a class="azur-pdp__shop" target="_blank" rel="noopener">${c.openInShop || c.toProductPage || 'Im Shop öffnen'} <span aria-hidden="true">↗</span></a>`
            : `<a class="azur-pdp__shop" target="_blank" rel="noopener">${c.openInShop || 'Im Shop öffnen'} <span aria-hidden="true">↗</span></a>`}
          <button class="azur-pdp__back" type="button" data-act="close"><span aria-hidden="true">←</span> ${c.backToRoom}</button>
        </div>`;
      document.body.appendChild(this.pdp);
      this.canvas = this.pdp.querySelector('.azur-pdp__canvas');
      this.viewer = A.Viewer ? new A.Viewer(this.canvas) : null;
      this.canvas.addEventListener('azur-touched', () => this.pdp.classList.add('is-touched'));
      this.pdp.querySelector('.azur-pdp__hint').textContent = matchMedia('(pointer: coarse)').matches ? c.viewerHintTouch : c.viewerHint;
      if (this.live) { this.drawer = null; this.bind(); return; }      // the theme's cart drawer takes over

      this.drawer = document.createElement('aside');
      this.drawer.className = 'azur-cart'; this.drawer.setAttribute('aria-label', c.cart); this.drawer.setAttribute('aria-hidden', 'true');
      this.drawer.innerHTML = `
        <header class="azur-cart__head"><h2>${c.cart}</h2><button type="button" class="azur-cart__close" aria-label="Schließen">×</button></header>
        <ul class="azur-cart__list"></ul>
        <footer class="azur-cart__foot">
          <p class="azur-cart__total"><span>${c.total}</span><strong></strong></p>
          <p class="azur-cart__vat">${c.inclVat} · ${A.store.shipping}</p>
          <button type="button" class="azur-cart__checkout">${c.checkout}</button>
          <p class="azur-cart__note">${c.prototypeNote}</p>
        </footer>`;
      document.body.appendChild(this.drawer);
      this.bind(); this.renderCart();
    }

    bind() {
      this.pdp.addEventListener('click', e => {
        const t = e.target.closest('[data-act]'); if (!t) return;
        if (t.dataset.act === 'close') this.close();
        if (t.dataset.act === 'add') this.add();
        if (t.dataset.act === 'more') { this.close(); this.app.keepLooking(); }
        if (t.dataset.act === 'cart') { this.close(); this.toggleCart(true); }
      });
      this.pdp.addEventListener('change', e => {
        if (e.target.name === 'azur-size') {
          this.size = e.target.value;
          const b = this.pdp.querySelector('.azur-pdp__add');
          b.disabled = false; b.textContent = A.config.copy.addToCart; b.classList.remove('is-done');
          this.pdp.querySelector('.azur-pdp__after').hidden = true;
        }
      });
      this.pdp.addEventListener('keydown', e => { if (e.key === 'Escape') this.close(); });
      if (!this.drawer) return;
      this.drawer.querySelector('.azur-cart__close').addEventListener('click', () => this.toggleCart(false));
      this.drawer.addEventListener('click', e => {
        const r = e.target.closest('[data-remove]'); if (!r) return;
        this.cart.splice(+r.dataset.remove, 1); this.save(); this.renderCart();
      });
      this.drawer.querySelector('.azur-cart__checkout').addEventListener('click', e => {
        e.currentTarget.textContent = 'Im Prototyp ohne Kasse'; setTimeout(() => { e.target.textContent = A.config.copy.checkout; }, 1800);
      });
    }

    open(product, fromRect) {
      if (!product || product.type !== 'product') return;
      this.product = product; this.size = null;
      const q = s => this.pdp.querySelector(s);
      q('.azur-pdp__title').textContent = product.name;
      q('.azur-pdp__price').textContent = A.formatPrice(product.price) + ' · inkl. MwSt.';
      q('.azur-pdp__fit').textContent = product.fit || '';
      q('.azur-pdp__desc').textContent = product.description;
      q('.azur-pdp__shop').href = product.productUrl;      // Shopify: the real product page
      const img = q('.azur-pdp__img'); img.src = product.image; img.alt = product.name;
      q('.azur-pdp__after').hidden = true;
      // the 3D jersey (scene3 models), the photo until then
      this.pdp.classList.remove('has-model', 'is-touched');
      if (this.viewer && this.viewer.ok && A.config.scene3) {
        const url = A.url(A.config.assetBase.replace(/views\/$/, 'models/') + product.key + '.glb');
        this.viewer.show(url).then(ok => { if (ok && this.product === product && this.pdp.classList.contains('is-on')) this.pdp.classList.add('has-model'); });
      }
      q('.azur-pdp__sizerow').innerHTML = product.variants.map((v, i) => `
        <label class="azur-size"><input type="radio" name="azur-size" value="${v.id}" ${v.available ? '' : 'disabled'}><span>${v.title}</span></label>`).join('');
      q('.azur-pdp__error').hidden = true;
      const add = q('.azur-pdp__add'); add.disabled = true; add.textContent = A.config.copy.chooseSize; add.classList.remove('is-done');
      this.pdp.style.setProperty('--accent', product.accent || '#333');
      this.pdp.classList.add('is-on');
      this.app.setWorldDim(0.42, 10);
      document.documentElement.classList.add('azur-pdp-open');
      // the jersey flies from the rail into the page (FLIP)
      if (fromRect && !this.app.reduced) {
        const fly = () => {
          const to = img.getBoundingClientRect();
          if (!to.height || !fromRect.height) return;
          const dx = fromRect.left + fromRect.width / 2 - (to.left + to.width / 2);
          const dy = fromRect.top + fromRect.height / 2 - (to.top + to.height / 2);
          const s = fromRect.height / to.height;
          img.animate([{ transform: `translate(${dx}px, ${dy}px) scale(${s})`, opacity: 0.9 }, { transform: 'none', opacity: 1 }],
            { duration: 780, easing: 'cubic-bezier(.2,.8,.2,1)' });
        };
        if (img.complete && img.naturalHeight) requestAnimationFrame(fly); else img.addEventListener('load', () => requestAnimationFrame(fly), { once: true });
      }
      setTimeout(() => q('.azur-pdp__crumbs button').focus({ preventScroll: true }), 50);
      try { history.replaceState(null, '', '#' + product.handle); } catch (e) { }
    }

    close() {
      if (!this.pdp.classList.contains('is-on')) return;
      this.pdp.classList.remove('is-on', 'has-model');
      if (this.viewer) this.viewer.stop();
      document.documentElement.classList.remove('azur-pdp-open');
      this.app.setWorldDim();
      try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { }
      this.app.afterProductClose();
    }

    add() {
      if (!this.product || !this.size) return;
      const v = this.product.variants.find(x => String(x.id) === String(this.size));
      if (this.live) return this.addLive(v);
      const line = this.cart.find(l => l.variant === v.id);
      if (line) line.qty += 1; else this.cart.push({ variant: v.id, key: this.product.key, name: this.product.name, size: v.title, price: this.product.price, image: this.product.image, qty: 1 });
      this.save(); this.renderCart();
      const b = this.pdp.querySelector('.azur-pdp__add'); b.textContent = A.config.copy.added + ' ✓'; b.classList.add('is-done');
      this.app.bumpCart();
      this.showAfter(this.cart.reduce((s, l) => s + l.price * l.qty, 0));
    }

    /* After the bag: how far to free shipping (A.store.freeShippingFrom, euros), keep looking or go to the bag. */
    showAfter(total) {
      const c = A.config.copy, from = Number(A.store && A.store.freeShippingFrom) || 0, box = this.pdp.querySelector('.azur-pdp__after');
      const ship = box.querySelector('.azur-pdp__ship'), bar = box.querySelector('.azur-pdp__bar');
      if (from > 0) {
        const left = Math.max(0, from - total);
        ship.textContent = left > 0.004 ? c.shipTo.replace('{x}', A.formatPrice(left)) : c.shipFree + ' ✓';
        bar.hidden = false; bar.style.setProperty('--p', '0');
        requestAnimationFrame(() => requestAnimationFrame(() => bar.style.setProperty('--p', Math.min(1, total / from).toFixed(3))));
      } else { ship.textContent = c.added + ' ✓'; bar.hidden = true; }
      box.hidden = false;
    }

    async addLive(v) {
      const b = this.pdp.querySelector('.azur-pdp__add'), err = this.pdp.querySelector('.azur-pdp__error'), c = A.config.copy;
      const root = (window.Shopify && Shopify.routes && Shopify.routes.root) || '/';
      b.disabled = true; b.textContent = c.adding || 'Wird hinzugefügt …'; err.hidden = true;
      try {
        const res = await fetch(root + 'cart/add.js', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ items: [{ id: Number(v.id), quantity: 1 }] }) });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status >= 400) throw new Error(data.description || data.message || 'Das hat nicht geklappt.');
        b.textContent = c.added + ' ✓'; b.classList.add('is-done');
        const cart = await fetch(root + 'cart.js', { headers: { Accept: 'application/json' } }).then(r => r.json()).catch(() => null);
        if (cart) { this.app.setCartCount(cart.item_count); this.showAfter(cart.total_price / 100); }
        else this.showAfter(0);
        this.app.bumpCart();
        document.dispatchEvent(new CustomEvent('azur:cart-changed', { detail: cart }));   // themes can refresh their own count
      } catch (e) {
        err.textContent = e.message; err.hidden = false;
        b.textContent = c.addToCart;
      } finally { b.disabled = false; }
    }

    renderCart() {
      const list = this.drawer.querySelector('.azur-cart__list');
      if (!this.cart.length) list.innerHTML = `<li class="azur-cart__empty">${A.config.copy.emptyCart}</li>`;
      else list.innerHTML = this.cart.map((l, i) => `
        <li class="azur-cart__line">
          <img src="${l.image}" alt="">
          <div><p class="azur-cart__name">${l.name}</p><p class="azur-cart__meta">Größe ${l.size} · ${l.qty} ×</p></div>
          <p class="azur-cart__price">${A.formatPrice(l.price * l.qty)}</p>
          <button type="button" data-remove="${i}" aria-label="${l.name} entfernen">Entfernen</button>
        </li>`).join('');
      const total = this.cart.reduce((s, l) => s + l.price * l.qty, 0);
      this.drawer.querySelector('.azur-cart__total strong').textContent = A.formatPrice(total);
      this.app.setCartCount(this.cart.reduce((s, l) => s + l.qty, 0));
    }

    toggleCart(on) {
      if (!this.drawer) {           // Shopify: the theme's drawer (its opener, or our bag carries data-cart-open)
        const o = document.querySelector('[data-cart-open]'); const root = (window.Shopify && Shopify.routes && Shopify.routes.root) || '/';
        if (on !== false) { if (o) o.click(); else location.href = root + 'cart'; }
        return;
      }
      const open = on == null ? !this.drawer.classList.contains('is-on') : on;
      this.drawer.classList.toggle('is-on', open); this.drawer.setAttribute('aria-hidden', String(!open));
      if (open) this.drawer.querySelector('.azur-cart__close').focus({ preventScroll: true });
    }

    load() { try { return JSON.parse(localStorage.getItem('azur-cart') || '[]'); } catch (e) { return []; } }
    save() { try { localStorage.setItem('azur-cart', JSON.stringify(this.cart)); } catch (e) { } }
  }

  A.Shop = Shop;
})();
