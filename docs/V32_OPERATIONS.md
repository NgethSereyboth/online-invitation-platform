# V32 Operations and Observability

V32 adds structured request IDs, secret-safe logs, local metrics, durable job state, storage/collaboration/publish health, liveness/readiness endpoints, maintenance mode and bounded graceful shutdown. The server stops accepting new work, shuts down HTTP service, drains bounded worker tasks and closes handles. Provider-neutral error monitoring and tracing use environment configuration and never record invitation contents, passwords, tokens, full signed URLs or private guest data.
