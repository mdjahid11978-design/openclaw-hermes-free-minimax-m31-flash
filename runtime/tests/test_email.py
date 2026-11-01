import unittest
from unittest.mock import MagicMock, patch

from jahids_runtime.email import (
    EmailConfigurationError,
    SmtpMailer,
)


class SmtpMailerTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "JAHIDS_SMTP_HOST": "smtp.example.test",
            "JAHIDS_SMTP_PORT": "465",
            "JAHIDS_SMTP_SECURITY": "ssl",
            "JAHIDS_SMTP_USERNAME": "admin@example.test",
            "JAHIDS_SMTP_PASSWORD": "test-secret",
            "JAHIDS_EMAIL_FROM": "admin@example.test",
            "JAHIDS_EMAIL_ALLOWED_RECIPIENTS": "owner@example.test",
        }

    @patch("jahids_runtime.email.smtplib.SMTP_SSL")
    def test_sends_only_to_explicitly_allowed_recipient(self, smtp_class):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp_class.return_value = smtp
        result = SmtpMailer(self.env).send(
            "owner@example.test", "JAHIDS test", "Test message"
        )
        self.assertEqual(result["status"], "sent")
        smtp.login.assert_called_once_with("admin@example.test", "test-secret")
        smtp.send_message.assert_called_once()
        sent = smtp.send_message.call_args.args[0]
        self.assertEqual(sent["To"], "owner@example.test")

    def test_rejects_unlisted_recipient(self):
        with self.assertRaises(PermissionError):
            SmtpMailer(self.env).send(
                "other@example.test", "Subject", "Body"
            )

    def test_requires_smtp_credentials(self):
        env = dict(self.env)
        env["JAHIDS_SMTP_PASSWORD"] = ""
        with self.assertRaises(EmailConfigurationError):
            SmtpMailer(env).send("owner@example.test", "Subject", "Body")

    def test_rejects_invalid_message_lengths(self):
        with self.assertRaises(ValueError):
            SmtpMailer(self.env).send("owner@example.test", "", "Body")


if __name__ == "__main__":
    unittest.main()
