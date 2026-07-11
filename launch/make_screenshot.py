#!/usr/bin/env python3
"""Generate terminal-window SVG screenshot from agentnap advise output.

Usage:
    python3 launch/make_screenshot.py
    python3 launch/make_screenshot.py --input launch/assets/advise_sample.txt --output launch/assets/advise.svg
"""

import argparse
import os
import xml.sax.saxutils as saxutils

# ── Palette (Catppuccin Mocha inspired) ────────────────────────────────
BG        = "#1e1e2e"
TITLE_BG  = "#181825"
BORDER    = "#45475a"
SEPARATOR = "#313244"
FG        = "#cdd6f4"  # default text
GRAY      = "#a6adc8"  # muted lines & title text
YELLOW    = "#f9e2af"  # bullets
TEAL      = "#94e2d5"  # inline code (backtick)
GREEN     = "#a6e3a1"  # status OK
BLUE      = "#89b4fa"  # highlight label

FONT      = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace"
FONT_SIZE = 13
LINE_H    = 21  # line-height ~1.6

W       = 820  # widest sample line is ~97 chars × ~7.8px at 13px mono + padding
TITLE_H = 38
PT      = 16   # padding top (below title bar)
PL      = 24   # padding left
PB      = 16   # padding bottom

# ── XML helpers ────────────────────────────────────────────────────────

def esc(text):
    return saxutils.escape(text)


def _parse_spans(text):
    """Split text into (segment, is_code) pairs by backtick pairs."""
    segments = []
    buf = []
    in_code = False
    for ch in text:
        if ch == '`':
            if buf:
                segments.append((''.join(buf), in_code))
                buf = []
            in_code = not in_code
        else:
            buf.append(ch)
    if buf:
        segments.append((''.join(buf), in_code))
    return segments


def _line_style(text, line_idx, total):
    """Return list of (segment_text, fill) for one line."""
    stripped = text.strip()
    if not stripped:
        return [(' ', FG)]

    # Line 0: stethoscope line → gray
    if line_idx == 0:
        return [(text, GRAY)]

    # Last line: guarantee → gray
    if line_idx == total - 1:
        return [(text, GRAY)]

    spans = _parse_spans(text)
    out = []

    for seg, is_code in spans:
        if is_code:
            out.append((seg, TEAL))
        elif '•' in seg:
            _bullet_style(seg, out)
        elif 'Memory pressure:' in seg:
            _memory_style(seg, text, out)
        else:
            out.append((seg, FG))

    return out


def _bullet_style(seg, out):
    """Style a segment containing • bullets."""
    parts = seg.split('•')
    for i, part in enumerate(parts):
        if i > 0:
            out.append(('•', YELLOW))
        if part:
            out.append((part, FG))


def _memory_style(seg, whole_line, out):
    """Style the 'Memory pressure: normal ✅ …' segment."""
    # seg is the non-code part which includes "Memory pressure: normal ✅ ..."
    idx = seg.index('Memory pressure:')
    # Text before "Memory pressure:" (e.g. leading spaces)
    if idx > 0:
        out.append((seg[:idx], FG))

    label = 'Memory pressure:'
    out.append((label, BLUE))
    rest = seg[idx + len(label):]

    # Try to extract the status word after "normal"
    rest_stripped = rest.lstrip()
    ws = len(rest) - len(rest_stripped)

    if ws > 0:
        out.append((rest[:ws], FG))

    # Check for "normal ✅" or similar status pattern
    import re
    m = re.match(r'(normal|ok|healthy|good)(\s*[✅✔✓]?)', rest_stripped)
    if m:
        out.append((m.group(0), GREEN))
        remainder = rest_stripped[m.end():]
        if remainder:
            out.append((remainder, FG))
    else:
        out.append((rest_stripped, FG))


# ── SVG generation ─────────────────────────────────────────────────────

