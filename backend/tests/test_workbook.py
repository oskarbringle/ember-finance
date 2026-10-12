from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.analytics import calculate_month_metrics, category_totals
from app.database import Base
from app.main import PREVIEWS, replace_import
from app.models import ExpenseEntry, IncomeEntry, NetWorthSnapshot, WealthFlowEntry
from app.schemas import ImportCommit
from app.workbook import parse_workbook
from workbook_fixture import realistic_workbook


def test_workbook_parser_detects_month_tabs_and_all_sections():
    parsed = parse_workbook(realistic_workbook(), "Budget.xlsx")
    assert parsed.detected_months == ["2026-08", "2026-09"]
    assert len(parsed.income) == 4
    assert len(parsed.expenses) == 10
    assert len(parsed.wealth_flows) == 6
    assert len(parsed.net_worth) == 6
    assert parsed.preview("test")["can_import"] is True


def test_future_month_tabs_need_no_code_change():
    parsed = parse_workbook(
        realistic_workbook(months=("October", "November", "December")),
        "Future.xlsx",
    )
    assert parsed.detected_months == ["2026-10", "2026-11", "2026-12"]


def test_category_aggregation():
    rows = [
        ExpenseEntry(month="2026-09", amount=50, description="A", category="Dining"),
        ExpenseEntry(month="2026-09", amount=25, description="B", category="Dining"),
        ExpenseEntry(month="2026-09", amount=25, description="C", category="Groceries"),
    ]
    categories = category_totals(rows)
    assert categories[0] == {
        "category": "Dining",
        "value": 75,
        "percentage": 75,
        "count": 2,
    }


def test_financial_definitions_exclude_transfers_reimbursements_and_irregular_spending():
    incomes = [
        IncomeEntry(month="2026-09", amount=4000, description="Pay", income_class="Paycheck"),
        IncomeEntry(month="2026-09", amount=200, description="Side", income_class="Side Income"),
        IncomeEntry(month="2026-09", amount=85, description="Client", income_class="Reimbursement"),
    ]
    expenses = [
        ExpenseEntry(month="2026-09", amount=1500, description="Rent", category="Housing", expense_tag=""),
        ExpenseEntry(month="2026-09", amount=85, description="Client", category="Work Meals", expense_tag="Work/Reimbursable"),
        ExpenseEntry(month="2026-09", amount=300, description="Desk", category="Shopping & Home", expense_tag="One-time"),
        ExpenseEntry(month="2026-09", amount=120, description="Trip", category="Travel", expense_tag="Personal Travel"),
    ]
    flows = [
        WealthFlowEntry(month="2026-09", amount=500, destination="401(k)", flow_class="Retirement Investment"),
        WealthFlowEntry(month="2026-09", amount=300, destination="Roth", flow_class="Investment"),
        WealthFlowEntry(month="2026-09", amount=1000, destination="HYSA", flow_class="Internal Transfer"),
    ]
    metrics = calculate_month_metrics("2026-09", incomes, expenses, flows)
    assert metrics.recurring_income == 4200
    assert metrics.personal_spending == 1920
    assert metrics.core_spending == 1500
    assert metrics.internal_transfers == 1000
    assert metrics.monthly_wealth_added == 3080
    assert round(metrics.wealth_building_rate, 2) == round(3080 / 4700 * 100, 2)


def test_reimport_replaces_monthly_data_and_deduplicates_net_worth():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    parsed = parse_workbook(realistic_workbook(), "Budget.xlsx")
    with Session(engine) as db:
        PREVIEWS["first"] = parsed
        first = replace_import("first", ImportCommit(), db)
        PREVIEWS["second"] = parsed
        second = replace_import("second", ImportCommit(), db)
        assert first["net_worth_snapshots_added"] == 6
        assert second["net_worth_snapshots_added"] == 0
        assert db.scalar(select(func.count(IncomeEntry.id))) == 4
        assert db.scalar(select(func.count(ExpenseEntry.id))) == 10
        assert db.scalar(select(func.count(WealthFlowEntry.id))) == 6
        assert db.scalar(select(func.count(NetWorthSnapshot.id))) == 6


def test_malformed_rows_have_sheet_row_and_reason():
    parsed = parse_workbook(realistic_workbook(malformed=True), "Broken.xlsx")
    issue = next(
        issue
        for issue in parsed.issues
        if issue.sheet == "August" and "category" in issue.message
    )
    assert issue.row == 5
    assert "category" in issue.message
    assert parsed.preview("test")["can_import"] is False
