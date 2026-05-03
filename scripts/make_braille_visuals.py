"""Generate slide-ready Braille-glyph visuals for the Kessai pitch deck.

Each UOR address is a 32-byte sequence; rendered as Braille each byte
becomes one Unicode codepoint U+2800 + byte. The result is a visually
distinctive 32-character string that's also a valid cryptographic identity.

Outputs three SVGs to pitch/visuals/:

  hero-uor-address.svg       Large hero shot of a single UOR address as Braille,
                              with the equivalent hex shown small underneath.

  hologram-cert.svg          The real cert:ModuleCertificate from
                              mcp/example-module-certificate.json — anchors the
                              "we're protocol-aligned" pitch.

  byte-to-glyph-primer.svg   Educational visual showing how 4 example bytes
                              map to Braille glyphs. Use on the slide that
                              explains the encoding.

These are SVG (text-based) so they scale to any resolution and edit in any
vector tool. Upload to Gamma directly, or convert to PNG with rsvg-convert.
"""

from __future__ import annotations

import json
from pathlib import Path


# Output directory.
OUT = Path(__file__).resolve().parent.parent / "pitch" / "visuals"
OUT.mkdir(parents=True, exist_ok=True)


def addr_to_glyph(addr_bytes: bytes) -> str:
    """Convert raw bytes to Braille codepoint string (U+2800 + byte each)."""
    return "".join(chr(0x2800 + b) for b in addr_bytes)


def svg_header(width: int, height: int, bg: str = "#0F1117") -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">\n'
        f'  <rect width="{width}" height="{height}" fill="{bg}"/>\n'
    )


def svg_footer() -> str:
    return "</svg>\n"


# ---------------------------------------------------------------------------
# Visual 1 — hero UOR address (sample cert hash)
# ---------------------------------------------------------------------------

def make_hero_address():
    """Render a stylized hero shot using the verified cross-check address.

    The hex is the SHA-256 of {"buyer":"alice","price":100,"task_id":"abc"}
    — the byte-identical-to-UOR-MCP fixture we live-verified.
    """
    hex_str = "4cc1e2fc2d60c1e0ab7f6967a59e23ad04094cd3c01351971b8cb5aa26013e67"
    addr_bytes = bytes.fromhex(hex_str)
    glyph = addr_to_glyph(addr_bytes)

    width, height = 1920, 1080
    svg = svg_header(width, height, bg="#0F1117")
    svg += f"""
  <!-- Headline -->
  <text x="{width // 2}" y="200" text-anchor="middle"
        font-family="system-ui, -apple-system, Helvetica, Arial, sans-serif"
        font-size="48" font-weight="300" fill="#9ca3af">
    one UOR address, four representations
  </text>

  <!-- Big Braille -->
  <text x="{width // 2}" y="540" text-anchor="middle"
        font-family="Menlo, Monaco, 'Courier New', monospace"
        font-size="120" font-weight="400" fill="#7DD3FC"
        letter-spacing="-2">
    {glyph}
  </text>

  <!-- Small label -->
  <text x="{width // 2}" y="640" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="32" font-weight="400" fill="#6B7280">
    store:uorAddress.u:glyph
  </text>

  <!-- Hex below -->
  <text x="{width // 2}" y="800" text-anchor="middle"
        font-family="Menlo, Monaco, 'Courier New', monospace"
        font-size="32" font-weight="400" fill="#9ca3af">
    sha256:{hex_str}
  </text>

  <!-- Footer -->
  <text x="{width // 2}" y="980" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="28" font-style="italic" fill="#6B7280">
    verified byte-identical to UOR Foundation's canonical reference
  </text>
"""
    svg += svg_footer()
    return svg


# ---------------------------------------------------------------------------
# Visual 2 — Hologram cert example (real published artifact)
# ---------------------------------------------------------------------------

