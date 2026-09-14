# V23.6.2 Library Import/Export Report

V23.6.2 adds portable JSON import/export for custom photo styles.

Export payload:

- schema version;
- export timestamp;
- custom styles only;
- normalized supported photo-look fields.

Import safeguards:

- 1 MB file-size ceiling;
- JSON parse validation;
- array/schema compatibility handling;
- record-count limit;
- sanitized text and identifiers;
- normalized look values;
- new local IDs rather than trusting imported IDs;
- duplicate-safe names;
- custom-library capacity enforcement;
- bounded serialized storage before persistence.

Import never executes code, loads remote assets, replaces image sources, or changes the active invitation automatically.
