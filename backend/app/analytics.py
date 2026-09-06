from __future__ import annotations

import json
from calendar import monthrange
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Account, BalanceSnapshot, Budget, Classification, Transaction


def date_bounds(period: str, start: date | None = None, end: date | None = None, post_job_start: date | None = None) -> tuple[date, date]:
    post_job_start = post_job_start or date.today()
    today = date.today()
    if start and end:
        return start, end
    if period == "last_month":
        first = today.replace(day=1)
        last_month_end = first.fromordinal(first.toordinal() - 1)
        return last_month_end.replace(day=1), last_month_end
    if period == "ytd":
        return today.replace(month=1, day=1), today
    if period == "pre_job":
        return date(1900, 1, 1), date.fromordinal(post_job_start.toordinal() - 1)
    if period == "post_job":
        return post_job_start, today
    return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])


def financial_totals(transactions: list[Transaction]) -> dict[str, float]:
    expense = sum(abs(tx.amount) for tx in transactions if tx.classification == Classification.EXPENSE and tx.amount < 0)
    refunds = sum(tx.amount for tx in transactions if tx.classification in (Classification.REFUND, Classification.REIMBURSEMENT) and tx.amount > 0)
    income = sum(tx.amount for tx in transactions if tx.classification == Classification.INCOME and tx.amount > 0)
    saved = sum(abs(tx.amount) for tx in transactions if tx.classification == Classification.SAVING and tx.amount < 0)
    invested = sum(abs(tx.amount) for tx in transactions if tx.classification == Classification.INVESTMENT and tx.amount < 0)
    spending = max(expense - refunds, 0)
    savings_rate = ((saved + invested) / income * 100) if income else 0
    return {
        "income": round(income, 2),
        "spending": round(spending, 2),
        "saved": round(saved, 2),
        "invested": round(invested, 2),
        "surplus": round(income - spending - saved - invested, 2),
        "savings_rate": round(savings_rate, 1),
        "refunds_and_reimbursements": round(refunds, 2),
    }


def dashboard_payload(db: Session, start: date, end: date) -> dict:
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        )
    )
    totals = financial_totals(transactions)
    month_key = end.strftime("%Y-%m")
    budget = db.scalar(select(Budget).where(Budget.month == month_key))
    budget_target = budget.spending_target if budget else 0
    budget_remaining = round(budget_target - totals["spending"], 2)
    totals["budget_target"] = budget_target
    totals["budget_remaining"] = budget_remaining
    totals["investable_surplus"] = max(budget_remaining, 0)

    category_totals: dict[str, float] = defaultdict(float)
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0, "spending": 0, "saving": 0, "investing": 0})
    for tx in transactions:
        month = tx.transaction_date.strftime("%b")
        if tx.classification == Classification.EXPENSE and tx.amount < 0:
            category_totals[tx.category] += abs(tx.amount)
            monthly[month]["spending"] += abs(tx.amount)
        elif tx.classification in (Classification.REFUND, Classification.REIMBURSEMENT) and tx.amount > 0:
            category_totals[tx.category] -= tx.amount
            monthly[month]["spending"] -= tx.amount
        elif tx.classification == Classification.INCOME and tx.amount > 0:
            monthly[month]["income"] += tx.amount
        elif tx.classification == Classification.SAVING:
            monthly[month]["saving"] += abs(tx.amount)
        elif tx.classification == Classification.INVESTMENT:
            monthly[month]["investing"] += abs(tx.amount)

    snapshots = list(db.scalars(select(BalanceSnapshot).order_by(BalanceSnapshot.snapshot_date)))
    accounts = {account.id: account for account in db.scalars(select(Account))}
    net_worth_by_date: dict[str, float] = defaultdict(float)
    for snapshot in snapshots:
        account = accounts.get(snapshot.account_id)
        if not account:
            continue
        signed = -abs(snapshot.balance) if account.type == "CREDIT_CARD" else snapshot.balance
        net_worth_by_date[snapshot.snapshot_date.isoformat()] += signed

    category_targets = json.loads(budget.category_targets_json) if budget else {}
    budget_categories = [
        {"category": name, "spent": round(max(category_totals.get(name, 0), 0), 2), "target": target}
        for name, target in category_targets.items()
    ]
    return {
        "range": {"start": start, "end": end},
        "totals": totals,
        "categories": [
            {"name": name, "value": round(max(value, 0), 2)}
            for name, value in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
            if value > 0
        ],
        "monthly": [{"month": key, **{k: round(v, 2) for k, v in values.items()}} for key, values in monthly.items()],
        "net_worth": [{"date": key, "value": round(value, 2)} for key, value in net_worth_by_date.items()],
        "budget_categories": budget_categories,
        "recent_transactions": transactions[:8],
        "review_count": sum(1 for tx in transactions if tx.classification == Classification.UNKNOWN or tx.confidence < 0.6),
    }


def current_net_worth(db: Session) -> dict:
    accounts = list(db.scalars(select(Account).where(Account.active.is_(True))))
    cash = sum(account.current_balance for account in accounts if account.type in ("CHECKING", "SAVINGS"))
    investments = sum(account.current_balance for account in accounts if account.type in ("BROKERAGE", "RETIREMENT"))
    other = sum(account.current_balance for account in accounts if account.type == "OTHER_ASSET")
    liabilities = sum(abs(account.current_balance) for account in accounts if account.type == "CREDIT_CARD")
    return {
        "current_net_worth": round(cash + investments + other - liabilities, 2),
        "cash": round(cash, 2),
        "investments": round(investments, 2),
        "other": round(other, 2),
        "liabilities": round(liabilities, 2),
    }
