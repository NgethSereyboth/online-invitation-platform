# Rea Studio

A separate, self-contained design workspace inside `rea_canva/`: a Canva-style
dashboard plus a full design board. It has nothing to do with the eInvite app's
build, routes, bundles or storage; both can run side by side.

- **Dashboard** (`app/index.html`) - quick-create sizes, recent designs, templates, search.
- **Board** (`app/editor.html`) - multi-page canvas with pan/zoom, drag, resize,
  rotate, snapping guides, layers, text editing, shapes, gradients, image
  uploads, undo/redo, PNG/JPG export and a preview mode.

Designs and uploads live in the browser's `localStorage` (`rea.canva.*`). No
account, backend or network calls are involved.

## Run it

```bash
python3 rea_canva/serve.py --port 8123
```

Then open <http://127.0.0.1:8123>. `python3 -m http.server 8123 -d rea_canva/app`
works too; the app is plain HTML/CSS/ES modules with no build step.

## Layout

```
rea_canva/
  app/
    index.html            dashboard
    editor.html           design board
    css/tokens.css        font faces, tokens, shared UI
    css/dashboard.css     dashboard layout
    css/editor.css        editor layout, board and selection chrome
    js/util.js            DOM, menu, modal, toast helpers
    js/model.js           document schema, presets, element factories, templates
    js/storage.js         localStorage designs, uploads, brand kit
    js/history.js         snapshot undo/redo
    js/batch.js           frame batcher
    js/render.js          canvas renderer (thumbnails, export)
    js/elements.js        DOM renderer for one element
    js/dashboard.js       dashboard behaviour
    js/editor/app.js      editor state, shortcuts, export, preview
    js/editor/board.js    view transform, gestures, snapping, text editing
    js/editor/panels.js   templates, elements, text, brand, uploads, layers
    js/editor/properties.js  contextual inspector
    js/editor/pages.js    page strip
    assets/fonts/         self-hosted Rea Sans (Inter) and Rea Serif (Noto Serif)
    assets/photos/        two template photographs
  serve.py                local static server
```

`_rea-canva/` and `_canva-verify/` hold the reverse-engineering evidence that
informed the interaction model (batched input, a single transform layer,
zoom-to-cursor, snapping, short motion budgets). They are research material,
are not served, and are excluded from git.
