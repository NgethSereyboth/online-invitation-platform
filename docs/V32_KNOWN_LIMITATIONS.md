# V32 Known Intentionally Deferred Limitations

- Full Photoshop-equivalent content-aware fill, advanced healing, CMYK proofing and GPU/CPU parity are not claimed.
- Boolean geometry is bounded; complex subtract/intersect/divide operations may report unsupported rather than flatten unsafe paths.
- The production collaboration adapter interface is WebSocket-compatible, but the included development transport uses authenticated polling.
- Redis-backed distributed queue/presence and external monitoring/tracing require provider configuration.
- S3/R2/MinIO requires `boto3` and deployment credentials; local storage remains the default.
- Production malware scanning, email, SMS/WhatsApp/Telegram, bot-risk, AI and error-monitoring providers require separate credentials/endpoints.
- Large-document, full-resolution raster, physical GPU, native Windows/Linux, browser compatibility and disaster-recovery certification are deferred to the independent audit.
- Advanced pen/node gestures and raster tools are intentionally desktop-oriented; mobile retains practical quick editing and clear desktop-required states.
