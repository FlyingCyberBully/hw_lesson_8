from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from datetime import datetime
from enum import StrEnum
from typing import List, Optional, Union


class Status(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SENT = "sent"
    FAILED = "failed"
    INVALID = "invalid"


class EmailAddress:
    """Класс-обёртка над email-адресом.
    Обеспечивает нормализацию, валидацию и маскированный вывод.
    """

    def __init__(self, address: str):
        self._address = self._normalize(address)
        self._validate(self._address)

    @staticmethod
    def _normalize(address: str) -> str:
        return address.strip().lower()

    @staticmethod
    def _validate(address: str) -> None:
        if "@" not in address:
            raise ValueError(f"Invalid email: {address}")

        domain_ok = any(address.endswith(tld) for tld in (".com", ".ru", ".net"))
        if not domain_ok:
            raise ValueError(f"Invalid email domain: {address}")

    @property
    def value(self) -> str:
        return self._address

    @property
    def masked(self) -> str:
        name, domain = self._address.split("@")
        prefix = name[:2]
        return f"{prefix}***@{domain}"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass
class Email:
    subject: str
    body: str
    sender: EmailAddress
    recipients: Union[EmailAddress, List[EmailAddress]]
    date: Optional[datetime] = None
    short_body: Optional[str] = None
    status: Status = Status.DRAFT

    def __post_init__(self) -> None:
        # recipients всегда должен быть списком
        if isinstance(self.recipients, EmailAddress):
            self.recipients = [self.recipients]
        else:
            self.recipients = list(self.recipients)

    # ----------------------- PREPARE ------------------------

    def prepare(self) -> None:
        """Очистка полей, валидация, установка статуса READY/INVALID."""
        self.subject = self.subject.strip()
        self.body = self.body.strip()

        self.add_short_body()
        self._validate_fields()

    def add_short_body(self, limit: int = 20) -> None:
        clean = " ".join(self.body.split())
        self.short_body = clean[:limit] + ("..." if len(clean) > limit else "")

    def _validate_fields(self) -> None:
        if not self.subject or not self.body:
            self.status = Status.INVALID
            return
        if not self.sender or not self.recipients:
            self.status = Status.INVALID
            return

        self.status = Status.READY

    # ----------------------- REPRESENTATION ------------------------

    def __repr__(self) -> str:
        rec_list = ", ".join(r.value for r in self.recipients)
        return (
            f"Email(from={self.sender.masked}, to=[{rec_list}], "
            f"subject='{self.subject}', status='{self.status}')"
        )


class EmailService:
    """Имитирует отправку. Для каждого получателя создаёт отдельное письмо."""

    def send_email(self, email: Email) -> List[Email]:
        result = []

        for recipient in email.recipients:
            new_email = deepcopy(email)
            new_email.recipients = [recipient]
            new_email.date = datetime.now()

            if email.status == Status.READY:
                new_email.status = Status.SENT
            else:
                new_email.status = Status.FAILED

            result.append(new_email)

        return result


class LoggingEmailService(EmailService):
    """Сервис отправки, дополнительно пишущий результат в send.log."""

    LOG_FILE = "send.log"

    def send_email(self, email: Email) -> List[Email]:
        results = super().send_email(email)

        with open(self.LOG_FILE, "a", encoding="utf-8") as file:
            for msg in results:
                file.write(
                    f"{datetime.now()}: "
                    f"FROM {email.sender.masked} "
                    f"TO {msg.recipients[0].masked} "
                    f"STATUS={msg.status.value}\n"
                )

        return results
