/* AZUR — product data.
   Same shape the Shopify section will print from Liquid (see BRIEF.md, Phase 2):
   id, type, handle, name, price, currency, image, productUrl, variants[], description, accent.
   Order = order on the rail, left to right. The last entry is the covered "Nächster Drop" garment. */
window.AZUR = window.AZUR || {};

AZUR.products = [
  {
    id: 'gid://shopify/Product/10885924946259', type: 'product', key: 'frankfurt',
    handle: 'frankfurt-trikot-azur-collection', name: 'Frankfurt 069 Trikot', price: 64.99, currency: 'EUR',
    image: 'assets/products/frankfurt.webp', imageAspect: 686 / 716,
    productUrl: 'https://azurclothing.com/products/frankfurt-trikot-azur-collection',
    description: 'Creme, dunkelgrün abgesetzt, goldene Paspeln. Polokragen mit Streifen, Adler-Emblem auf der Brust, Azur-Signatur. FRANKFURT-Band vorn, 069 auf dem Rücken. Seitenteile in Mesh.',
    fit: 'Retro-Schnitt', accent: '#1f4d36',
    variants: [
      { id: 'gid://shopify/ProductVariant/55081072722259', title: 'S', available: true },
      { id: 'gid://shopify/ProductVariant/55081072755027', title: 'M', available: true },
      { id: 'gid://shopify/ProductVariant/55081072787795', title: 'L', available: true },
      { id: 'gid://shopify/ProductVariant/55081072820563', title: 'XL', available: true }
    ]
  },
  {
    id: 'gid://shopify/Product/10886281167187', type: 'product', key: 'berlin',
    handle: 'berlin-trikot-azur-collection', name: 'Berlin 030 Trikot', price: 64.99, currency: 'EUR',
    image: 'assets/products/berlin.webp', imageAspect: 680 / 716,
    productUrl: 'https://azurclothing.com/products/berlin-trikot-azur-collection',
    description: 'Schwarz mit feinen Nadelstreifen, cremefarbene Einsätze an Schultern und Seiten, Paspeln in Bordeaux. Polokragen mit Streifen, Berliner Bär auf der Brust, Azur-Signatur. BERLIN vorn, 030 auf dem Rücken.',
    fit: 'Lockerer Retro-Schnitt', accent: '#5a1622',
    variants: [
      { id: 'gid://shopify/ProductVariant/55083930026323', title: 'S', available: true },
      { id: 'gid://shopify/ProductVariant/55083930059091', title: 'M', available: true },
      { id: 'gid://shopify/ProductVariant/55083930091859', title: 'L', available: true },
      { id: 'gid://shopify/ProductVariant/55083930124627', title: 'XL', available: true }
    ]
  },
  {
    id: 'gid://shopify/Product/10876882387283', type: 'product', key: 'brasilien',
    handle: 'brasilien-trikot-azur-collection', name: 'Brasilien Trikot', price: 54.99, currency: 'EUR',
    image: 'assets/products/brasilien.webp', imageAspect: 826 / 960,
    productUrl: 'https://azurclothing.com/products/brasilien-trikot-azur-collection',
    description: 'Gelb, grün abgesetzt. Gesticktes Wappen auf der Brust, Azur-Signatur, Streifenbesatz an den Schultern, Kontrastkragen und -bündchen in Grün.',
    fit: 'Regular Fit', accent: '#1d6b3a',
    variants: [
      { id: 'gid://shopify/ProductVariant/55050824319315', title: 'S', available: true },
      { id: 'gid://shopify/ProductVariant/55050824352083', title: 'M', available: true },
      { id: 'gid://shopify/ProductVariant/55050824384851', title: 'L', available: true },
      { id: 'gid://shopify/ProductVariant/55050824417619', title: 'XL', available: true }
    ]
  },
  {
    id: 'gid://shopify/Product/10876882190675', type: 'product', key: 'deutschland',
    handle: 'deutschland-trikot-azur-collection', name: 'Deutschland Trikot', price: 54.99, currency: 'EUR',
    image: 'assets/products/deutschland.webp', imageAspect: 868 / 960,
    productUrl: 'https://azurclothing.com/products/deutschland-trikot-azur-collection',
    description: 'Weiß, schwarz abgesetzt. Adler-Emblem mit vier Sternen auf der Brust, Azur-Signatur, Streifenbesatz an den Schultern.',
    fit: 'Regular Fit', accent: '#1b1b1b',
    variants: [
      { id: 'gid://shopify/ProductVariant/55050823958867', title: 'S', available: true },
      { id: 'gid://shopify/ProductVariant/55050823991635', title: 'M', available: true },
      { id: 'gid://shopify/ProductVariant/55050824024403', title: 'L', available: true },
      { id: 'gid://shopify/ProductVariant/55050824057171', title: 'XL', available: true }
    ]
  },
  {
    id: 'gid://shopify/Product/10876882026835', type: 'product', key: 'tuerkei',
    handle: 'turkei-trikot-azur-collection', name: 'Türkei Trikot', price: 54.99, currency: 'EUR',
    image: 'assets/products/tuerkei.webp', imageAspect: 886 / 960,
    productUrl: 'https://azurclothing.com/products/turkei-trikot-azur-collection',
    description: 'Kräftiges Rot. Gesticktes Halbmond-und-Stern-Emblem auf der Brust. Azur-Signatur, Streifenbesatz an den Schultern, Kontrastkragen in Weiß.',
    fit: 'Regular Fit', accent: '#a5141c',
    variants: [
      { id: 'gid://shopify/ProductVariant/55050823663955', title: 'S', available: true },
      { id: 'gid://shopify/ProductVariant/55050823696723', title: 'M', available: true },
      { id: 'gid://shopify/ProductVariant/55050823729491', title: 'L', available: true },
      { id: 'gid://shopify/ProductVariant/55050823762259', title: 'XL', available: true }
    ]
  },
  {
    id: 'drop-next', type: 'drop', key: 'drop', name: 'Nächster Drop', price: null, currency: 'EUR',
    image: null, imageAspect: 0.66,
    description: 'Noch unter Verschluss.',
    signupTags: 'newsletter, drops'      // same tags as the live theme's snippets/signup-form.liquid
  }
];

/* Store facts used on the product page (from the live theme settings). */
AZUR.store = {
  name: 'Azur',
  shipping: 'Versand in Deutschland 1,99 €, ab 90 € kostenlos',
  freeShippingFrom: 90,                 // euros; the product view counts down to it after something goes into the bag
  supportEmail: 'kontakt@azurclothing.com',
  care: 'Material- und Pflegehinweise werden ergänzt.'
};

AZUR.formatPrice = function (value) {
  return value == null ? '' : value.toFixed(2).replace('.', ',') + ' €';
};
