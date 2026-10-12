# Ember Finance

Ember is a local personal-finance analytics dashboard powered by your budgeting spreadsheet. The spreadsheet remains where you enter and organize data; Ember turns it into clear spending, income, investing, comparison, and net-worth views.

There is no login, telemetry, bank connection, cloud database, or automatic upload. The repository contains only source code and invented test fixtures. Imported workbook data stays in an ignored SQLite database on your computer.

## Workbook structure

Use one monthly tab per month. Full month names, abbreviations, and optional years are supported, such as `August`, `Sep`, or `October 2026`. Row counts can vary and future month tabs are detected automatically.

Each monthly tab can contain these side-by-side tables beginning on row 1:

- Income: `Income`, `Type`, `Income Class`
- Expenses: `Expense`, `Type`, `Category`, optional `Expense Tag`
- Wealth Flow: `Wealth Flow`, `Destination`, `Flow Class`

The earlier stacked-table format with an `Amount` column remains supported. The `Networth` tab can use side-by-side `Savings` and `Investments` blocks with an “as of” date, or an `Account`, `Account Type`, and `Value` table with a date. Re-importing replaces monthly records; a net-worth snapshot is appended only when its date is newer than the latest saved snapshot.

## Start locally

Requirements: macOS, Python 3.11+, and Node.js 22.13+.

```bash
cd /path/to/ember-finance
chmod +x scripts/*.sh
./scripts/start-local.sh
```

Open [http://localhost:3000](http://localhost:3000). Press `Control-C` to stop both services.

On first use, open **Import**, select your `.xlsx` workbook, review every detected month and warning, then choose **Import / Replace Data**.

## Financial definitions

- Recurring Earned Income: Paycheck + Side Income
- Personal Spending: all expenses excluding `Work/Reimbursable`
- Core Spending: personal spending excluding `One-time` and `Personal Travel`
- Monthly Wealth Added: recurring earned income − personal spending + retirement investment + other investment
- Wealth-Building Rate: Monthly Wealth Added ÷ (Recurring Earned Income + Retirement Investment)

Internal transfers never count as spending, income, investing, or newly created wealth. These formulas live in `backend/app/analytics.py`.

## Privacy and sharing

Before publishing changes, run:

```bash
./scripts/privacy-check.sh
```

The check rejects tracked databases, statements, secrets, home paths, and account-number-like values. Friends can clone the public repository and receive a clean database with none of your imported data.

To permanently clear local imported data:

```bash
./scripts/reset-local-data.sh
```

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm install
.venv/bin/pytest backend/tests -q
npm run lint
npm run build
```

Ember is MIT licensed and provided without financial or accuracy warranties.
