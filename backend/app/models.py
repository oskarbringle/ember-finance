from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class IncomeEntry(Base):
    __tablename__ = "income_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(240))
    income_class: Mapped[str] = mapped_column(String(80), index=True)


class ExpenseEntry(Base):
    __tablename__ = "expense_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(80), index=True)
    expense_tag: Mapped[str] = mapped_column(String(80), default="", index=True)


class WealthFlowEntry(Base):
    __tablename__ = "wealth_flow_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    amount: Mapped[float] = mapped_column(Float)
    destination: Mapped[str] = mapped_column(String(240))
    flow_class: Mapped[str] = mapped_column(String(80), index=True)


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots_v2"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "account", name="uq_net_worth_date_account"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    account: Mapped[str] = mapped_column(String(160))
    account_type: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[float] = mapped_column(Float)


class WorkbookState(Base):
    __tablename__ = "workbook_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    workbook_name: Mapped[str] = mapped_column(String(255))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
