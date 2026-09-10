from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category, Setting


CATEGORY_COLORS = {
    "Housing": "#3F5E52",
    "Groceries": "#DB8B59",
    "Dining": "#E5B75C",
    "Bars & Nightlife": "#9D7A70",
    "Gas & Fuel": "#B8845B",
    "Transportation": "#739A8C",
    "Travel": "#8A86A8",
    "Shopping": "#C58D86",
    "Entertainment": "#7286A0",
    "Health & Fitness": "#7C9B74",
    "Subscriptions": "#A98268",
    "Gifts": "#A37F9B",
    "Fees": "#89786B",
    "Miscellaneous": "#8A918A",
}


def initialize_reference_data(db: Session) -> None:
    """Create only generic reference data; never create accounts or transactions."""
    existing_categories = set(db.scalars(select(Category.name)))
    for name, color in CATEGORY_COLORS.items():
        if name not in existing_categories:
            db.add(Category(name=name, kind="EXPENSE", color=color))
    for name in (
        "Salary",
        "Bonus",
        "Side Income",
        "Refund",
        "Reimbursement",
        "Savings Transfer",
        "Investment Contribution",
        "Internal Transfer",
        "Credit Card Payment",
    ):
        if name not in existing_categories:
            db.add(Category(name=name, kind="NON_EXPENSE", color="#8A918A"))
    if not db.get(Setting, "post_job_start_date"):
        db.add(Setting(key="post_job_start_date", value=date.today().isoformat()))
    db.commit()
