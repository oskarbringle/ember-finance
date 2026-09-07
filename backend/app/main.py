from __future__ import annotations

import csv
import io
import json
import re
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .analytics import current_net_worth, dashboard_payload, date_bounds, financial_totals
from .classification import classify_transaction, transaction_fingerprint
from .database import Base, DATABASE_PATH, engine, get_db
from .models import Account, BalanceSnapshot, Budget, Category, Classification, ImportBatch, Rule, Setting, Transaction
from .parsers import GenericCsvParser, PdfStatementParser
from .sample_data import initialize_reference_data
from .schemas import AccountCreate, AccountRead, BudgetUpsert, RuleCreate, SnapshotCreate, TransactionRead, TransactionUpdate


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        initialize_reference_data(db)
        refunds = db.scalars(select(Transaction).where(Transaction.classification == Classification.REFUND, Transaction.category == "Refund")).all()
        for refund in refunds:
            original = db.scalar(
                select(Transaction)
                .where(
                    Transaction.normalized_merchant == refund.normalized_merchant,
                    Transaction.classification == Classification.EXPENSE,
                    Transaction.transaction_date <= refund.transaction_date,
                )
                .order_by(Transaction.transaction_date.desc())
            )
            if original:
                refund.category = original.category
        db.commit()
    yield


app = FastAPI(title="Ember Finance API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": str(DATABASE_PATH)}


@app.get("/api/accounts", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)):
    return db.scalars(select(Account).order_by(Account.active.desc(), Account.name)).all()


@app.post("/api/accounts", response_model=AccountRead)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    values = payload.model_dump(exclude={"save_snapshot"})
    account = Account(**values)
    db.add(account)
    db.flush()
    if payload.save_snapshot and payload.balance_mode == "MANUAL":
        db.add(BalanceSnapshot(account_id=account.id, balance=account.current_balance))
    db.commit()
    db.refresh(account)
    return account


