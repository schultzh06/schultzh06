#!/usr/bin/env python3
"""Generate animated fastfetch-style profile SVGs (dark + light) for the README.

A port of ~/.config/fastfetch/archfetch.py to SVG: the logo (the 3x3 grid
from haydenschultz.dev's favicon) builds itself top-down, a Catppuccin
gradient flows through it and on through the keys, and a shimmer sweeps
across. Pure CSS/SMIL, since GitHub serves README SVGs as <img> (no JS).

Edit INFO below, then run:  python3 scripts/gen_fastfetch.py
"""

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

USER, HOST = "hayden", "schultzh06"
LINK = "github.com/schultzh06"  # shown under the logo

# --- logo: favicon.svg's 3x3 grid, bottom-right square is the accent -------
SQ_W, SQ_H, GAP_X, GAP_Y = 9, 4, 2, 1  # cells; ~square at a 1:2.4 cell ratio
SQUARE = [".+ooooo+.", "+sssssss+", "+sssssss+", "`+ooooo+`"]
COLS = 3 * SQ_W + 2 * GAP_X  # 31
ROWS = 3 * SQ_H + 2 * GAP_Y  # 14
PAD_TOP, PAD_RIGHT = 1, 4  # logo padding, like config.jsonc

INFO = [
    ("OS", "Worcester Polytechnic Institute"),
    ("Kernel", "Computer Science, B.S."),
    ("Concentration", "Cybersecurity"),
    ("Minor", "Electrical & Computer Engineering"),
    ("Host", "haydenschultz.dev"),
    ("Languages", "TypeScript, JavaScript, Go, Python, C, C++, Java, SQL, Bash, PowerShell"),
    ("Frontend", "React, Vite, Astro, TailwindCSS, shadcn/ui, Three.js"),
    ("Backend", "Node.js, Express, Prisma, Auth0"),
    ("Databases", "PostgreSQL, SQLite, Oracle"),
    ("Embedded", "STM32 (HAL, CubeMX), ARM Cortex-M, CMake"),
    ("Infra", "Linux (Arch), Docker, Proxmox, Tailscale, WireGuard, restic, Git"),
    ("AI/Testing", "OpenAI API, Ollama, Vitest, pytest"),
    ("Security", "Wazuh, MITRE ATT&CK, FIDO2/YubiKey, LUKS2, AES-GCM/Argon2id"),
    ("Offense", "Atomic Red Team, Nmap, Kali"),
    ("AppSec", "Threat Modeling, SQL AST validation"),
    ("Workflow", "Agile/Scrum, Jira, UML, ERDs"),
    ("Contact", "me@haydenschultz.dev"),
]

# --- animation (same knobs as archfetch.py) ---------------------------------
DURATION = 3.6  # s, one gradient cycle (and one shimmer sweep)
BUILD = 0.8  # s, logo build-in
START = 0.35  # s, delay before the build-in starts
BUCKETS = 48  # gradient phase classes (quantised animation-delays)

