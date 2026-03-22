#!/usr/bin/env python3
"""
Generate the forensics challenge file.

This script creates a PNG file with a hidden flag.
"""

import os
from pathlib import Path

# Challenge configuration
FLAG = "FLAG{h1dd3n_1n_pl41n_s1ght}"

def create_minimal_png_with_hidden_data():
    """Create a minimal valid PNG with hidden flag appended."""

    # Minimal 1x1 white PNG (valid PNG structure)
    # PNG signature + IHDR + IDAT + IEND
    png_data = bytes([
        # PNG Signature
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        # IHDR chunk (13 bytes data)
        0x00, 0x00, 0x00, 0x0D,  # Length
        0x49, 0x48, 0x44, 0x52,  # Type: IHDR
        0x00, 0x00, 0x00, 0x01,  # Width: 1
        0x00, 0x00, 0x00, 0x01,  # Height: 1
        0x08, 0x02,              # Bit depth: 8, Color type: RGB
        0x00, 0x00, 0x00,        # Compression, Filter, Interlace
        0x90, 0x77, 0x53, 0xDE,  # CRC
        # IDAT chunk (minimal compressed data for 1x1 white pixel)
        0x00, 0x00, 0x00, 0x0C,  # Length
        0x49, 0x44, 0x41, 0x54,  # Type: IDAT
        0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
        0x05, 0xFE, 0x02, 0xFE,
        0xA3, 0x6C, 0xEC, 0xB5,  # CRC
        # IEND chunk
        0x00, 0x00, 0x00, 0x00,  # Length
        0x49, 0x45, 0x4E, 0x44,  # Type: IEND
        0xAE, 0x42, 0x60, 0x82,  # CRC
    ])

    # Append hidden data after the PNG (still valid PNG, extra data ignored)
    hidden_data = f"\n\n<!-- Secret: {FLAG} -->\n".encode()

    return png_data + hidden_data


def main():
    # Create output directory
    output_dir = Path(__file__).parent.parent / "files"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate the challenge file
    output_file = output_dir / "mystery.png"
    png_with_flag = create_minimal_png_with_hidden_data()

    output_file.write_bytes(png_with_flag)
    print(f"[+] Generated: {output_file}")
    print(f"[+] File size: {len(png_with_flag)} bytes")
    print(f"[+] Hidden flag: {FLAG}")

    # Verify
    print("\n[*] Verification:")
    print(f"    strings {output_file} | grep FLAG")


if __name__ == "__main__":
    main()
