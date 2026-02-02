#!/usr/bin/env python3
"""Create Swiss flag logo PNG using Pillow.

This draws the logo programmatically without requiring SVG conversion.

Usage:
    pip install Pillow
    python scripts/create_guardian_logo_png.py
"""

from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Pillow not installed.")
    print("Install with: pip install Pillow")
    exit(1)


def create_swiss_flag():
    """Create a simple Swiss flag icon as PNG.

    Design: Red square with white cross (official Swiss proportions)
    Size: 80x80 (displays at 40x40 in email)
    """
    # 2x resolution for crisp display
    size = 80

    # Swiss flag colors
    swiss_red = (255, 0, 0)      # Official Swiss red
    white = (255, 255, 255)

    # Create image with red background
    img = Image.new('RGB', (size, size), swiss_red)
    draw = ImageDraw.Draw(img)

    # Swiss cross proportions: cross is 1/5 width, 3/5 length
    # Using official proportions from Swiss government
    cross_width = size // 5        # Width of cross arm
    cross_length = size * 3 // 5   # Length of cross arm

    # Center point
    cx, cy = size // 2, size // 2

    # Horizontal bar of cross
    h_left = cx - cross_length // 2
    h_right = cx + cross_length // 2
    h_top = cy - cross_width // 2
    h_bottom = cy + cross_width // 2
    draw.rectangle([h_left, h_top, h_right, h_bottom], fill=white)

    # Vertical bar of cross
    v_left = cx - cross_width // 2
    v_right = cx + cross_width // 2
    v_top = cy - cross_length // 2
    v_bottom = cy + cross_length // 2
    draw.rectangle([v_left, v_top, v_right, v_bottom], fill=white)

    # Save
    output_path = Path(__file__).parent.parent / "docs" / "assets" / "swiss-flag.png"
    img.save(output_path, 'PNG')

    print(f"Created: {output_path}")
    print(f"Size: {output_path.stat().st_size} bytes")
    print(f"Dimensions: {size}x{size} (displays at 40x40)")

    return output_path


if __name__ == "__main__":
    create_swiss_flag()