# Catppuccin Mocha / Latte.
THEMES = {
    "dark": dict(
        base="#1e1e2e",
        mantle="#181825",
        border="#313244",
        text="#cdd6f4",
        dim="#6c7086",
        user="#f5c2e7",
        host="#cba6f7",
        prompt="#a6e3a1",
        accent="#fab387",
        shine="#f5e0dc",
        stops=[
            "#f5c2e7",
            "#cba6f7",
            "#b4befe",
            "#89b4fa",
            "#74c7ec",
            "#89b4fa",
            "#b4befe",
            "#cba6f7",
        ],
        colors=[
            "#45475a",
            "#f38ba8",
            "#a6e3a1",
            "#f9e2af",
            "#89b4fa",
            "#f5c2e7",
            "#94e2d5",
            "#bac2de",
        ],
        bright=[
            "#585b70",
            "#f37799",
            "#89d88b",
            "#ebd391",
            "#74a8fc",
            "#f2aede",
            "#6bd7ca",
            "#a6adc8",
        ],
    ),
    "light": dict(
        base="#eff1f5",
        mantle="#e6e9ef",
        border="#ccd0da",
        text="#4c4f69",
        dim="#9ca0b0",
        user="#ea76cb",
        host="#8839ef",
        prompt="#40a02b",
        accent="#fe640b",
        shine="#ffffff",
        stops=[
            "#ea76cb",
            "#8839ef",
            "#7287fd",
            "#1e66f5",
            "#209fb5",
            "#1e66f5",
            "#7287fd",
            "#8839ef",
        ],
        colors=[
            "#5c5f77",
            "#d20f39",
            "#40a02b",
            "#df8e1d",
            "#1e66f5",
            "#ea76cb",
            "#179299",
            "#acb0be",
        ],
        bright=[
            "#6c6f85",
            "#de293e",
            "#49af3d",
            "#eea02d",
            "#456eff",
            "#fe85d8",
            "#2d9fa8",
            "#bcc0cc",
        ],
    ),
}

FONT = "'JetBrains Mono','Fira Code','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
SIZE, LH = 14, 20  # font size, line height (px)
CW = 8.45  # monospace char width at 14px
PAD, BAR = 24, 34  # window padding, title-bar height


def logo_cells():
    """(x, y, char, is_accent) for every non-space cell of the logo."""
    cells = []
    for gy in range(3):
        for gx in range(3):
            accent = (gx, gy) == (2, 2)
            for dy, row in enumerate(SQUARE):
                for dx, ch in enumerate(row):
                    if ch != " ":
                        cells.append(
                            (gx * (SQ_W + GAP_X) + dx, gy * (SQ_H + GAP_Y) + dy, ch, accent)
                        )
    return cells


def hash01(x, y):
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n & 0xFFFF) / 0xFFFF


def phase_class(x, y):
    """archfetch colours cell (x, y) at time t with gradient(s - t/D), where
    s = 0.55*y/h + 0.2*x/w: a travelling wave, so one @keyframes with a
    per-cell negative delay reproduces it exactly."""
    s = (0.55 * y / ROWS + 0.2 * x / COLS) % 1.0
    return f"g{round(s * BUCKETS) % BUCKETS}"


MAX_VALUE = 48  # chars; longer values wrap at ", " (keeps the SVG ~884px wide)


def wrap(value: str) -> list[str]:
    """Split a comma-separated value into lines of at most MAX_VALUE chars,
    each continuation line hanging under the value column."""
    lines, cur = [], ""
    for part in value.split(", "):
        nxt = f"{cur}, {part}" if cur else part
        if cur and len(nxt) + 1 > MAX_VALUE:  # +1 for the trailing comma
            lines.append(cur + ",")
            cur = part
        else:
            cur = nxt
    return lines + [cur]


