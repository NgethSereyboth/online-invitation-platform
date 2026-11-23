// Design document model: everything the board edits is plain JSON that can be
// saved to localStorage, rendered to a canvas and cloned for undo.

import { uid } from './util.js';

export const CANVAS_LIMITS = { min: 200, max: 5000 };

export const PAGE_PRESETS = [
  { id: 'presentation', label: 'Presentation', hint: '16:9', w: 1920, h: 1080 },
  { id: 'social', label: 'Instagram Post', hint: '1:1', w: 1080, h: 1080 },
  { id: 'story', label: 'Story', hint: '9:16', w: 1080, h: 1920 },
  { id: 'poster', label: 'Poster', hint: 'A2-ish', w: 1587, h: 2245 },
  { id: 'document', label: 'A4 Document', hint: 'Portrait', w: 1240, h: 1754 },
  { id: 'card', label: 'Business Card', hint: 'Landscape', w: 1050, h: 600 },
  { id: 'wide', label: 'Desktop Banner', hint: '2:1', w: 2000, h: 1000 },
  { id: 'square-small', label: 'Logo', hint: '500 x 500', w: 500, h: 500 },
];

export const FONTS = [
  { id: 'sans', name: 'Rea Sans', stack: '"Rea Sans", Inter, system-ui, sans-serif', kind: 'Sans' },
  { id: 'serif', name: 'Rea Serif', stack: '"Rea Serif", "Noto Serif", Georgia, serif', kind: 'Serif' },
  { id: 'georgia', name: 'Georgia', stack: 'Georgia, "Times New Roman", serif', kind: 'Serif' },
  { id: 'times', name: 'Times New Roman', stack: '"Times New Roman", Times, serif', kind: 'Serif' },
  { id: 'mono', name: 'Courier', stack: '"Courier New", ui-monospace, monospace', kind: 'Mono' },
  { id: 'impact', name: 'Impact', stack: 'Impact, "Arial Black", sans-serif', kind: 'Display' },
];

export const FONT_WEIGHTS = [
  { value: 300, label: 'Light' },
  { value: 400, label: 'Regular' },
  { value: 500, label: 'Medium' },
  { value: 600, label: 'Semibold' },
  { value: 700, label: 'Bold' },
  { value: 800, label: 'Extrabold' },
];

export const SWATCHES = [
  '#ffffff', '#f6f3ee', '#fef3e2', '#ffe8d6', '#ffd166', '#ff8a5b',
  '#ef476f', '#c9184a', '#8b3dff', '#5e5cff', '#00c4cc', '#2ec4b6',
  '#06d6a0', '#118ab2', '#0e1318', '#3d4451', '#8b93a1', '#d9dee6',
];

export const GRADIENTS = [
  { id: 'aurora', name: 'Aurora', from: '#00c4cc', to: '#7d2ae8', angle: 135 },
  { id: 'sunset', name: 'Sunset', from: '#ffd166', to: '#ef476f', angle: 120 },
  { id: 'ember', name: 'Ember', from: '#ff8a5b', to: '#c9184a', angle: 100 },
  { id: 'midnight', name: 'Midnight', from: '#1b2140', to: '#0b0b12', angle: 160 },
  { id: 'mint', name: 'Mint', from: '#d9f7ef', to: '#2ec4b6', angle: 130 },
  { id: 'blush', name: 'Blush', from: '#ffe8d6', to: '#ef476f', angle: 125 },
];

export const SHAPES = [
  { type: 'rect', label: 'Rectangle', icon: 'shape' },
  { type: 'roundRect', label: 'Rounded', radius: 44 },
  { type: 'ellipse', label: 'Circle' },
  { type: 'triangle', label: 'Triangle' },
  { type: 'diamond', label: 'Diamond' },
  { type: 'hexagon', label: 'Hexagon' },
  { type: 'star', label: 'Star' },
  { type: 'arrow', label: 'Arrow' },
  { type: 'line', label: 'Line' },
];

export const SHAPE_LABELS = {
  text: 'Text',
  rect: 'Rectangle',
  roundRect: 'Rounded rectangle',
  ellipse: 'Ellipse',
  triangle: 'Triangle',
  diamond: 'Diamond',
  hexagon: 'Hexagon',
  star: 'Star',
  arrow: 'Arrow',
  line: 'Line',
  image: 'Image',
};

export function fontStack(fontId) {
  return (FONTS.find((font) => font.id === fontId) || FONTS[0]).stack;
}

