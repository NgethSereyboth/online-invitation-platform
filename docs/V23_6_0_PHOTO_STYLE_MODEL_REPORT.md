# V23.6.0 Photo-Style Model Report

V23.6.0 introduces a reusable data-only photo-style model over the normalized V23.5 photo-look fields.

Completed behavior:

- ten built-in invitation-oriented styles derived from the existing photo presets;
- custom style capture from the selected image;
- bounded names, descriptions, categories, tags, IDs, timestamps, and normalized look values;
- exclusion of source media and composition fields;
- duplicate-safe custom names;
- browser-profile persistence with restricted-storage fallback;
- maximum 36 custom records and 900 KB serialized storage boundary.

No invitation schema, database table, publishing payload, or renderer version was introduced.
