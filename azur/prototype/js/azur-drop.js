/* AZUR — the covered "Nächster Drop" garment: e-mail sign-up and a holographic confirmation card.
   In the prototype the sign-up is simulated. In Shopify it posts the live theme's customer form
   (snippets/signup-form.liquid, tags "newsletter, drops", double opt-in handled by Shopify). */
(function () {
  const A = window.AZUR = window.AZUR || {};

  class Drop {
    constructor(root, app) {
      this.app = app;
      const c = A.config.copy;
      this.el = document.createElement('div');
      this.el.className = 'azur-drop'; this.el.setAttribute('role', 'dialog'); this.el.setAttribute('aria-label', c.dropTitle);
      this.el.innerHTML = `
        <p class="azur-drop__kicker">${c.dropTitle}</p>
        <p class="azur-drop__text">${c.dropText}</p>
        <form class="azur-drop__form" novalidate>
          <label class="azur-sr" for="azur-drop-email">E-Mail</label>
          <input id="azur-drop-email" class="azur-drop__input" type="email" name="contact[email]" autocomplete="email" inputmode="email" spellcheck="false" placeholder="${c.dropPlaceholder}" required>
          <input type="hidden" name="contact[tags]" value="newsletter, drops">
          <button class="azur-drop__btn" type="submit">${c.dropButton}</button>
          <p class="azur-drop__error" role="alert" hidden></p>
        </form>
        <p class="azur-drop__legal">${c.dropLegal}</p>
        <button class="azur-drop__close" type="button" aria-label="Schließen">×</button>`;
      root.appendChild(this.el);
      this.card = document.createElement('div');
      this.card.className = 'azur-holo'; this.card.setAttribute('role', 'status');
      this.card.innerHTML = `
        <div class="azur-holo__card">
          <div class="azur-holo__sheen" aria-hidden="true"></div>
          <img class="azur-holo__logo" src="assets/brand/azur-logo-ink.webp" alt="AZUR">
          <p class="azur-holo__title">${c.dropDone}</p>
          <p class="azur-holo__text">${c.dropDoneText}</p>
          <p class="azur-holo__meta"><span>Nächster Drop</span><span class="azur-holo__mail"></span></p>
          <span class="azur-holo__notch azur-holo__notch--l" aria-hidden="true"></span>
          <span class="azur-holo__notch azur-holo__notch--r" aria-hidden="true"></span>
        </div>
        <button class="azur-holo__close" type="button">${c.backToRoom}</button>`;
      document.body.appendChild(this.card);
      this.bind();
    }

    bind() {
      const form = this.el.querySelector('form'), err = this.el.querySelector('.azur-drop__error');
      form.addEventListener('submit', e => {
        e.preventDefault();                                 // prototype: nothing leaves the page
        const v = form.querySelector('input[type=email]').value.trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) { err.textContent = A.config.copy.dropInvalid; err.hidden = false; return; }
        err.hidden = true;
        try { localStorage.setItem('azur-drop-signup', v); } catch (x) { /* storage blocked: fine */ }
        this.confirm(v);
      });
      this.el.querySelector('.azur-drop__close').addEventListener('click', () => this.app.select(-1));
      this.card.querySelector('.azur-holo__close').addEventListener('click', () => { this.hideCard(); this.app.select(-1); });
      const card = this.card.querySelector('.azur-holo__card');
      const tilt = (x, y) => {
        const r = card.getBoundingClientRect();
        const nx = ((x - r.left) / r.width - 0.5) * 2, ny = ((y - r.top) / r.height - 0.5) * 2;
        const m = A.app && A.app.reduced ? 0 : 1;
        card.style.setProperty('--rx', (-ny * 9 * m).toFixed(2) + 'deg');
        card.style.setProperty('--ry', (nx * 12 * m).toFixed(2) + 'deg');
        card.style.setProperty('--sx', ((nx + 1) * 50).toFixed(1) + '%');
        card.style.setProperty('--sy', ((ny + 1) * 50).toFixed(1) + '%');
        card.style.setProperty('--hue', (nx * 40 + ny * 25).toFixed(1) + 'deg');
      };
      this.card.addEventListener('pointermove', e => tilt(e.clientX, e.clientY));
      this.card.addEventListener('pointerleave', () => { ['--rx', '--ry'].forEach(p => card.style.setProperty(p, '0deg')); });
      this.card.addEventListener('keydown', e => { if (e.key === 'Escape') { this.hideCard(); this.app.select(-1); } });
    }

    open() {
      let known = null; try { known = localStorage.getItem('azur-drop-signup'); } catch (x) { }
      if (known) this.el.querySelector('input[type=email]').value = known;
      this.el.classList.add('is-on');
      setTimeout(() => { if (!this.app.isMobile) this.el.querySelector('input').focus({ preventScroll: true }); }, 380);
    }
    close() { this.el.classList.remove('is-on'); }

    position(x, y, p) {
      if (!this.el.classList.contains('is-on')) return;
      const vw = this.app.stage.clientWidth;
      const w = Math.min(340, vw - 32);
      let left = x - p.w * 0.5 - w - 24;               // to the left of the bag, the rail continues on the right
      if (left < 16) left = Math.min(vw - w - 16, x + p.w * 0.5 + 24);
      if (this.app.isMobile) { this.el.style.transform = ''; return; }
      this.el.style.width = w + 'px';
      this.el.style.transform = `translate3d(${left.toFixed(1)}px, ${Math.max(84, y).toFixed(1)}px, 0)`;
    }

    confirm(mail) {
      this.close();
      this.card.querySelector('.azur-holo__mail').textContent = mail;
      this.card.classList.add('is-on');
      this.app.setWorldDim(0.45, 6);
      setTimeout(() => this.card.querySelector('.azur-holo__close').focus({ preventScroll: true }), 500);
    }
    hideCard() { this.card.classList.remove('is-on'); this.app.setWorldDim(); }
  }

  A.Drop = Drop;
})();
