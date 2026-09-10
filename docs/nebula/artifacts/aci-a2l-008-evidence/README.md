# ACI-A2L-008 evidence

Explicit human approval. Fixture tests only. The locked Jay song was not approved.

- `tests/test_approve.py` — fixture SHA `aci-a2l-008-fixture`
- Locked-song `a2l_pipeline/approved_lyrics/` — **NOT CREATED**
- Locked-song review remains `approval_status=NOT_APPROVED`

Runtime approved files, when they exist for other jobs, live under `artifacts/ingest/<sha>/a2l_pipeline/approved_lyrics/` (gitignored ingest tree).
