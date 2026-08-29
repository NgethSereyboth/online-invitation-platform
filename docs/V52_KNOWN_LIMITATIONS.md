# V52 Known Limitations

- Independent Codex testing and release certification are pending.
- External AI, DNS, certificate, animation-rendering, email/messaging, marketplace-signing, payment, monitoring, and bot-risk providers require configured adapters and credentials.
- Development domain verification accepts explicit development evidence; production DNS/certificate verification must use a provider adapter.
- Animation exports currently provide a deterministic provider-neutral render manifest unless a production renderer is configured; full MP4/GIF/WebM rendering is provider work.
- Plugin execution is intentionally declarative and sandbox-limited; arbitrary third-party JavaScript is not supported.
- Bulk merge is capped at 5,000 rows per job and requires later scale/load validation.
- Event intelligence is deterministic operational analysis, not an unrestricted generative decision maker.
- Native mobile, cross-browser, physical GPU, large-media, marketplace moderation, payments, real external messaging, penetration, disaster-recovery, and multi-region validation remain pending.
