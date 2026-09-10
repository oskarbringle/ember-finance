from __future__ import annotations

import os
import platform
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pdfplumber

from .base import ParsedTransaction, TransactionParser


AMOUNT_PATTERN = r"(?:[+\-−]\s*)?\(?\s*(?:[$€£]\s*)?[+\-−]?\s*(?:\d[\d,]*\.\d{2}|\.\d{2})\)?(?:\s*(?:CR|DR))?"
SHORT_DATE_PATTERN = r"\d{1,2}[/-]\d{1,2}"
FULL_DATE_PATTERN = r"\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})"
ISO_DATE_PATTERN = r"\d{4}-\d{1,2}-\d{1,2}"
NAMED_DATE_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?"
)
DATE_PATTERN = rf"(?:{ISO_DATE_PATTERN}|{FULL_DATE_PATTERN}|{SHORT_DATE_PATTERN}|{NAMED_DATE_PATTERN})"
SKIP_DESCRIPTIONS = re.compile(
    r"^(?:TOTAL(?:S|\s+(?:TRANSACTIONS|DEPOSITS|WITHDRAWALS|PURCHASES|FEES|"
    r"INTEREST|CREDITS|PAYMENTS|AMOUNT))\b|BEGINNING BALANCE|ENDING BALANCE|"
    r"DATE DESCRIPTION|TRANSACTION DATE|PAGE \d+|ACCOUNT SUMMARY)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OcrObservation:
    page: int
    x: float
    y: float
    width: float
    height: float
    text: str


class PdfStatementParser(TransactionParser):
    """Local, deterministic parser for text-based consumer bank statements.

    Chase checking/savings and Chase card layouts receive provider-specific sign
    handling. Other searchable PDFs use flexible table and text-row extraction
    and are marked for careful review in the import report.
    """

    provider = "generic_pdf"

    def __init__(self) -> None:
        self.last_report: dict = {}
        self._ocr_error = ""
        self._ocr_reconciliation: tuple[int, int] | None = None

    def parse(self, content: BytesIO, *, account_type: str, sign_convention: str = "auto") -> list[ParsedTransaction]:
        try:
            with pdfplumber.open(content) as pdf:
                page_texts = [page.extract_text(layout=True) or page.extract_text() or "" for page in pdf.pages]
                table_rows = [table for page in pdf.pages for table in (page.extract_tables() or [])]
        except Exception as exc:
            raise ValueError("This PDF could not be opened. It may be encrypted or damaged.") from exc

        text = "\n".join(page_texts)
        text_pages = sum(bool(page.strip()) for page in page_texts)
        if not text.strip():
            raise ValueError(
                "This appears to be a scanned PDF with no searchable text. Run local OCR first "
                "(for example: ocrmypdf input.pdf output.pdf), then upload the searchable copy."
            )

        self.provider = self._detect_provider(text, account_type)
        statement_end = self._statement_end(text)
        if self.provider == "chase_credit_card_pdf":
            parsed = self._parse_chase_card_pages(page_texts, statement_end)
            method = "Chase card layout"
        else:
            parsed = self._parse_tables(table_rows, account_type, statement_end, sign_convention)
            method = "tables"
        if not parsed:
            parsed = self._parse_lines(page_texts, account_type, statement_end, sign_convention)
            method = "text lines"
        if not parsed and self.provider == "chase_bank_pdf":
            observations = self._ocr_pdf(content.getvalue())
            parsed = self._parse_chase_bank_ocr(observations, statement_end)
            method = "Apple Vision OCR"
        if not parsed:
            ocr_detail = f" On-device OCR was unavailable: {self._ocr_error}" if self._ocr_error else ""
            raise ValueError(
                "Ember could read this PDF, but could not identify transaction rows reliably enough to preview. "
                "Nothing was imported. Check that this is the full statement rather than a summary, or use the "
                f"bank's transaction CSV export for this statement.{ocr_detail}"
            )

        warnings: list[str] = []
        if self.provider == "generic_pdf":
            warnings.append("Generic PDF layout: inspect every date, description, and amount before committing.")
        if text_pages < len(page_texts) and self.provider != "chase_credit_card_pdf":
            warnings.append("Some pages had no searchable text and may require local OCR.")
        if statement_end is None:
            warnings.append("Statement year was inferred because no closing date was recognized.")
        if method == "Apple Vision OCR":
            warnings.append(
                "This statement used private on-device OCR. Reconcile the preview "
                "row count and totals before importing."
            )
            if self._ocr_reconciliation:
                reconciled, statements = self._ocr_reconciliation
                if reconciled == statements:
                    warnings.append(
                        f"All {statements} statement periods reconcile to their "
                        "beginning and ending balances."
                    )
                else:
                    warnings.append(
                        f"{reconciled} of {statements} statement periods reconcile; "
                        "inspect the remaining periods carefully."
                    )
        self.last_report = {
            "provider": self.provider,
            "method": method,
            "pages": len(page_texts),
            "searchable_pages": text_pages,
            "transactions_found": len(parsed),
            "statement_end": statement_end.isoformat() if statement_end else None,
            "confidence": "high" if self.provider != "generic_pdf" and not warnings else "review",
            "inflows": round(sum(row.amount for row in parsed if row.amount > 0), 2),
            "outflows": round(sum(abs(row.amount) for row in parsed if row.amount < 0), 2),
            "net": round(sum(row.amount for row in parsed), 2),
            "warnings": warnings,
        }
        return parsed

    @staticmethod
    def _detect_provider(text: str, account_type: str) -> str:
        upper = text.upper()
        is_chase = "CHASE" in upper or "JPMORGAN CHASE" in upper
        if is_chase and (account_type == "CREDIT_CARD" or "CARDMEMBER" in upper or "PAYMENT DUE DATE" in upper):
            return "chase_credit_card_pdf"
        if is_chase:
            return "chase_bank_pdf"
        if account_type == "CREDIT_CARD":
            return "generic_credit_card_pdf"
        return "generic_pdf"

    @staticmethod
    def _statement_end(text: str) -> date | None:
        explicit = PdfStatementParser._explicit_statement_end(text)
        if explicit:
            return explicit
        years = [int(year) for year in re.findall(r"\b(20\d{2})\b", text)]
        return date(max(years), 12, 31) if years else None

    @staticmethod
    def _explicit_statement_end(text: str) -> date | None:
        patterns = (
            r"OPENING/CLOSING DATE\s*[:\-]?\s*\d{1,2}/\d{1,2}/"
            r"(?:\d{4}|\d{2})\s*[-–]\s*(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))",
            r"(?:CLOSING DATE|STATEMENT DATE|THROUGH)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))",
            r"(?:CLOSING DATE|STATEMENT DATE)\s*[:\-]?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
            r"THROUGH\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = match.group(1)
            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    pass
        return None

    @staticmethod
    def _date(value: str, statement_end: date | None) -> date:
        value = re.sub(r"\s+", " ", value.strip().replace(",", ""))
        if not re.fullmatch(ISO_DATE_PATTERN, value):
            value = value.replace("-", "/")
        for fmt in (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%B %d %Y",
            "%b %d %Y",
        ):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        reference = statement_end or date.today()
        for fmt in ("%B %d", "%b %d"):
            try:
                parsed = datetime.strptime(value, fmt)
                year = (
                    reference.year - 1
                    if parsed.month > reference.month and reference.month <= 2
                    else reference.year
                )
                return date(year, parsed.month, parsed.day)
            except ValueError:
                pass
        month, day = (int(part) for part in value.split("/"))
        year = reference.year - 1 if month > reference.month and reference.month <= 2 else reference.year
        return date(year, month, day)

    @staticmethod
    def _amount(value: str) -> float:
        clean = (
            value.replace("$", "")
            .replace("€", "")
            .replace("£", "")
            .replace(",", "")
            .replace(" ", "")
            .replace("−", "-")
        )
        suffix = clean[-2:].upper() if len(clean) >= 2 else ""
        if suffix in {"CR", "DR"}:
            clean = clean[:-2]
        negative = clean.startswith("-") or (clean.startswith("(") and clean.endswith(")")) or suffix == "DR"
        number = float(clean.strip("()-+"))
        return -number if negative else number

    def _signed_amount(
        self,
        raw: str,
        description: str,
        account_type: str,
        section: str,
        sign_convention: str,
    ) -> float:
        amount = self._amount(raw)
        upper = description.upper()
        if raw.strip().upper().endswith("CR"):
            return abs(amount)
        if raw.strip().upper().endswith("DR"):
            return -abs(amount)
        if sign_convention == "positive_outflow":
            return -amount
        if account_type == "CREDIT_CARD":
            if amount < 0 or re.search(r"PAYMENT|CREDIT|REFUND|RETURN|REVERSAL", upper):
                return abs(amount)
            return -abs(amount)
        if self.provider == "chase_bank_pdf":
            if amount < 0 or section == "debit":
                return -abs(amount)
            return abs(amount)
        if amount < 0:
            return amount
        if section == "credit":
            return abs(amount)
        if section == "debit":
            return -abs(amount)
        if re.search(r"DEPOSIT|PAYROLL|DIRECT DEP|INTEREST PAID|CREDIT", upper):
            return abs(amount)
        if re.search(r"WITHDRAWAL|PURCHASE|PAYMENT|CHECK|FEE|ZELLE|VENMO|TRANSFER TO", upper):
            return -abs(amount)
        return -abs(amount)

    def _parse_chase_card_pages(
        self,
        pages: list[str],
        statement_end: date | None,
    ) -> list[ParsedTransaction]:
        row_pattern = re.compile(
            rf"^\s*({SHORT_DATE_PATTERN})(?:\s+({SHORT_DATE_PATTERN}))?\s+(.+?)\s+({AMOUNT_PATTERN})\s*$",
            re.IGNORECASE,
        )
        period_rows: dict[date, list[ParsedTransaction]] = {}
        interest_charges: dict[date, float] = {}
        current_end = statement_end
        for page in pages:
            page_end = self._explicit_statement_end(page)
            if page_end:
                current_end = page_end
            if current_end:
                interest_match = re.search(
                    rf"Interest Charged\s+\$?({AMOUNT_PATTERN})",
                    page,
                    re.IGNORECASE,
                )
                if interest_match:
                    interest_charges[current_end] = abs(self._amount(interest_match.group(1)))
            if not re.search(r"DATE OF\s+TRANSACTION|ACCOUNT ACTIVITY", page, re.IGNORECASE):
                continue
            for raw_line in page.splitlines():
                match = row_pattern.match(re.sub(r"\s+", " ", raw_line).strip())
                if not match:
                    continue
                date_value, posted_value, description, amount_raw = match.groups()
                try:
                    transaction_date = self._date(date_value, current_end)
                    posted_date = self._date(posted_value, current_end) if posted_value else None
                except (TypeError, ValueError):
                    continue
                if SKIP_DESCRIPTIONS.search(description):
                    continue
                if current_end is None:
                    continue
                period_rows.setdefault(current_end, []).append(
                    ParsedTransaction(
                        transaction_date=transaction_date,
                        posted_date=posted_date,
                        description=description.strip(),
                        amount=round(-self._amount(amount_raw), 2),
                    )
                )
        parsed: list[ParsedTransaction] = []
        for period_end, rows in period_rows.items():
            interest = interest_charges.get(period_end, 0)
            has_interest_row = any("INTEREST CHARGE" in row.description.upper() for row in rows)
            if interest and not has_interest_row:
                rows.append(
                    ParsedTransaction(
                        transaction_date=period_end,
                        posted_date=None,
                        description="Interest charged",
                        amount=-round(interest, 2),
                    )
                )
            parsed.extend(rows)
        return parsed

    def _ocr_pdf(self, pdf_bytes: bytes) -> list[OcrObservation]:
        if platform.system() != "Darwin":
            self._ocr_error = "Apple Vision OCR requires macOS"
            return []
        source = Path(__file__).with_name("macos_pdf_ocr.swift")
        binary = Path(tempfile.gettempdir()) / "ember-finance-pdf-ocr"
        cache = Path(tempfile.gettempdir()) / "ember-finance-swift-cache"
        environment = os.environ.copy()
        environment["CLANG_MODULE_CACHE_PATH"] = str(cache / "clang")
        environment["SWIFT_MODULECACHE_PATH"] = str(cache / "swift")
        try:
            if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
                subprocess.run(
                    [
                        "xcrun",
                        "--sdk",
                        "macosx",
                        "swiftc",
                        str(source),
                        "-framework",
                        "PDFKit",
                        "-framework",
                        "Vision",
                        "-o",
                        str(binary),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=environment,
                )
            with tempfile.NamedTemporaryFile(suffix=".pdf") as statement:
                statement.write(pdf_bytes)
                statement.flush()
                result = subprocess.run(
                    [str(binary), statement.name],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=environment,
                )
        except (OSError, subprocess.SubprocessError) as exc:
            self._ocr_error = str(exc)
            return []

        observations: list[OcrObservation] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t", 5)
            if len(parts) != 6:
                continue
            try:
                observations.append(
                    OcrObservation(
                        page=int(parts[0]),
                        x=float(parts[1]),
                        y=float(parts[2]),
                        width=float(parts[3]),
                        height=float(parts[4]),
                        text=parts[5].strip(),
                    )
                )
            except ValueError:
                continue
        return observations

    def _parse_chase_bank_ocr(
        self,
        observations: list[OcrObservation],
        statement_end: date | None,
    ) -> list[ParsedTransaction]:
        grouped_rows: dict[date, list[tuple[str, str, float | None, float | None]]] = {}
        starting_balances: dict[date, float] = {}
        expected_changes: dict[date, float] = {}
        pages = sorted({item.page for item in observations})
        current_end = statement_end
        for page_number in pages:
            page_items = [item for item in observations if item.page == page_number]
            page_text = "\n".join(item.text for item in page_items)
            explicit_end = self._explicit_statement_end(page_text)
            if explicit_end:
                current_end = explicit_end
            page_end = current_end
            if page_end is None:
                continue
            dates = [
                item
                for item in page_items
                if item.x < 0.115
                and 0.035 < item.y < 0.9
                and re.fullmatch(SHORT_DATE_PATTERN, item.text)
            ]
            anchors = sorted(
                (
                    item
                    for item in page_items
                    if 0.66 < item.x < 0.8
                    and 0.035 < item.y < 0.9
                    and re.fullmatch(AMOUNT_PATTERN, item.text, re.IGNORECASE)
                    and any(
                        balance.x > 0.8
                        and abs(balance.y - item.y) < 0.012
                        and re.fullmatch(AMOUNT_PATTERN, balance.text, re.IGNORECASE)
                        for balance in page_items
                    )
                ),
                key=lambda item: item.y,
                reverse=True,
            )
            if anchors and page_end not in starting_balances:
                possible_starts = [
                    item
                    for item in page_items
                    if item.x > 0.8
                    and anchors[0].y + 0.004 < item.y < anchors[0].y + 0.12
                    and re.fullmatch(AMOUNT_PATTERN, item.text, re.IGNORECASE)
                ]
                if possible_starts:
                    closest = min(possible_starts, key=lambda item: item.y - anchors[0].y)
                    starting_balances[page_end] = self._amount(closest.text)
                expected_change = self._ocr_statement_change(page_items, anchors[0].y)
                if expected_change is not None:
                    expected_changes[page_end] = expected_change
            for index, amount_item in enumerate(anchors):
                lower_bound = anchors[index + 1].y + 0.006 if index + 1 < len(anchors) else 0.035
                row = [
                    item
                    for item in page_items
                    if lower_bound < item.y <= amount_item.y + 0.012
                ]
                row_dates = [
                    item
                    for item in row
                    if item.x < 0.115 and re.fullmatch(SHORT_DATE_PATTERN, item.text)
                ]
                balances = [
                    item
                    for item in row
                    if item.x > 0.8
                    and re.fullmatch(AMOUNT_PATTERN, item.text, re.IGNORECASE)
                ]
                description_parts = [
                    item
                    for item in row
                    if 0.115 <= item.x <= 0.66 and item.text
                ]
                if not balances:
                    continue
                description = (
                    " ".join(
                        item.text
                        for item in sorted(description_parts, key=lambda item: (-item.y, item.x))
                    )
                    or "Description unreadable — review statement"
                )
                embedded_date = re.search(SHORT_DATE_PATTERN, description)
                nearest_date = min(dates, key=lambda item: abs(item.y - amount_item.y)) if dates else None
                date_value = (
                    min(row_dates, key=lambda item: abs(item.y - amount_item.y)).text
                    if row_dates
                    else embedded_date.group() if embedded_date
                    else nearest_date.text if nearest_date
                    else ""
                )
                try:
                    self._date(date_value, page_end)
                    raw_amount = self._amount(amount_item.text)
                    running_balance = self._amount(
                        min(balances, key=lambda item: abs(item.y - amount_item.y)).text
                    )
                except (TypeError, ValueError):
                    continue
                grouped_rows.setdefault(page_end, []).append(
                    (date_value, re.sub(r"\s+", " ", description).strip(), raw_amount, running_balance)
                )

        parsed: list[ParsedTransaction] = []
        reconciled_statements = 0
        for page_end, rows in grouped_rows.items():
            previous_balance = starting_balances.get(page_end)
            resolved: list[tuple[str, str, float, float | None]] = []
            for date_value, description, raw_amount, running_balance in rows:
                derived_amount = (
                    round(running_balance - previous_balance, 2)
                    if previous_balance is not None and running_balance is not None
                    else None
                )
                if running_balance is not None:
                    previous_balance = running_balance
                amount = raw_amount if raw_amount is not None else derived_amount
                if amount is None:
                    continue
                resolved.append((date_value, description, amount, derived_amount))

            expected = expected_changes.get(page_end)
            if expected is not None:
                base_total = round(sum(item[2] for item in resolved), 2)
                alternatives = [
                    (index, round(item[3] - item[2], 2))
                    for index, item in enumerate(resolved)
                    if item[3] is not None
                    and abs(item[3] - item[2]) > 0.009
                    and abs(item[3]) < 100_000
                ]
                selected = self._closest_corrections(alternatives, round(expected - base_total, 2))
                if selected is not None:
                    for index in selected:
                        date_value, description, _, derived_amount = resolved[index]
                        resolved[index] = (
                            date_value,
                            description,
                            derived_amount if derived_amount is not None else 0,
                            derived_amount,
                        )
                if abs(sum(item[2] for item in resolved) - expected) <= 0.01:
                    reconciled_statements += 1

            for date_value, description, amount, _ in resolved:
                parsed.append(
                    ParsedTransaction(
                        transaction_date=self._date(date_value, page_end),
                        posted_date=None,
                        description=description,
                        amount=round(amount, 2),
                    )
                )
        if expected_changes:
            self._ocr_reconciliation = (reconciled_statements, len(expected_changes))
        return parsed

    def _ocr_statement_change(
        self,
        page_items: list[OcrObservation],
        first_transaction_y: float,
    ) -> float | None:
        values: list[float] = []
        for label in ("BEGINNING BALANCE", "ENDING BALANCE"):
            labels = [
                item
                for item in page_items
                if item.y > first_transaction_y
                and item.text.upper().startswith(label)
            ]
            if not labels:
                return None
            target = max(labels, key=lambda item: item.y)
            amounts = [
                item
                for item in page_items
                if item.x > 0.5
                and abs(item.y - target.y) < 0.012
                and re.fullmatch(AMOUNT_PATTERN, item.text, re.IGNORECASE)
            ]
            if not amounts:
                return None
            values.append(self._amount(min(amounts, key=lambda item: abs(item.y - target.y)).text))
        return round(values[1] - values[0], 2)

    @staticmethod
    def _closest_corrections(
        alternatives: list[tuple[int, float]],
        target: float,
    ) -> set[int] | None:
        if abs(target) <= 0.01:
            return set()
        if len(alternatives) > 20:
            return None
        best_error = abs(target)
        best: set[int] | None = None
        for mask in range(1, 1 << len(alternatives)):
            correction = sum(
                value for bit, (_, value) in enumerate(alternatives) if mask & (1 << bit)
            )
            error = abs(target - correction)
            if error < best_error:
                best_error = error
                best = {
                    index
                    for bit, (index, _) in enumerate(alternatives)
                    if mask & (1 << bit)
                }
                if error <= 0.01:
                    break
        return best if best_error <= 0.01 else None

    def _parse_tables(
        self,
        tables: Iterable[list[list[str | None]]],
        account_type: str,
        statement_end: date | None,
        sign_convention: str,
    ) -> list[ParsedTransaction]:
        parsed: list[ParsedTransaction] = []
        for table in tables:
            header_map: dict[str, int] | None = None
            section = ""
            for raw_row in table:
                row = [re.sub(r"\s+", " ", str(cell or "")).strip() for cell in raw_row]
                joined = " ".join(row).upper()
                if "DEPOSIT" in joined or "ADDITION" in joined:
                    section = "credit"
                if (
                    "WITHDRAWAL" in joined
                    or "DEDUCTION" in joined
                    or "CHECKS PAID" in joined
                ):
                    section = "debit"
                if any("DATE" in cell.upper() for cell in row) and any(
                    token in joined for token in ("DESCRIPTION", "MERCHANT", "TRANSACTION")
                ):
                    header_map = self._header_map(row)
                    continue
                tx = (
                    self._table_transaction(
                        row,
                        header_map,
                        account_type,
                        statement_end,
                        section,
                        sign_convention,
                    )
                    if header_map
                    else self._inferred_table_transaction(
                        row,
                        account_type,
                        statement_end,
                        section,
                        sign_convention,
                    )
                )
                if tx:
                    parsed.append(tx)
        return parsed

    @staticmethod
    def _header_map(row: list[str]) -> dict[str, int]:
        result: dict[str, int] = {}
        for index, cell in enumerate(row):
            upper = cell.upper()
            if "POST" in upper and "DATE" in upper:
                result["posted"] = index
            elif "DATE" in upper and "date" not in result:
                result["date"] = index
            if "DESCRIPTION" in upper or "MERCHANT" in upper:
                result["description"] = index
            if "WITHDRAW" in upper or "DEBIT" in upper:
                result["debit"] = index
            elif "DEPOSIT" in upper or "CREDIT" in upper:
                result["credit"] = index
            elif "AMOUNT" in upper:
                result["amount"] = index
        return result

    def _table_transaction(
        self,
        row: list[str],
        columns: dict[str, int],
        account_type: str,
        statement_end: date | None,
        section: str,
        sign_convention: str,
    ) -> ParsedTransaction | None:
        date_index = columns.get("date", columns.get("posted"))
        desc_index = columns.get("description")
        if (
            date_index is None
            or desc_index is None
            or date_index >= len(row)
            or desc_index >= len(row)
        ):
            return None
        date_value, description = row[date_index], row[desc_index]
        if (
            not re.fullmatch(
                rf"(?:{FULL_DATE_PATTERN}|{SHORT_DATE_PATTERN})", date_value
            )
            or not description
            or SKIP_DESCRIPTIONS.search(description)
        ):
            return None
        amount_raw = ""
        amount_section = section
        for key, implied in (("debit", "debit"), ("credit", "credit"), ("amount", section)):
            index = columns.get(key)
            if (
                index is not None
                and index < len(row)
                and re.fullmatch(AMOUNT_PATTERN, row[index])
            ):
                amount_raw, amount_section = row[index], implied
                break
        if not amount_raw:
            return None
        posted = (
            row[columns["posted"]]
            if "posted" in columns and columns["posted"] < len(row)
            else ""
        )
        return ParsedTransaction(
            transaction_date=self._date(date_value, statement_end),
            posted_date=(
                self._date(posted, statement_end)
                if re.fullmatch(
                    rf"(?:{FULL_DATE_PATTERN}|{SHORT_DATE_PATTERN})", posted
                )
                else None
            ),
            description=description,
            amount=round(
                self._signed_amount(
                    amount_raw,
                    description,
                    account_type,
                    amount_section,
                    sign_convention,
                ),
                2,
            ),
        )

    def _inferred_table_transaction(
        self,
        row: list[str],
        account_type: str,
        statement_end: date | None,
        section: str,
        sign_convention: str,
    ) -> ParsedTransaction | None:
        date_cells = [
            (index, cell)
            for index, cell in enumerate(row)
            if re.fullmatch(DATE_PATTERN, cell, re.IGNORECASE)
        ]
        amount_cells = [
            (index, cell)
            for index, cell in enumerate(row)
            if re.fullmatch(AMOUNT_PATTERN, cell, re.IGNORECASE)
        ]
        if not date_cells or not amount_cells:
            return None

        excluded = {index for index, _ in date_cells + amount_cells}
        description_cells = [
            cell
            for index, cell in enumerate(row)
            if index not in excluded and cell and not SKIP_DESCRIPTIONS.search(cell)
        ]
        description = " ".join(description_cells).strip()
        if not description:
            return None

        transaction_date = self._date(date_cells[0][1], statement_end)
        posted_date = (
            self._date(date_cells[1][1], statement_end)
            if len(date_cells) > 1
            else None
        )
        amount_raw = amount_cells[0][1]
        return ParsedTransaction(
            transaction_date=transaction_date,
            posted_date=posted_date,
            description=description,
            amount=round(
                self._signed_amount(
                    amount_raw,
                    description,
                    account_type,
                    section,
                    sign_convention,
                ),
                2,
            ),
        )

    def _parse_lines(
        self,
        pages: list[str],
        account_type: str,
        statement_end: date | None,
        sign_convention: str,
    ) -> list[ParsedTransaction]:
        parsed: list[ParsedTransaction] = []
        section = ""
        leading_dates = re.compile(
            rf"^\s*({DATE_PATTERN})(?:\s+({DATE_PATTERN}))?\s*(.*)$",
            re.IGNORECASE,
        )
        amount = re.compile(AMOUNT_PATTERN, re.IGNORECASE)
        pending: tuple[str, str, str] | None = None

        def append_transaction(
            transaction_date: str,
            posted_date: str,
            description: str,
            amount_raw: str,
        ) -> None:
            if not description or SKIP_DESCRIPTIONS.search(description):
                return
            parsed.append(
                ParsedTransaction(
                    transaction_date=self._date(transaction_date, statement_end),
                    posted_date=(
                        self._date(posted_date, statement_end)
                        if posted_date
                        else None
                    ),
                    description=description.strip(),
                    amount=round(
                        self._signed_amount(
                            amount_raw,
                            description,
                            account_type,
                            section,
                            sign_convention,
                        ),
                        2,
                    ),
                )
            )

        for page in pages:
            for raw_line in page.splitlines():
                line = re.sub(r"\s+", " ", raw_line).strip()
                upper = line.upper()
                if re.search(r"DEPOSITS?(?: AND ADDITIONS)?|CREDITS?", upper) and not re.match(r"^\d", line):
                    section = "credit"
                elif re.search(r"WITHDRAWALS?|CHECKS PAID|DEDUCTIONS?|PURCHASES", upper) and not re.match(r"^\d", line):
                    section = "debit"
                match = leading_dates.match(line)
                if match:
                    transaction_date, posted_date, remainder = match.groups()
                    amount_match = amount.search(remainder)
                    if amount_match:
                        append_transaction(
                            transaction_date,
                            posted_date or "",
                            remainder[: amount_match.start()].strip(" -·|"),
                            amount_match.group(),
                        )
                        pending = None
                    else:
                        pending = (
                            transaction_date,
                            posted_date or "",
                            remainder.strip(),
                        )
                    continue
                if pending and line:
                    transaction_date, posted_date, description = pending
                    combined = f"{description} {line}".strip()
                    amount_match = amount.search(combined)
                    if amount_match:
                        append_transaction(
                            transaction_date,
                            posted_date,
                            combined[: amount_match.start()].strip(" -·|"),
                            amount_match.group(),
                        )
                        pending = None
                    elif len(combined) <= 300:
                        pending = (transaction_date, posted_date, combined)
        return parsed
