// Snapshot undo/redo. Each committed design state is a deep clone, so a drag,
// a resize or a text edit is one undo step no matter how many frames it took.

import { deepClone } from './util.js';

export class History {
  constructor(doc, apply) {
    this.apply = apply;
    this.stack = [];
    this.index = -1;
    this.onChange = null;
    this.reset(doc);
  }

  reset(doc) {
    this.stack = [deepClone(doc)];
    this.index = 0;
    this.onChange?.();
  }

  push(doc) {
    const snapshot = deepClone(doc);
    if (this.index < this.stack.length - 1) this.stack = this.stack.slice(0, this.index + 1);
    this.stack.push(snapshot);
    if (this.stack.length > 60) this.stack.shift();
    this.index = this.stack.length - 1;
    this.onChange?.();
  }

  canUndo() {
    return this.index > 0;
  }

  canRedo() {
    return this.index < this.stack.length - 1;
  }

  undo() {
    if (!this.canUndo()) return null;
    this.index -= 1;
    this.onChange?.();
    return deepClone(this.stack[this.index]);
  }

  redo() {
    if (!this.canRedo()) return null;
    this.index += 1;
    this.onChange?.();
    return deepClone(this.stack[this.index]);
  }
}
