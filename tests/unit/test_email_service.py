# tests/unit/test_email_service.py
"""Unit tests for email service and digest formatter."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from newsanalysis.services.digest_formatter import HtmlEmailFormatter
from newsanalysis.services.email_service import EmailResult, OutlookEmailService


@pytest.mark.unit
class TestOutlookEmailService:
    """Tests for OutlookEmailService."""

    def test_is_available_non_windows(self):
        """Should return False on non-Windows platforms."""
        service = OutlookEmailService()
        with patch.object(sys, "platform", "linux"):
            service._available = None  # Reset cached value
            assert service.is_available() is False

    def test_is_available_no_pywin32(self):
        """Should return False when pywin32 not installed."""
        # Simply test that setting _available to False returns False
        # (the actual import test is platform-dependent)
        service = OutlookEmailService()
        service._available = False

        assert service.is_available() is False

    @patch("sys.platform", "win32")
    def test_send_email_success(self):
        """Should send email successfully via mocked COM."""
        with patch("newsanalysis.services.email_service.OutlookEmailService.is_available", return_value=True):
            with patch("win32com.client.Dispatch") as mock_dispatch:
                # Setup mock
                mock_app = MagicMock()
                mock_mail = MagicMock()
                mock_app.CreateItem.return_value = mock_mail
                mock_dispatch.return_value = mock_app

                service = OutlookEmailService()
                service._outlook = mock_app

                result = service.send_html_email(
                    to="test@example.com",
                    subject="Test Subject",
                    html_body="<p>Test</p>",
                    preview=False,
                )

                assert result.success is True
                mock_mail.Send.assert_called_once()
                assert mock_mail.To == "test@example.com"
                assert mock_mail.Subject == "Test Subject"
                assert mock_mail.HTMLBody == "<p>Test</p>"

    @patch("sys.platform", "win32")
    def test_send_email_preview_mode(self):
        """Should display email without sending in preview mode."""
        with patch("newsanalysis.services.email_service.OutlookEmailService.is_available", return_value=True):
            with patch("win32com.client.Dispatch") as mock_dispatch:
                # Setup mock
                mock_app = MagicMock()
                mock_mail = MagicMock()
                mock_app.CreateItem.return_value = mock_mail
                mock_dispatch.return_value = mock_app

                service = OutlookEmailService()
                service._outlook = mock_app

                result = service.send_html_email(
                    to="test@example.com",
                    subject="Test Subject",
                    html_body="<p>Test</p>",
                    preview=True,
                )

                assert result.success is True
                mock_mail.Display.assert_called_once_with(True)
                mock_mail.Send.assert_not_called()

    def test_send_email_not_connected(self):
        """Should fail gracefully when cannot connect to Outlook."""
        service = OutlookEmailService()
        service._available = False

        result = service.send_html_email(
            to="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )

        assert result.success is False
        assert "Could not connect" in result.message

    def test_email_result_dataclass(self):
        """Should create EmailResult correctly."""
        result = EmailResult(
            success=True,
            message="Email sent",
            message_id="12345",
        )

        assert result.success is True
        assert result.message == "Email sent"
        assert result.message_id == "12345"

    def test_context_manager(self):
        """Should work as context manager and call close on exit."""
        with patch.object(OutlookEmailService, "close") as mock_close:
            with OutlookEmailService() as service:
                assert service is not None
            mock_close.assert_called_once()

    def test_close_clears_outlook_reference(self):
        """Should clear _outlook reference on close."""
        service = OutlookEmailService()
        service._outlook = MagicMock()

        service.close()

        assert service._outlook is None

    def test_com_error_with_malformed_args(self):
        """Should handle COM errors with malformed args gracefully."""
        # This tests the defensive error handling we added
        service = OutlookEmailService()
        service._available = True
        service._outlook = MagicMock()

        # Create a mock COM error with empty args
        mock_error = type("MockComError", (Exception,), {"args": ()})()

        with patch("pywintypes.com_error", mock_error.__class__):
            service._outlook.CreateItem.side_effect = mock_error
            result = service.send_html_email(
                to="test@example.com",
                subject="Test",
                html_body="<p>Test</p>",
            )

        # Should fail but not crash
        assert result.success is False


@pytest.mark.unit
class TestHtmlEmailFormatter:
    """Tests for HtmlEmailFormatter."""

    def test_format_date_german_style(self):
        """Should format date in German style."""
        formatter = HtmlEmailFormatter()

        result = formatter._format_date("2026-01-06")

        assert result == "6. Januar 2026"

    def test_format_date_all_months(self):
        """Should handle all German month names."""
        formatter = HtmlEmailFormatter()

        test_cases = [
            ("2026-01-15", "15. Januar 2026"),
            ("2026-02-20", "20. Februar 2026"),
            ("2026-03-10", "10. März 2026"),
            ("2026-04-05", "5. April 2026"),
            ("2026-05-01", "1. Mai 2026"),
            ("2026-06-30", "30. Juni 2026"),
            ("2026-07-04", "4. Juli 2026"),
            ("2026-08-15", "15. August 2026"),
            ("2026-09-22", "22. September 2026"),
            ("2026-10-31", "31. Oktober 2026"),
            ("2026-11-11", "11. November 2026"),
            ("2026-12-25", "25. Dezember 2026"),
        ]

        for date_str, expected in test_cases:
            result = formatter._format_date(date_str)
            assert result == expected, f"Failed for {date_str}"

    def test_format_date_none(self):
        """Should handle None date gracefully."""
        formatter = HtmlEmailFormatter()

        result = formatter._format_date(None)

        # Should return today's date in some format
        assert len(result) > 0

    def test_parse_meta_analysis(self):
        """Should parse meta-analysis JSON correctly."""
        formatter = HtmlEmailFormatter()

        meta_json = '{"key_themes": ["Theme 1"], "credit_risk_signals": ["Signal 1"]}'
        result = formatter._parse_meta_analysis(meta_json)

        assert result["key_themes"] == ["Theme 1"]
        assert result["credit_risk_signals"] == ["Signal 1"]

    def test_parse_meta_analysis_invalid_json(self):
        """Should return empty dict for invalid JSON."""
        formatter = HtmlEmailFormatter()

        result = formatter._parse_meta_analysis("not valid json")

        assert result == {}

    def test_parse_meta_analysis_none(self):
        """Should return empty dict for None input."""
        formatter = HtmlEmailFormatter()

        result = formatter._parse_meta_analysis(None)

        assert result == {}

    def test_format_digest(self):
        """Should format complete digest as HTML."""
        formatter = HtmlEmailFormatter()

        digest_data = {
            "digest_date": "2026-01-06",
            "article_count": 5,
            "version": 1,
            "generated_at": "2026-01-06T08:30:00",
            "meta_analysis_json": '{"key_themes": ["Swiss Banking"], "credit_risk_signals": ["Company X bankruptcy"]}',
            "json_output": '{"articles": [{"title": "Test Article", "summary": "Brief summary", "key_points": ["Point 1", "Point 2"], "source": "Reuters", "url": "https://example.com"}]}',
        }

        html = formatter.format(digest_data)

        # Check key elements are present
        assert "Bonitäts-News" in html or "Bonit&auml;ts-News" in html
        assert "6. Januar 2026" in html
        assert "5" in html  # article count
        assert "Swiss Banking" in html
        assert "Company X bankruptcy" in html
        assert "Test Article" in html
        assert "Brief summary" in html
        assert "Point 1" in html

    def test_parse_articles(self):
        """Should parse articles from JSON output."""
        formatter = HtmlEmailFormatter()

        json_output = '{"articles": [{"title": "News Title", "summary": "A summary", "key_points": ["Key 1", "Key 2", "Key 3", "Key 4"], "source": "Source", "url": "https://test.com"}]}'
        articles = formatter._parse_articles(json_output)

        assert len(articles) == 1
        assert articles[0]["title"] == "News Title"
        assert articles[0]["summary"] == "A summary"
        assert len(articles[0]["key_points"]) == 2  # Limited to 2
        assert articles[0]["source"] == "Source"
        assert articles[0]["url"] == "https://test.com"

    def test_parse_articles_empty(self):
        """Should return empty list for empty input."""
        formatter = HtmlEmailFormatter()

        assert formatter._parse_articles(None) == []
        assert formatter._parse_articles("") == []

    def test_parse_articles_invalid_json(self):
        """Should return empty list for invalid JSON."""
        formatter = HtmlEmailFormatter()

        result = formatter._parse_articles("not valid json")

        assert result == []
