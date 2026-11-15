import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyGalleryAccess,
  managedMediaPath,
  mediaSignature,
  protectedGalleryMediaPaths,
  pythonQuote,
  rewriteDocumentMediaUrls,
  signedMediaUrl,
} from '../lib/media.mjs';
import { applyGuestBindings, mergeFields } from '../lib/public-document.mjs';

const SECRET = 'test-secret';
const ID = 'inv-1';

test('quote matches Python quote(value, safe="") for the awkward characters', () => {
  assert.equal(pythonQuote('a b'), 'a%20b');
  assert.equal(pythonQuote("!*'()"), '%21%2A%27%28%29');
  assert.equal(pythonQuote('héro.png'), 'h%C3%A9ro.png');
});

test('managed paths reduce to their stored filename', () => {
  assert.equal(managedMediaPath('/uploads/hero.png'), 'hero.png');
  assert.equal(managedMediaPath('/api/image/a%20b.png?w=320'), 'a b.png');
  assert.equal(managedMediaPath('/api/media/c.png?i=x&exp=1&sig=2'), 'c.png');
  assert.equal(managedMediaPath('https://cdn.test/uploads/d.png'), 'd.png');
  assert.equal(managedMediaPath('/other/e.png'), '');
  assert.equal(managedMediaPath(''), '');
});

test('signed URL carries Python\'s exact payload and shape', () => {
  const url = signedMediaUrl('/uploads/hero.png', ID, 1_800_000_000, SECRET);
  assert.equal(
    url,
    `/api/media/hero.png?i=inv-1&exp=1800000000&sig=${mediaSignature('hero.png', ID, 1_800_000_000, SECRET)}`,
  );
  // The signature is over "<file>|<invitation>|<exp>" with the shared secret.
  assert.match(url, /^\/api\/media\/hero\.png\?i=inv-1&exp=1800000000&sig=[0-9a-f]{64}$/);
});

test('gallery-only media is locked without a token and signed with one', () => {
  const document = {
    galleryProtection: { enabled: true },
    objects: {
      hero: { type: 'image', src: '/uploads/hero.png', showInGallery: true, showInHero: true },
      gallery: { type: 'image', src: '/uploads/only.png', showInGallery: true, showInHero: false },
      text: { type: 'text', html: 'hi' },
    },
  };
  assert.deepEqual([...protectedGalleryMediaPaths(document)], ['only.png']);

  const locked = applyGalleryAccess(document, ID, false, { secret: SECRET });
  assert.equal(locked.galleryProtection.locked, true);
  assert.equal(locked.objects.gallery.src, '');
  assert.equal(locked.objects.gallery.showInGallery, false);
  assert.equal(locked.objects.hero.src, '/uploads/hero.png');

  const unlocked = applyGalleryAccess(document, ID, true, { secret: SECRET });
  assert.equal(unlocked.galleryProtection.locked, false);
  assert.match(unlocked.objects.gallery.src, /^\/api\/media\/only\.png\?i=inv-1&exp=\d+&sig=[0-9a-f]{64}$/);
  assert.equal(document.objects.gallery.src, '/uploads/only.png', 'input is not mutated');
});

test('a document with no gallery-only media is returned untouched', () => {
  const document = { galleryProtection: { enabled: true }, objects: { hero: { type: 'image', src: '/uploads/hero.png' } } };
  assert.equal(applyGalleryAccess(document, ID, false, { secret: SECRET }), document);
});

test('password documents rewrite plain and embedded media URLs', () => {
  const document = {
    objects: {
      image: { src: '/uploads/hero.png?w=640&format=webp' },
      rich: { html: '<p><img src="/uploads/inline.png?w=320"></p>' },
    },
  };
  const rewritten = rewriteDocumentMediaUrls(document, ID, { secret: SECRET, nowSeconds: 1_000 });
  assert.match(
    rewritten.objects.image.src,
    /^\/api\/media\/hero\.png\?i=inv-1&exp=1900&sig=[0-9a-f]{64}&w=640&format=webp$/,
  );
  assert.match(rewritten.objects.rich.html, /\/api\/media\/inline\.png\?i=inv-1&exp=1900&sig=[0-9a-f]{64}&w=320/);
});

test('merge fields matches Python for missing, null and dotted keys', () => {
  assert.equal(mergeFields('Hi {{ name }}!', { name: 'Ada' }), 'Hi Ada!');
  assert.equal(mergeFields('Hi {{ name }}!', {}), 'Hi !');
  assert.equal(mergeFields('Hi {{ name }}!', { name: null }), 'Hi !');
  assert.equal(mergeFields('{{ a.b }}', { 'a.b': 'x' }), 'x');
  assert.equal(mergeFields('{{unspaced}}', { unspaced: 3 }), '3');
});

test('guest bindings resolve in both canvas groups and leave others alone', () => {
  const document = {
    objects: {
      bound: { contentBinding: 'guest.name', html: 'Hello {{ name }}' },
      boundText: { contentBinding: 'guest.name', html: 'x', text: 'Hi {{ name }}' },
      plain: { html: 'no binding' },
    },
    designPages: [{ objects: { page: { contentBinding: 'guest.table_name', text: 'Table {{ table_name }}' } } }],
  };
  applyGuestBindings(document, { name: 'Ada', table_name: 'Table 1' });
  assert.equal(document.objects.bound.html, 'Hello Ada');
  // Python takes `html` when it exists and writes the merged value into text too,
  // so an object carrying both fields has its text replaced by the html value.
  assert.equal(document.objects.boundText.text, 'x');
  assert.equal(document.objects.plain.html, 'no binding');
  assert.equal(document.designPages[0].objects.page.text, 'Table Table 1');
});
