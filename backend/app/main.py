from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .analytics import (
    aggregate_metrics,
    calculate_month_metrics,
    category_totals,
    net_worth_group,
    net_worth_series,
    normalized,
)
from .database import Base, DATABASE_PATH, engine, get_db
from .models import (
    ExpenseEntry,
    IncomeEntry,
    NetWorthSnapshot,
    WealthFlowEntry,
    WorkbookState,
)
from .schemas import ImportCommit
from .workbook import ParsedWorkbook, parse_workbook


PREVIEWS: dict[str, ParsedWorkbook] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Ember Finance", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _available_months(
    incomes: list[IncomeEntry],
    expenses: list[ExpenseEntry],
    flows: list[WealthFlowEntry],
) -> list[str]:
    return sorted({row.month for row in [*incomes, *expenses, *flows]})


def _selected_months(
    available: list[str],
    period: str,
    start_month: str | None,
    end_month: str | None,
) -> list[str]:
    if not available:
        return []
    if period == "this_month":
        return available[-1:]
    if period == "last_month":
        return available[-2:-1] or available[-1:]
    if period == "last_3_months":
        return available[-3:]
    if period == "custom":
        if not start_month or not end_month:
            raise HTTPException(400, "Custom range needs a start and end month")
        if start_month > end_month:
            raise HTTPException(400, "Custom range start must be before its end")
        return [month for month in available if start_month <= month <= end_month]
    return available


def _expense_dict(row: ExpenseEntry) -> dict:
    return {
        "id": row.id,
        "month": row.month,
        "amount": round(row.amount, 2),
        "description": row.description,
        "category": row.category,
        "expense_tag": row.expense_tag,
    }


def _income_dict(row: IncomeEntry) -> dict:
    return {
        "id": row.id,
        "month": row.month,
        "amount": round(row.amount, 2),
        "description": row.description,
        "income_class": row.income_class,
    }


def _flow_dict(row: WealthFlowEntry) -> dict:
    return {
        "id": row.id,
        "month": row.month,
        "amount": round(row.amount, 2),
        "destination": row.destination,
        "flow_class": row.flow_class,
    }


def _insights(monthly: list[dict], expenses: list[ExpenseEntry]) -> list[str]:
    if not monthly:
        return []
    latest = monthly[-1]
    prior = monthly[-2] if len(monthly) > 1 else None
    latest_expenses = [row for row in expenses if row.month == latest["month"]]
    categories = category_totals(latest_expenses)
    insights: list[str] = []
    if categories:
        names = ", ".join(row["category"] for row in categories[:3])
        insights.append(f"Your largest categories this month are {names}.")
    insights.append(
        f"You added approximately ${latest['monthly_wealth_added']:,.0f} of new wealth this month."
    )
    irregular = sum(
        row.amount
        for row in latest_expenses
        if normalized(row.expense_tag) in {"one-time", "personal travel"}
    )
    if irregular:
        insights.append(
            f"${irregular:,.0f} of this month's spending was one-time or travel-related."
        )
    if prior:
        change = latest["wealth_building_rate"] - prior["wealth_building_rate"]
        direction = "increased" if change >= 0 else "decreased"
        insights.append(
            f"Your wealth-building rate {direction} from {prior['wealth_building_rate']:.1f}% to {latest['wealth_building_rate']:.1f}%."
        )
        current_categories = {row["category"]: row["value"] for row in categories}
        prior_categories = {
            row["category"]: row["value"]
            for row in category_totals(
                row for row in expenses if row.month == prior["month"]
            )
        }
        comparable = [
            (category, value, prior_categories.get(category, 0))
            for category, value in current_categories.items()
            if prior_categories.get(category, 0) > 0
        ]
        if comparable:
            category, current, before = max(
                comparable, key=lambda item: abs(item[1] - item[2])
            )
            percent = abs(current - before) / before * 100
            direction = "higher" if current >= before else "lower"
            insights.append(
                f"{category} spending is {percent:.0f}% {direction} than last month."
            )
    return insights[:5]


@app.get("/api/health")
def health():
    return {"status": "ok", "database": str(DATABASE_PATH)}


