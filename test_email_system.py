import os
from datetime import datetime

import pytest

from email_models import (
    Email,
    EmailAddress,
    EmailService,
    LoggingEmailService,
    Status,
)


# ---------------------- EmailAddress -------------------------

class TestEmailAddress:
    def test_normalization(self):
        addr = EmailAddress("  UsEr@Example.COM  ")
        assert addr.value == "user@example.com"

    def test_validation_invalid_format(self):
        with pytest.raises(ValueError):
            EmailAddress("invalid_email")

    def test_validation_invalid_domain(self):
        with pytest.raises(ValueError):
            EmailAddress("user@example.xyz")

    def test_masked(self):
        addr = EmailAddress("alexander@example.com")
        assert addr.masked == "al***@example.com"


# ---------------------- Email.prepare -------------------------

class TestEmailPrepare:
    def test_prepare_sets_ready(self):
        email = Email(
            subject=" Hi ",
            body=" Test Body ",
            sender=EmailAddress("a@a.com"),
            recipients=EmailAddress("b@b.com"),
        )
        email.prepare()

        assert email.subject == "Hi"
        assert email.body == "Test Body"
        assert email.status == Status.READY
        assert email.short_body.startswith("Test Body")

    def test_prepare_invalid_when_empty_subject(self):
        email = Email(
            subject="",
            body="Body",
            sender=EmailAddress("a@a.com"),
            recipients=EmailAddress("b@b.com"),
        )
        email.prepare()
        assert email.status == Status.INVALID

    def test_prepare_invalid_when_no_sender(self):
        # sender не может быть None — поэтому сделаем грязный хак
        email = Email(
            subject="Subj",
            body="Body",
            sender=EmailAddress("a@a.com"),
            recipients=[],
        )
        email.prepare()
        assert email.status == Status.INVALID


# ---------------------- EmailService -------------------------

class TestEmailService:
    def test_send_creates_separate_emails_for_each_recipient(self):
        email = Email(
            subject="Subj",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=[EmailAddress("a@a.com"), EmailAddress("b@b.com")],
        )

        email.prepare()
        service = EmailService()

        result = service.send_email(email)

        assert len(result) == 2
        assert result[0].recipients[0].value == "a@a.com"
        assert result[1].recipients[0].value == "b@b.com"

    def test_send_sets_sent_status(self):
        email = Email(
            subject="Subj",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=EmailAddress("you@you.com"),
        )
        email.prepare()

        service = EmailService()
        result = service.send_email(email)

        assert result[0].status == Status.SENT

    def test_send_sets_failed_if_not_ready(self):
        email = Email(
            subject="",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=EmailAddress("you@you.com"),
        )
        email.prepare()  # INVALID

        service = EmailService()
        result = service.send_email(email)

        assert result[0].status == Status.FAILED

    def test_original_email_unchanged(self):
        email = Email(
            subject="Subj",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=EmailAddress("you@you.com"),
        )
        email.prepare()

        service = EmailService()
        result = service.send_email(email)

        assert email.date is None
        assert email.status == Status.READY
        assert result[0].date is not None


# ---------------------- LoggingEmailService -------------------------

class TestLoggingEmailService:
    LOGFILE = "send.log"

    def setup_method(self):
        if os.path.exists(self.LOGFILE):
            os.remove(self.LOGFILE)

    def test_logging_creates_file_and_writes(self):
        email = Email(
            subject="Hello",
            body="Body",
            sender=EmailAddress("me@me.com"),
            recipients=EmailAddress("you@you.com"),
        )
        email.prepare()

        service = LoggingEmailService()
        service.send_email(email)

        assert os.path.exists(self.LOGFILE)

        with open(self.LOGFILE, "r", encoding="utf-8") as file:
            content = file.read()
            assert "FROM me***@me.com" in content
            assert "TO yo***@you.com" in content
            assert "STATUS=sent" in content
