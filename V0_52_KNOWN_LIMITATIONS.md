# V0.52 Known Limitations

- This execution environment blocks Playwright HTTP navigation before application code with `net::ERR_BLOCKED_BY_ADMINISTRATOR`; therefore the new real served-browser AI, dashboard-cover and autosave regressions require an unrestricted independent rerun.
- Native Windows, native Linux, WebKit/Safari, Firefox, Android and iOS certification remains pending.
- External AI providers, DNS/certificate providers, production video encoders, messaging providers, plugin signing services, payments, monitoring, malware scanning, distributed queues and external object storage require environment configuration and credentials.
- Production domain activation cannot complete without a configured DNS/certificate provider.
- Plugin execution remains deliberately declarative; arbitrary JavaScript plugins are not supported.
- Animation export prepares provider-neutral manifests unless a production renderer is configured.
- Bulk generation remains capped at 5,000 rows per job.
- Security assessment, penetration testing, load testing, physical-GPU testing and disaster-recovery exercises remain pending.
