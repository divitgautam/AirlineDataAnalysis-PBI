"""Draws docs/approach_diagram.png for AirlineDataAnalysis-PBI (1920x1080) in the InXiteOut palette. Run: python _build/make_approach_diagram.py"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap

OUT = Path(__file__).resolve().parents[1] / "docs"
OUT.mkdir(exist_ok=True)
import sys
sys.path.insert(0, str(Path(__file__).parent))
import airline_theme as t   # Runway theme: same colours as the dashboard
NAVY, VIOLET, LILAC, PURPLE, WHITE, INK, MUTED = t.NAVY, t.BLUE, t.CYAN, t.AMBER, t.WHITE, t.INK, t.MUTED
plt.rcParams["font.family"] = ["Bahnschrift", "Segoe UI"]

W, H = 19.2, 10.8
fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

# background: navy to purple diagonal, like the site's hero bands
grad = LinearSegmentedColormap.from_list("bg", [NAVY, NAVY, t.NAVY_2, "#1A5694"])
xx, yy = np.meshgrid(np.linspace(0, 1, 400), np.linspace(0, 1, 225))
ax.imshow(grad(np.clip(xx * .75 + (1 - yy) * .35 - .15, 0, 1)), extent=[0, W, 0, H], aspect="auto", zorder=0)

ax.text(W - .8, 9.85, "✈", color=LILAC, fontsize=46, ha="right", va="top", fontfamily="Segoe UI Symbol", rotation=30)
ax.text(.8, 9.95, "From 40,175 flights to network decisions", color=WHITE, fontsize=34, weight="bold", va="top")
ax.text(.8, 9.1, "How AirlineDataAnalysis-PBI was built: audit first, fix the distances, answer in Power BI, go deeper in Python",
        color=t.SUBTITLE, fontsize=15, va="top")

stages = [
    ("01", "DATA", "One flight-level CSV",
     ["40,175 flights", "179 routes, 38 airports", "Jan 2024 to May 2025", "Seats, passengers, revenue"]),
    ("02", "AUDIT & MODEL", "Trust before charts",
     ["14 data-quality checks", "14% of flights had another", "route's distance: fixed with", "great-circle km from coordinates",
      "Fare outliers by route median"]),
    ("03", "POWER BI", "Answer the brief",
     ["119 DAX measures", "5 pages + drill-through,", "tooltip & phone layouts", "Route quadrants, demand, RASK",
      "Scored 10/10; BPA 27/27"]),
    ("04", "PYTHON", "Go deeper",
     ["Audit + EDA notebooks", "Route quadrants, seasonality", "Forecast Jun-Dec 2025,", "backtested on held-out months",
      "Revenue levers sized"]),
    ("05", "DECISIONS", "What to do next",
     ["2025: ~Rs 64 Cr if fares hold", "Review 48 weak routes", "Move capacity: +Rs 1.4 Cr/yr", "Lift full low-RASK fares 5%",
      "Fix international load factor"]),
]
n = len(stages); gap = .42; left = .8; cw = (W - 2 * left - (n - 1) * gap) / n; top, ch = 8.1, 5.15
for i, (num, name, tag, lines) in enumerate(stages):
    x = left + i * (cw + gap)
    hi = i in (2, 3)
    ax.add_patch(FancyBboxPatch((x, top - ch), cw, ch, boxstyle="round,pad=0,rounding_size=.22",
                                fc=WHITE, ec=LILAC if hi else "none", lw=2.5, zorder=2))
    ax.add_patch(FancyBboxPatch((x, top - .14), cw, .14, boxstyle="round,pad=0,rounding_size=.07",
                                fc=VIOLET if i % 2 == 0 else PURPLE, ec="none", zorder=3))
    ax.text(x + .32, top - .45, num, color=VIOLET, fontsize=30, weight="bold", va="top", zorder=4)
    ax.text(x + .32, top - 1.32, name, color=INK, fontsize=17, weight="bold", va="top", zorder=4)
    ax.text(x + .32, top - 1.82, tag, color=MUTED, fontsize=12.5, va="top", style="italic", zorder=4)
    for j, ln in enumerate(lines):
        ax.text(x + .32, top - 2.45 - j * .5, ln.replace("Rs ", "₹"), color=INK, fontsize=12.5, va="top", zorder=4)
    if i < n - 1:
        ax.add_patch(FancyArrowPatch((x + cw + .04, top - ch / 2), (x + cw + gap - .04, top - ch / 2),
                                     arrowstyle="-|>,head_length=8,head_width=6", color=LILAC, lw=2.5, zorder=5))
bx = left + 2 * (cw + gap); bw = 2 * cw + gap
ax.add_patch(FancyBboxPatch((bx, 1.6), bw, .93, boxstyle="round,pad=0,rounding_size=.18", fc=VIOLET, ec="none", zorder=2))
ax.text(bx + bw / 2, 2.25, "Reconciled exactly: Python = Power BI", color=WHITE, fontsize=14, weight="bold", ha="center", va="center", zorder=3)
ax.text(bx + bw / 2, 1.88, "40,175 flights  |  2.21 M passengers  |  4.14 bn seat-km  |  ₹64.9 Cr revenue",
        color="#DCEBFA", fontsize=12, ha="center", va="center", zorder=3)
for cx in (bx + cw / 2, bx + cw + gap + cw / 2):
    ax.plot([cx, cx], [top - ch, 2.53], color=LILAC, lw=2, ls=(0, (3, 3)), zorder=1)
ax.text(.8, 1.0, "Key finding: 2025 growth is price-led (fares +39% from Nov 2024) and planes still got fuller; "
        "Pune is the network's hub.", color=WHITE, fontsize=14.5, va="center")
ax.text(W - .8, .45, "Power BI  |  DAX  |  Power Query  |  Python (pandas, scipy, statsmodels)",
        color=t.SUBTITLE, fontsize=11.5, ha="right", va="center")

fig.savefig(OUT / "approach_diagram.png", dpi=100)
print("saved", OUT / "approach_diagram.png")