export function fontName(fontId) {
  return (FONTS.find((font) => font.id === fontId) || FONTS[0]).name;
}

export function fillCss(fill) {
  if (!fill) return 'transparent';
  if (typeof fill === 'string') return fill;
  return `linear-gradient(${fill.angle ?? 135}deg, ${fill.from}, ${fill.to})`;
}

export function isGradient(fill) {
  return Boolean(fill && typeof fill === 'object' && fill.from && fill.to);
}

export function normalizedPoints(type, sides = 6) {
  if (type === 'triangle') return [[0.5, 0], [1, 1], [0, 1]];
  if (type === 'diamond') return [[0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5]];
  if (type === 'hexagon') {
    const points = [];
    for (let i = 0; i < 6; i += 1) {
      const angle = -Math.PI / 2 + (i * Math.PI) / 3;
      points.push([0.5 + Math.cos(angle) * 0.5, 0.5 + Math.sin(angle) * 0.5]);
    }
    return points;
  }
  if (type === 'arrow') {
    return [[0, 0.32], [0.62, 0.32], [0.62, 0.06], [1, 0.5], [0.62, 0.94], [0.62, 0.68], [0, 0.68]];
  }
  if (type === 'star') {
    const points = [];
    for (let i = 0; i < 10; i += 1) {
      const radius = i % 2 === 0 ? 0.5 : 0.21;
      const angle = -Math.PI / 2 + (i * Math.PI) / 5;
      points.push([0.5 + Math.cos(angle) * radius, 0.5 + Math.sin(angle) * radius]);
    }
    return points;
  }
  return [];
}

export function polygonCss(type) {
  const points = normalizedPoints(type);
  if (!points.length) return '';
  return `polygon(${points.map(([x, y]) => `${(x * 100).toFixed(2)}% ${(y * 100).toFixed(2)}%`).join(', ')})`;
}

const BASE_ELEMENT = {
  x: 0,
  y: 0,
  w: 240,
  h: 240,
  rotation: 0,
  opacity: 1,
  locked: false,
  visible: true,
};

const TEXT_DEFAULTS = {
  text: 'Add your text',
  font: 'sans',
  size: 48,
  weight: 400,
  italic: false,
  underline: false,
  align: 'left',
  color: '#12161c',
  lineHeight: 1.2,
  letterSpacing: 0,
};

export function createElement(type, overrides = {}) {
  let specific;
  switch (type) {
    case 'text':
      specific = { ...TEXT_DEFAULTS, w: 520, h: 140 };
      break;
    case 'image':
      specific = { src: '', fit: 'cover', w: 480, h: 360 };
      break;
    case 'line':
      specific = { fill: '#12161c', w: 320, h: 8 };
      break;
    case 'roundRect':
      specific = { fill: '#7d2ae8', radius: 48 };
      break;
    default:
      specific = { fill: '#7d2ae8', stroke: 'transparent', strokeWidth: 0, radius: 0 };
  }
  const element = {
    ...BASE_ELEMENT,
    id: uid(type),
    type,
    name: SHAPE_LABELS[type] || 'Element',
    ...specific,
    ...overrides,
  };
  if (type === 'image' && !element.name) element.name = 'Image';
  return element;
}

export function textElement(overrides) {
  return createElement('text', overrides);
}

export function createPage(overrides = {}) {
  return { id: uid('page'), background: '#ffffff', elements: [], ...overrides };
}

export function createDesign({ title = 'Untitled design', preset = 'social', background = '#ffffff' } = {}) {
  const size = PAGE_PRESETS.find((item) => item.id === preset) || PAGE_PRESETS[1];
  const now = Date.now();
  return {
    id: uid('design'),
    title,
    w: size.w,
    h: size.h,
    createdAt: now,
    updatedAt: now,
    pages: [createPage({ background })],
  };
}

export function designTitleFor(element) {
  if (element.type === 'text') {
    const firstLine = String(element.text || '').split('\n')[0].trim();
    if (firstLine) return firstLine.slice(0, 32);
  }
  return SHAPE_LABELS[element.type] || 'Element';
}

/* ------------------------------------------------------------------ */
/* Templates                                                           */
/* ------------------------------------------------------------------ */

const img = (x, y, w, h, src, fit = 'cover') => createElement('image', { x, y, w, h, src, fit });

const rect = (x, y, w, h, fill, extra = {}) =>
  createElement('rect', { x, y, w, h, fill, ...extra });

