# Ember Finance

Ember is a polished, local-first personal finance dashboard. It begins with an empty database, imports statement PDFs or CSVs on your own computer, and makes every dashboard number traceable to the transactions behind it.

There is no login, telemetry, bank credential, cloud database, or automatic upload. The source repository contains only code and clearly invented test fixtures.

## What works

- Clean first-run onboarding with no demo accounts, balances, transactions, or budgets
- Guided Home setup and editable account details, balances, and active status
- Searchable PDF import for Chase checking, savings, and credit-card statements
- Broad generic PDF support for numeric, ISO, and month-name dates; debit/credit suffixes; extracted tables; and wrapped rows
- CSV import for date/description/amount or debit/credit layouts
- Preview-before-commit, sign checks, confidence reporting, and deterministic duplicate detection
- Expense, income, saving, investment, transfer, card-payment, refund, and reimbursement accounting
- Review inbox for ambiguous transactions and optional user-created rules
- Dashboard, transaction ledger, spending detail, comparisons, monthly report, FIRE metrics, recurring costs, and net worth
- Local SQLite backup/restore and transaction CSV export

## Start on your Mac

Requirements: Python 3.11+ and Node.js 22.13+.

First, open Terminal and move into the downloaded project folder. Running the command from `~` will produce “No such file or directory.”

```bash
cd /path/to/ember-finance
chmod +x scripts/*.sh
./scripts/start-local.sh
```

Open [http://localhost:3000](http://localhost:3000). The API reference is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The start script creates an isolated Python environment, installs missing dependencies, installs JavaScript dependencies, and starts both services. Press `Control-C` once to stop both.

## Your first statement

1. Start on **Home**, then open **Settings** and create the account that owns the statement. Use a nickname and, optionally, only the final four digits.
2. Open **Import**, select that account, and choose the PDF or CSV.
3. Inspect the parser name, warnings, dates, merchants, classifications, and signed amounts in the preview.
4. Commit only when the extracted rows match the statement.
5. Open **Review** and resolve uncertain person-to-person payments or unfamiliar descriptions.

PDF extraction is deterministic and entirely local. Searchable Chase statements receive specialized parsing. Other searchable layouts use table and flexible text-row extraction and are marked for review. Image-only scans are rejected with local OCR instructions rather than guessed at. A bank can change its layout, so always reconcile row count and totals against the original statement before relying on the dashboard.

If a searchable statement layout is not recognized, use the bank’s CSV export when available or contribute a fully redacted fixture and parser test. Never commit a real statement.

## Share it safely

Friends can clone the repository and run the same three commands. Each clone creates its own ignored database under `backend/data/`; no user data is inherited from the repository.

Before every GitHub push or release:

```bash
./scripts/privacy-check.sh
```

The check rejects tracked databases, statements, backup folders, secret files, absolute home-directory paths, and long account-number-like values. `.gitignore` also excludes PDFs, financial interchange files, CSV exports outside `sample-data/`, and local data folders.

To build a source-only zip from the current commit:

```bash
./scripts/package-release.sh 0.1.0
```

## Reset everything

Stop Ember first, then run:

```bash
./scripts/reset-local-data.sh
```

The script requires typing `RESET`. It permanently deletes the local database; the next launch creates a fresh one containing only generic category names.

## Accounting model

Spending includes `EXPENSE` outflows and subtracts `REFUND` and `REIMBURSEMENT` inflows. Credit-card payments and internal transfers are excluded to prevent double counting. Savings rate is `(SAVING + INVESTMENT) / earned INCOME`. Ambiguous imports remain `UNKNOWN` until reviewed.

The definitions live in `backend/app/analytics.py`; statement extraction lives in `backend/app/parsers/`.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm install
.venv/bin/pytest backend/tests -q
npm run build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Ember is MIT licensed and provided without financial or accuracy warranties.
