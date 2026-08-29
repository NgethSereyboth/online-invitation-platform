# V31 Offline Merge Behavior

Clients apply local updates immediately and retain a bounded installation/actor-scoped queue. Reconnect sends idempotent update IDs, receives missed updates and merges by Lamport clock plus actor tie-break. Sequence operations use stable CRDT identities rather than array indexes. Duplicate updates are ignored. Authorization loss preserves a downloadable recovery copy. Publishing uses server-acknowledged draft state and fingerprint, not an unconfirmed local-only view.
