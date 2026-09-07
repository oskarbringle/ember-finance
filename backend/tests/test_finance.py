from __future__ import annotations

import io
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics import dashboard_payload, financial_totals
from app.classification import classify_transaction, transaction_fingerprint
from app.database import Base
from app.main import update_account
from app.models import Account, Budget, Classification, Transaction
from app.parsers import GenericCsvParser
from app.schemas import AccountCreate


def parsed_tx(account_id: int, tx_date: date, description: str, amount: float) -> Transaction:
    result = classify_transaction(description, amount)
    return Transaction(
        account_id=account_id, transaction_date=tx_date, raw_description=description,
        normalized_merchant=result.merchant, amount=amount, direction="CREDIT" if amount > 0 else "DEBIT",
        category=result.category, classification=result.classification, confidence=result.confidence,
        fingerprint=transaction_fingerprint(account_id, tx_date, amount, description),
    )


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_csv_parser_supports_debit_and_credit_columns():
    source = io.BytesIO(b"Date,Description,Debit,Credit\n09/05/2026,Publix,80,\n09/01/2026,Payroll,,4000\n")
    rows = GenericCsvParser().parse(source, account_type="CHECKING")
    assert rows[0].amount == -80
    assert rows[1].amount == 4000


def test_csv_parser_supports_credit_card_positive_charge_convention():
    source = io.BytesIO(b"Date,Description,Amount\n09/05/2026,Publix,80\n")
    rows = GenericCsvParser().parse(source, account_type="CREDIT_CARD", sign_convention="positive_outflow")
    assert rows[0].amount == -80


def test_deterministic_fingerprint_and_database_deduplication(db: Session):
    account = Account(name="Checking", type="CHECKING", institution="Chase")
    db.add(account); db.flush()
    first = parsed_tx(account.id, date(2026, 9, 5), "PUBLIX #1061", -80)
    second = parsed_tx(account.id, date(2026, 9, 5), "PUBLIX #1061", -80)
    assert first.fingerprint == second.fingerprint
    db.add(first); db.commit(); db.add(second)
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize(("description", "amount", "expected"), [
    ("CHASE CREDIT CARD PAYMENT", -1200, Classification.CREDIT_CARD_PAYMENT),
    ("ACH XFER TO CHECKING", -100, Classification.TRANSFER),
    ("TRANSFER TO SAVINGS", -1000, Classification.SAVING),
    ("FIDELITY BROKERAGE CONTRIBUTION", -500, Classification.INVESTMENT),
    ("AMAZON RETURN REFUND", 50, Classification.REFUND),
    ("VENMO DINNER REIMBURSEMENT", 40, Classification.REIMBURSEMENT),
])
def test_classification_rules(description: str, amount: float, expected: Classification):
    assert classify_transaction(description, amount).classification == expected


def test_zelle_without_context_is_sent_to_review():
    result = classify_transaction("ZELLE JOHN SMITH", -1505)
    assert result.classification == Classification.UNKNOWN
    assert result.confidence < 0.6


def test_zelle_rent_is_housing_expense():
    result = classify_transaction("ZELLE RENT LANDLORD", -1505)
    assert result.classification == Classification.EXPENSE
    assert result.category == "Housing"


def test_core_accounting_has_no_double_counting():
    rows = [
        parsed_tx(1, date(2026, 9, 5), "PUBLIX #1061", -80),
        parsed_tx(1, date(2026, 9, 2), "ZELLE RENT LANDLORD", -1505),
        parsed_tx(1, date(2026, 9, 4), "CHASE CREDIT CARD PAYMENT", -1200),
        parsed_tx(1, date(2026, 9, 3), "TRANSFER TO SAVINGS", -1000),
        parsed_tx(1, date(2026, 9, 1), "ADP PAYROLL DIRECT DEP", 4000),
    ]
    totals = financial_totals(rows)
    assert totals["spending"] == 1585
    assert totals["saved"] == 1000
    assert totals["income"] == 4000
    assert totals["savings_rate"] == 25


def test_refund_and_reimbursement_offset_spending_not_income():
    rows = [
        parsed_tx(1, date(2026, 9, 1), "RESTAURANT PURCHASE", -100),
        parsed_tx(1, date(2026, 9, 2), "RESTAURANT REFUND", 20),
        parsed_tx(1, date(2026, 9, 3), "VENMO DINNER REIMBURSEMENT", 30),
        parsed_tx(1, date(2026, 9, 4), "PAYROLL", 1000),
    ]
    totals = financial_totals(rows)
    assert totals["spending"] == 50
    assert totals["income"] == 1000


def test_budget_surplus_calculation(db: Session):
    account = Account(name="Checking", type="CHECKING", institution="Chase")
    db.add(account); db.flush()
    db.add(Budget(month="2026-09", spending_target=3500))
    db.add_all([
        parsed_tx(account.id, date(2026, 9, 1), "PAYROLL", 4000),
        parsed_tx(account.id, date(2026, 9, 2), "PUBLIX", -3100),
    ])
    db.commit()
    result = dashboard_payload(db, date(2026, 9, 1), date(2026, 9, 30))
    assert result["totals"]["budget_remaining"] == 400
    assert result["totals"]["investable_surplus"] == 400


def test_account_details_can_be_edited(db: Session):
    account = Account(name="Old name", type="CHECKING", institution="Bank")
    db.add(account)
    db.commit()
    db.refresh(account)

    updated = update_account(
        account.id,
        AccountCreate(
            name="Household checking",
            type="CHECKING",
            institution="Local credit union",
            last_four="4321",
            current_balance=825.50,
            balance_mode="TRANSACTION_DERIVED",
            active=True,
        ),
        db,
    )

    assert updated.name == "Household checking"
    assert updated.institution == "Local credit union"
    assert updated.last_four == "4321"
    assert updated.current_balance == 825.50
