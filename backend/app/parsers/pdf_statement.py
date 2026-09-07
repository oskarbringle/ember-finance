from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Iterable

import pdfplumber

from .base import ParsedTransaction, TransactionParser


AMOUNT_PATTERN = r"(?:[+\-−]\s*)?\(?\s*(?:[$€£]\s*)?[+\-−]?\s*\d[\d,]*\.\d{2}\)?(?:\s*(?:CR|DR))?"
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
    r"^(?:TOTAL|BEGINNING BALANCE|ENDING BALANCE|DATE DESCRIPTION|TRANSACTION DATE|PAGE \d+|ACCOUNT SUMMARY)",
    re.IGNORECASE,
)


class PdfStatementParser(TransactionParser):
    """Local, deterministic parser for text-based consumer bank statements.

    Chase checking/savings and Chase card layouts receive provider-specific sign
    handling. Other searchable PDFs use flexible table and text-row extraction
    and are marked for careful review in the import report.
    """

    provider = "generic_pdf"

    def __init__(self) -> None:
        self.last_report: dict = {}

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
        parsed = self._parse_tables(table_rows, account_type, statement_end, sign_convention)
        method = "tables"
        if not parsed:
            parsed = self._parse_lines(page_texts, account_type, statement_end, sign_convention)
            method = "text lines"
        parsed = self._unique(parsed)
        if not parsed:
            raise ValueError(
                "Ember could read this PDF, but could not identify transaction rows reliably enough to preview. "
                "Nothing was imported. Check that this is the full statement rather than a summary, or use the "
                "bank's transaction CSV export for this statement."
            )

        warnings: list[str] = []
        if self.provider == "generic_pdf":
            warnings.append("Generic PDF layout: inspect every date, description, and amount before committing.")
        if text_pages < len(page_texts):
            warnings.append("Some pages had no searchable text and may require local OCR.")
        if statement_end is None:
            warnings.append("Statement year was inferred because no closing date was recognized.")
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
        patterns = (
            r"(?:CLOSING DATE|STATEMENT DATE|THROUGH)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))",
            r"(?:CLOSING DATE|STATEMENT DATE)\s*[:\-]?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
            r"THROUGH\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
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
        years = [int(year) for year in re.findall(r"\b(20\d{2})\b", text)]
        return date(max(years), 12, 31) if years else None

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

    def _signed_amount(self, raw: str, description: str, account_type: str, section: str, sign_convention: str) -> float:
        amount = self._amount(raw)
        upper = description.upper()
        if raw.strip().upper().endswith("CR"):
            return abs(amount)
        if raw.strip().upper().endswith("DR"):
            return -abs(amount)
        if sign_convention == "positive_outflow":
            return -amount
        if amount < 0:
            return amount
        if account_type == "CREDIT_CARD":
            if re.search(r"PAYMENT|CREDIT|REFUND|RETURN|REVERSAL", upper):
                return abs(amount)
            return -abs(amount)
        if section == "credit":
            return abs(amount)
        if section == "debit":
            return -abs(amount)
        if re.search(r"DEPOSIT|PAYROLL|DIRECT DEP|INTEREST PAID|CREDIT", upper):
            return abs(amount)
        if re.search(r"WITHDRAWAL|PURCHASE|PAYMENT|CHECK|FEE|ZELLE|VENMO|TRANSFER TO", upper):
            return -abs(amount)
        return -abs(amount)

    def _parse_tables(self, tables: Iterable[list[list[str | None]]], account_type: str, statement_end: date | None, sign_convention: str) -> list[ParsedTransaction]:
        parsed: list[ParsedTransaction] = []
        for table in tables:
            header_map: dict[str, int] | None = None
            section = ""
            for raw_row in table:
                row = [re.sub(r"\s+", " ", str(cell or "")).strip() for cell in raw_row]
                joined = " ".join(row).upper()
                if "DEPOSIT" in joined or "ADDITION" in joined:
                    section = "credit"
                if "WITHDRAWAL" in joined or "DEDUCTION" in joined or "CHECKS PAID" in joined:
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

    def _table_transaction(self, row: list[str], columns: dict[str, int], account_type: str, statement_end: date | None, section: str, sign_convention: str) -> ParsedTransaction | None:
        date_index = columns.get("date", columns.get("posted"))
        desc_index = columns.get("description")
        if date_index is None or desc_index is None or date_index >= len(row) or desc_index >= len(row):
            return None
        date_value, description = row[date_index], row[desc_index]
        if not re.fullmatch(rf"(?:{FULL_DATE_PATTERN}|{SHORT_DATE_PATTERN})", date_value) or not description or SKIP_DESCRIPTIONS.search(description):
            return None
        amount_raw = ""
        amount_section = section
        for key, implied in (("debit", "debit"), ("credit", "credit"), ("amount", section)):
            index = columns.get(key)
            if index is not None and index < len(row) and re.fullmatch(AMOUNT_PATTERN, row[index]):
                amount_raw, amount_section = row[index], implied
                break
        if not amount_raw:
            return None
        posted = row[columns["posted"]] if "posted" in columns and columns["posted"] < len(row) else ""
        return ParsedTransaction(
            transaction_date=self._date(date_value, statement_end),
            posted_date=self._date(posted, statement_end) if re.fullmatch(rf"(?:{FULL_DATE_PATTERN}|{SHORT_DATE_PATTERN})", posted) else None,
            description=description,
            amount=round(self._signed_amount(amount_raw, description, account_type, amount_section, sign_convention), 2),
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

    def _parse_lines(self, pages: list[str], account_type: str, statement_end: date | None, sign_convention: str) -> list[ParsedTransaction]:
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

    @staticmethod
    def _unique(rows: list[ParsedTransaction]) -> list[ParsedTransaction]:
        seen: set[tuple] = set()
        unique: list[ParsedTransaction] = []
        for row in rows:
            key = (row.transaction_date, row.posted_date, row.description.upper(), row.amount)
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique
