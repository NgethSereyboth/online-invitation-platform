# V23.6 Performance Report

A real Chromium focused run in the development container measured:

- First Photo Styles library open: approximately 111.9 ms.
- Creating the bounded maximum of 36 custom styles: approximately 379.6 ms total.
- Filtering the full built-in/custom library: approximately 76.9 ms including the test interaction window.
- Custom-style payload at the maximum tested count: below 900,000 bytes.
- Dialog instances after repeated open/close cycles: one.
- Registered `photoStyles.open` commands after repeated cycles: one.
- Command registry conflicts: zero.

The latest generated initial editor route is 1,419,964 bytes against the established 1,420,000-byte budget. `photo-style-library-v23.js` remains second-stage loaded and its stylesheet is runtime-injected, so it does not add a blocking script or stylesheet request to the initial page.
