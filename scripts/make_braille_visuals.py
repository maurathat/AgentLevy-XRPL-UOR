"""Generate slide-ready Braille-glyph visuals for the Kessai pitch deck.

Each UOR address is a 32-byte sequence; rendered as Braille each byte
becomes one Unicode codepoint U+2800 + byte. The result is a visually
distinctive 32-character string that's also a valid cryptographic identity.

Outputs three visuals to ``pitch/visuals/`` — each as both SVG (vector,
editable in any tool) and PNG (1920x1080, ready to drag into Gamma /
Keynote / PowerPoint):

  hero-uor-address.{svg,png}      Large hero shot of a single UOR address
                                   as Braille, with hex underneath.

  hologram-cert.{svg,png}         The real cert:ModuleCertificate from
                                   mcp/example-module-certificate.json —
                                   anchors the "we're protocol-aligned" pitch.

  byte-to-glyph-primer.{svg,png}  Educational visual showing how 4 example
                                   bytes map to Braille glyphs. Use on the
                                   slide that explains the encoding.

PNG rendering uses ``rsvg-convert`` (``brew install librsvg``). If it's
missing, the script still writes the SVGs and prints an install hint
instead of failing.

Run with ``--no-png`` to skip PNG rendering even if rsvg-convert is
available.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


# Output directory.
OUT = Path(__file__).resolve().parent.parent / "pitch" / "visuals"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Brand constants — pulled from Kessai/Kessaibrandkit/kessai_brand_kit.html
# ---------------------------------------------------------------------------
# Single source of truth: edit here, re-run the script, all visuals stay
# in sync with the brand kit. Color names are the brand's own (Japanese
# pigment terminology).

# Colors
RURI = "#283A8C"            # Primary indigo — hero/stamp ground
RURI_DEEP = "#1B2864"       # Deep indigo — alternate ground
KARAKURENAI = "#B0223A"     # Accent crimson — seal, settled state
KARAKURENAI_DEEP = "#8A1A2E"
PAPER = "#F6F7FA"           # Document ground (light)
HAKUJI_DEEP = "#ECEFF5"     # Slightly cooler paper
WASHI = "#F4EFE4"           # Cream — type on indigo
SUMI = "#1A1714"            # Ink — body type on light grounds
GIN = "#9BA0A0"             # Silver — hairlines, tertiary

# Pairing rule (from brand kit): Ruri and Karakurenai do not touch directly
# except inside the sealed hanko. Around them, Cream (on indigo) or Paper
# (on white) is the breathing surface.

# Fonts (installed via `brew install --cask font-fraunces font-dm-sans
# font-ibm-plex-mono font-noto-serif-jp` — required for rsvg-convert PNG
# rendering to embed the right glyphs).
FONT_DISPLAY = "'Fraunces', 'Times New Roman', serif"
FONT_BODY = "'DM Sans', 'Helvetica Neue', sans-serif"
FONT_MONO = "'IBM Plex Mono', Menlo, monospace"
FONT_KANJI = "'Noto Serif JP', 'Hiragino Mincho ProN', serif"


def addr_to_glyph(addr_bytes: bytes) -> str:
    """Convert raw bytes to Braille codepoint string (U+2800 + byte each)."""
    return "".join(chr(0x2800 + b) for b in addr_bytes)


def svg_header(width: int, height: int, bg: str = RURI) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">\n'
        f'  <rect width="{width}" height="{height}" fill="{bg}"/>\n'
    )


def svg_footer() -> str:
    return "</svg>\n"


def kessai_attribution(x: int, y: int, on_dark: bool = True) -> str:
    """Small wordmark attribution. Place in slide footer.

    Uses DM Sans for the latin name and Noto Serif JP for the kanji.
    Color flips based on ground.
    """
    color = WASHI if on_dark else SUMI
    return f'''
  <g opacity="0.55">
    <text x="{x}" y="{y}" text-anchor="end"
          font-family="{FONT_BODY}" font-size="20" font-weight="500"
          letter-spacing="2" fill="{color}">KESSAI</text>
    <text x="{x + 14}" y="{y}" text-anchor="start"
          font-family="{FONT_KANJI}" font-size="20" font-weight="500"
          fill="{color}">·  決済</text>
  </g>'''


# ---------------------------------------------------------------------------
# Visual 1 — hero UOR address (sample cert hash)
# ---------------------------------------------------------------------------

def make_hero_address():
    """Hero shot — UOR address as Braille, brand-aligned (Ruri ground, hanko-on-paper).

    The hex is the SHA-256 of {"buyer":"alice","price":100,"task_id":"abc"} —
    the byte-identical-to-UOR-MCP fixture we live-verified.

    Composition follows the brand kit's "Hero · Stamp · Cover" mode: deep
    indigo (Ruri) ground with a centered washi panel acting as the hanko
    paper, glyph in karakurenai (the seal/settled color) so Ruri and
    Karakurenai never touch except inside the sealed hanko.
    """
    hex_str = "4cc1e2fc2d60c1e0ab7f6967a59e23ad04094cd3c01351971b8cb5aa26013e67"
    addr_bytes = bytes.fromhex(hex_str)
    glyph = addr_to_glyph(addr_bytes)

    width, height = 1920, 1080
    glyph_y = 580  # vertical center of the karakurenai glyph

    svg = svg_header(width, height, bg=RURI)
    svg += f"""
  <!-- Top hairline (Cream-on-Ruri) -->
  <line x1="130" y1="120" x2="{width - 130}" y2="120"
        stroke="{WASHI}" stroke-width="1" opacity="0.32"/>

  <!-- Eyebrow / kicker -->
  <text x="130" y="180" text-anchor="start"
        font-family="{FONT_BODY}" font-size="22" font-weight="500"
        letter-spacing="3" fill="{WASHI}" opacity="0.7">
    UOR · CONTENT ADDRESS
  </text>

  <!-- Headline (Fraunces, Cream) -->
  <text x="{width // 2}" y="320" text-anchor="middle"
        font-family="{FONT_DISPLAY}" font-size="64" font-weight="600"
        fill="{WASHI}">
    One address. Four representations.
  </text>

  <!-- Big Braille glyph (Karakurenai on Ruri ground) -->
  <text x="{width // 2}" y="{glyph_y}" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="92" font-weight="500"
        fill="{KARAKURENAI}">
    {glyph}
  </text>

  <!-- Hex below (IBM Plex Mono, Cream) -->
  <text x="{width // 2}" y="800" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="28" font-weight="500"
        fill="{WASHI}">
    sha256:{hex_str}
  </text>
  <text x="{width // 2}" y="848" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="22" font-weight="500"
        letter-spacing="2" fill="{WASHI}" opacity="0.6">
    store:uorAddress.u:glyph
  </text>

  <!-- Footer line: brand voice + attribution -->
  <text x="130" y="{height - 70}" text-anchor="start"
        font-family="{FONT_DISPLAY}" font-size="26" font-weight="500"
        font-style="italic" fill="{WASHI}" opacity="0.85">
    Verified byte-identical to UOR Foundation's canonical reference.
  </text>
  {kessai_attribution(width - 130, height - 70, on_dark=True)}
