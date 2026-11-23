// The design board. One transform layer moves the whole page; gestures are
// batched to one commit per frame; selection chrome lives in screen space so
// handles stay the same size at every zoom level.

import { createFrameBatcher } from '../batch.js';
import { createElementNode, styleElementNode } from '../elements.js';
import { designTitleFor } from '../model.js';
import { deepClone, uid } from '../util.js';

const MIN_ZOOM = 0.05;
const MAX_ZOOM = 8;
const MIN_SIZE = 12;
const HANDLES = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
const DRAG_THRESHOLD = 3;

const rotatePoint = (point, radians) => ({
  x: point.x * Math.cos(radians) - point.y * Math.sin(radians),
  y: point.x * Math.sin(radians) + point.y * Math.cos(radians),
});

const unionBox = (elements) => {
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;
  for (const element of elements) {
    left = Math.min(left, element.x);
    top = Math.min(top, element.y);
    right = Math.max(right, element.x + element.w);
    bottom = Math.max(bottom, element.y + element.h);
  }
  if (!Number.isFinite(left)) return { x: 0, y: 0, w: 0, h: 0 };
  return { x: left, y: top, w: right - left, h: bottom - top };
};

export class Board {
  constructor(viewport, editor) {
    this.viewport = viewport;
    this.editor = editor;
    this.stage = viewport.querySelector('#stage');
    this.surface = viewport.querySelector('#pageSurface');
    this.layer = viewport.querySelector('#pageElements');
    this.overlay = viewport.querySelector('#overlay');
    this.guidesHost = viewport.querySelector('#guides');
    this.marqueeNode = viewport.querySelector('#marquee');
    this.selection = viewport.querySelector('#selection');

    this.zoom = 1;
    this.pan = { x: 0, y: 0 };
    this.autoFit = true;
    this.nodes = new Map();
    this.gesture = null;
    this.pending = null;
    this.editingId = null;
    this.spaceDown = false;
    this.hasFitted = false;
    this.onView = null;

    this.zoomBatcher = createFrameBatcher(
      (a, b) => ({ delta: a.delta + b.delta, x: b.x, y: b.y }),
      ({ delta, x, y }) => {
        const factor = 2 ** (-Math.max(-140, Math.min(140, delta)) / 200);
        this.zoomAt(x, y, this.zoom * factor);
      },
    );
    this.panBatcher = createFrameBatcher(
      (a, b) => ({ dx: a.dx + b.dx, dy: a.dy + b.dy }),
      ({ dx, dy }) => this.panBy(-dx, -dy),
    );
    this.gestureBatcher = createFrameBatcher(
      (a, b) => b,
      (point) => this.applyGesture(point),
    );

    this.buildHandles();
    this.bind();
  }

  /* ---------------------------------------------------------------- */
  /* View                                                              */
  /* ---------------------------------------------------------------- */

  buildHandles() {
    const frag = document.createDocumentFragment();
    for (const handle of HANDLES) {
      const node = document.createElement('div');
      node.className = `sel-handle handle-${handle}`;
      node.dataset.handle = handle;
      node.setAttribute('aria-hidden', 'true');
      frag.append(node);
    }
    const rotate = document.createElement('div');
    rotate.className = 'sel-handle handle-rotate';
    rotate.dataset.handle = 'rotate';
    rotate.setAttribute('aria-hidden', 'true');
    rotate.append(document.createElement('span'));
    frag.append(rotate);
    this.selection.append(frag);
  }

  bind() {
    this.viewport.addEventListener('wheel', (event) => this.onWheel(event), { passive: false });
    this.viewport.addEventListener('pointerdown', (event) => this.onPointerDown(event));
    this.viewport.addEventListener('pointermove', (event) => this.onPointerMove(event));
    this.viewport.addEventListener('pointerup', (event) => this.onPointerUp(event));
    this.viewport.addEventListener('pointercancel', (event) => this.onPointerUp(event));
    this.viewport.addEventListener('dblclick', (event) => this.onDoubleClick(event));
    this.viewport.addEventListener('contextmenu', (event) => {
      if (event.target.closest('.canvas-el')) event.preventDefault();
    });

    const resize = new ResizeObserver(() => {
      if (this.autoFit) this.fit();
      else this.refreshOverlay();
    });
    resize.observe(this.viewport);
  }

