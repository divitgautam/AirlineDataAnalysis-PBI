"""'Runway' theme for AirlineDataAnalysis-PBI: aviation palette, airport-signage typography, header artwork.
Imported by build_report.py before any page is built. Also used by the LinkedIn visuals."""

# ---- palette: night sky, sky blue, contrail cyan, runway amber
NAVY = "#0A2540"        # header band, night sky
NAVY_2 = "#0E3A6B"      # header gradient end
BLUE = "#1673C8"        # primary series
CYAN = "#5BC0EB"        # secondary series, flight paths
AMBER = "#F5A623"       # runway lights: highlight lines, warnings
CORAL = "#E4572E"       # bad / below target
GREEN = "#2BAE66"       # good / on target
SLATE = "#5B6B7F"
INK, MUTED, BG, LINE, WHITE = "#0B1B2E", "#5B6B7F", "#EEF3F8", "#D9E2EC", "#FFFFFF"
SUBTITLE, ROW_ALT, BAND_LIGHT = "#A9C7E8", "#F2F7FC", "#BFDDF5"
FONT = "'Segoe UI', sans-serif"
FONT_BOLD = "'Bahnschrift SemiBold', 'Bahnschrift', 'Segoe UI Semibold', sans-serif"   # DIN-style airport signage face

# Material Design "flight" glyph (Apache 2.0), 24x24, nose up
PLANE = ("M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z")


def header_svg(width=1280, height=72):
    """Navy-to-blue band with faint dotted flight paths and a plane emblem on the left."""
    arcs = [((150, 66), (420, -6), (720, 52)), ((360, 70), (640, 8), (930, 60)), ((620, 68), (900, -2), (1180, 46)),
            ((40, 58), (260, 20), (470, 70))]
    paths = "".join(f'<path d="M{a[0]} {a[1]} Q{b[0]} {b[1]} {c[0]} {c[1]}" fill="none" stroke="{CYAN}" stroke-opacity=".28" '
                    f'stroke-width="1.4" stroke-dasharray="2 6" stroke-linecap="round"/>' for a, b, c in arcs)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{CYAN}" fill-opacity=".55"/>'
                   for (x, y), _, (x2, y2) in arcs for x, y in ((x, y), (x2, y2)) if 0 < y < height)
    trail = (f'<path d="M1010 50 Q1080 34 1146 22" fill="none" stroke="{WHITE}" stroke-opacity=".22" stroke-width="1.6" '
             f'stroke-dasharray="6 5" stroke-linecap="round"/>'
             f'<g transform="translate(1146 8) rotate(58 12 12)" fill="{WHITE}" fill-opacity=".30"><path d="{PLANE}"/></g>')
    emblem = (f'<circle cx="34" cy="36" r="21" fill="{BLUE}"/><circle cx="34" cy="36" r="21" fill="none" stroke="{CYAN}" stroke-opacity=".6"/>'
              f'<g transform="translate(22 24) rotate(45 12 12)" fill="{WHITE}"><path d="{PLANE}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NAVY}"/>'
            f'<stop offset="1" stop-color="{NAVY_2}"/></linearGradient></defs>'
            f'<rect width="{width}" height="{height}" fill="url(#g)"/>{paths}{dots}{trail}'
            f'<rect y="{height - 3}" width="{width}" height="3" fill="{AMBER}" fill-opacity=".85"/>{emblem}</svg>')


def apply(kit):
    """Point the shared PBIR kit at this theme."""
    kit.set_theme(NAVY=NAVY, TEAL=BLUE, AMBER=CYAN, CORAL=AMBER, SLATE=SLATE, GREEN=GREEN,
                  INK=INK, MUTED=MUTED, BG=BG, LINE=LINE, WHITE=WHITE, FONT=FONT, FONT_BOLD=FONT_BOLD,
                  SUBTITLE=SUBTITLE, ROW_ALT=ROW_ALT, EXTRA_COLORS=[CORAL, "#8E9AAF"],
                  THEME_NAME="Runway", THEME_FILE="Runway.json",
                  HEADER_IMAGE="header_runway.svg", HEADER_TEXT_X=64, IMAGES={"header_runway.svg": header_svg()})
