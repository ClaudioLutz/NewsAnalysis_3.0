"""Unit tests for email image embedding."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from newsanalysis.services.email_service import OutlookEmailService, EmailResult


@pytest.mark.unit
class TestEmailImageEmbedding:
    """Test email service with image attachments."""

    def test_send_html_email_with_images_success(self, tmp_path):
        """Test sending email with CID image attachments."""
        # Create test image file
        test_image = tmp_path / "test_image.jpg"
        test_image.write_bytes(b"fake image content")

        service = OutlookEmailService()

        # Mock Outlook connection
        mock_outlook = MagicMock()
        mock_mail = MagicMock()
        mock_attachment = MagicMock()

        mock_outlook.CreateItem.return_value = mock_mail
        mock_mail.Attachments.Add.return_value = mock_attachment

        service._outlook = mock_outlook

        # Prepare image attachments
        image_attachments = {
            "article_1_img": str(test_image),
        }

        # Send email with images
        result = service.send_html_email_with_images(
            to="test@example.com",
            subject="Test Digest",
            html_body='<html><body><img src="cid:article_1_img"></body></html>',
            image_attachments=image_attachments,
            preview=True,  # Use preview mode for testing
        )

        assert result.success is True
        assert "images" in result.message.lower()

        # Verify attachment was added
        mock_mail.Attachments.Add.assert_called_once()

        # Verify Content-ID was set
        mock_attachment.PropertyAccessor.SetProperty.assert_called_once_with(
            "http://schemas.microsoft.com/mapi/proptag/0x3712001F",
            "article_1_img",
        )

    def test_send_html_email_with_missing_image(self, tmp_path):
        """Test sending email when image file doesn't exist."""
        service = OutlookEmailService()

        # Mock Outlook connection
        mock_outlook = MagicMock()
        mock_mail = MagicMock()

        mock_outlook.CreateItem.return_value = mock_mail
        service._outlook = mock_outlook

        # Reference non-existent image
        image_attachments = {
            "article_1_img": str(tmp_path / "nonexistent.jpg"),
        }

        # Send email - should succeed but skip missing image
        result = service.send_html_email_with_images(
            to="test@example.com",
            subject="Test Digest",
            html_body='<html><body><img src="cid:article_1_img"></body></html>',
            image_attachments=image_attachments,
            preview=True,
        )

        assert result.success is True

        # Verify no attachment was added
        mock_mail.Attachments.Add.assert_not_called()

    def test_send_html_email_without_images(self):
        """Test sending email without image attachments."""
        service = OutlookEmailService()

        # Mock Outlook connection
        mock_outlook = MagicMock()
        mock_mail = MagicMock()

        mock_outlook.CreateItem.return_value = mock_mail
        service._outlook = mock_outlook

        # Send email without images
        result = service.send_html_email_with_images(
            to="test@example.com",
            subject="Test Digest",
            html_body="<html><body>Plain text</body></html>",
            image_attachments=None,  # No images
            preview=True,
        )

        assert result.success is True

        # Verify no attachments were attempted
        mock_mail.Attachments.Add.assert_not_called()

    def test_send_html_email_with_multiple_images(self, tmp_path):
        """Test sending email with multiple CID images."""
        # Create multiple test images
        images = {}
        for i in range(3):
            test_image = tmp_path / f"image_{i}.jpg"
            test_image.write_bytes(b"fake image content")
            images[f"article_{i}_img"] = str(test_image)

        service = OutlookEmailService()

        # Mock Outlook connection
        mock_outlook = MagicMock()
        mock_mail = MagicMock()
        mock_attachment = MagicMock()

        mock_outlook.CreateItem.return_value = mock_mail
        mock_mail.Attachments.Add.return_value = mock_attachment

        service._outlook = mock_outlook

        # Send email with multiple images
        result = service.send_html_email_with_images(
            to="test@example.com",
            subject="Test Digest",
            html_body='<html><body><img src="cid:article_0_img"><img src="cid:article_1_img"><img src="cid:article_2_img"></body></html>',
            image_attachments=images,
            preview=True,
        )

        assert result.success is True

        # Verify all 3 attachments were added
        assert mock_mail.Attachments.Add.call_count == 3

        # Verify all 3 Content-IDs were set
        assert mock_attachment.PropertyAccessor.SetProperty.call_count == 3
