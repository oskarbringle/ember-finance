from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from io import BytesIO


@dataclass
class ParsedTransaction:
    transaction_date: date
    posted_date: date | None
    description: str
    amount: float


class TransactionParser(ABC):
    provider = "base"

    @abstractmethod
    def parse(self, content: BytesIO, *, account_type: str, sign_convention: str = "auto") -> list[ParsedTransaction]:
        raise NotImplementedError