  applyView() {
    this.stage.style.transform = `translate(${this.pan.x}px, ${this.pan.y}px) scale(${this.zoom})`;
    this.surface.classList.toggle('is-tiny', this.zoom < 0.25);
    this.onView?.(this.zoom);
    this.refreshOverlay();
  }

  fit() {
    const doc = this.editor.doc;
    const vw = this.viewport.clientWidth;
    const vh = this.viewport.clientHeight;
    const inspector = document.querySelector('#inspector');
    const inspectorWidth =
      inspector && inspector.offsetParent !== null && window.innerWidth > 1080
        ? inspector.offsetWidth + 14
        : 0;
    const pad = { left: 96, right: 96 + inspectorWidth, top: 64, bottom: 156 };
    const availW = Math.max(120, vw - pad.left - pad.right);
    const availH = Math.max(120, vh - pad.top - pad.bottom);
    const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.min(availW / doc.w, availH / doc.h)));
    this.zoom = zoom;
    this.pan = {
      x: Math.round(pad.left + (availW - doc.w * zoom) / 2),
      y: Math.round(pad.top + (availH - doc.h * zoom) / 2),
    };
    this.autoFit = true;
    this.hasFitted = true;
    this.applyView();
  }

  zoomAt(x, y, nextZoom) {
    const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, nextZoom));
    if (Math.abs(zoom - this.zoom) < 0.0001) return;
    const worldX = (x - this.pan.x) / this.zoom;
    const worldY = (y - this.pan.y) / this.zoom;
    this.zoom = zoom;
    this.pan = { x: x - worldX * zoom, y: y - worldY * zoom };
    this.autoFit = false;
    this.applyView();
  }

  setZoom(nextZoom) {
    const centerX = this.viewport.clientWidth / 2;
    const centerY = this.viewport.clientHeight / 2;
    this.zoomAt(centerX, centerY, nextZoom);
  }

  panBy(dx, dy) {
    this.pan = { x: this.pan.x + dx, y: this.pan.y + dy };
    this.autoFit = false;
    this.applyView();
  }

  onWheel(event) {
    if (!this.editor.doc) return;
    event.preventDefault();
    const rect = this.viewport.getBoundingClientRect();
    if (event.ctrlKey || event.metaKey) {
      this.zoomBatcher.accumulate({
        delta: event.deltaY,
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
      return;
    }
    const unit = event.deltaMode === 1 ? 40 : event.deltaMode === 2 ? 800 : 1;
    const horizontal = event.shiftKey && !event.deltaX;
    this.panBatcher.accumulate({
      dx: (horizontal ? event.deltaY : event.deltaX) * unit,
      dy: (horizontal ? 0 : event.deltaY) * unit,
    });
  }

  setSpace(down) {
    this.spaceDown = down;
    this.viewport.classList.toggle('is-space', down);
  }

  worldFromClient(clientX, clientY) {
    const rect = this.viewport.getBoundingClientRect();
    return {
      x: (clientX - rect.left - this.pan.x) / this.zoom,
      y: (clientY - rect.top - this.pan.y) / this.zoom,
    };
  }

  localFromClient(clientX, clientY) {
    const rect = this.viewport.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  /* ---------------------------------------------------------------- */
  /* Rendering                                                         */
  /* ---------------------------------------------------------------- */

  renderPage() {
    if (this.editingId) this.finishTextEdit(false);
    const { doc } = this.editor;
    const page = this.editor.page;
    this.surface.style.width = `${doc.w}px`;
    this.surface.style.height = `${doc.h}px`;
    this.surface.style.background = page.background || '#ffffff';
    this.layer.replaceChildren();
    this.nodes.clear();
    for (const element of page.elements) {
      const node = createElementNode(element);
      this.nodes.set(element.id, node);
      if (element.type === 'text') {
        const body = node.querySelector('.text-body');
        body.addEventListener('blur', () => this.finishTextEdit(true));
        body.addEventListener('keydown', (event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            this.finishTextEdit(true);
            this.viewport.focus({ preventScroll: true });
          }
        });
        body.addEventListener('paste', (event) => {
          event.preventDefault();
          const text = event.clipboardData?.getData('text/plain') || '';
          document.execCommand('insertText', false, text);
        });
      }
      this.layer.append(node);
    }
    this.applyView();
  }

  refreshNodes(ids = null) {
    const targets = ids ? ids.map((id) => this.editor.findElement(id)).filter(Boolean) : this.editor.page.elements;
    for (const element of targets) {
      const node = this.nodes.get(element.id);
      if (node) styleElementNode(node, element);
    }
    this.refreshOverlay();
  }

  /* ---------------------------------------------------------------- */
  /* Selection chrome                                                  */
  /* ---------------------------------------------------------------- */

  refreshOverlay() {
    if (!this.editor.doc) return;
    const selected = this.editor.selectedElements().filter((element) => element.visible !== false);
    if (!selected.length) {
      this.selection.hidden = true;
      this.guidesHost.replaceChildren();
      return;
    }
    this.selection.hidden = false;

    let box;
    let rotation = 0;
    if (selected.length === 1) {
      const element = selected[0];
      box = { x: element.x, y: element.y, w: element.w, h: element.h };
      rotation = element.rotation || 0;
    } else {
      box = unionBox(selected);
    }

    const centerX = this.pan.x + (box.x + box.w / 2) * this.zoom;
    const centerY = this.pan.y + (box.y + box.h / 2) * this.zoom;
    this.selection.style.left = `${centerX}px`;
    this.selection.style.top = `${centerY}px`;
    this.selection.style.width = `${Math.max(0, box.w * this.zoom)}px`;
    this.selection.style.height = `${Math.max(0, box.h * this.zoom)}px`;
    this.selection.style.transform = `translate(-50%, -50%) rotate(${rotation}deg)`;
    this.selection.classList.toggle('is-locked', selected.every((element) => element.locked));
    this.selection.classList.toggle('is-editing', Boolean(this.editingId));
  }

  showGuides(guides) {
    this.guidesHost.replaceChildren();
    for (const guide of guides) {
      const node = document.createElement('div');
      node.className = guide.axis === 'x' ? 'guide guide-v' : 'guide guide-h';
      const position = guide.axis === 'x'
        ? this.pan.x + guide.at * this.zoom
        : this.pan.y + guide.at * this.zoom;
      if (guide.axis === 'x') node.style.left = `${position}px`;
      else node.style.top = `${position}px`;
      this.guidesHost.append(node);
    }
  }

  /* ---------------------------------------------------------------- */
  /* Pointer gestures                                                  */
  /* ---------------------------------------------------------------- */

  onPointerDown(event) {
    if (!this.editor.doc) return;
    if (event.button === 1 || (event.button === 0 && this.spaceDown)) {
      event.preventDefault();
      this.gesture = {
        kind: 'pan',
        pointerId: event.pointerId,
        startClient: { x: event.clientX, y: event.clientY },
        startPan: { ...this.pan },
      };
      this.viewport.classList.add('is-panning');
      this.viewport.setPointerCapture(event.pointerId);
      return;
    }
    if (event.button !== 0) return;

    const handle = event.target.closest('[data-handle]');
    if (handle && !this.selection.hidden) {
      event.preventDefault();
      this.startTransform(event, handle.dataset.handle);
      return;
    }

    const node = event.target.closest('.canvas-el');
    if (node) {
      const id = node.dataset.id;
      if (this.editingId === id) return;
      const additive = event.shiftKey || event.metaKey || event.ctrlKey;
      const selected = this.editor.selected;
      if (additive) this.editor.toggleSelection(id);
      else if (!selected.has(id)) this.editor.select([id]);
      const element = this.editor.findElement(id);
      if (element && !element.locked && this.editor.selected.has(id)) {
        this.startMove(event, id, additive);
      }
      return;
    }

    if (this.editingId) this.finishTextEdit(true);
    if (!event.shiftKey && !event.metaKey && !event.ctrlKey) this.editor.select([]);
    this.gesture = {
      kind: 'marquee',
      pointerId: event.pointerId,
      startLocal: this.localFromClient(event.clientX, event.clientY),
      base: new Set(event.shiftKey || event.metaKey || event.ctrlKey ? this.editor.selected : []),
      moved: false,
    };
    this.capturePointer(event);
    this.marqueeNode.hidden = false;
  }

  capturePointer(event) {
    try {
      this.viewport.setPointerCapture(event.pointerId);
    } catch {
      /* synthetic events and released pointers have no capture target */
    }
  }

  startMove(event, id, additive) {
    const selected = this.editor.selectedElements().filter((element) => !element.locked);
    this.gesture = {
      kind: 'move',
      pointerId: event.pointerId,
      id,
      additive,
      startClient: { x: event.clientX, y: event.clientY },
      startWorld: this.worldFromClient(event.clientX, event.clientY),
      starts: selected.map((element) => ({
        id: element.id,
        x: element.x,
        y: element.y,
        w: element.w,
        h: element.h,
      })),
      moved: false,
    };
  }

  startTransform(event, handle) {
    const selected = this.editor.selectedElements();
    if (!selected.length || selected.some((element) => element.locked)) return;
    if (handle === 'rotate') {
      const box = unionBox(selected);
      const center = { x: box.x + box.w / 2, y: box.y + box.h / 2 };
      const origin = this.worldFromClient(event.clientX, event.clientY);
      this.gesture = {
        kind: 'rotate',
        pointerId: event.pointerId,
        center,
        startAngle: Math.atan2(origin.y - center.y, origin.x - center.x),
        starts: selected.map((element) => ({
          id: element.id,
          x: element.x,
          y: element.y,
          w: element.w,
          h: element.h,
          rotation: element.rotation || 0,
        })),
        box,
        moved: false,
      };
      this.capturePointer(event);
      return;
    }

    if (selected.length === 1) {
      const element = selected[0];
      const center = { x: element.x + element.w / 2, y: element.y + element.h / 2 };
      const theta = ((element.rotation || 0) * Math.PI) / 180;
      this.gesture = {
        kind: 'resize',
        mode: 'single',
        handle,
        pointerId: event.pointerId,
        center,
        theta,
        start: { ...element },
        starts: null,
        moved: false,
      };
      this.capturePointer(event);
      return;
    }

    const box = unionBox(selected);
    this.gesture = {
      kind: 'resize',
      mode: 'group',
      handle,
      pointerId: event.pointerId,
      box,
      pointerStart: this.worldFromClient(event.clientX, event.clientY),
      starts: selected.map((element) => ({
        id: element.id,
        x: element.x,
        y: element.y,
        w: element.w,
        h: element.h,
      })),
      moved: false,
    };
    this.capturePointer(event);
  }

  onPointerMove(event) {
    if (!this.gesture) return;
    const gesture = this.gesture;
    if (gesture.pointerId !== event.pointerId) return;

    if (gesture.kind === 'pan') {
      this.panBatcher.flush();
      this.pan = {
        x: gesture.startPan.x + (event.clientX - gesture.startClient.x),
        y: gesture.startPan.y + (event.clientY - gesture.startClient.y),
      };
      this.autoFit = false;
      this.applyView();
      return;
    }

    if (gesture.kind === 'marquee') {
      const point = this.localFromClient(event.clientX, event.clientY);
      this.gestureBatcher.accumulate(point);
      return;
    }

    if (gesture.kind === 'move') {
      if (!gesture.moved) {
        const distance = Math.hypot(
          event.clientX - gesture.startClient.x,
          event.clientY - gesture.startClient.y,
        );
        if (distance < DRAG_THRESHOLD) return;
        gesture.moved = true;
        this.viewport.classList.add('is-dragging');
        try {
          this.viewport.setPointerCapture(event.pointerId);
        } catch {
          /* pointer capture is best effort */
        }
      }
      this.gestureBatcher.accumulate({
        kind: 'move',
        clientX: event.clientX,
        clientY: event.clientY,
        shiftKey: event.shiftKey,
      });
      return;
    }

    gesture.moved = true;
    this.gestureBatcher.accumulate({
      kind: gesture.kind,
      clientX: event.clientX,
      clientY: event.clientY,
      shiftKey: event.shiftKey,
    });
  }

  applyGesture(input) {
    if (!this.gesture) return;
    const gesture = this.gesture;
    if (gesture.kind === 'marquee') {
      this.applyMarquee(input);
      return;
    }
    if (gesture.kind === 'move') this.applyMove(input);
    else if (gesture.kind === 'resize') this.applyResize(input);
    else if (gesture.kind === 'rotate') this.applyRotate(input);
  }

  applyMove(input) {
    const gesture = this.gesture;
    const world = this.worldFromClient(input.clientX, input.clientY);
    let dx = world.x - gesture.startWorld.x;
    let dy = world.y - gesture.startWorld.y;

    const moving = gesture.starts
      .map((start) => ({ start, element: this.editor.findElement(start.id) }))
      .filter((entry) => entry.element);

    const box = unionBox(moving.map(({ start }) => start));
    const threshold = 6 / this.zoom;
    const targets = this.snapTargets(gesture.starts.map((start) => start.id));
    const guides = [];

    const snapX = this.findSnap(
      [box.x + dx, box.x + dx + box.w / 2, box.x + dx + box.w],
      targets.xs,
      threshold,
    );
    if (snapX) {
      dx += snapX.delta;
      guides.push({ axis: 'x', at: snapX.at });
    }
    const snapY = this.findSnap(
      [box.y + dy, box.y + dy + box.h / 2, box.y + dy + box.h],
      targets.ys,
      threshold,
    );
    if (snapY) {
      dy += snapY.delta;
      guides.push({ axis: 'y', at: snapY.at });
    }

    for (const { start, element } of moving) {
      element.x = Math.round((start.x + dx) * 100) / 100;
      element.y = Math.round((start.y + dy) * 100) / 100;
      const node = this.nodes.get(element.id);
      if (node) {
        node.style.left = `${element.x}px`;
        node.style.top = `${element.y}px`;
      }
    }
    this.showGuides(guides);
    this.refreshOverlay();
  }

  applyResize(input) {
    const gesture = this.gesture;
    const world = this.worldFromClient(input.clientX, input.clientY);
    if (gesture.mode === 'single') this.applyResizeSingle(input, world);
    else this.applyResizeGroup(input, world);
    this.refreshOverlay();
  }

  applyResizeSingle(input, world) {
    const gesture = this.gesture;
    const element = this.editor.findElement(gesture.start.id);
    if (!element) return;
    const local = rotatePoint(
      { x: world.x - gesture.center.x, y: world.y - gesture.center.y },
      -gesture.theta,
    );
    const start = gesture.start;
    let left = -start.w / 2;
    let right = start.w / 2;
    let top = -start.h / 2;
    let bottom = start.h / 2;
    const handle = gesture.handle;

    if (handle.includes('w')) left = Math.min(local.x, right - MIN_SIZE);
    if (handle.includes('e')) right = Math.max(local.x, left + MIN_SIZE);
    if (handle.includes('n')) top = Math.min(local.y, bottom - MIN_SIZE);
    if (handle.includes('s')) bottom = Math.max(local.y, top + MIN_SIZE);

    let width = right - left;
    let height = bottom - top;

    if (input.shiftKey && handle.length === 2) {
      const scale = Math.max(width / start.w, height / start.h);
      width = start.w * scale;
      height = start.h * scale;
      if (handle.includes('w')) left = right - width;
      else right = left + width;
      if (handle.includes('n')) top = bottom - height;
      else bottom = top + height;
    }

    const localCenter = { x: (left + right) / 2, y: (top + bottom) / 2 };
    const worldCenter = rotatePoint(localCenter, gesture.theta);
    element.w = Math.round(width * 100) / 100;
    element.h = Math.round(height * 100) / 100;
    element.x = Math.round((gesture.center.x + worldCenter.x - width / 2) * 100) / 100;
    element.y = Math.round((gesture.center.y + worldCenter.y - height / 2) * 100) / 100;

    const node = this.nodes.get(element.id);
    if (node) styleElementNode(node, element);
    this.showGuides([]);
  }

  applyResizeGroup(input, world) {
    const gesture = this.gesture;
    const box = gesture.box;
    const handle = gesture.handle;
    let left = box.x;
    let right = box.x + box.w;
    let top = box.y;
    let bottom = box.y + box.h;

    if (handle.includes('w')) left = Math.min(world.x, right - MIN_SIZE);
    if (handle.includes('e')) right = Math.max(world.x, left + MIN_SIZE);
    if (handle.includes('n')) top = Math.min(world.y, bottom - MIN_SIZE);
    if (handle.includes('s')) bottom = Math.max(world.y, top + MIN_SIZE);

    const scaleX = (right - left) / Math.max(1, box.w);
    const scaleY = (bottom - top) / Math.max(1, box.h);

    for (const start of gesture.starts) {
      const element = this.editor.findElement(start.id);
      if (!element) continue;
      element.x = Math.round((left + (start.x - box.x) * scaleX) * 100) / 100;
      element.y = Math.round((top + (start.y - box.y) * scaleY) * 100) / 100;
      element.w = Math.max(2, Math.round(start.w * scaleX * 100) / 100);
      element.h = Math.max(2, Math.round(start.h * scaleY * 100) / 100);
      const node = this.nodes.get(element.id);
      if (node) styleElementNode(node, element);
    }
    this.showGuides([]);
  }

  applyRotate(input) {
    const gesture = this.gesture;
    const world = this.worldFromClient(input.clientX, input.clientY);
    const angle = Math.atan2(world.y - gesture.center.y, world.x - gesture.center.x);
    let delta = ((angle - gesture.startAngle) * 180) / Math.PI;
    if (input.shiftKey) delta = Math.round(delta / 15) * 15;
    const radians = (delta * Math.PI) / 180;

    for (const start of gesture.starts) {
      const element = this.editor.findElement(start.id);
      if (!element) continue;
      element.rotation = Math.round((start.rotation + delta) * 10) / 10;
      if (gesture.starts.length > 1) {
        const offset = {
          x: start.x + start.w / 2 - gesture.center.x,
          y: start.y + start.h / 2 - gesture.center.y,
        };
        const rotated = rotatePoint(offset, radians);
        element.x = Math.round((gesture.center.x + rotated.x - start.w / 2) * 100) / 100;
        element.y = Math.round((gesture.center.y + rotated.y - start.h / 2) * 100) / 100;
      }
      const node = this.nodes.get(element.id);
      if (node) styleElementNode(node, element);
    }
    this.showGuides([]);
  }

  applyMarquee(point) {
    const gesture = this.gesture;
    const start = gesture.startLocal;
    const left = Math.min(start.x, point.x);
    const top = Math.min(start.y, point.y);
    const width = Math.abs(point.x - start.x);
    const height = Math.abs(point.y - start.y);
    this.marqueeNode.style.left = `${left}px`;
    this.marqueeNode.style.top = `${top}px`;
    this.marqueeNode.style.width = `${width}px`;
    this.marqueeNode.style.height = `${height}px`;
    gesture.moved = width > 4 || height > 4;

    const worldLeft = (left - this.pan.x) / this.zoom;
    const worldTop = (top - this.pan.y) / this.zoom;
    const worldRight = (left + width - this.pan.x) / this.zoom;
    const worldBottom = (top + height - this.pan.y) / this.zoom;

    const hits = this.editor.page.elements
      .filter((element) => element.visible !== false)
      .filter((element) => {
        const right = element.x + element.w;
        const bottom = element.y + element.h;
        return element.x < worldRight && right > worldLeft && element.y < worldBottom && bottom > worldTop;
      })
      .map((element) => element.id);

    this.editor.select([...gesture.base, ...hits]);
  }

  onPointerUp(event) {
    if (!this.gesture) return;
    if (this.gesture.pointerId !== event.pointerId) return;
    const gesture = this.gesture;
    this.gestureBatcher.flush();

    if (gesture.kind === 'pan') {
      this.viewport.classList.remove('is-panning');
    } else if (gesture.kind === 'marquee') {
      this.marqueeNode.hidden = true;
      this.marqueeNode.style.cssText = '';
      if (!gesture.moved && !event.shiftKey) this.editor.select([]);
    } else if (gesture.kind === 'move') {
      this.viewport.classList.remove('is-dragging');
      if (gesture.moved) {
        this.editor.commit('Move elements');
      } else if (!gesture.additive) {
        this.editor.select([gesture.id]);
      }
    } else if (gesture.kind === 'resize') {
      if (gesture.moved) this.editor.commit('Resize elements');
    } else if (gesture.kind === 'rotate') {
      if (gesture.moved) this.editor.commit('Rotate elements');
    }

    this.showGuides([]);
    try {
      this.viewport.releasePointerCapture(event.pointerId);
    } catch {
      /* pointer already released */
    }
    this.gesture = null;
    this.refreshOverlay();
  }

  snapTargets(excludeIds) {
    const doc = this.editor.doc;
    const xs = [0, doc.w / 2, doc.w];
    const ys = [0, doc.h / 2, doc.h];
    for (const element of this.editor.page.elements) {
      if (excludeIds.includes(element.id) || element.visible === false) continue;
      xs.push(element.x, element.x + element.w / 2, element.x + element.w);
      ys.push(element.y, element.y + element.h / 2, element.y + element.h);
    }
    return { xs, ys };
  }

  findSnap(values, targets, threshold) {
    let best = null;
    for (const value of values) {
      for (const target of targets) {
        const delta = target - value;
        if (Math.abs(delta) <= threshold && (!best || Math.abs(delta) < Math.abs(best.delta))) {
          best = { delta, at: target };
        }
      }
    }
    return best;
  }

  /* ---------------------------------------------------------------- */
  /* Text editing                                                      */
  /* ---------------------------------------------------------------- */

  onDoubleClick(event) {
    const node = event.target.closest('.canvas-el');
    if (!node) return;
    const element = this.editor.findElement(node.dataset.id);
    if (!element) return;
    if (element.type === 'text') {
      event.preventDefault();
      this.startTextEdit(element.id);
    } else if (element.type === 'image') {
      this.editor.emit('replace-image', element.id);
    }
  }

  startTextEdit(id) {
    const element = this.editor.findElement(id);
    if (!element || element.type !== 'text' || element.locked) return;
    const node = this.nodes.get(id);
    if (!node) return;
    this.editor.select([id]);
    this.editingId = id;
    const body = node.querySelector('.text-body');
    body.contentEditable = 'true';
    body.spellcheck = false;
    node.classList.add('is-editing');
    this.selection.classList.add('is-editing');
    body.focus({ preventScroll: true });
    const range = document.createRange();
    range.selectNodeContents(body);
    if (!/^(Add |$)/.test(element.text || '')) range.collapse(false);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    this.textSnapshot = element.text;
  }

  finishTextEdit(commit) {
    if (!this.editingId) return;
    const id = this.editingId;
    this.editingId = null;
    const element = this.editor.findElement(id);
    const node = this.nodes.get(id);
    if (!node) return;
    const body = node.querySelector('.text-body');
    body.contentEditable = 'false';
    node.classList.remove('is-editing');
    this.selection.classList.remove('is-editing');
    if (element) {
      const text = (body.innerText || '').replace(/\u00a0/g, ' ').replace(/\n$/, '');
      if (commit && text !== this.textSnapshot) {
        element.text = text;
        if (!element.name || element.name === 'Text') element.name = designTitleFor(element);
        this.editor.commit('Edit text');
      } else if (text !== element.text) {
        body.textContent = element.text;
      }
    }
    this.refreshOverlay();
  }

  /* ---------------------------------------------------------------- */
  /* Keyboard helpers used by the editor shell                         */
  /* ---------------------------------------------------------------- */

  nudge(dx, dy, commit = true) {
    const selected = this.editor.selectedElements().filter((element) => !element.locked);
    if (!selected.length) return;
    for (const element of selected) {
      element.x = Math.round((element.x + dx) * 100) / 100;
      element.y = Math.round((element.y + dy) * 100) / 100;
      const node = this.nodes.get(element.id);
      if (node) {
        node.style.left = `${element.x}px`;
        node.style.top = `${element.y}px`;
      }
    }
    this.refreshOverlay();
    if (commit) this.editor.commit('Nudge elements', { coalesce: `nudge-${uid('k')}` });
  }

  duplicateSelection() {
    const copies = this.editor.selectedElements().map((element) => {
      const copy = deepClone(element);
      copy.id = uid(element.type);
      copy.x += 24;
      copy.y += 24;
      return copy;
    });
    if (!copies.length) return;
    this.editor.page.elements.push(...copies);
    this.editor.select(copies.map((copy) => copy.id));
    this.editor.commit('Duplicate elements');
    this.renderPage();
  }
}
