// localStorage persistence for designs, uploads and the brand kit.

import { seedDesigns, createDesign, SWATCHES } from './model.js';
import { deepClone, uid } from './util.js';

const DESIGNS_KEY = 'rea.canva.designs.v1';
const UPLOADS_KEY = 'rea.canva.uploads.v1';
const BRAND_KEY = 'rea.canva.brand.v1';

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function listDesigns() {
  let designs = read(DESIGNS_KEY, null);
  if (!Array.isArray(designs) || designs.length === 0) {
    designs = seedDesigns();
    write(DESIGNS_KEY, designs);
  }
  return designs.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

export function getDesign(id) {
  return listDesigns().find((design) => design.id === id) || null;
}

export function saveDesign(design) {
  const designs = read(DESIGNS_KEY, null) || seedDesigns();
  const next = designs.filter((item) => item.id !== design.id);
  next.unshift(design);
  return write(DESIGNS_KEY, next.slice(0, 60));
}

export function deleteDesign(id) {
  const designs = listDesigns().filter((design) => design.id !== id);
  write(DESIGNS_KEY, designs);
}

export function duplicateDesign(id) {
  const source = getDesign(id);
  if (!source) return null;
  const copy = deepClone(source);
  copy.id = uid('design');
  copy.title = `${source.title} (copy)`;
  copy.createdAt = Date.now();
  copy.updatedAt = Date.now();
  copy.pages = copy.pages.map((page) => ({ ...page, id: uid('page') }));
  saveDesign(copy);
  return copy;
}

export function createNewDesign(presetId, title) {
  const design = createDesign({ title, preset: presetId });
  saveDesign(design);
  return design;
}

export function listUploads() {
  const uploads = read(UPLOADS_KEY, []);
  return Array.isArray(uploads) ? uploads : [];
}

export function addUpload(name, src) {
  const uploads = listUploads();
  const record = { id: uid('upload'), name, src, at: Date.now() };
  const next = [record, ...uploads.filter((item) => item.src !== src)].slice(0, 12);
  if (!write(UPLOADS_KEY, next)) return null;
  return record;
}

export const DEFAULT_BRAND = {
  colors: ['#7d2ae8', '#00c4cc', '#ffd166', '#ef476f', '#0e1318', ...SWATCHES.slice(0, 3)],
  heading: 'serif',
  body: 'sans',
};

export function getBrand() {
  const brand = read(BRAND_KEY, null);
  if (!brand || !Array.isArray(brand.colors)) return deepClone(DEFAULT_BRAND);
  return { ...deepClone(DEFAULT_BRAND), ...brand };
}

export function saveBrand(brand) {
  write(BRAND_KEY, brand);
}

export function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