@app.patch("/api/accounts/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountCreate, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    old_balance = account.current_balance
    for field, value in payload.model_dump(exclude={"save_snapshot"}).items():
        setattr(account, field, value)
    if payload.save_snapshot and old_balance != account.current_balance:
        existing = db.scalar(select(BalanceSnapshot).where(BalanceSnapshot.account_id == account.id, BalanceSnapshot.snapshot_date == date.today()))
        if existing:
            existing.balance = account.current_balance
        else:
            db.add(BalanceSnapshot(account_id=account.id, balance=account.current_balance))
    db.commit()
    db.refresh(account)
    return account


@app.post("/api/accounts/{account_id}/snapshots")
def create_snapshot(account_id: int, payload: SnapshotCreate, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    account.current_balance = payload.balance
    snapshot = db.scalar(select(BalanceSnapshot).where(BalanceSnapshot.account_id == account_id, BalanceSnapshot.snapshot_date == payload.snapshot_date))
    if snapshot:
        snapshot.balance = payload.balance
    else:
        snapshot = BalanceSnapshot(account_id=account_id, **payload.model_dump())
        db.add(snapshot)
    db.commit()
    return {"status": "saved", "balance": payload.balance, "date": payload.snapshot_date}


@app.get("/api/transactions", response_model=list[TransactionRead])
def list_transactions(
    account_id: int | None = None,
    category: str | None = None,
    merchant: str | None = None,
    classification: str | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = select(Transaction)
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category:
        query = query.where(Transaction.category == category)
    if merchant:
        query = query.where(Transaction.normalized_merchant.ilike(f"%{merchant}%"))
    if classification:
        query = query.where(Transaction.classification == classification)
    if start:
        query = query.where(Transaction.transaction_date >= start)
    if end:
        query = query.where(Transaction.transaction_date <= end)
    return db.scalars(query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(min(limit, 2000))).all()


@app.patch("/api/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transaction not found")
    for field, value in payload.model_dump(exclude={"create_rule", "rule_pattern"}, exclude_none=True).items():
        setattr(transaction, field, value)
    transaction.confidence = 1.0
    if payload.create_rule:
        pattern = payload.rule_pattern or re.escape(transaction.raw_description)
        db.add(Rule(
            name=f"Rule for {transaction.normalized_merchant}", pattern=pattern,
            merchant=transaction.normalized_merchant, category=transaction.category,
            classification=transaction.classification, priority=200, user_created=True,
        ))
    db.commit()
    db.refresh(transaction)
    return transaction


@app.get("/api/review", response_model=list[TransactionRead])
def review_queue(db: Session = Depends(get_db)):
    return db.scalars(
        select(Transaction)
        .where((Transaction.classification == Classification.UNKNOWN) | (Transaction.confidence < 0.6), Transaction.manually_reviewed.is_(False))
        .order_by(Transaction.transaction_date.desc())
    ).all()


def _user_rules(db: Session) -> list[dict]:
    return [
        {"pattern": rule.pattern, "merchant": rule.merchant, "category": rule.category,
         "classification": rule.classification, "priority": rule.priority, "active": rule.active}
        for rule in db.scalars(select(Rule).where(Rule.active.is_(True)))
    ]


@app.post("/api/imports/preview")
async def preview_import(
    account_id: int = Form(...),
    sign_convention: str = Form("auto"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    filename = file.filename or "import"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".csv", ".pdf"):
        raise HTTPException(400, "Choose a CSV or PDF statement")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(400, "Statements must be smaller than 25 MB")
    parser = PdfStatementParser() if suffix == ".pdf" else GenericCsvParser()
    try:
        parsed = parser.parse(io.BytesIO(content), account_type=account.type, sign_convention=sign_convention)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    rules = _user_rules(db)
    preview_rows = []
    duplicates = 0
    uncertain = 0
    for row in parsed:
        fingerprint = transaction_fingerprint(account_id, row.transaction_date, row.amount, row.description)
        if db.scalar(select(Transaction.id).where(Transaction.fingerprint == fingerprint)):
            duplicates += 1
            continue
        result = classify_transaction(row.description, row.amount, rules)
        category = result.category
        if result.classification == Classification.REFUND:
            original = db.scalar(
                select(Transaction)
                .where(
                    Transaction.normalized_merchant == result.merchant,
                    Transaction.classification == Classification.EXPENSE,
                    Transaction.transaction_date <= row.transaction_date,
                )
                .order_by(Transaction.transaction_date.desc())
            )
            if original:
                category = original.category
        uncertain += int(result.classification == Classification.UNKNOWN or result.confidence < 0.6)
        preview_rows.append({
            "transaction_date": row.transaction_date.isoformat(),
            "posted_date": row.posted_date.isoformat() if row.posted_date else None,
            "raw_description": row.description,
            "normalized_merchant": result.merchant,
            "amount": row.amount,
            "direction": "CREDIT" if row.amount > 0 else "DEBIT",
            "category": category,
            "classification": result.classification,
            "confidence": result.confidence,
            "fingerprint": fingerprint,
        })
    batch_id = uuid.uuid4().hex
    batch = ImportBatch(
        id=batch_id, account_id=account_id, source_file=filename,
        total_rows=len(parsed), duplicate_rows=duplicates, uncertain_rows=uncertain,
        preview_json=json.dumps(preview_rows),
    )
    db.add(batch)
    db.commit()
    return {
        "batch_id": batch_id, "account": account.name, "total_rows": len(parsed),
        "ready_to_import": len(preview_rows), "duplicates": duplicates, "uncertain": uncertain,
        "preview": preview_rows[:50],
        "parser": getattr(parser, "provider", "unknown"),
        "parse_report": getattr(parser, "last_report", {}),
    }


@app.post("/api/imports/{batch_id}/commit")
def commit_import(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Import preview not found")
    if batch.status == "COMMITTED":
        return {"batch_id": batch.id, "committed": batch.committed_rows, "duplicates": batch.duplicate_rows, "status": batch.status}
    committed = 0
    duplicates = batch.duplicate_rows
    for row in json.loads(batch.preview_json):
        if db.scalar(select(Transaction.id).where(Transaction.fingerprint == row["fingerprint"])):
            duplicates += 1
            continue
        db.add(Transaction(
            account_id=batch.account_id, transaction_date=date.fromisoformat(row["transaction_date"]),
            posted_date=date.fromisoformat(row["posted_date"]) if row["posted_date"] else None,
            raw_description=row["raw_description"], normalized_merchant=row["normalized_merchant"],
            amount=row["amount"], direction=row["direction"], category=row["category"],
            classification=row["classification"], confidence=row["confidence"], source_file=batch.source_file,
            import_batch_id=batch.id, fingerprint=row["fingerprint"],
        ))
        committed += 1
    batch.status = "COMMITTED"
    batch.committed_rows = committed
    batch.duplicate_rows = duplicates
    batch.preview_json = "[]"
    db.commit()
    return {"batch_id": batch.id, "committed": committed, "duplicates": duplicates, "uncertain": batch.uncertain_rows, "status": batch.status}


@app.get("/api/imports")
def import_history(db: Session = Depends(get_db)):
    batches = db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc())).all()
    return [{
        "id": batch.id, "account_id": batch.account_id, "source_file": batch.source_file,
        "status": batch.status, "total_rows": batch.total_rows, "duplicate_rows": batch.duplicate_rows,
        "uncertain_rows": batch.uncertain_rows, "committed_rows": batch.committed_rows, "created_at": batch.created_at,
    } for batch in batches]


@app.get("/api/dashboard")
def dashboard(period: str = "this_month", start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    boundary = db.get(Setting, "post_job_start_date")
    post_job_start = date.fromisoformat(boundary.value) if boundary else date.today()
    start_date, end_date = date_bounds(period, start, end, post_job_start)
    return dashboard_payload(db, start_date, end_date)


@app.get("/api/net-worth")
def net_worth(db: Session = Depends(get_db)):
    payload = current_net_worth(db)
    payload["history"] = dashboard_payload(db, date(1900, 1, 1), date.today())["net_worth"]
    return payload


@app.get("/api/comparison")
def comparison(
    start_a: date, end_a: date, start_b: date, end_b: date,
    db: Session = Depends(get_db),
):
    def txs(start: date, end: date):
        return list(db.scalars(select(Transaction).where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)))
    a, b = txs(start_a, end_a), txs(start_b, end_b)
    totals_a, totals_b = financial_totals(a), financial_totals(b)
    categories = sorted({tx.category for tx in a + b if tx.classification == Classification.EXPENSE})
    def spend(rows, category):
        return sum(abs(tx.amount) for tx in rows if tx.classification == Classification.EXPENSE and tx.category == category and tx.amount < 0)
    return {
        "period_a": totals_a, "period_b": totals_b,
        "categories": [{"category": name, "period_a": round(spend(a, name), 2), "period_b": round(spend(b, name), 2)} for name in categories],
    }


@app.get("/api/recurring")
def recurring(db: Session = Depends(get_db)):
    transactions = list(db.scalars(select(Transaction).where(Transaction.classification == Classification.EXPENSE).order_by(Transaction.transaction_date)))
    groups: dict[str, list[Transaction]] = {}
    for tx in transactions:
        groups.setdefault(tx.normalized_merchant, []).append(tx)
    results = []
    for merchant, rows in groups.items():
        if len(rows) < 2:
            continue
        intervals = [(rows[i].transaction_date - rows[i - 1].transaction_date).days for i in range(1, len(rows))]
        avg_interval = sum(intervals) / len(intervals)
        frequency = "Monthly" if 25 <= avg_interval <= 35 else "Weekly" if 5 <= avg_interval <= 9 else "Yearly" if 340 <= avg_interval <= 390 else "Irregular"
        if frequency == "Irregular":
            continue
        avg_amount = sum(abs(tx.amount) for tx in rows) / len(rows)
        next_date = rows[-1].transaction_date.fromordinal(rows[-1].transaction_date.toordinal() + round(avg_interval))
        results.append({"merchant": merchant, "expected_amount": round(avg_amount, 2), "frequency": frequency, "last_charge": rows[-1].transaction_date, "next_estimated_charge": next_date, "category": rows[-1].category, "active": True})
    return results


@app.get("/api/rules")
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(Rule).order_by(Rule.priority.desc(), Rule.name)).all()


@app.post("/api/rules")
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    rule = Rule(**payload.model_dump(), user_created=True)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.get("/api/categories")
def categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.kind, Category.name)).all()


