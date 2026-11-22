"""Draws docs/key_insights.png (1080x1350, LinkedIn portrait) in the InXiteOut palette."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap

OUT = Path(__file__).resolve().parents[1] / "docs"; OUT.mkdir(exist_ok=True)
NAVY, VIOLET, LILAC, PURPLE, WHITE, INK, MUTED = "#030734", "#682EFF", "#CD83FF", "#AC24FF", "#FFFFFF", "#020618", "#62748E"
plt.rcParams["font.family"] = "Segoe UI"
W, H = 10.8, 13.5
fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
grad = LinearSegmentedColormap.from_list("bg", [NAVY, NAVY, "#2A0F6E", "#5B19B8"])
xx, yy = np.meshgrid(np.linspace(0, 1, 300), np.linspace(0, 1, 375))
ax.imshow(grad(np.clip(xx * .7 + (1 - yy) * .45 - .2, 0, 1)), extent=[0, W, 0, H], aspect="auto", zorder=0)

ax.text(.7, 12.85, "What 40,175 flights told us", color=WHITE, fontsize=30, weight="bold", va="top")
ax.text(.7, 12.1, "Airline network, Jan 2024 to May 2025  |  Power BI + Python", color="#C8C3F5", fontsize=14, va="top")

cards = [
    ("+71%", "revenue, Jan-May 2025 vs 2024", "on +25% passengers: fares rose 39% from Nov 2024"),
    ("+1.9 pp", "load factor despite higher fares", "57.4% to 60.5%: demand did not flinch at the price rise"),
    ("31%", "of revenue departs Pune (PNQ)", "86% of flights touch Pune, Mumbai or Bengaluru"),
    ("48", "routes trail the network on LF and RASK", "19% of revenue, led by BLR-BOM and DEL-GOX"),
    ("14%", "of flights had another route's distance", "Fixed with great-circle km before computing RASK"),
    ("₹0.176", "RASK in 2025, +15% and on target", "Yield explains ~90% of the gain"),
]
top, ch, gap = 11.35, 1.52, .2
for i, (big, line1, line2) in enumerate(cards):
    y = top - i * (ch + gap)
    ax.add_patch(FancyBboxPatch((.7, y - ch), W - 1.4, ch, boxstyle="round,pad=0,rounding_size=.18", fc=WHITE, ec="none", zorder=2))
    ax.add_patch(FancyBboxPatch((.7, y - ch), .12, ch, boxstyle="round,pad=0,rounding_size=.06",
                                fc=VIOLET if i % 2 == 0 else PURPLE, ec="none", zorder=3))
    ax.text(1.1, y - ch / 2, big, color=VIOLET, fontsize=27, weight="bold", va="center", zorder=4)
    ax.text(4.05, y - .5, line1, color=INK, fontsize=14.5, weight="bold", va="center", zorder=4)
    ax.text(4.05, y - 1.0, line2, color=MUTED, fontsize=12.5, va="center", zorder=4)

ax.text(.7, .62, "Biggest lever: move capacity off the weakest routes (+₹1.4 Cr a year).",
        color=WHITE, fontsize=14, weight="bold", va="center")
fig.savefig(OUT / "key_insights.png", dpi=100)
print("saved", OUT / "key_insights.png")