@app.get("/api/dashboard")
def dashboard(
    period: str = Query("this_month"),
    start_month: str | None = None,
    end_month: str | None = None,
    include_work_reimbursable: bool = False,
    include_one_time: bool = True,
    include_personal_travel: bool = True,
    db: Session = Depends(get_db),
):
    incomes = list(db.scalars(select(IncomeEntry).order_by(IncomeEntry.month, IncomeEntry.id)))
    expenses = list(db.scalars(select(ExpenseEntry).order_by(ExpenseEntry.month, ExpenseEntry.id)))
    flows = list(db.scalars(select(WealthFlowEntry).order_by(WealthFlowEntry.month, WealthFlowEntry.id)))
    snapshots = list(db.scalars(select(NetWorthSnapshot).order_by(NetWorthSnapshot.snapshot_date, NetWorthSnapshot.id)))
    available = _available_months(incomes, expenses, flows)
    selected = _selected_months(available, period, start_month, end_month)
    monthly_metrics = [
        calculate_month_metrics(month, incomes, expenses, flows) for month in available
    ]
    selected_metrics = [row for row in monthly_metrics if row.month in selected]
    selected_expenses = [row for row in expenses if row.month in selected]
    visible_expenses = [
        row
        for row in selected_expenses
        if (include_work_reimbursable or normalized(row.expense_tag) != "work/reimbursable")
        and (include_one_time or normalized(row.expense_tag) != "one-time")
        and (include_personal_travel or normalized(row.expense_tag) != "personal travel")
    ]
    state = db.get(WorkbookState, 1)
    net_worth = net_worth_series(snapshots)
    latest_date = max((row.snapshot_date for row in snapshots), default=None)
    latest_accounts = [row for row in snapshots if row.snapshot_date == latest_date]
    composition: dict[str, float] = {}
    for row in latest_accounts:
        group = net_worth_group(row.account, row.account_type)
        composition[group] = composition.get(group, 0) + row.value
    return {
        "metadata": {
            "workbook_name": state.workbook_name if state else None,
            "imported_at": state.imported_at.isoformat() if state else None,
            "available_months": available,
            "selected_months": selected,
        },
        "metrics": aggregate_metrics(selected_metrics),
        "average_core_spending": round(
            sum(row.core_spending for row in selected_metrics) / len(selected_metrics), 2
        ) if selected_metrics else 0,
        "monthly": [row.as_dict() for row in monthly_metrics],
        "categories": category_totals(visible_expenses),
        "category_trends": [
            {
                "month": month,
                **{
                    category: round(
                        sum(
                            row.amount
                            for row in expenses
                            if row.month == month and row.category == category
                        ),
                        2,
                    )
                    for category in sorted({row.category for row in expenses})
                },
            }
            for month in available
        ],
        "expenses": [_expense_dict(row) for row in visible_expenses],
        "all_expenses": [_expense_dict(row) for row in selected_expenses],
        "income": [_income_dict(row) for row in incomes if row.month in selected],
        "wealth_flows": [_flow_dict(row) for row in flows if row.month in selected],
        "net_worth": net_worth,
        "net_worth_accounts": [
            {
                "account": row.account,
                "account_type": row.account_type,
                "value": round(row.value, 2),
                "group": net_worth_group(row.account, row.account_type),
            }
            for row in latest_accounts
        ],
        "net_worth_composition": [
            {"group": group, "value": round(value, 2)}
            for group, value in sorted(composition.items(), key=lambda item: item[1], reverse=True)
        ],
        "current_net_worth": round(sum(row.value for row in latest_accounts), 2),
        "insights": _insights([row.as_dict() for row in monthly_metrics], expenses),
    }


@app.post("/api/imports/preview")
async def preview_import(file: UploadFile = File(...)):
    filename = file.filename or "budget.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Choose an .xlsx budgeting workbook")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "Workbook is larger than the 25 MB local import limit")
    token = uuid4().hex
    parsed = parse_workbook(content, filename)
    PREVIEWS[token] = parsed
    return parsed.preview(token)


@app.post("/api/imports/{token}/replace")
def replace_import(
    token: str,
    payload: ImportCommit,
    db: Session = Depends(get_db),
):
    parsed = PREVIEWS.get(token)
    if not parsed:
        raise HTTPException(404, "Import preview expired; choose the workbook again")
    preview = parsed.preview(token)
    if not preview["can_import"]:
        raise HTTPException(400, "Resolve workbook errors before importing")
    if not payload.replace_current_data:
        raise HTTPException(400, "Spreadsheet imports must replace current monthly data")

    db.execute(delete(IncomeEntry))
    db.execute(delete(ExpenseEntry))
    db.execute(delete(WealthFlowEntry))
    db.add_all(
        IncomeEntry(
            month=row.month,
            amount=row.amount,
            description=row.description,
            income_class=row.income_class,
        )
        for row in parsed.income
    )
    db.add_all(
        ExpenseEntry(
            month=row.month,
            amount=row.amount,
            description=row.description,
            category=row.category,
            expense_tag=row.expense_tag,
        )
        for row in parsed.expenses
    )
    db.add_all(
        WealthFlowEntry(
            month=row.month,
            amount=row.amount,
            destination=row.destination,
            flow_class=row.flow_class,
        )
        for row in parsed.wealth_flows
    )
    latest_snapshot = db.scalar(select(func.max(NetWorthSnapshot.snapshot_date)))
    new_net_worth = [
        row
        for row in parsed.net_worth
        if latest_snapshot is None or row.snapshot_date > latest_snapshot
    ]
    db.add_all(
        NetWorthSnapshot(
            snapshot_date=row.snapshot_date,
            account=row.account,
            account_type=row.account_type,
            value=row.value,
        )
        for row in new_net_worth
    )
    state = db.get(WorkbookState, 1)
    if state:
        state.workbook_name = parsed.workbook_name
        state.imported_at = datetime.now(UTC)
    else:
        db.add(
            WorkbookState(
                id=1,
                workbook_name=parsed.workbook_name,
                imported_at=datetime.now(UTC),
            )
        )
    db.commit()
    PREVIEWS.pop(token, None)
    return {
        "status": "imported",
        "months": parsed.detected_months,
        "income_entries": len(parsed.income),
        "expense_entries": len(parsed.expenses),
        "wealth_flow_entries": len(parsed.wealth_flows),
        "net_worth_snapshots_added": len(new_net_worth),
    }