def _make_rounded_top_path(x, y, w, h, r):
    """SVG path for a rect with only top corners rounded."""
    return (
        f'M{x + r},{y} '
        f'L{x + w - r},{y} '
        f'Q{x + w},{y} {x + w},{y + r} '
        f'L{x + w},{y + h} '
        f'L{x},{y + h} '
        f'L{x},{y + r} '
        f'Q{x},{y} {x + r},{y} Z'
    )


def generate_svg(lines, output_path):
    n = len(lines)
    text_h = n * LINE_H
    H = TITLE_H + PT + text_h + PB

    # Window outer (with stroke) + content clipping
    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{W}" height="{H}"\n'
        f'     viewBox="0 0 {W} {H}">\n'
    )

    # Shadow filter
    svg.append(
        '  <defs>\n'
        '    <filter id="shadow" x="-4%" y="-4%" width="108%" height="108%">\n'
        '      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#000" flood-opacity="0.35" />\n'
        '    </filter>\n'
        '  </defs>\n'
    )

    # Outer background + border
    svg.append(
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}"\n'
        f'        rx="10" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"\n'
        f'        filter="url(#shadow)" />\n'
    )

    # Title bar background (top-rounded only)
    tp = _make_rounded_top_path(0.5, 0.5, W - 1, TITLE_H, 10)
    svg.append(f'  <path d="{tp}" fill="{TITLE_BG}" />\n')

    # Title bar separator line
    svg.append(
        f'  <line x1="0.5" y1="{TITLE_H + 0.5}" x2="{W - 0.5}" y2="{TITLE_H + 0.5}"\n'
        f'        stroke="{SEPARATOR}" stroke-width="1" />\n'
    )

    # Traffic-light dots
    svg.append(
        f'  <circle cx="20" cy="{TITLE_H // 2}" r="6" fill="#f38ba8" />\n'
        f'  <circle cx="40" cy="{TITLE_H // 2}" r="6" fill="{YELLOW}" />\n'
        f'  <circle cx="60" cy="{TITLE_H // 2}" r="6" fill="{GREEN}" />\n'
    )

    # Title text
    svg.append(
        f'  <text x="76" y="{TITLE_H // 2 + 4}"\n'
        f'        font-family="{FONT}" font-size="12" fill="{GRAY}"\n'
        f'        font-weight="600">agentnap advise</text>\n'
    )

    # ── Content lines ──
    svg.append(f'  <g transform="translate({PL}, {TITLE_H + PT})">\n')

    for i, line in enumerate(lines):
        y = i * LINE_H + FONT_SIZE  # baseline offset
        segs = _line_style(line, i, n)

        if len(segs) == 1:
            t, c = segs[0]
            svg.append(
                f'    <text x="0" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}" fill="{c}">'
                f'{esc(t)}</text>\n'
            )
        else:
            svg.append(f'    <text x="0" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}">')
            for t, c in segs:
                svg.append(f'<tspan fill="{c}">{esc(t)}</tspan>')
            svg.append('</text>\n')

    svg.append('  </g>\n')
    svg.append('</svg>\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(svg)

    return H


def main():
    p = argparse.ArgumentParser(description='Generate terminal-window SVG from advise output')
    p.add_argument('--input', default='launch/assets/advise_sample.txt',
                   help='Input sample file (default: launch/assets/advise_sample.txt)')
    p.add_argument('--output', default='launch/assets/advise.svg',
                   help='Output SVG path (default: launch/assets/advise.svg)')
    args = p.parse_args()

    # Resolve input path
    input_path = args.input
    if not os.path.isabs(input_path):
        # relative to cwd
        input_path = os.path.join(os.getcwd(), input_path)

    if not os.path.exists(input_path):
        # fallback relative to script dir
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt = os.path.join(script_dir, args.input)
        if os.path.exists(alt):
            input_path = alt
        else:
            p.error(f'Input file not found: {args.input}')

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.rstrip('\n').split('\n')
    h = generate_svg(lines, args.output)
    print(f'SVG screenshot saved: {args.output} ({W}x{h})')


if __name__ == '__main__':
    main()
