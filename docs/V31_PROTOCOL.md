# V31 Collaboration Protocol

V31 uses project-owned version-1 updates with: stable document ID, epoch, actor ID, logical clock, update ID, typed operation, bounded path/payload, timestamp and origin. Supported operations are set, delete, conflict-safe sequence insert/move, structured rich-text change and checkpoint.

The local adapter is `crdt-adapter-v31.js`; transport and UI are in `collaboration-studio-v31.js`; durable storage and authorization are in `platform_v32`. Production may replace polling with a WebSocket-compatible adapter without exposing library-specific types to renderers or business logic. Presence is ephemeral, expires after 45 seconds, is rate-limited client-side and never enters snapshots.
