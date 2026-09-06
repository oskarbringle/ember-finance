from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class AccountType(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    BROKERAGE = "BROKERAGE"
    RETIREMENT = "RETIREMENT"
    OTHER_ASSET = "OTHER_ASSET"


class Classification(StrEnum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    CREDIT_CARD_PAYMENT = "CREDIT_CARD_PAYMENT"
    SAVING = "SAVING"
    INVESTMENT = "INVESTMENT"
    REFUND = "REFUND"
    REIMBURSEMENT = "REIMBURSEMENT"
    UNKNOWN = "UNKNOWN"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(32), index=True)
    institution: Mapped[str] = mapped_column(String(120), default="")
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    current_balance: Mapped[float] = mapped_column(Float, default=0)
    balance_mode: Mapped[str] = mapped_column(String(24), default="TRANSACTION_DERIVED")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
    snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_transaction_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_description: Mapped[str] = mapped_column(Text)
    normalized_merchant: Mapped[str] = mapped_column(String(180), index=True)
    amount: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(80), index=True)
    classification: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    manually_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    source_file: Mapped[str] = mapped_column(String(255), default="")
    import_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    account: Mapped[Account] = relationship(back_populates="transactions")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    pattern: Mapped[str] = mapped_column(String(220), index=True)
    merchant: Mapped[str | None] = mapped_column(String(180), nullable=True)
    category: Mapped[str] = mapped_column(String(80))
    classification: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_created: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(24), default="EXPENSE")
    color: Mapped[str] = mapped_column(String(12), default="#8A918A")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    spending_target: Mapped[float] = mapped_column(Float, default=0)
    savings_target: Mapped[float] = mapped_column(Float, default=0)
    investment_target: Mapped[float] = mapped_column(Float, default=0)
    savings_rate_target: Mapped[float] = mapped_column(Float, default=0)
    category_targets_json: Mapped[str] = mapped_column(Text, default="{}")


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (UniqueConstraint("account_id", "snapshot_date", name="uq_balance_snapshot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    balance: Mapped[float] = mapped_column(Float)
    account: Mapped[Account] = relationship(back_populates="snapshots")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    source_file: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="PREVIEW")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    uncertain_rows: Mapped[int] = mapped_column(Integer, default=0)
    committed_rows: Mapped[int] = mapped_column(Integer, default=0)
    preview_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