const head = (x, y, w, h, text, size, extra = {}) =>
  textElement({ x, y, w, h, text, size, font: 'sans', ...extra });

const TEMPLATE_DEFS = [
  {
    id: 'social-launch',
    name: 'Launch post',
    category: 'Social',
    preset: 'social',
    background: '#0e1318',
    build(w, h) {
      return [
        img(0, 0, w, h, 'assets/photos/abstract.jpg'),
        rect(0, 0, w, h, '#0e1318', { opacity: 0.34 }),
        head(80, 78, 640, 40, 'REA STUDIO / 2026', 24, { color: '#ffffffcc', letterSpacing: 6, weight: 600 }),
        createElement('star', { x: 824, y: 108, w: 156, h: 156, fill: '#ffd166', rotation: -12 }),
        createElement('ellipse', {
          x: 768, y: 742, w: 236, h: 236, fill: 'transparent', stroke: '#ffffff66', strokeWidth: 2,
        }),
        head(80, 606, 780, 340, 'Make it\nreal.', 150, {
          font: 'serif', lineHeight: 0.95, color: '#ffffff',
        }),
        head(80, 930, 560, 90, 'A design board that moves\nat the speed of your ideas.', 27, {
          color: '#ffffffb3', lineHeight: 1.4,
        }),
        head(80, 1010, 560, 30, 'rea.studio / studio edition', 17, { color: '#ffffff80', letterSpacing: 2 }),
      ];
    },
  },
  {
    id: 'poster-quiet',
    name: 'Quiet Hour poster',
    category: 'Print',
    preset: 'poster',
    background: '#f3ede3',
    build(w, h) {
      return [
        head(150, 148, 1000, 40, 'ISSUE 04   THE QUIET HOUR', 24, { color: '#5b5348', letterSpacing: 6, weight: 600 }),
        rect(150, 220, w - 300, 2, '#1a1a1a'),
        head(140, 300, 1320, 920, 'The\nQuiet\nHour', 330, {
          font: 'serif', lineHeight: 0.9, color: '#14110e',
        }),
        head(150, 1290, 760, 150, 'A study in light, patience and the\nspaces between.', 42, {
          font: 'serif', color: '#3a342c', lineHeight: 1.35,
        }),
        createElement('ellipse', {
          x: 1000, y: 1430, w: 420, h: 420,
          fill: { from: '#00c4cc', to: '#7d2ae8', angle: 135 },
        }),
        rect(150, 1936, w - 300, 2, '#1a1a1a'),
        head(150, 1984, 600, 34, 'REA PRESS', 22, { letterSpacing: 6, weight: 600 }),
        head(1240, 1980, 200, 34, '24', 22, { align: 'right', color: '#5b5348' }),
      ];
    },
  },
  {
    id: 'presentation-launch',
    name: 'Product launch deck',
    category: 'Presentation',
    preset: 'presentation',
    background: '#f7f4ef',
    build(w, h) {
      return [
        img(w - 840, 0, 840, h, 'assets/photos/desk.jpg'),
        head(120, 112, 700, 36, 'PRODUCT LAUNCH', 22, { color: '#7d2ae8', letterSpacing: 7, weight: 600 }),
        head(120, 280, 900, 340, 'Design at the\nspeed of thought.', 104, {
          font: 'serif', lineHeight: 1.02, color: '#141821',
        }),
        head(120, 690, 660, 120, 'A board that keeps up with the hand. Move, scale and align without losing the thread.', 28, {
          color: '#4a5262', lineHeight: 1.45,
        }),
        rect(120, 872, 160, 10, { from: '#00c4cc', to: '#7d2ae8', angle: 90 }),
        head(1500, 1000, 300, 30, '2026', 20, { color: '#ffffffcc', align: 'right', letterSpacing: 4 }),
      ];
    },
  },
  {
    id: 'story-sale',
    name: 'Spring sale story',
    category: 'Social',
    preset: 'story',
    background: '#0b0b12',
    build(w, h) {
      return [
        rect(0, 0, w, h, { from: '#1b2140', to: '#0b0b12', angle: 160 }),
        createElement('star', { x: 760, y: 170, w: 180, h: 180, fill: '#ffd166', rotation: 10 }),
        head(0, 420, w, 60, 'UP TO', 40, { align: 'center', letterSpacing: 14, color: '#ffffffcc' }),
        head(0, 496, w, 450, '50%', 380, { font: 'serif', align: 'center', color: '#ffffff' }),
        head(0, 1000, w, 80, 'OFF EVERYTHING', 52, { align: 'center', letterSpacing: 8, weight: 600, color: '#ffffff' }),
        rect(300, 1180, 480, 96, '#ffffff', { radius: 48 }),
        head(300, 1206, 480, 50, 'Shop the edit', 30, { align: 'center', color: '#141821', weight: 600 }),
        head(0, 1740, w, 30, 'rea.studio / spring drop', 18, { align: 'center', letterSpacing: 5, color: '#ffffff80' }),
      ];
    },
  },
  {
    id: 'card-minimal',
    name: 'Minimal invitation card',
    category: 'Print',
    preset: 'card',
    background: '#101418',
    build(w, h) {
      return [
        head(70, 66, 500, 30, 'REA STUDIO', 18, { color: '#ffffff80', letterSpacing: 8, weight: 600 }),
        createElement('star', { x: 876, y: 76, w: 96, h: 96, fill: '#ffd166' }),
        head(70, 164, 780, 300, 'Sophea\n& Dara', 112, { font: 'serif', lineHeight: 0.98, color: '#ffffff' }),
        rect(70, 508, 120, 6, { from: '#00c4cc', to: '#7d2ae8', angle: 90 }),
        head(230, 498, 620, 30, 'SATURDAY / 14 FEBRUARY 2026', 17, {
          color: '#ffffffb3', letterSpacing: 4,
        }),
      ];
    },
  },
  {
    id: 'flyer-workshop',
    name: 'Workshop flyer',
    category: 'Print',
    preset: 'document',
    background: '#fef3e2',
    build(w, h) {
      return [
        rect(0, 0, 1240, 660, { from: '#c9184a', to: '#ff8a5b', angle: 120 }),
        head(90, 100, 700, 32, 'WORKSHOP / 04', 24, { color: '#ffffffcc', letterSpacing: 8, weight: 600 }),
        head(80, 190, 1020, 300, 'Build your\nbrand board', 104, {
          font: 'serif', lineHeight: 0.96, color: '#ffffff',
        }),
        head(90, 760, 940, 100, 'A hands-on evening of type, colour and grid.', 32, { color: '#3a342c' }),
        rect(90, 860, 1060, 2, '#14110e'),
        head(90, 908, 620, 30, 'THU 12 MARCH / 18:30', 24, { letterSpacing: 4, weight: 600 }),
        head(90, 956, 760, 30, 'The Studio, 12 Rue Basse', 24, { color: '#5b5348' }),
        head(90, 1140, 940, 110, 'Bring a laptop.\nLeave with a system.', 46, { font: 'serif', color: '#14110e' }),
        rect(90, 1400, 230, 64, '#14110e', { radius: 32 }),
        head(90, 1422, 230, 34, 'Save a seat', 22, { align: 'center', color: '#ffffff', weight: 600 }),
        createElement('star', { x: 980, y: 1450, w: 140, h: 140, fill: '#ef476f', rotation: -6 }),
        head(90, 1400, 1060, 30, '', 18, {}),
      ].filter((element) => element.text !== '');
    },
  },
];

