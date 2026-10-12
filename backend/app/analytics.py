from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models import ExpenseEntry, IncomeEntry, NetWorthSnapshot, WealthFlowEntry


RECURRING_INCOME_CLASSES = {"paycheck", "side income"}
CORE_EXCLUDED_TAGS = {"work/reimbursable", "one-time", "personal travel"}


def normalized(value: str) -> str:
    return " ".join(value.strip().lower().split())


@dataclass(frozen=True)
class MonthMetrics:
    month: str
    total_income: float
    recurring_income: float
    total_spending: float
    personal_spending: float
    core_spending: float
    cash_flow_surplus: float
    retirement_investing: float
    other_investing: float
    internal_transfers: float
    monthly_wealth_added: float
    wealth_building_rate: float

    def as_dict(self) -> dict:
        return {
            key: round(value, 2) if isinstance(value, float) else value
            for key, value in vars(self).items()
        }


def calculate_month_metrics(
    month: str,
    incomes: Iterable[IncomeEntry],
    expenses: Iterable[ExpenseEntry],
    flows: Iterable[WealthFlowEntry],
) -> MonthMetrics:
    month_incomes = [row for row in incomes if row.month == month]
    month_expenses = [row for row in expenses if row.month == month]
    month_flows = [row for row in flows if row.month == month]
    total_income = sum(abs(row.amount) for row in month_incomes)
    recurring_income = sum(
        abs(row.amount)
        for row in month_incomes
        if normalized(row.income_class) in RECURRING_INCOME_CLASSES
    )
    total_spending = sum(abs(row.amount) for row in month_expenses)
    work_spending = sum(
        abs(row.amount)
        for row in month_expenses
        if normalized(row.expense_tag) == "work/reimbursable"
    )
    personal_spending = total_spending - work_spending
    core_spending = sum(
        abs(row.amount)
        for row in month_expenses
        if normalized(row.expense_tag) not in CORE_EXCLUDED_TAGS
    )
    retirement_investing = sum(
        abs(row.amount)
        for row in month_flows
        if normalized(row.flow_class) == "retirement investment"
    )
    other_investing = sum(
        abs(row.amount)
        for row in month_flows
        if normalized(row.flow_class) == "investment"
    )
    internal_transfers = sum(
        abs(row.amount)
        for row in month_flows
        if normalized(row.flow_class) == "internal transfer"
    )
    cash_flow_surplus = total_income - personal_spending
    monthly_wealth_added = (
        recurring_income
        - personal_spending
        + retirement_investing
        + other_investing
    )
    denominator = recurring_income + retirement_investing
    wealth_building_rate = monthly_wealth_added / denominator * 100 if denominator else 0
    return MonthMetrics(
        month,
        total_income,
        recurring_income,
        total_spending,
        personal_spending,
        core_spending,
        cash_flow_surplus,
        retirement_investing,
        other_investing,
        internal_transfers,
        monthly_wealth_added,
        wealth_building_rate,
    )


def aggregate_metrics(metrics: list[MonthMetrics]) -> dict:
    if not metrics:
        return MonthMetrics("", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0).as_dict()
    values = {
        key: sum(getattr(row, key) for row in metrics)
        for key in (
            "total_income",
            "recurring_income",
            "total_spending",
            "personal_spending",
            "core_spending",
            "cash_flow_surplus",
            "retirement_investing",
            "other_investing",
            "internal_transfers",
            "monthly_wealth_added",
        )
    }
    denominator = values["recurring_income"] + values["retirement_investing"]
    values["wealth_building_rate"] = (
        values["monthly_wealth_added"] / denominator * 100 if denominator else 0
    )
    values["month"] = metrics[-1].month
    return {
        key: round(value, 2) if isinstance(value, float) else value
        for key, value in values.items()
    }


def category_totals(expenses: Iterable[ExpenseEntry]) -> list[dict]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for row in expenses:
        totals[row.category] += abs(row.amount)
        counts[row.category] += 1
    grand_total = sum(totals.values())
    return [
        {
            "category": category,
            "value": round(value, 2),
            "percentage": round(value / grand_total * 100, 1) if grand_total else 0,
            "count": counts[category],
        }
        for category, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def net_worth_group(account: str, account_type: str) -> str:
    text = normalized(f"{account} {account_type}")
    if "roth" in text:
        return "Roth IRA"
    if "hsa" in text:
        return "HSA"
    if "401" in text:
        return "401(k)"
    if any(token in text for token in ("cash", "checking", "saving", "hysa")):
        return "Cash"
    return "Taxable Investments"


def net_worth_series(snapshots: Iterable[NetWorthSnapshot]) -> list[dict]:
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in snapshots:
        date_key = row.snapshot_date.isoformat()
        group = net_worth_group(row.account, row.account_type)
        grouped[date_key][group] += row.value
        grouped[date_key]["total"] += row.value
    return [
        {"date": date_key, **{key: round(value, 2) for key, value in values.items()}}
        for date_key, values in sorted(grouped.items())
    ]
