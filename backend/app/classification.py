from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date

from .models import Classification


@dataclass(frozen=True)
class ClassificationResult:
    merchant: str
    category: str
    classification: str
    confidence: float


MERCHANT_RULES = [
    (r"AMAZON\s+PRIME|AMZN\s+PRIME", "Amazon Prime"),
    (r"AMAZON|AMZN\s*MKT", "Amazon"),
    (r"PUBLIX", "Publix"),
    (r"ALDI", "Aldi"),
    (r"UBER\s*\*?\s*EATS", "Uber Eats"),
    (r"LYFT", "Lyft"),
    (r"TRADER JOE", "Trader Joe's"),
    (r"WHOLEFDS|WHOLE FOODS", "Whole Foods"),
    (r"NETFLIX", "Netflix"),
    (r"SPOTIFY", "Spotify"),
    (r"EQUINOX", "Equinox"),
]


def clean_description(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def normalize_merchant(description: str) -> str:
    cleaned = clean_description(description)
    for pattern, merchant in MERCHANT_RULES:
        if re.search(pattern, cleaned):
            return merchant
    cleaned = re.sub(r"\b(POS|DEBIT|PURCHASE|ACH|ONLINE|CHECKCARD|CARD)\b", "", cleaned)
    cleaned = re.sub(r"[#*]\w+", "", cleaned)
    cleaned = re.sub(r"\b\d{4,}\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip().title() or "Unknown merchant"


def classify_transaction(description: str, amount: float, user_rules: list[dict] | None = None) -> ClassificationResult:
    text = clean_description(description)
    merchant = normalize_merchant(description)

    for rule in sorted(user_rules or [], key=lambda row: row.get("priority", 100), reverse=True):
        if rule.get("active", True) and re.search(rule["pattern"], text, re.IGNORECASE):
            return ClassificationResult(
                rule.get("merchant") or merchant,
                rule["category"],
                rule["classification"],
                0.99,
            )

    if re.search(r"CHASE.*(CARD|CREDIT).*PAY|CREDIT CARD PAYMENT|AUTOPAY.*CARD|PAYMENT THANK YOU|AUTOMATIC PAYMENT", text):
        return ClassificationResult("Chase Card Payment", "Credit Card Payment", Classification.CREDIT_CARD_PAYMENT, 0.98)
    if re.search(r"TRANSFER.*(SAV|HYSA)|TO SAVINGS", text):
        return ClassificationResult("Savings Transfer", "Savings Transfer", Classification.SAVING, 0.98)
    if re.search(r"VANGUARD|FIDELITY|SCHWAB|ROBINHOOD|BROKERAGE CONTRIBUTION", text) and amount < 0:
        return ClassificationResult(merchant, "Investment Contribution", Classification.INVESTMENT, 0.96)
    if re.search(r"PAYROLL|DIRECT DEP|SALARY|ADP PAY", text) and amount > 0:
        return ClassificationResult(merchant, "Salary", Classification.INCOME, 0.98)
    if re.search(r"BONUS", text) and amount > 0:
        return ClassificationResult(merchant, "Bonus", Classification.INCOME, 0.96)
    if re.search(r"REFUND|RETURN|REVERSAL", text) and amount > 0:
        return ClassificationResult(merchant, "Refund", Classification.REFUND, 0.92)
    if re.search(r"REIMBURSE|PAYBACK|SPLIT DINNER", text) and amount > 0:
        return ClassificationResult(merchant, "Reimbursement", Classification.REIMBURSEMENT, 0.9)
    if re.search(r"ZELLE|VENMO|CASH APP|CASHAPP", text):
        if re.search(r"RENT|LANDLORD|LEASE", text) and amount < 0:
            return ClassificationResult(merchant, "Housing", Classification.EXPENSE, 0.94)
        return ClassificationResult(merchant, "Miscellaneous", Classification.UNKNOWN, 0.25)
    if re.search(r"TRANSFER|ACH XFER", text):
        return ClassificationResult(merchant, "Internal Transfer", Classification.TRANSFER, 0.76)

    category_patterns = [
        (r"PUBLIX|ALDI|TRADER JOE|WHOLEFDS|WHOLE FOODS|KROGER", "Groceries"),
        (r"UBER\s*\*?\s*EATS|DOORDASH|GRUBHUB|RESTAURANT|CAFE|COFFEE", "Dining"),
        (r"LYFT|UBER(?!\s*EATS)|SHELL|EXXON|PARKING|TRANSIT", "Transportation"),
        (r"AMAZON\s+PRIME|NETFLIX|SPOTIFY|HULU|APPLE\.COM/BILL", "Subscriptions"),
        (r"AIRBNB|HOTEL|AIRLINES|DELTA|UNITED", "Travel"),
        (r"CVS|WALGREENS|EQUINOX|GYM", "Health & Fitness"),
        (r"AMAZON|TARGET|BEST BUY|NORDSTROM", "Shopping"),
        (r"AMC|CINEMA|TICKETMASTER", "Entertainment"),
    ]
    for pattern, category in category_patterns:
        if re.search(pattern, text):
            return ClassificationResult(merchant, category, Classification.EXPENSE, 0.91)

    if amount > 0:
        return ClassificationResult(merchant, "Other Income", Classification.UNKNOWN, 0.35)
    return ClassificationResult(merchant, "Miscellaneous", Classification.UNKNOWN, 0.3)


def transaction_fingerprint(account_id: int, transaction_date: date, amount: float, description: str) -> str:
    stable = f"{account_id}|{transaction_date.isoformat()}|{amount:.2f}|{clean_description(description)}"
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