export const TEMPLATES = TEMPLATE_DEFS.map((template) => {
  const preset = PAGE_PRESETS.find((item) => item.id === template.preset) || PAGE_PRESETS[1];
  return {
    ...template,
    w: preset.w,
    h: preset.h,
    buildPages() {
      return [createPage({ background: template.background, elements: template.build(preset.w, preset.h) })];
    },
  };
});

export function designFromTemplate(templateId, title) {
  const template = TEMPLATES.find((item) => item.id === templateId);
  if (!template) return createDesign({ title });
  const now = Date.now();
  return {
    id: uid('design'),
    title: title || template.name,
    w: template.w,
    h: template.h,
    createdAt: now,
    updatedAt: now,
    pages: template.buildPages(),
  };
}

export function seedDesigns() {
  const now = Date.now();
  const seeds = [
    designFromTemplate('social-launch', 'Launch announcement'),
    designFromTemplate('presentation-launch', 'Product launch deck'),
    designFromTemplate('card-minimal', 'Sophea and Dara card'),
  ];
  seeds.forEach((design, index) => {
    design.id = `seed-${design.pages[0].id}`;
    design.createdAt = now - (index + 1) * 86_400_000;
    design.updatedAt = now - (index + 1) * 3_600_000;
  });
  return seeds;
}

export function findPreset(w, h) {
  return PAGE_PRESETS.find((preset) => preset.w === w && preset.h === h) || null;
}