def make_hologram_cert():
    """Render the real Hologram SDK cert:ModuleCertificate as a hero visual."""
    example_path = Path(__file__).resolve().parent.parent / "mcp" / "example-module-certificate.json"
    with open(example_path, "r", encoding="utf-8") as f:
        cert = json.load(f)
    glyph = cert["store:uorAddress"]["u:glyph"]
    cid = cert["cert:cid"]
    subject = cert["cert:subject"]

    width, height = 1920, 1080
    svg = svg_header(width, height, bg="#0F1117")
    svg += f"""
  <!-- Subtitle -->
  <text x="{width // 2}" y="180" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="36" font-weight="300" fill="#9ca3af">
    A real UOR Module Certificate
  </text>

  <!-- Subject -->
  <text x="{width // 2}" y="270" text-anchor="middle"
        font-family="Menlo, Monaco, monospace"
        font-size="36" font-weight="500" fill="#fb923c">
    {subject}
  </text>

  <!-- Big Braille -->
  <text x="{width // 2}" y="540" text-anchor="middle"
        font-family="Menlo, Monaco, 'Courier New', monospace"
        font-size="100" font-weight="400" fill="#7DD3FC"
        letter-spacing="-2">
    {glyph}
  </text>

  <!-- CID below -->
  <text x="{width // 2}" y="700" text-anchor="middle"
        font-family="Menlo, Monaco, monospace"
        font-size="22" font-weight="400" fill="#6B7280">
    {cid}
  </text>

  <!-- Footer -->
  <text x="{width // 2}" y="900" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="32" font-style="italic" fill="#9ca3af">
    every UOR-certified object has the same shape
  </text>
  <text x="{width // 2}" y="950" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="28" fill="#6B7280">
    Kessai certs follow the same format, byte-for-byte
  </text>
"""
    svg += svg_footer()
    return svg


# ---------------------------------------------------------------------------
# Visual 3 — Byte → Braille primer
# ---------------------------------------------------------------------------

def make_primer():
    """Educational diagram: how a byte becomes a Braille codepoint."""

    # Four illustrative byte values
    samples = [
        ("\\x00", 0x00, "empty (no bits set)"),
        ("\\x42", 0x42, "the letter 'B' in ASCII"),
        ("\\xff", 0xFF, "all bits set"),
        ("\\xa5", 0xA5, "alternating bits"),
    ]

    width, height = 1920, 1080
    svg = svg_header(width, height, bg="#0F1117")
    svg += f"""
  <!-- Title -->
  <text x="{width // 2}" y="120" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="48" font-weight="300" fill="#e5e7eb">
    Each byte becomes one Braille codepoint
  </text>
  <text x="{width // 2}" y="180" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="28" fill="#9ca3af">
    codepoint = U+2800 + byte_value
  </text>

  <!-- Header row -->
  <text x="350" y="320" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="24" fill="#6B7280">byte</text>
  <text x="800" y="320" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="24" fill="#6B7280">codepoint</text>
  <text x="1250" y="320" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="24" fill="#6B7280">glyph</text>
  <text x="1700" y="320" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="24" fill="#6B7280">meaning</text>

  <line x1="200" y1="350" x2="1820" y2="350" stroke="#374151" stroke-width="1"/>
"""

    y = 440
    for label, byte_val, meaning in samples:
        glyph = chr(0x2800 + byte_val)
        codepoint_label = f"U+{0x2800 + byte_val:04X}"
        svg += f"""
  <text x="350" y="{y}" text-anchor="middle"
        font-family="Menlo, Monaco, monospace"
        font-size="44" fill="#fb923c">
    0x{byte_val:02X}
  </text>
  <text x="800" y="{y}" text-anchor="middle"
        font-family="Menlo, Monaco, monospace"
        font-size="36" fill="#9ca3af">
    {codepoint_label}
  </text>
  <text x="1250" y="{y}" text-anchor="middle"
        font-family="Menlo, Monaco, monospace"
        font-size="100" fill="#7DD3FC">
    {glyph}
  </text>
  <text x="1700" y="{y - 12}" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="22" fill="#9ca3af">
    {meaning}
  </text>
"""
        y += 160

    svg += f"""
  <!-- Footer -->
  <text x="{width // 2}" y="{height - 60}" text-anchor="middle"
        font-family="system-ui, -apple-system, sans-serif"
        font-size="28" font-style="italic" fill="#6B7280">
    32 bytes -> 32 Braille codepoints. The address IS the byte sequence, visualized.
  </text>
"""
    svg += svg_footer()
    return svg


def main():
    out_files = {
        "hero-uor-address.svg": make_hero_address(),
        "hologram-cert.svg": make_hologram_cert(),
        "byte-to-glyph-primer.svg": make_primer(),
    }
    for name, svg in out_files.items():
        path = OUT / name
        path.write_text(svg, encoding="utf-8")
        print(f"  wrote {path.relative_to(Path(__file__).resolve().parent.parent)} ({path.stat().st_size:,} bytes)")
    print()
    print("Upload these to Gamma:")
    print("  - hero-uor-address.svg     -> headline slide for 'verified byte-identical' moment")
    print("  - hologram-cert.svg        -> 'real UOR cert example' slide")
    print("  - byte-to-glyph-primer.svg -> 'how the encoding works' explainer slide")


if __name__ == "__main__":
    main()
