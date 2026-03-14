# Fix AVIF Images Not Displaying in Outlook

## Summary

20 Minuten images were not displaying in the Outlook email digest because their CDN returns AVIF images (via `?auto=format` URL parameter) despite the URL having `.jpg`/`.png` extensions. Outlook cannot render AVIF. Added automatic conversion of AVIF/WebP to JPEG in the image cache layer.

## Context / Problem

The 20min.ch CDN uses automatic format negotiation (`?auto=format,compress,enhance` query parameters). When the HTTP client doesn't send an explicit `Accept: image/jpeg` header, the CDN returns AVIF images — a modern format that Outlook does not support. The images were saved with the URL-derived extension (`.jpg`, `.png`) but contained AVIF binary data, causing Outlook to silently fail to render them.

## What Changed

- **`src/newsanalysis/services/image_cache.py`**: Added `_convert_for_outlook()` method that detects non-Outlook-compatible formats (AVIF, WebP) from image binary headers using Pillow, and converts them to JPEG. Integrated into `save_image()` so all cached images are automatically Outlook-compatible. Changed `save_image()` return type from `bool` to `Optional[Path]` to reflect that the saved path may differ from the requested path after format conversion.
- **`src/newsanalysis/services/image_download_service.py`**: Updated `_download_single_image()` to use the actual saved path returned by `save_image()`. Added cache lookup for `.jpg` variant when the original extension doesn't exist (handles re-runs after conversion).
- **`tests/unit/test_image_cache.py`**: Updated `test_save_and_get_image` for new `save_image()` return type.
- **`tests/integration/test_image_pipeline.py`**: Updated `test_image_cache_integration` for new `save_image()` return type.
- Converted 14 existing cached AVIF images to JPEG and updated database records.

## How to Test

```bash
# Run image-related tests
pytest tests/ -k "image" --ignore=tests/unit/test_date_utils.py

# Regenerate digest and verify images appear in Outlook
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

## Risk / Rollback Notes

- Low risk. Pillow (already a dependency) handles the conversion. Only non-Outlook-compatible formats are converted; standard JPEG/PNG/GIF pass through unchanged.
- JPEG quality is set to 90, which is visually near-lossless but increases file size compared to AVIF.
- Rollback: revert the code changes. Cached images already converted to JPEG will continue to work.
