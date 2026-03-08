import os
from unittest.mock import patch, MagicMock
from backend.services.email.email_service import EmailService


@patch("imaplib.IMAP4_SSL")
def test_email_connection(mock_imap):

    mock_instance = MagicMock()
    mock_imap.return_value = mock_instance

    os.environ["EMAIL_USER"] = "test@gmail.com"
    os.environ["EMAIL_PASS"] = "testpass"

    service = EmailService(enable_auth=False)

    assert service.read_unread_emails() is not None