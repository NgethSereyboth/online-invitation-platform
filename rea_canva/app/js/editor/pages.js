// Page strip along the bottom of the board.

import { debounce } from '../batch.js';
import { paintThumbnail } from '../render.js';
import { el, openMenu, svgIcon, ICONS } from '../util.js';

export function mountPages(host, editor) {
  let seq = 0;
  const schedule = debounce(render, 220);

  function render() {
    if (!editor.doc) return;
    const run = ++seq;
    host.replaceChildren();

    editor.doc.pages.forEach((page, index) => {
      const button = el('button', {
        class: `page-chip${index === editor.pageIndex ? ' is-active' : ''}`,
        type: 'button',
        title: `Page ${index + 1}`,
        'aria-label': `Page ${index + 1}`,
      });
      const canvas = el('canvas', { class: 'page-thumb' });
      button.append(canvas, el('span', { class: 'page-number', text: String(index + 1) }));
      button.addEventListener('click', () => editor.setPage(index));
      if (index === editor.pageIndex) {
        const more = el('span', { class: 'page-more', title: 'Page options', role: 'button', tabindex: '0' }, svgIcon(ICONS.more, 16));
        more.addEventListener('click', (event) => {
          event.stopPropagation();
          openMenu(more, [
            { label: 'Duplicate page', icon: ICONS.copy, onSelect: () => editor.duplicatePage(index) },
            { label: 'Add page', icon: ICONS.plus, onSelect: () => editor.addPage() },
            { separator: true },
            { label: 'Delete page', icon: ICONS.trash, danger: true, onSelect: () => editor.deletePage(index) },
          ], { align: 'right' });
        });
        button.append(more);
      }
      host.append(button);
      paintThumbnail(canvas, { w: editor.doc.w, h: editor.doc.h }, page, 56, 56).catch(() => null);
      if (run !== seq) return;
    });

    const add = el('button', { class: 'page-add', type: 'button', title: 'Add page', 'aria-label': 'Add page' }, svgIcon(ICONS.plus, 18));
    add.addEventListener('click', () => editor.addPage());
    host.append(add);

    const background = el('button', {
      class: 'page-bg',
      type: 'button',
      title: 'Page background',
      'aria-label': 'Page background',
      style: { background: editor.page.background },
    });
    background.addEventListener('click', () => {
      editor.select([]);
      editor.inspector.render();
    });
    host.append(background);
  }

  render();
  return { render, schedule };
}
