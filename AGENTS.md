# M5-AI Builder development rules
- Every new application using external hardware must use the shared m5lib_hardware profile API and declare its dependency in the app .deps.json. Do not duplicate module pin, UART baud, I2C address or PaHub channel settings in apps.
- Reuse shared sensor drivers; keep device-specific bus construction in adapters. Extend profiles centrally and preserve backwards compatibility. Cardputer and Core2 hardware defaults differ; validate on each target before claiming compatibility.
- Do not drive conflicting Grove protocols simultaneously. Disconnect power before changing wiring or pin assignments.
- Keep existing signed publication, version monotonicity and production approval. Never push changes while an AutoPublish request awaits approval.
- Test saved profile changes without republishing apps. Report physical validation separately from compilation and publication.
- If a new module needs a profile not yet supported, extend the shared profile schema and launcher together before releasing its app.
