# V23.6.3 Known Limitations

- Custom photo styles are local to the current browser profile; cloud synchronization and cross-device account storage are not part of this release.
- A reusable style changes non-destructive visual treatment fields only. It deliberately excludes image source, asset identity, object geometry, crop position, fit, frame/mask geometry, flips, perspective, and warp composition.
- Style cards use the selected image or a generic sample; custom pixel-identical thumbnail capture is not included.
- The library is intentionally bounded to 36 custom styles and 900 KB of serialized browser storage.
- Import/export transfers custom style definitions, not uploaded media or complete invitation documents.
- Photo editing remains object styling rather than destructive pixel editing; brush, healing, clone-stamp, liquify, content-aware fill, and a Photoshop-style raster layer engine remain deferred.
- Native Windows three-run certification, native Linux three-run certification, and physical-GPU benchmarking remain pending.
- The uninterrupted all-generation review runner exceeded the available container execution window. Its exact 58 deterministic checks passed in isolated serial batches, and the load-bearing V22/V23 browser suites passed in focused isolated runs.
