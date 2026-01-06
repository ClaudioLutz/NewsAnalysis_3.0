"""Outlook email service for sending HTML emails via COM automation."""

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from newsanalysis.utils.logging import get_logger

if TYPE_CHECKING:
    import pywintypes  # noqa: F401

logger = get_logger(__name__)


@dataclass
class EmailResult:
    """Result of an email operation."""

    success: bool
    message: str
    message_id: Optional[str] = None


class OutlookEmailService:
    """Service for sending emails via Outlook COM automation.

    This service uses pywin32/win32com to interact with Microsoft Outlook
    through Windows COM automation. Requires Outlook to be installed and
    configured on the machine.

    Use as context manager for proper resource cleanup:
        with OutlookEmailService() as service:
            service.send_html_email(...)
    """

    def __init__(self) -> None:
        """Initialize the email service."""
        self._outlook: Any = None
        self._available: Optional[bool] = None

    def __enter__(self) -> "OutlookEmailService":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and cleanup resources."""
        self.close()

    def close(self) -> None:
        """Release COM resources."""
        if self._outlook is not None:
            try:
                # Release COM object reference
                self._outlook = None
                logger.debug("outlook_connection_closed")
            except Exception as e:
                logger.warning("outlook_close_failed", error=str(e))

    def is_available(self) -> bool:
        """Check if Outlook automation is available on this system.

        Returns:
            True if pywin32 is installed and we're on Windows.
        """
        if self._available is not None:
            return self._available

        if sys.platform != "win32":
            logger.warning("outlook_not_available", reason="Not running on Windows")
            self._available = False
            return False

        try:
            import win32com.client  # noqa: F401

            self._available = True
            return True
        except ImportError:
            logger.warning(
                "outlook_not_available",
                reason="pywin32 not installed. Run: pip install pywin32",
            )
            self._available = False
            return False

    def connect(self) -> bool:
        """Establish connection to Outlook.

        Returns:
            True if connection successful, False otherwise.
        """
        if not self.is_available():
            return False

        try:
            import win32com.client

            self._outlook = win32com.client.Dispatch("Outlook.Application")
            logger.debug("outlook_connected")
            return True
        except Exception as e:
            logger.error("outlook_connection_failed", error=str(e))
            return False

    def send_html_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        preview: bool = False,
    ) -> EmailResult:
        """Send an HTML email via Outlook.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML content of the email body.
            preview: If True, display email in Outlook without sending.

        Returns:
            EmailResult with success status and message.
        """
        if not self._outlook:
            if not self.connect():
                return EmailResult(
                    success=False,
                    message="Could not connect to Outlook. Ensure Outlook is installed and running.",
                )

        try:
            import pywintypes

            # Create mail item (0 = olMailItem)
            mail = self._outlook.CreateItem(0)
            mail.To = to
            mail.Subject = subject
            mail.HTMLBody = html_body

            if preview:
                mail.Display(True)
                logger.info("email_displayed", recipient=to, subject=subject)
                return EmailResult(
                    success=True,
                    message="Email opened in Outlook for preview",
                )
            else:
                mail.Send()
                logger.info("email_sent", recipient=to, subject=subject)
                return EmailResult(
                    success=True,
                    message=f"Email sent successfully to {to}",
                )

        except pywintypes.com_error as e:
            # Defensive extraction of COM error details
            try:
                error_code = e.args[0] if e.args and len(e.args) > 0 else "Unknown"
                error_msg = e.args[2] if len(e.args) > 2 else str(e)
            except (IndexError, TypeError):
                error_code = "Unknown"
                error_msg = str(e)
            logger.error(
                "email_send_failed",
                error_code=str(error_code),
                error_message=str(error_msg),
            )
            return EmailResult(
                success=False,
                message=f"COM Error {error_code}: {error_msg}",
            )
        except Exception as e:
            logger.error("email_send_failed", error=str(e))
            return EmailResult(
                success=False,
                message=f"Unexpected error: {e}",
            )