@app.put("/api/budgets/{month}")
def upsert_budget(month: str, payload: BudgetUpsert, db: Session = Depends(get_db)):
    budget = db.scalar(select(Budget).where(Budget.month == month))
    values = payload.model_dump(exclude={"category_targets", "month"})
    if budget:
        for key, value in values.items():
            setattr(budget, key, value)
        budget.category_targets_json = json.dumps(payload.category_targets)
    else:
        budget = Budget(month=month, **values, category_targets_json=json.dumps(payload.category_targets))
        db.add(budget)
    db.commit()
    return {"status": "saved", "month": month}


@app.get("/api/budgets/{month}")
def get_budget(month: str, db: Session = Depends(get_db)):
    budget = db.scalar(select(Budget).where(Budget.month == month))
    if not budget:
        return {
            "month": month, "spending_target": 0, "savings_target": 0,
            "investment_target": 0, "savings_rate_target": 0, "category_targets": {},
        }
    return {
        "month": budget.month, "spending_target": budget.spending_target,
        "savings_target": budget.savings_target, "investment_target": budget.investment_target,
        "savings_rate_target": budget.savings_rate_target,
        "category_targets": json.loads(budget.category_targets_json or "{}"),
    }


@app.get("/api/settings")
def settings(db: Session = Depends(get_db)):
    return {item.key: item.value for item in db.scalars(select(Setting))}


