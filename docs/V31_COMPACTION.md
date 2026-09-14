# V31 Update Compaction and Checkpoints

Collaboration updates are bounded by count and bytes and indexed by invitation, epoch and revision. Named checkpoints contain the acknowledged structured document, fingerprint and state vector. Compaction preserves a bounded recent update tail, creates a checkpoint and advances metadata without invalidating active identities. Restore creates a new document epoch; clients with an older epoch must export/recover unsynced updates rather than silently applying them.
