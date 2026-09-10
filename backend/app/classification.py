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


EXPENSE_CATEGORY_RULES = [
    (
        r"\b(?:SHELL|EXXON|CHEVRON|RACETRAC|RACE TRAC|QUIKTRIP|QT\s*#?\d*|BP|SUNOCO|"
        r"CIRCLE K|BUC-?EE'?S|MARATHON|MOBIL|VALERO|WAWA|COSTCO GAS|CITGO)\b|"
        r"FUEL|GAS STATION",
        "Gas & Fuel",
        0.96,
    ),
    (
        r"UBER\s*\*?\s*EATS|DOORDASH|GRUBHUB|RESTAURANT|DINING|CAFE|COFFEE|PIZZA|"
        r"TACO|BURGER|GRILL|KITCHEN|BAGEL|BAKERY|DELI|SUSHI|GYRO|WINGS|WAFFLE HOUSE|"
        r"CHICK-?FIL-?A|CHIPOTLE|SUBWAY|PANDA EXPRESS|PAPA JOHN|MOE'?S|COOK OUT|"
        r"IN-?N-?OUT|PLAYA BOWLS|PEI WEI|JOEANDTHEJUICE|FOOD STORE|TECH DINING|"
        r"STARBUCKS|MCDONALD'?S|WENDY'?S|FIREHOUSE SUBS|RAISING CANES|CULVERS|"
        r"JERSEY MIKES|CAVA|CANTINA|TRATTORIA|BISTRO|GOURMET|PANCAKE|SHOKUDO|"
        r"GYOZA|RAMEN|CREAMERY|COOKIES|CATERING|DRIVE IN|ASIAN FUSION|KING OF POPS|"
        r"MEXI|RESTA\b|HIBACHI|EL TIEMPO|SUB-WING|HENRYS END|BANANA COMPANY|"
        r"COCA COLA|CORTADO|TST\s*\*?",
        "Dining",
        0.94,
    ),
    (
        r"TAVERN|NIGHTCLUB|NIGHTLIFE|BREWERY|BREWING|BEER|WINE(?:MIDTOWN| (?:AND|&) MORE)|"
        r"PACKAGE STORE|LIQUOR|COCKTAIL|PUB\b|LOUNGE|BAR\b|TONGUE AND GROOVE|"
        r"THE SWAMP|PAT O BRIENS|LITTLE WOODROWS|PIG (?:AND|&) PARROT",
        "Bars & Nightlife",
        0.93,
    ),
    (
        r"PUBLIX|ALDI|TRADER JOE|WHOLEFDS|WHOLE FOODS|KROGER|SUPERMARKET|GROCERY|"
        r"FAMILYMART|SEVEN-?ELEVEN|7-?ELEVEN|BIRITE|BI-RITE|WM SUPERCENTER|WAL-?MART|"
        r"MARKET|ICA KVANTUM|PRESSBYRAN|GENERAL STORE",
        "Groceries",
        0.94,
    ),
    (
        r"LYFT|UBER(?!\s*EATS)|PARKING|TRANSIT|MTA\*?|NYCT|LIRR|PATH TAPP|METRO|"
        r"AMTRAK|TOLL|SUICA|TAP TO RIDE|BIRD APP|SKANETRAFIKEN|SL APP|SJ APP|JR EAST|"
        r"BULLET TRAIN|RTD EAST|BUSTANG|PORT AUTHORITY|CENTER GARAGE",
        "Transportation",
        0.95,
    ),
    (
        r"AIRBNB|HOTEL|WESTIN|MARRIOTT|HILTON|HYATT|AIRLINES?|DELTA|UNITED|JETBLUE|"
        r"SOUTHWEST|FRONTIER AI|ROYAL CARIBBEAN|CRUISE|TRIP ADVISOR|EXPEDIA|"
        r"BOOKING\.COM|PASSPORT UTD|HAKUBA VALLEY",
        "Travel",
        0.94,
    ),
    (
        r"AMAZON\s+PRIME|NETFLIX|SPOTIFY|HULU|APPLE\.COM/BILL|OPENAI.*SUBSCR|"
        r"MICROSOFT\*?XBOX(?: GAME PA)?|GAME PASS|YOUTUBE PREMIUM|DISNEY\+|"
        r"OPENAI.*(?:CHALGPT|SUBSOR)",
        "Subscriptions",
        0.95,
    ),
    (
        r"STUBHUB|TICKETMASTER|AMC|CINEMA|REGAL|THEATRE|THEATER|PRIZEPICKS|"
        r"GOLF|GLF\*|BILLIARD|BOWLING|CONCESSION|AMPHITHEA|SILVERBACKS|EVENTS?|"
        r"TICKETS?OCK|AMERIS BANK AMPHITH|STADIUM CONC|BILJARD|KALSHI",
        "Entertainment",
        0.93,
    ),
    (
        r"CVS|WALGREENS|PHARMACY|EQUINOX|GYM|FITNESS|DENTAL|DENTIST|MEDICAL|"
        r"HOSPITAL|URGENT CARE|THERAPY|DERMATOLOGY",
        "Health & Fitness",
        0.94,
    ),
    (
        r"AMAZON|AMZN\s*MKT|TARGET|BEST BUY|NORDSTROM|HOMEGOODS|IKEA|TEMU|REI\.COM|"
        r"PGA TOUR SUPERSTORE|BOOKSTORE|BOOK STORE|BOOKSHOP|BKST|FURNITURE|UNIQLO|EBAY|"
        r"ADIDAS|DICKS SPORTING|LULULEMON|AUTOZONE|HARDWARE|PETER MILLAR|PLATOS CLOSET|"
        r"UPS STORE|TEN THOUSAND",
        "Shopping",
        0.92,
    ),
    (
        r"FOREIGN TRANSACTION FEE|ATM FEE|SERVICE FEE|LATE FEE|ANNUAL FEE|"
        r"FOREIGN.*(?:FEE|FOE|FOO)|EXCH.*ADJ.*(?:FEE|FOE|FOO)",
        "Fees",
        0.98,
    ),
    (
        r"MORTGAGE|PROPERTY MANAGEMENT|APARTMENT|ELECTRIC|WATER BILL|UTILITY|"
        r"GEORGIA POWER|COMCAST|XFINITY|INTERNET SERVICE",
        "Housing",
        0.93,
    ),
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


def classify_transaction(
    description: str,
    amount: float,
    user_rules: list[dict] | None = None,
    account_type: str | None = None,
) -> ClassificationResult:
    text = clean_description(description)
    merchant = normalize_merchant(description)

    for rule in sorted(user_rules or [], key=lambda row: row.get("priority", 100), reverse=True):
        classification = str(rule["classification"])
        invalid_direction = (
            amount > 0
            and classification
            in {Classification.EXPENSE, Classification.SAVING, Classification.INVESTMENT}
        ) or (
            amount < 0
            and classification
            in {Classification.INCOME, Classification.REFUND, Classification.REIMBURSEMENT}
        )
        if (
            rule.get("active", True)
            and not invalid_direction
            and re.search(rule["pattern"], text, re.IGNORECASE)
        ):
            return ClassificationResult(
                rule.get("merchant") or merchant,
                rule["category"],
                rule["classification"],
                0.99,
            )

    if re.search(
        r"CHASE.*(?:CARD|CREDIT).*PAY|CREDIT CARD PAYMENT|AUTOPAY.*CARD|"
        r"PAYMENT THANK YOU|AUTOMATIC PAYMENT|PAYMENT TO CHASE (?:CARD )?ENDING",
        text,
    ):
        return ClassificationResult("Chase Card Payment", "Credit Card Payment", Classification.CREDIT_CARD_PAYMENT, 0.98)
    if re.search(r"TRANS(?:FER|TER).*(SAV|HYSA)|TO SAVINGS", text):
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

    for pattern, category, confidence in EXPENSE_CATEGORY_RULES:
        if amount < 0 and re.search(pattern, text):
            return ClassificationResult(merchant, category, Classification.EXPENSE, confidence)

    if amount > 0 and account_type == "CREDIT_CARD":
        return ClassificationResult(merchant, "Refund", Classification.REFUND, 0.82)
    if amount > 0:
        return ClassificationResult(merchant, "Other Income", Classification.INCOME, 0.82)
    return ClassificationResult(merchant, "Miscellaneous", Classification.UNKNOWN, 0.3)


def transaction_fingerprint(
    account_id: int,
    transaction_date: date,
    amount: float,
    description: str,
    occurrence: int = 0,
) -> str:
    stable = f"{account_id}|{transaction_date.isoformat()}|{amount:.2f}|{clean_description(description)}"
    if occurrence:
        stable = f"{stable}|{occurrence}"
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