"""
    svg += svg_footer()
    return svg


# ---------------------------------------------------------------------------
# Visual 2 — Hologram cert example (real published artifact)
# ---------------------------------------------------------------------------

def make_hologram_cert():
    """Render the real Hologram SDK cert:ModuleCertificate as a hero visual.

    Brand-aligned: Ruri ground, hanko-paper panel for the karakurenai glyph,
    Fraunces headline, IBM Plex Mono for the CID, DM Sans for body text.
    """
    example_path = Path(__file__).resolve().parent.parent / "mcp" / "example-module-certificate.json"
    with open(example_path, "r", encoding="utf-8") as f:
        cert = json.load(f)
    glyph = cert["store:uorAddress"]["u:glyph"]
    cid = cert["cert:cid"]
    subject = cert["cert:subject"]

    width, height = 1920, 1080
    glyph_y = 600  # vertical center of the karakurenai glyph

    svg = svg_header(width, height, bg=RURI)
    svg += f"""
  <!-- Top hairline -->
  <line x1="130" y1="120" x2="{width - 130}" y2="120"
        stroke="{WASHI}" stroke-width="1" opacity="0.32"/>

  <!-- Eyebrow -->
  <text x="130" y="180" text-anchor="start"
        font-family="{FONT_BODY}" font-size="22" font-weight="500"
        letter-spacing="3" fill="{WASHI}" opacity="0.7">
    UOR · MODULE CERTIFICATE
  </text>

  <!-- Headline -->
  <text x="{width // 2}" y="290" text-anchor="middle"
        font-family="{FONT_DISPLAY}" font-size="60" font-weight="600"
        fill="{WASHI}">
    A real UOR cert in the wild.
  </text>

  <!-- Subject (mono, Cream) -->
  <text x="{width // 2}" y="385" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="30" font-weight="500"
        fill="{WASHI}" opacity="0.85">
    {subject}
  </text>

  <!-- Big Braille glyph (Karakurenai on Ruri ground) -->
  <text x="{width // 2}" y="{glyph_y}" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="86" font-weight="500"
        fill="{KARAKURENAI}">
    {glyph}
  </text>

  <!-- CID below -->
  <text x="{width // 2}" y="800" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="22" font-weight="400"
        fill="{WASHI}" opacity="0.7">
    {cid}
  </text>

  <!-- Footer line: brand voice + attribution -->
  <text x="130" y="{height - 70}" text-anchor="start"
        font-family="{FONT_DISPLAY}" font-size="26" font-weight="500"
        font-style="italic" fill="{WASHI}" opacity="0.85">
    Every UOR-certified object has the same shape. Kessai's, byte-for-byte.
  </text>
  {kessai_attribution(width - 130, height - 70, on_dark=True)}
