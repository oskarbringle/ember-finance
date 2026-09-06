from __future__ import annotations

from io import BytesIO

import pandas as pd

from .base import ParsedTransaction, TransactionParser


class GenericCsvParser(TransactionParser):
    provider = "generic_csv"

    DATE_NAMES = ("transaction date", "date", "trans date", "posting date", "post date")
    POSTED_NAMES = ("posted date", "posting date", "post date")
    DESC_NAMES = ("description", "details", "merchant", "name", "memo", "transaction")
    AMOUNT_NAMES = ("amount", "transaction amount")

    def _find(self, columns: dict[str, str], names: tuple[str, ...], required: bool = True) -> str | None:
        for name in names:
            if name in columns:
                return columns[name]
        if required:
            raise ValueError(f"Could not identify required column. Expected one of: {', '.join(names)}")
        return None

    def parse(self, content: BytesIO, *, account_type: str, sign_convention: str = "auto") -> list[ParsedTransaction]:
        frame = pd.read_csv(content)
        if frame.empty:
            return []
        columns = {str(column).strip().lower(): column for column in frame.columns}
        date_col = self._find(columns, self.DATE_NAMES)
        posted_col = self._find(columns, self.POSTED_NAMES, required=False)
        desc_col = self._find(columns, self.DESC_NAMES)
        amount_col = self._find(columns, self.AMOUNT_NAMES, required=False)
        debit_col = columns.get("debit") or columns.get("withdrawal")
        credit_col = columns.get("credit") or columns.get("deposit")
        type_col = columns.get("type") or columns.get("transaction type")
        if not amount_col and not (debit_col or credit_col):
            raise ValueError("Could not identify amount, debit, or credit columns")

        rows: list[ParsedTransaction] = []
        for _, row in frame.iterrows():
            parsed_date = pd.to_datetime(row[date_col], errors="coerce")
            if pd.isna(parsed_date):
                continue
            posted_date = None
            if posted_col:
                parsed_posted = pd.to_datetime(row[posted_col], errors="coerce")
                posted_date = None if pd.isna(parsed_posted) else parsed_posted.date()

            if debit_col or credit_col:
                debit = pd.to_numeric(row.get(debit_col), errors="coerce") if debit_col else float("nan")
                credit = pd.to_numeric(row.get(credit_col), errors="coerce") if credit_col else float("nan")
                amount = float(credit) if not pd.isna(credit) else -abs(float(debit))
            else:
                raw = str(row[amount_col]).replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
                amount = float(raw)
                tx_type = str(row.get(type_col, "")).upper() if type_col else ""
                if any(token in tx_type for token in ("SALE", "PURCHASE", "DEBIT")):
                    amount = -abs(amount)
                elif any(token in tx_type for token in ("PAYMENT", "RETURN", "CREDIT")):
                    amount = abs(amount)
                elif sign_convention == "positive_outflow":
                    amount = -amount

            rows.append(
                ParsedTransaction(
                    transaction_date=parsed_date.date(),
                    posted_date=posted_date,
                    description=str(row[desc_col]).strip(),
                    amount=round(amount, 2),
                )
            )
        return rows