@app.put("/api/settings/{key}")
def update_setting(key: str, value: str, db: Session = Depends(get_db)):
    item = db.get(Setting, key)
    if item:
        item.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()
    return {"key": key, "value": value}


@app.get("/api/export/transactions.csv")
def export_transactions(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "account_id", "merchant", "description", "amount", "category", "classification", "notes"])
    for tx in db.scalars(select(Transaction).order_by(Transaction.transaction_date)):
        writer.writerow([tx.transaction_date, tx.account_id, tx.normalized_merchant, tx.raw_description, tx.amount, tx.category, tx.classification, tx.notes])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ember-transactions.csv"})


@app.get("/api/backup")
def backup_database():
    if not DATABASE_PATH.exists():
        raise HTTPException(404, "Database has not been created yet")
    return FileResponse(DATABASE_PATH, media_type="application/x-sqlite3", filename="ember-finance-backup.db")


@app.post("/api/backup/restore")
async def restore_database(file: UploadFile = File(...)):
    if not (file.filename or "").endswith((".db", ".sqlite", ".sqlite3")):
        raise HTTPException(400, "Choose a SQLite database backup")
    restore_path = DATABASE_PATH.with_suffix(".restore")
    with restore_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)
    with restore_path.open("rb") as source:
        if source.read(16) != b"SQLite format 3\x00":
            restore_path.unlink(missing_ok=True)
            raise HTTPException(400, "This file is not a valid SQLite database")
    backup_path = DATABASE_PATH.with_suffix(".before-restore.db")
    engine.dispose()
    if DATABASE_PATH.exists():
        shutil.copy2(DATABASE_PATH, backup_path)
    restore_path.replace(DATABASE_PATH)
    return {"status": "restored", "safety_backup": str(backup_path)}
