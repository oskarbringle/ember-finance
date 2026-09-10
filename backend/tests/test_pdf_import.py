from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.classification import transaction_fingerprint
from app.database import Base
from app.models import Account, Category, Transaction
from app.parsers import PdfStatementParser
from app.parsers.pdf_statement import OcrObservation
from app.sample_data import initialize_reference_data


def statement_pdf(lines: list[str]) -> BytesIO:
    output = BytesIO()
    document = canvas.Canvas(output)
    y = 760
    for line in lines:
        document.drawString(54, y, line)
        y -= 22
    document.save()
    output.seek(0)
    return output


def test_chase_credit_card_pdf_uses_purchase_and_payment_signs():
    pdf = statement_pdf([
        "CHASE CARDMEMBER SERVICES",
        "Statement Date: 08/31/2026",
        "ACCOUNT ACTIVITY",
        "08/01 08/02 PUBLIX #1061 80.00",
        "08/03 08/04 PAYMENT THANK YOU -1,200.00",
        "08/05 08/06 AMAZON RETURN -36.25",
    ])
    parser = PdfStatementParser()
    rows = parser.parse(pdf, account_type="CREDIT_CARD")
    assert parser.provider == "chase_credit_card_pdf"
    assert [row.amount for row in rows] == [-80, 1200, 36.25]
    assert rows[0].transaction_date.isoformat() == "2026-08-01"
    assert rows[0].posted_date.isoformat() == "2026-08-02"
    assert parser.last_report["confidence"] == "high"
    assert parser.last_report["inflows"] == 1236.25
    assert parser.last_report["outflows"] == 80
    assert parser.last_report["net"] == 1156.25


def test_chase_card_layout_handles_signed_payments_and_leading_decimal_fees():
    pdf = statement_pdf([
        "CHASE CARDMEMBER SERVICES",
        "Statement Date: 01/25/2026",
        "ACCOUNT ACTIVITY",
        "Date of Transaction Merchant Name or Transaction Description $ Amount",
        "01/22 AUTOMATIC PAYMENT - THANK YOU -425.38",
        "01/02 FOREIGN TRANSACTION FEE .09",
        "01/14 TOTAL WINE AND MORE 35.11",
        "01/02 YEN",
        "510 X 0.006411764 (EXCHG RATE)",
    ])
    rows = PdfStatementParser().parse(pdf, account_type="CREDIT_CARD")
    assert [(row.description, row.amount) for row in rows] == [
        ("AUTOMATIC PAYMENT - THANK YOU", 425.38),
        ("FOREIGN TRANSACTION FEE", -0.09),
        ("TOTAL WINE AND MORE", -35.11),
    ]


def test_chase_bank_ocr_uses_table_coordinates_and_statement_signs():
    observations = [
        OcrObservation(1, 0.45, 0.95, 0.3, 0.01, "December 20, 2025 through January 23, 2026"),
        OcrObservation(1, 0.07, 0.80, 0.04, 0.01, "12/22"),
        OcrObservation(1, 0.16, 0.80, 0.3, 0.01, "PAYROLL DEPOSIT"),
        OcrObservation(1, 0.70, 0.80, 0.06, 0.01, "75.00"),
        OcrObservation(1, 0.84, 0.80, 0.06, 0.01, "900.00"),
        OcrObservation(1, 0.07, 0.72, 0.04, 0.01, "01/02"),
        OcrObservation(1, 0.16, 0.72, 0.3, 0.01, "CARD PURCHASE"),
        OcrObservation(1, 0.16, 0.70, 0.3, 0.01, "LOCAL MARKET"),
        OcrObservation(1, 0.70, 0.72, 0.06, 0.01, "-12.50"),
        OcrObservation(1, 0.84, 0.72, 0.06, 0.01, "887.50"),
    ]
    parser = PdfStatementParser()
    rows = parser._parse_chase_bank_ocr(observations, None)
    assert [(row.transaction_date.isoformat(), row.amount) for row in rows] == [
        ("2025-12-22", 75.0),
        ("2026-01-02", -12.5),
    ]
    assert rows[1].description == "CARD PURCHASE LOCAL MARKET"


def test_repeated_identical_transactions_receive_stable_distinct_fingerprints():
    transaction_date = date(2026, 8, 14)
    first = transaction_fingerprint(1, transaction_date, -35.11, "TOTAL WINE")
    repeated = transaction_fingerprint(1, transaction_date, -35.11, "TOTAL WINE", 1)
    assert first != repeated


def test_chase_bank_pdf_uses_statement_sections_for_signs():
    pdf = statement_pdf([
        "JPMORGAN CHASE BANK",
        "Statement Date: 09/30/2026",
        "DEPOSITS AND ADDITIONS",
        "09/01 ADP PAYROLL DIRECT DEP 4,000.00",
        "ELECTRONIC WITHDRAWALS",
        "09/02 PUBLIX #1061 80.00",
        "09/03 TRANSFER TO SAVINGS 1,000.00",
    ])
    parser = PdfStatementParser()
    rows = parser.parse(pdf, account_type="CHECKING")
    assert parser.provider == "chase_bank_pdf"
    assert [row.amount for row in rows] == [4000, -80, -1000]


def test_generic_pdf_supports_named_and_iso_dates_with_debit_credit_suffixes():
    pdf = statement_pdf([
        "Statement Date: 09/30/2026",
        "Sep 01 ACME MARKET 42.18 DR",
        "2026-09-02 EMPLOYER PAYROLL 2,500.00 CR",
    ])
    rows = PdfStatementParser().parse(pdf, account_type="CHECKING")
    assert [row.transaction_date.isoformat() for row in rows] == [
        "2026-09-01",
        "2026-09-02",
    ]
    assert [row.amount for row in rows] == [-42.18, 2500]


def test_generic_pdf_combines_wrapped_transaction_rows():
    pdf = statement_pdf([
        "Statement Date: 09/30/2026",
        "09/03/2026 09/04/2026 LOCAL HARDWARE STORE",
        "DOWNTOWN LOCATION 18.75",
    ])
    rows = PdfStatementParser().parse(pdf, account_type="CHECKING")
    assert len(rows) == 1
    assert rows[0].posted_date.isoformat() == "2026-09-04"
    assert rows[0].description == "LOCAL HARDWARE STORE DOWNTOWN LOCATION"
    assert rows[0].amount == -18.75


def test_generic_pdf_defaults_unsigned_non_income_rows_to_outflows():
    pdf = statement_pdf([
        "Statement Date: 09/30/2026",
        "09/05 CORNER MARKET 27.40",
    ])
    rows = PdfStatementParser().parse(pdf, account_type="CHECKING")
    assert rows[0].amount == -27.40


def test_blank_scanned_pdf_gives_local_ocr_guidance():
    pdf = statement_pdf([])
    with pytest.raises(ValueError, match="scanned PDF"):
        PdfStatementParser().parse(pdf, account_type="CHECKING")


def test_fresh_database_has_reference_categories_but_no_financial_data():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        initialize_reference_data(db)
        assert db.scalar(select(func.count(Category.id))) > 0
        assert db.scalar(select(func.count(Account.id))) == 0
        assert db.scalar(select(func.count(Transaction.id))) == 0
