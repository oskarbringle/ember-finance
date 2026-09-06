# Contributing to Ember

Thanks for helping improve Ember. Keep pull requests focused, add tests for accounting or parser changes, and run both test suites before submitting.

```bash
.venv/bin/pytest backend/tests -q
npm run build
./scripts/privacy-check.sh
```

Never commit real financial information. That includes statements, databases, exports, account numbers, balances, names from transaction descriptions, API keys, screenshots of real data, or backups. Use only invented fixtures under `sample-data/` and in tests.

PDF parsers must remain deterministic and local. Every parser must return a preview before a user can commit transactions, report its confidence and warnings, and include tests for inflow/outflow signs.