def build(t: dict) -> str:
    key_w = max(len(k) for k, _ in INFO)
    title = f"{USER}@{HOST}"
    info = [(k if j == 0 else "", ln) for k, v in INFO for j, ln in enumerate(wrap(v))]
    n_info = 2 + len(info) + 3  # title, sep, info, break, 2 colour rows
    rows = max(ROWS + PAD_TOP, n_info)

    lx, ly = PAD, BAR + PAD + LH  # logo/info origin (row 0 top)
    ix = lx + (COLS + PAD_RIGHT) * CW  # info column x
    vx = ix + (key_w + 2) * CW  # value column x
    width = int(vx + max(len(v) for _, v in info) * CW + PAD)
    height = int(ly + rows * LH + LH + PAD)
    base = lambda r: ly + r * LH + 15  # text baseline for row r

    # gradient keyframes: progress k shows gradient(1 - k), i.e. stops reversed
    st = t["stops"]
    kf = " ".join(
        f"{i * 100 / len(st):.3f}%{{fill:{st[(len(st) - i) % len(st)]}}}"
        for i in range(len(st) + 1)
    )
    css = [
        f"text{{font-family:{FONT};font-size:{SIZE}px;white-space:pre}}",
        f"@keyframes grad{{{kf}}}",
        "@keyframes build{from{opacity:0}to{opacity:1}}",
        f".g{{animation:grad {DURATION}s linear infinite}}",
        ".l{opacity:0;animation-name:grad,build;animation-duration:"
        f"{DURATION}s,.12s;animation-timing-function:linear,ease-out;"
        "animation-iteration-count:infinite,1;animation-fill-mode:none,forwards}",
        ".a{opacity:0;animation:build .12s ease-out forwards}",
        "@media (prefers-reduced-motion:reduce){.g,.l,.a{animation:none;opacity:1}}",
    ]
    for b in range(BUCKETS):
        d = -((1 - b / BUCKETS) % 1.0) * DURATION
        css.append(f".g{b}{{animation-delay:{d:.3f}s}}")

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="fastfetch-style profile for {HOST}">',
        f"<title>{title} — fastfetch</title>",
        "<style>" + "".join(css) + "</style>",
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="10" fill="{t["base"]}" stroke="{t["border"]}"/>',
        f'<path d="M.5 {BAR}V10.5a10 10 0 0 1 10-10H{width - 10.5}a10 10 0 0 1 10 10V{BAR}Z" fill="{t["mantle"]}"/>',
        f'<line x1=".5" y1="{BAR}" x2="{width - 0.5}" y2="{BAR}" stroke="{t["border"]}"/>',
    ]
    for i, c in enumerate(["#f38ba8", "#f9e2af", "#a6e3a1"]):
        out.append(f'<circle cx="{20 + i * 20}" cy="{BAR / 2}" r="6" fill="{c}"/>')
    out.append(
        f'<text x="{width / 2}" y="{BAR / 2 + 5}" text-anchor="middle" fill="{t["dim"]}">{title}: ~</text>'
    )
    out.append(
        f'<text x="{PAD}" y="{base(-1)}" xml:space="preserve"><tspan fill="{t["prompt"]}">❯</tspan>'
        f'<tspan fill="{t["text"]}"> fastfetch</tspan></text>'
    )

    # --- logo: one <text> per cell, on an exact grid -----------------------
    logo = []
    for x, y, ch, accent in logo_cells():
        delay = START + BUILD * ((y / ROWS) * 0.65 + hash01(x, y) * 0.35)
        cx, cy = lx + x * CW, base(y + PAD_TOP)
        if accent:
            logo.append(
                f'<text x="{cx:.1f}" y="{cy}" class="a" fill="{t["accent"]}" '
                f'style="animation-delay:{delay:.2f}s">{escape(ch)}</text>'
            )
        else:
            g = phase_class(x, y)
            d = -((1 - int(g[1:]) / BUCKETS) % 1.0) * DURATION
            logo.append(
                f'<text x="{cx:.1f}" y="{cy}" class="l" fill="{st[0]}" '
                f'style="animation-delay:{d:.3f}s,{delay:.2f}s">{escape(ch)}</text>'
            )
    out.append('<g font-weight="bold">' + "".join(logo) + "</g>")

    # --- github link under the logo, built in per character like the logo -
    gy = PAD_TOP + ROWS + 1
    gx0 = (COLS - len(LINK)) // 2
    split = LINK.index("/") + 1
    for j, ch in enumerate(LINK):
        x = gx0 + j
        delay = START + BUILD * ((gy / rows) * 0.65 + hash01(x, gy) * 0.35)
        fill = t["dim"] if j < split else t["text"]
        out.append(
            f'<text x="{lx + x * CW:.1f}" y="{base(gy)}" class="a" fill="{fill}" '
            f'style="animation-delay:{delay:.2f}s">{escape(ch)}</text>'
        )

    # --- shimmer: a skewed light band sweeping across a copy of the logo ---
    lw, lh = COLS * CW, (ROWS + PAD_TOP) * LH
    band = 70
    out += [
        "<defs>",
        '<linearGradient id="band"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".75"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
        f'<mask id="sweep" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">'
        f'<g transform="translate({lx},{ly}) skewX(-25)">'
        f'<rect y="0" width="{band}" height="{lh + LH}" fill="url(#band)">'
        f'<animate attributeName="x" values="{-band - lh * 0.5:.0f};{lw + lh * 0.5 + band:.0f}" '
        f'dur="{DURATION}s" begin="{START + BUILD:.2f}s" repeatCount="indefinite"/></rect></g></mask>',
        "</defs>",
    ]
    shine = "".join(
        f'<text x="{lx + x * CW:.1f}" y="{base(y + PAD_TOP)}">{escape(ch)}</text>'
        for x, y, ch, _ in logo_cells()
    )
    out.append(
        f'<g mask="url(#sweep)" fill="{t["shine"]}" font-weight="bold" opacity="0">'
        f'<set attributeName="opacity" to="1" begin="{START + BUILD:.2f}s"/>{shine}</g>'
    )

    # --- info: each line phases in top-down, with the logo's jitter --------
    key_col = COLS + PAD_RIGHT

    def phase_in(r, x=key_col):
        """Opening tag of a group that fades in at line r's build time."""
        delay = START + BUILD * ((r / rows) * 0.65 + hash01(x, r) * 0.35)
        return f'<g class="a" style="animation-delay:{delay:.2f}s">'

    out.append(
        phase_in(0) + f'<text x="{ix:.1f}" y="{base(0)}" font-weight="bold"><tspan fill="{t["user"]}">{USER}</tspan>'
        f'<tspan fill="{t["dim"]}">@</tspan><tspan fill="{t["host"]}">{HOST}</tspan></text></g>'
    )
    out.append(phase_in(1) + f'<text x="{ix:.1f}" y="{base(1)}" fill="{t["dim"]}">{"─" * len(title)}</text></g>')
    for i, (k, v) in enumerate(info):
        r = i + 2
        line = [phase_in(r)]
        if k:
            # keys carry the gradient on past the logo, like archfetch's glyphs
            g = phase_class(key_col, r - PAD_TOP)
            line.append(
                f'<text x="{ix:.1f}" y="{base(r)}" class="g {g}" fill="{st[0]}" font-weight="bold">{escape(k)}</text>'
            )
        line.append(f'<text x="{vx:.1f}" y="{base(r)}" fill="{t["text"]}">{escape(v)}</text></g>')
        out.append("".join(line))
    r = len(info) + 3
    # fastfetch's colors module: normal 0-7, then bright 8-15, block by block
    for row, palette in enumerate((t["colors"], t["bright"])):
        for i, c in enumerate(palette):
            out.append(
                phase_in(r + row, key_col + 4 + i * 3)
                + f'<rect x="{ix + (4 + i * 3) * CW:.1f}" y="{ly + (r + row) * LH}" width="{3 * CW:.1f}" height="{LH}" fill="{c}"/></g>'
            )

    # trailing prompt + blinking cursor
    yc = base(rows + 1)
    out.append(f'<text x="{PAD}" y="{yc}" fill="{t["prompt"]}">❯</text>')
    out.append(
        f'<rect x="{PAD + 2 * CW:.1f}" y="{yc - SIZE + 1}" width="{CW:.1f}" height="{SIZE + 3}" fill="{t["text"]}">'
        '<animate attributeName="opacity" values="1;1;0;0" dur="1.2s" repeatCount="indefinite"/></rect>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for name, theme in THEMES.items():
        p = ROOT / f"fastfetch-{name}.svg"
        p.write_text(build(theme), encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size // 1024} KB)")
