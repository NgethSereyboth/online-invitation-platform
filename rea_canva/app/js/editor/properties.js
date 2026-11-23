// Right-hand inspector: page settings when nothing is selected, element
// properties when something is. Rebuilt only on selection/commit, so typing in
// a field never loses focus.

import {
  FONTS,
  FONT_WEIGHTS,
  GRADIENTS,
  PAGE_PRESETS,
  SWATCHES,
  fillCss,
  findPreset,
} from '../model.js';
import { el, svgIcon, ICONS } from '../util.js';

export function mountInspector(host, editor) {
  let scheduled = false;

  const api = { render, renderSoon };

  function renderSoon() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      render();
    });
  }

  function section(title, children, aside) {
    return el('section', { class: 'insp-section' }, [
      el('div', { class: 'insp-head' }, [
        el('h3', { class: 'insp-title', text: title }),
        aside || null,
      ]),
      ...children.filter(Boolean),
    ]);
  }

  function field(label, value, onChange, options = {}) {
    const input = el('input', {
      class: 'field-input',
      type: 'number',
      value: Number.isFinite(value) ? Math.round(value * 10) / 10 : 0,
      min: options.min,
      max: options.max,
      step: options.step ?? 1,
      'aria-label': label,
    });
    const commit = () => {
      const next = Number(input.value);
      if (!Number.isFinite(next)) return;
      onChange(next);
    };
    input.addEventListener('change', commit);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        input.blur();
      }
    });
    return el('label', { class: 'field' }, [
      el('span', { class: 'field-label', text: label }),
      input,
      options.suffix ? el('span', { class: 'field-suffix', text: options.suffix }) : null,
    ]);
  }

  function swatchGrid(current, onPick) {
    const grid = el('div', { class: 'swatch-grid' });
    for (const color of SWATCHES) {
      const button = el('button', {
        class: `swatch${String(current).toLowerCase() === color ? ' is-active' : ''}`,
        type: 'button',
        title: color,
        'aria-label': color,
        style: { background: color },
      });
      button.addEventListener('click', () => onPick(color));
      grid.append(button);
    }
    return grid;
  }

  function customColor(current, onChange) {
    const safe = /^#[0-9a-f]{6}$/i.test(current || '') ? current : '#12161c';
    const input = el('input', { class: 'color-input', type: 'color', value: safe, 'aria-label': 'Custom color' });
    input.addEventListener('input', () => onChange(input.value));
    return el('label', { class: 'color-row' }, [
      input,
      el('span', { class: 'color-value', text: (current || '').toUpperCase() }),
      el('span', { class: 'color-hint', text: 'Custom' }),
    ]);
  }

  function iconButton(icon, label, onClick, options = {}) {
    const button = el('button', {
      class: `tool-btn${options.active ? ' is-active' : ''}`,
      type: 'button',
      title: label,
      'aria-label': label,
      disabled: options.disabled,
    }, [svgIcon(ICONS[icon] || ICONS.shape, 18), options.text ? el('span', { text: options.text }) : null]);
    button.addEventListener('click', onClick);
    return button;
  }

  function render() {
    if (!editor.doc) return;
    const selected = editor.selectedElements();
    host.replaceChildren();

    if (!selected.length) {
      renderPageSettings();
      return;
    }

    const single = selected.length === 1 ? selected[0] : null;
    const types = new Set(selected.map((element) => element.type));
    const commonType = types.size === 1 ? [...types][0] : null;

    host.append(
      el('div', { class: 'insp-summary' }, [
        el('div', { class: 'insp-summary-main' }, [
          el('span', { class: 'insp-kicker', text: single ? (single.name || single.type) : `${selected.length} elements` }),
          el('span', {
            class: 'insp-sub',
            text: single
              ? `${Math.round(single.w)} x ${Math.round(single.h)} px`
              : 'Group selection',
          }),
        ]),
        iconButton('duplicate', 'Duplicate', () => editor.duplicateSelected()),
        iconButton('trash', 'Delete', () => editor.deleteSelected()),
      ]),
    );

    if (single) {
      host.append(
        section('Position', [
          el('div', { class: 'field-grid' }, [
            field('X', single.x, (value) => editor.updateElement(single.id, { x: value }, 'Set position'), { suffix: 'px' }),
            field('Y', single.y, (value) => editor.updateElement(single.id, { y: value }, 'Set position'), { suffix: 'px' }),
          ]),
          el('div', { class: 'field-grid' }, [
            field('W', single.w, (value) => editor.updateElement(single.id, { w: Math.max(2, value) }, 'Set size'), { suffix: 'px', min: 2 }),
            field('H', single.h, (value) => editor.updateElement(single.id, { h: Math.max(2, value) }, 'Set size'), { suffix: 'px', min: 2 }),
          ]),
          el('div', { class: 'field-grid' }, [
            field('Rotate', single.rotation || 0, (value) => editor.updateElement(single.id, { rotation: value }, 'Set rotation'), { suffix: 'deg' }),
            field('Opacity', Math.round((single.opacity ?? 1) * 100), (value) => editor.updateElement(single.id, { opacity: Math.max(0, Math.min(1, value / 100)) }, 'Set opacity'), { suffix: '%', min: 0, max: 100 }),
          ]),
        ]),
      );
    }

    host.append(
      section('Align', [
        el('div', { class: 'align-row' }, [
          iconButton('alignLeft', 'Align left', () => editor.align('left')),
          iconButton('alignCenter', 'Align center', () => editor.align('center')),
          iconButton('alignRight', 'Align right', () => editor.align('right')),
          iconButton('alignTop', 'Align top', () => editor.align('top')),
          iconButton('alignMiddle', 'Align middle', () => editor.align('middle')),
          iconButton('alignBottom', 'Align bottom', () => editor.align('bottom')),
        ]),
        el('button', { class: 'wide-btn', type: 'button', text: `Center on page`, on: { click: () => editor.centerOnPage() } }),
      ]),
    );

    host.append(
      section('Arrange', [
        el('div', { class: 'align-row' }, [
          iconButton('toFront', 'Bring to front', () => editor.arrange('front')),
          iconButton('forward', 'Bring forward', () => editor.arrange('forward')),
          iconButton('backward', 'Send backward', () => editor.arrange('backward')),
          iconButton('toBack', 'Send to back', () => editor.arrange('back')),
        ]),
        el('div', { class: 'align-row' }, [
          iconButton(selected.every((item) => item.locked) ? 'unlock' : 'lock', 'Lock selection', () => {
            editor.lockSelected(!selected.every((item) => item.locked));
          }, { active: selected.every((item) => item.locked), text: selected.every((item) => item.locked) ? 'Locked' : 'Lock' }),
        ]),
      ]),
    );

    if (commonType === 'text' || selected.some((item) => item.type === 'text')) {
      const first = selected.find((item) => item.type === 'text');
      host.append(
        section('Text', [
          el('label', { class: 'field field-full' }, [
            el('span', { class: 'field-label', text: 'Font' }),
            (() => {
              const select = el('select', { class: 'field-input' });
              for (const font of FONTS) {
                const option = el('option', { value: font.id, text: `${font.name} - ${font.kind}` });
                if (font.id === first.font) option.selected = true;
                select.append(option);
              }
              select.addEventListener('change', () => editor.setTextStyle({ font: select.value }));
              return select;
            })(),
          ]),
          el('div', { class: 'field-grid' }, [
            field('Size', first.size, (value) => editor.setTextStyle({ size: Math.max(4, value) }), { suffix: 'px', min: 4 }),
            (() => {
              const select = el('select', { class: 'field-input', 'aria-label': 'Font weight' });
              for (const weight of FONT_WEIGHTS) {
                const option = el('option', { value: String(weight.value), text: weight.label });
                if (weight.value === first.weight) option.selected = true;
                select.append(option);
              }
              select.addEventListener('change', () => editor.setTextStyle({ weight: Number(select.value) }));
              return el('label', { class: 'field field-weight' }, [
                el('span', { class: 'field-label', text: 'Wt' }),
                select,
              ]);
            })(),
          ]),
          el('div', { class: 'style-row' }, [
            el('button', {
              class: `mini-toggle${first.weight >= 700 ? ' is-active' : ''}`,
              type: 'button',
              title: 'Bold',
              text: 'B',
              on: { click: () => editor.setTextStyle({ weight: first.weight >= 700 ? 400 : 700 }) },
            }),
            el('button', {
              class: `mini-toggle${first.italic ? ' is-active' : ''}`,
              type: 'button',
              title: 'Italic',
              text: 'I',
              style: { fontStyle: 'italic' },
              on: { click: () => editor.setTextStyle({ italic: !first.italic }) },
            }),
            el('button', {
              class: `mini-toggle${first.underline ? ' is-active' : ''}`,
              type: 'button',
              title: 'Underline',
              text: 'U',
              style: { textDecoration: 'underline' },
              on: { click: () => editor.setTextStyle({ underline: !first.underline }) },
            }),
            el('span', { class: 'style-sep' }),
            ...['left', 'center', 'right'].map((align) =>
              el('button', {
                class: `mini-toggle${first.align === align ? ' is-active' : ''}`,
                type: 'button',
                title: `Align ${align}`,
                on: { click: () => editor.setTextStyle({ align }) },
              }, [svgIcon(ICONS[align === 'left' ? 'alignLeft' : align === 'center' ? 'alignCenter' : 'alignRight'], 17)]),
            ),
          ]),
          el('div', { class: 'field-grid' }, [
            field('Line', first.lineHeight || 1.2, (value) => editor.setTextStyle({ lineHeight: Math.max(0.6, value) }), { step: 0.05, min: 0.6 }),
            field('Spacing', first.letterSpacing || 0, (value) => editor.setTextStyle({ letterSpacing: value }), { step: 0.5 }),
          ]),
          el('div', { class: 'swatch-caption', text: 'Text colour' }),
          swatchGrid(first.color, (color) => editor.setTextStyle({ color })),
          customColor(first.color, (color) => editor.setTextStyle({ color })),
        ]),
      );
    }

    if (commonType === 'image') {
      const first = selected[0];
      host.append(
        section('Image', [
          el('div', { class: 'style-row' }, [
            el('button', {
              class: `wide-btn${first.fit !== 'contain' ? ' is-active' : ''}`,
              type: 'button',
              text: 'Fill frame',
              on: { click: () => editor.updateSelected({ fit: 'cover' }, 'Fit image') },
            }),
            el('button', {
              class: `wide-btn${first.fit === 'contain' ? ' is-active' : ''}`,
              type: 'button',
              text: 'Fit inside',
              on: { click: () => editor.updateSelected({ fit: 'contain' }, 'Fit image') },
            }),
          ]),
          el('button', {
            class: 'wide-btn',
            type: 'button',
            text: 'Replace image',
            on: { click: () => editor.emit('replace-image', first.id) },
          }),
        ]),
      );
    }

    if (commonType && commonType !== 'text' && commonType !== 'image') {
      const first = selected[0];
      const isGradient = first.fill && typeof first.fill === 'object';
      host.append(
        section('Colour', [
          el('div', { class: 'swatch-caption', text: isGradient ? 'Gradient fill' : 'Solid fill' }),
          swatchGrid(isGradient ? '' : first.fill, (color) => editor.updateSelected({ fill: color }, 'Set fill')),
          customColor(isGradient ? '#7d2ae8' : first.fill, (color) => editor.updateSelected({ fill: color }, 'Set fill')),
          el('div', { class: 'swatch-caption', text: 'Stroke' }),
          swatchGrid(first.stroke === 'transparent' ? '' : first.stroke, (color) => editor.updateSelected({ stroke: color, strokeWidth: first.strokeWidth || 2 }, 'Set stroke')),
          el('div', { class: 'field-grid' }, [
            field('Stroke', first.strokeWidth || 0, (value) => editor.updateSelected({ strokeWidth: Math.max(0, value) }, 'Set stroke'), { min: 0, suffix: 'px' }),
            field('Radius', first.radius || 0, (value) => editor.updateSelected({ radius: Math.max(0, value) }, 'Set radius'), { min: 0, suffix: 'px' }),
          ]),
        ]),
      );
    }

    if (single && single.type !== 'text' && single.type !== 'image') {
      host.append(
        section('Fill style', [
          el('div', { class: 'swatch-caption', text: 'Gradient presets' }),
          (() => {
            const row = el('div', { class: 'gradient-row' });
            for (const gradient of GRADIENTS.slice(0, 4)) {
              const button = el('button', {
                class: 'gradient-chip',
                type: 'button',
                title: gradient.name,
                'aria-label': `Apply ${gradient.name} gradient`,
                style: { background: fillCss(gradient) },
              });
              button.addEventListener('click', () => editor.updateSelected({ fill: { ...gradient } }, 'Set gradient'));
              row.append(button);
            }
            return row;
          })(),
        ]),
      );
    }
  }

  function renderPageSettings() {
    const preset = findPreset(editor.doc.w, editor.doc.h);
    host.append(
      el('div', { class: 'insp-summary' }, [
        el('div', { class: 'insp-summary-main' }, [
          el('span', { class: 'insp-kicker', text: 'Page' }),
          el('span', { class: 'insp-sub', text: `Page ${editor.pageIndex + 1} of ${editor.doc.pages.length}` }),
        ]),
      ]),
    );

    host.append(
      section('Background', [
        swatchGrid(editor.page.background, (color) => {
          editor.setPageBackground(color);
        }),
        customColor(editor.page.background, (color) => editor.setPageBackground(color)),
      ]),
    );

    const widthInput = el('input', { class: 'field-input', type: 'number', value: editor.doc.w, min: 200, max: 5000 });
    const heightInput = el('input', { class: 'field-input', type: 'number', value: editor.doc.h, min: 200, max: 5000 });
    host.append(
      section('Design size', [
        el('label', { class: 'field field-full' }, [
          el('span', { class: 'field-label', text: 'Preset' }),
          (() => {
            const select = el('select', { class: 'field-input' });
            for (const item of PAGE_PRESETS) {
              const option = el('option', { value: item.id, text: `${item.label} (${item.w} x ${item.h})` });
              if (preset?.id === item.id) option.selected = true;
              select.append(option);
            }
            const custom = el('option', { value: 'custom', text: 'Custom size' });
            if (!preset) custom.selected = true;
            select.append(custom);
            select.addEventListener('change', () => {
              if (select.value !== 'custom') editor.setDesignSize(select.value);
            });
            return select;
          })(),
        ]),
        el('div', { class: 'field-grid' }, [
          el('label', { class: 'field' }, [el('span', { class: 'field-label', text: 'W' }), widthInput]),
          el('label', { class: 'field' }, [el('span', { class: 'field-label', text: 'H' }), heightInput]),
        ]),
        el('button', {
          class: 'wide-btn is-active',
          type: 'button',
          text: 'Apply custom size',
          on: {
            click: () => editor.setDesignSizeCustom(Number(widthInput.value), Number(heightInput.value)),
          },
        }),
      ]),
    );

    host.append(
      section('Pages', [
        el('div', { class: 'stack' }, [
          el('button', { class: 'wide-btn', type: 'button', text: 'Add page', on: { click: () => editor.addPage() } }),
          el('button', { class: 'wide-btn', type: 'button', text: 'Duplicate page', on: { click: () => editor.duplicatePage() } }),
          el('button', { class: 'wide-btn', type: 'button', text: 'Delete page', on: { click: () => editor.deletePage() } }),
        ]),
      ]),
    );

    host.append(
      section('Shortcuts', [
        el('dl', { class: 'shortcuts' }, [
          el('dt', { text: 'Zoom to cursor' }), el('dd', { text: 'Ctrl / Cmd + scroll' }),
          el('dt', { text: 'Pan the board' }), el('dd', { text: 'Space + drag' }),
          el('dt', { text: 'Inline edit' }), el('dd', { text: 'Double-click text' }),
        ]),
      ]),
    );
  }

  render();
  return api;
}
