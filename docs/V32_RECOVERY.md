# V32 Backup and Recovery

Workspace backups are generated to files rather than unbounded response memory, include structured documents and manifests, carry checksums and immutable metadata, and run as durable jobs. Provider interfaces support local development and production off-device storage/encryption policies. Restore must require reauthentication and explicit confirmation, validate ZIP paths/checksums/schema and create a new recovery epoch. RPO/RTO values are deployment targets, never guarantees.

Native disaster-recovery drills, off-device encryption configuration and restoration at production scale remain required during the independent audit.