"""
    svg += svg_footer()
    return svg


# ---------------------------------------------------------------------------
# Visual 3 — Byte → Braille primer
# ---------------------------------------------------------------------------

def make_primer():
    """Educational diagram: how a byte becomes a Braille codepoint.

    Brand-aligned in the kit's "Document · UI · Receipt" treatment: Paper
    ground, Sumi body type, Ruri headers, Karakurenai glyphs. Hairlines in
    Gin per the brand pairing logic.
    """

    # Four illustrative byte values
    samples = [
        (0x00, "empty (no bits set)"),
        (0x42, "the letter 'B' in ASCII"),
        (0xFF, "all bits set"),
        (0xA5, "alternating bits"),
    ]

    width, height = 1920, 1080
    svg = svg_header(width, height, bg=PAPER)
    svg += f"""
  <!-- Top hairline -->
  <line x1="130" y1="120" x2="{width - 130}" y2="120"
        stroke="{GIN}" stroke-width="1" opacity="0.4"/>

  <!-- Eyebrow -->
  <text x="130" y="180" text-anchor="start"
        font-family="{FONT_BODY}" font-size="22" font-weight="500"
        letter-spacing="3" fill="{RURI}">
    UOR · ENCODING PRIMER
  </text>

  <!-- Title (Fraunces, Sumi) -->
  <text x="{width // 2}" y="280" text-anchor="middle"
        font-family="{FONT_DISPLAY}" font-size="60" font-weight="600"
        fill="{SUMI}">
    Each byte becomes one Braille codepoint.
  </text>
  <text x="{width // 2}" y="340" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="26" font-weight="500"
        fill="{RURI}">
    codepoint = U+2800 + byte_value
  </text>

  <!-- Header row labels (DM Sans, Gin) -->
  <text x="350" y="450" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="20" font-weight="500"
        letter-spacing="2" fill="{GIN}">BYTE</text>
  <text x="800" y="450" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="20" font-weight="500"
        letter-spacing="2" fill="{GIN}">CODEPOINT</text>
  <text x="1250" y="450" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="20" font-weight="500"
        letter-spacing="2" fill="{GIN}">GLYPH</text>
  <text x="1700" y="450" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="20" font-weight="500"
        letter-spacing="2" fill="{GIN}">MEANING</text>

  <line x1="200" y1="475" x2="1820" y2="475"
        stroke="{GIN}" stroke-width="1" opacity="0.45"/>
