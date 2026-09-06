from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    name: str
    type: str
    institution: str = ""
    last_four: str | None = Field(default=None, max_length=4)
    current_balance: float = 0
    balance_mode: str = "TRANSACTION_DERIVED"
    active: bool = True
    save_snapshot: bool = True


class AccountRead(OrmModel):
    id: int
    name: str
    type: str
    institution: str
    last_four: str | None
    current_balance: float
    balance_mode: str
    active: bool
    created_at: datetime


class TransactionRead(OrmModel):
    id: int
    account_id: int
    transaction_date: date
    posted_date: date | None
    raw_description: str
    normalized_merchant: str
    amount: float
    direction: str
    category: str
    classification: str
    confidence: float
    notes: str
    manually_reviewed: bool
    source_file: str
    import_batch_id: str | None


class TransactionUpdate(BaseModel):
    normalized_merchant: str | None = None
    category: str | None = None
    classification: str | None = None
    notes: str | None = None
    manually_reviewed: bool = True
    create_rule: bool = False
    rule_pattern: str | None = None


class RuleCreate(BaseModel):
    name: str
    pattern: str
    merchant: str | None = None
    category: str
    classification: str
    priority: int = 100
    active: bool = True


class BudgetUpsert(BaseModel):
    month: str
    spending_target: float
    savings_target: float = 0
    investment_target: float = 0
    savings_rate_target: float = 0
    category_targets: dict[str, float] = {}


class SnapshotCreate(BaseModel):
    balance: float
    snapshot_date: date = Field(default_factory=date.today)