"""

    y = 555
    for byte_val, meaning in samples:
        glyph = chr(0x2800 + byte_val)
        codepoint_label = f"U+{0x2800 + byte_val:04X}"
        svg += f"""
  <text x="350" y="{y}" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="38" font-weight="600"
        fill="{RURI}">
    0x{byte_val:02X}
  </text>
  <text x="800" y="{y}" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="30" font-weight="500"
        fill="{SUMI}">
    {codepoint_label}
  </text>
  <text x="1250" y="{y + 8}" text-anchor="middle"
        font-family="{FONT_MONO}" font-size="76" font-weight="500"
        fill="{KARAKURENAI}">
    {glyph}
  </text>
  <text x="1700" y="{y - 4}" text-anchor="middle"
        font-family="{FONT_BODY}" font-size="22" font-weight="500"
        fill="{SUMI}">
    {meaning}
  </text>
"""
        y += 110

    svg += f"""
  <!-- Bottom hairline -->
  <line x1="130" y1="{height - 130}" x2="{width - 130}" y2="{height - 130}"
        stroke="{GIN}" stroke-width="1" opacity="0.4"/>

  <!-- Footer voice line + attribution -->
  <text x="130" y="{height - 70}" text-anchor="start"
        font-family="{FONT_DISPLAY}" font-size="24" font-weight="500"
        font-style="italic" fill="{SUMI}">
    32 bytes → 32 Braille codepoints. The address IS the byte sequence, visualized.
  </text>
  {kessai_attribution(width - 130, height - 70, on_dark=False)}
"""
    svg += svg_footer()
    return svg


def render_png(svg_path: Path, width: int = 1920, height: int = 1080) -> Path | None:
    """Render an SVG to PNG via rsvg-convert. Returns the PNG path on success.

    Returns None (without raising) if ``rsvg-convert`` isn't installed —
    callers should print an install hint instead of crashing the SVG-only
    fast path.
    """
    if shutil.which("rsvg-convert") is None:
        return None
    png_path = svg_path.with_suffix(".png")
    subprocess.run(
        ["rsvg-convert", "-w", str(width), "-h", str(height),
         "-o", str(png_path), str(svg_path)],
        check=True,
    )
    return png_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-png", action="store_true",
                        help="Skip PNG rendering even if rsvg-convert is installed.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_files = {
        "hero-uor-address.svg": make_hero_address(),
        "hologram-cert.svg": make_hologram_cert(),
        "byte-to-glyph-primer.svg": make_primer(),
    }

    svg_paths: list[Path] = []
    for name, svg in out_files.items():
        path = OUT / name
        path.write_text(svg, encoding="utf-8")
        svg_paths.append(path)
        print(f"  wrote {path.relative_to(repo_root)} ({path.stat().st_size:,} bytes)")

    if args.no_png:
        print("\n(--no-png set; PNG rendering skipped.)")
    elif shutil.which("rsvg-convert") is None:
        print(
            "\nrsvg-convert not found — SVGs only. To get PNG output:\n"
            "  brew install librsvg\n"
            "then re-run this script."
        )
    else:
        print()
        for svg_path in svg_paths:
            png_path = render_png(svg_path)
            print(f"  wrote {png_path.relative_to(repo_root)} ({png_path.stat().st_size:,} bytes)")

    print()
    print("Upload these to Gamma (PNG drags in cleanly; SVG also works):")
    print("  - hero-uor-address     -> headline slide for 'verified byte-identical' moment")
    print("  - hologram-cert        -> 'real UOR cert example' slide")
    print("  - byte-to-glyph-primer -> 'how the encoding works' explainer slide")


if __name__ == "__main__":
    main()
