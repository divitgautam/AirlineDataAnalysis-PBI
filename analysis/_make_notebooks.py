"""Builds the AirlineDataAnalysis-PBI notebooks. Run: python _make_notebooks.py, then execute them with nbconvert."""
from pathlib import Path
import nbformat as nbf

HERE = Path(__file__).parent


def nb(cells):
    book = nbf.v4.new_notebook()
    book.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    book.cells = [nbf.v4.new_markdown_cell(s.strip()) if k == "md" else nbf.v4.new_code_cell(s.strip()) for k, s in cells]
    return book


SETUP = r'''
import sys, json, warnings
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from scipy import stats
from src.metrics import load_clean, headline, DATA_DIR, OUTPUT_DIR, DATA_END
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
NAVY, VIOLET, LILAC, ORANGE, SLATE, GREEN = "#030734", "#682EFF", "#CD83FF", "#F05100", "#62748E", "#009588"
sns.set_theme(style="whitegrid", palette=[VIOLET, LILAC, NAVY, ORANGE, SLATE, GREEN])
FIG = OUTPUT_DIR / "figures"; FIG.mkdir(parents=True, exist_ok=True); DATA_DIR.mkdir(parents=True, exist_ok=True)
Cr = lambda v: f"₹{v/1e7:,.2f} Cr"; Lk = lambda v: f"₹{v/1e5:,.1f} L"
findings = []
def note(q, topic, text):
    findings.append(dict(q=q, topic=topic, finding=text)); print(f"[{q}] {topic}: {text}")
def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight"); plt.show()
def kpis(g):
    return pd.Series({"flights": len(g), "revenue": g.Revenue.sum(), "pax": g.PaxCount.sum(), "seats": g.Capacity.sum(),
                      "ask": g.ask.sum(), "rpk": g.rpk.sum(), "lf": g.PaxCount.sum() / g.Capacity.sum(),
                      "fare": g.Revenue.sum() / g.PaxCount.sum(), "rask": g.Revenue.sum() / g.ask.sum(),
                      "yield_rpk": g.Revenue.sum() / g.rpk.sum(), "stage_km": g.ask.sum() / g.Capacity.sum()})
'''
LOAD = r'''
f = pd.read_parquet(DATA_DIR / "flights.parquet")
NET = kpis(f)
'''

# ------------------------------------------------------------------ 00 load & clean
n00 = [
    ("md", """
# 00 · Load and clean

Applies the cleaning rules in `src/metrics.py` (the same rules as the Power BI model's Power Query), saves
`data/flights.parquet`, and **asserts the totals match the Power BI report**.
"""),
    ("code", SETUP),
    ("code", r'''
d = load_clean(); f = d["flights"]
h = headline(f); h
'''),
    ("code", r'''
# Totals read from the Power BI model after refresh (pbi dax). Python must reproduce them exactly.
PBI = {"flights": 40175, "passengers": 2214543, "seats": 3767214, "revenue": 648972690,
       "routes": 179, "distance_corrected_flights": 5660, "fare_outliers": 86,
       "ask": 4142864685, "rpk": 2424978029}
rec = pd.DataFrame({"python": h[list(PBI)], "power_bi": pd.Series(PBI)}); rec["match"] = rec.python.round(0) == rec.power_bi
assert rec["match"].all(), rec
rec
'''),
    ("code", r'''
f.to_parquet(DATA_DIR / "flights.parquet", index=False)
f.shape
'''),
]

# ------------------------------------------------------------------ 01 audit
n01 = [
    ("md", """
# 01 · Data audit

Every check records PASS / WARN / FAIL. Outputs: `output/audit_findings.csv` and charts in `output/figures/`.
"""),
    ("code", SETUP),
    ("code", r'''
d = load_clean(); raw, f, ap = d["raw"], d["flights"], d["airports"]
rows = []
def record(n, check, status, count, detail):
    rows.append(dict(n=n, check=check, status=status, count=int(count), detail=detail)); print(f"[{status}] {n}. {check}: {detail}")
'''),
    ("code", r'''
record(1, "Completeness", "PASS" if raw.isna().sum().sum() == 0 else "FAIL", raw.isna().sum().sum(),
       f"{len(raw):,} rows x {raw.shape[1]} columns, no missing values")
record(2, "Unique flight IDs", "PASS" if not raw.FlightID.duplicated().any() else "FAIL", raw.FlightID.duplicated().sum(),
       "FlightID is unique; no fully duplicated rows")
rep = f.duplicated(["date", "FlightNumber", "Origin", "Destination"]).sum()
record(3, "Repeated flight number + date + route", "WARN", rep,
       f"{rep} flights share a flight number, date and route with another flight but differ in seats, passengers and revenue: "
       "kept as separate operations")
bad_dates = pd.to_datetime(raw.DepartureDate, format="%d-%m-%Y", errors="coerce").isna().sum()
record(4, "Valid dates", "PASS" if bad_dates == 0 else "FAIL", bad_dates, f"All dates parse as dd-mm-yyyy; {f.date.min():%d %b %Y} to {f.date.max():%d %b %Y}, no gaps")
unknown = set(f.Origin) | set(f.Destination); unknown -= set(ap.IATA)
record(5, "Airports known", "PASS" if not unknown else "FAIL", len(unknown), f"All 38 airport codes found in reference/airports.csv")
'''),
    ("md", "### 6 · Recorded distance vs great-circle distance"),
    ("code", r'''
r = f.groupby(["route", "Distance"]).agg(flights=("FlightID", "size"), gc=("gc_km", "first")).reset_index()
r["ratio"] = r.Distance / r.gc
bad = r[~r.ratio.between(0.9, 1.25)].sort_values("flights", ascending=False)
display(bad.head(12))
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.scatter(r.gc, r.Distance, s=np.sqrt(r.flights) * 3, c=np.where(r.ratio.between(0.9, 1.25), VIOLET, ORANGE), alpha=.7)
ax.plot([0, 3600], [0, 3600], color=SLATE, lw=1, ls="--"); ax.set_xlabel("Great-circle km"); ax.set_ylabel("Recorded km")
ax.set_title("Recorded vs great-circle distance (orange = replaced)"); save(fig, "a06_distance_check")
record(6, "Distance matches geography", "FAIL", f.distance_corrected.sum(),
       f"{f.distance_corrected.sum():,} flights ({f.distance_corrected.mean():.0%}) on {bad.route.nunique()} routes carry another route's distance "
       f"(e.g. PNQ-BOM recorded 1,138 km = Delhi-Mumbai; true 124 km). Replaced with great-circle distance for ASK/RPK")
'''),
    ("code", r'''
rev_d = f.groupby("route").distance_km.first()
asym = [(a, b) for a in rev_d.index for b in [f"{a.split('-')[1]}-{a.split('-')[0]}"] if b in rev_d.index and rev_d[a] != rev_d[b]]
record(7, "Same distance both directions", "PASS" if not asym else "WARN", len(asym) // 2,
       "After correction every route and its return leg have the same distance" if not asym else f"{len(asym)//2} route pairs still differ")
record(8, "Domestic flag consistent", "PASS" if (f.international == (f.DomesticFlag == 0)).all() else "FAIL", 0,
       "DomesticFlag = 0 exactly for flights touching AUH, DOH, JED, KWI or RUH")
'''),
    ("code", r'''
lf_max = f.load_factor.max()
fig, ax = plt.subplots(figsize=(8, 3)); sns.histplot(f.load_factor, bins=60, ax=ax, color=VIOLET)
ax.axvline(lf_max, color=ORANGE, ls="--"); ax.set_title(f"Load factor per flight: hard ceiling at {lf_max:.1%}"); save(fig, "a09_load_factor_ceiling")
record(9, "Load factor plausibility", "WARN", (f.load_factor >= .66).sum(),
       f"No flight is more than {lf_max:.1%} full (max {f.PaxCount.max()} passengers on {f.Capacity.min()}-{f.Capacity.max()} seats); "
       "real airlines run 80-90%. Passenger counts look scaled or synthetic: compare load factors relatively")
fare_med = f.Revenue.sum() / f.PaxCount.sum()
record(10, "Fare plausibility", "WARN", 0,
       f"Average revenue per passenger is ₹{fare_med:,.0f}, far below real Indian fares: revenue appears scaled. Trends and comparisons hold; absolute rupees are illustrative")
record(11, "Fare outliers (3x route median)", "WARN", f.fare_outlier.sum(),
       f"{f.fare_outlier.sum()} flights ({f.Revenue[f.fare_outlier].sum()/f.Revenue.sum():.1%} of revenue) priced above 3x their route's median fare: flagged, kept")
low = (f.PaxCount < 20).sum()
record(12, "Very low loads", "WARN", low, f"{low} flights carried fewer than 20 passengers ({f.Revenue[f.PaxCount < 20].sum()/f.Revenue.sum():.1%} of revenue)")
odd = f.Capacity.isin([89, 90, 96]).sum()
record(13, "Aircraft capacities", "PASS", odd, f"Four standard seat counts (87, 93, 95, 99) cover all but {odd} flights")
pnqbom = f[f.route == "PNQ-BOM"]
record(14, "Short route priced as long", "WARN", len(pnqbom),
       f"PNQ-BOM is 124 km but averages ₹{pnqbom.Revenue.sum()/pnqbom.PaxCount.sum():,.0f} per passenger, more than BLR-BOM (834 km). "
       "Its fare looks based on the wrong 1,138 km distance; its RASK (₹{:.2f}) is an outlier".format(pnqbom.Revenue.sum()/pnqbom.ask.sum()))
'''),
    ("code", r'''
A = pd.DataFrame(rows); A.to_csv(OUTPUT_DIR / "audit_findings.csv", index=False)
A.status.value_counts()
'''),
]

# ------------------------------------------------------------------ 02 EDA (brief Q1, Q2, Q3)
n02 = [
    ("md", "# 02 · EDA: network, demand trends and the RASK KPI"),
    ("code", SETUP), ("code", LOAD),
    ("md", "## Q1 · Network and route performance"),
    ("code", r'''
R = f.groupby("route").apply(kpis, include_groups=False)
R["share"] = R.revenue / R.revenue.sum(); R = R.sort_values("revenue", ascending=False)
R["quadrant"] = np.select([(R.lf >= NET.lf) & (R.rask >= NET.rask), (R.lf < NET.lf) & (R.rask >= NET.rask),
                           (R.lf >= NET.lf) & (R.rask < NET.rask)], ["Star", "Fill seats", "Raise yield"], "Review route")
Q = R.groupby("quadrant").agg(routes=("share", "size"), revenue_share=("share", "sum"), lf=("lf", "mean"), rask=("rask", "median"))
display(R.head(10)[["flights", "revenue", "share", "lf", "fare", "rask", "stage_km", "quadrant"]]); display(Q)
R.to_csv(OUTPUT_DIR / "route_scorecard.csv")
n80 = int((R.share.cumsum() < .8).sum() + 1)
A = f.groupby("Origin").apply(kpis, include_groups=False).sort_values("revenue", ascending=False); A["share"] = A.revenue / A.revenue.sum()
hub = f[f.Origin.isin(["PNQ", "BOM", "BLR"]) | f.Destination.isin(["PNQ", "BOM", "BLR"])].shape[0] / len(f)
note("Q1", "Concentration", f"Top 10 routes earn {R.share.head(10).sum():.0%} of revenue; {n80} of {len(R)} routes make 80%. "
     f"{(R.flights < 100).sum()} thin routes (<100 flights) add only {R.share[R.flights < 100].sum():.1%}.")
note("Q1", "Hubs", f"Pune is the main hub: {A.share['PNQ']:.0%} of revenue departs PNQ, then Bengaluru {A.share['BLR']:.0%} and Delhi {A.share['DEL']:.0%}. "
     f"{hub:.0%} of flights touch PNQ, BOM or BLR.")
note("Q1", "Route quadrants", " | ".join(f"{q}: {int(r.routes)} routes, {r.revenue_share:.0%} of revenue" for q, r in Q.iterrows()))
rv = R[R.quadrant == "Review route"].head(4)
note("Q1", "Routes to review", "Largest routes below the network on both load factor and RASK: " +
     ", ".join(f"{i} ({r.share:.1%} of revenue, LF {r.lf:.0%}, RASK ₹{r.rask:.3f})" for i, r in rv.iterrows()))
'''),
    ("code", r'''
fig, ax = plt.subplots(figsize=(9, 5))
for q, c in zip(["Star", "Fill seats", "Raise yield", "Review route"], [VIOLET, LILAC, NAVY, ORANGE]):
    s = R[R.quadrant == q]; ax.scatter(s.lf, s.rask.clip(upper=.6), s=s.revenue / 2e5, c=c, alpha=.7, label=f"{q} ({len(s)})")
ax.axvline(NET.lf, color=SLATE, ls="--", lw=1); ax.axhline(NET.rask, color=SLATE, ls="--", lw=1)
ax.set_xlabel("Load factor"); ax.set_ylabel("RASK (₹ per seat-km, capped at 0.6)"); ax.legend()
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.set_title("Route quadrants vs network average"); save(fig, "e01_route_quadrants")
c = np.corrcoef(np.log(R.stage_km), np.log(R.rask))[0, 1]
note("Q1", "Stage length", f"Longer routes earn less per seat-km (log correlation {c:.2f}). Compare RASK between routes of similar length.")
'''),
    ("md", "## Q2 · Demand trends"),
    ("code", r'''
Mo = f.groupby("month").apply(kpis, include_groups=False)
Y = f[f.date.dt.month <= 5].groupby(f.date.dt.year).apply(kpis, include_groups=False)
yoy = Y.loc[2025] / Y.loc[2024] - 1
display(Y.T)
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
ax[0].bar(Mo.index, Mo.pax / 1e3, width=20, color=VIOLET); ax[0].set_title("Passengers per month ('000)")
ax2 = ax[0].twinx(); ax2.plot(Mo.index, Mo.fare, color=ORANGE, marker="o"); ax2.set_ylabel("Avg fare (₹)"); ax2.grid(False)
ax[1].plot(Mo.index, Mo.lf, marker="o", color=NAVY); ax[1].set_title("Load factor per month"); ax[1].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
save(fig, "e02_monthly_trend")
pre, post = f[f.date < "2024-11-01"], f[f.date >= "2024-11-01"]
kp, kq = kpis(pre), kpis(post)
rp = f.assign(per=np.where(f.date >= "2024-11-01", "post", "pre")).groupby(["route", "per"]).apply(
    lambda g: g.Revenue.sum() / g.PaxCount.sum(), include_groups=False).unstack().dropna()
note("Q2", "Growth Jan-May 2025 vs 2024", f"Flights {yoy.flights:+.0%}, passengers {yoy.pax:+.0%}, revenue {yoy.revenue:+.0%}, "
     f"average fare {yoy.fare:+.0%}, load factor {(Y.loc[2025].lf - Y.loc[2024].lf) * 100:+.1f} pp, RASK {yoy.rask:+.0%}.")
note("Q2", "Fare step Nov 2024", f"Average fare rose from ₹{kp.fare:,.0f} (Jan-Oct 2024) to ₹{kq.fare:,.0f} from Nov 2024 ({kq.fare/kp.fare-1:+.0%}) "
     f"while load factor also rose ({kp.lf:.1%} to {kq.lf:.1%}). {(rp.post / rp.pre > 1.2).mean():.0%} of routes raised fares 20%+. Demand did not fall.")
lo = Mo.loc["2024-07-01":"2024-10-01"]
note("Q2", "Seasonality", f"Weakest stretch Jul-Oct 2024: load factor {lo.pax.sum()/lo.seats.sum():.1%} and RASK ₹{lo.revenue.sum()/lo.ask.sum():.3f} "
     f"vs network {NET.lf:.1%} / ₹{NET.rask:.3f}. Strongest month: {Mo.rask.idxmax():%b %Y} (RASK ₹{Mo.rask.max():.3f}).")
wd = f.groupby(f.date.dt.dayofweek).PaxCount.mean(); chi = stats.kruskal(*[g.PaxCount.values for _, g in f.groupby(f.date.dt.dayofweek)])
note("Q2", "Weekday", f"Passengers per flight range only {wd.min():.1f}-{wd.max():.1f} across the week: the difference is statistically real "
     f"(Kruskal p={chi.pvalue:.3g}, 40k flights) but only {wd.max()/wd.min()-1:.0%} from lowest to highest day. Not worth scheduling around.")
'''),
    ("md", "## Q3 · KPI: RASK and its drivers"),
    ("code", r'''
Mk = f.groupby("market").apply(kpis, include_groups=False); display(Mk.T)
rask25, rask24 = Y.loc[2025].rask, Y.loc[2024].rask
# decomposition of RASK change: RASK = seat-km LF x yield per RPK (log split)
lf_c = np.log((Y.loc[2025].rpk / Y.loc[2025].ask) / (Y.loc[2024].rpk / Y.loc[2024].ask))
yl_c = np.log(Y.loc[2025].yield_rpk / Y.loc[2024].yield_rpk)
note("Q3", "RASK 2025", f"Jan-May 2025 RASK ₹{rask25:.3f} vs ₹{rask24:.3f} a year earlier ({rask25/rask24-1:+.0%}); target (+5%) ₹{rask24*1.05:.3f}: on target. "
     f"Yield explains {yl_c/(yl_c+lf_c):.0%} of the gain, seat-km load factor {lf_c/(yl_c+lf_c):.0%}.")
note("Q3", "Domestic vs international", f"International is {Mk.loc['International','flights']/NET.flights:.0%} of flights and {Mk.loc['International','revenue']/NET.revenue:.0%} of revenue, "
     f"but load factor {Mk.loc['International','lf']:.0%} vs {Mk.loc['Domestic','lf']:.0%} and RASK ₹{Mk.loc['International','rask']:.3f} vs ₹{Mk.loc['Domestic','rask']:.3f} "
     f"(stage {Mk.loc['International','stage_km']:,.0f} km vs {Mk.loc['Domestic','stage_km']:,.0f} km).")
'''),
    ("code", r'''
F = pd.DataFrame(findings); F.to_csv(OUTPUT_DIR / "eda_findings.csv", index=False)
json.dump({"net": NET.to_dict(), "yoy": yoy.to_dict(), "Y": Y.to_dict(), "quadrants": Q.to_dict(), "pre": kp.to_dict(), "post": kq.to_dict(),
           "market": Mk.to_dict()}, open(OUTPUT_DIR / "eda_numbers.json", "w"), default=float, indent=1)
pd.set_option("display.max_colwidth", None); F
'''),
]

# ------------------------------------------------------------------ 03 forecast
n03 = [
    ("md", """
# 03 · Forecast Jun–Dec 2025

Revenue = passengers x average fare, forecast separately because they behave differently:
- **Passengers** grow steadily with capacity. Model: log-linear trend plus a seasonal index from 2024, backtested on Mar–May 2025.
- **Fares** stepped up ~39% in Nov 2024 (a structural break). The forecast uses the post-break level, with two scenarios.

Bands come from 2,000 bootstrap draws of the model's monthly residuals.
"""),
    ("code", SETUP), ("code", LOAD),
    ("code", r'''
Mo = f.groupby("month").apply(kpis, include_groups=False); Mo.index = pd.to_datetime(Mo.index)
t = np.arange(len(Mo)); moy = Mo.index.month
def fit_pax(idx):
    """log(pax) = a + b*t + seasonal(month), seasonal estimated from 2024 detrended residuals (month dummies, ridge-shrunk)."""
    y = np.log(Mo.pax.values[idx]); tt = t[idx]; b, a = np.polyfit(tt, y, 1)
    res = pd.Series(y - (a + b * tt), index=moy[idx]).groupby(level=0).mean() * 0.5   # shrink: one year of seasonality only
    return a, b, res
def pred_pax(params, tt, months):
    a, b, s = params; return np.exp(a + b * tt + np.array([s.get(m, 0.0) for m in months]))
train = np.arange(len(Mo) - 3); test = np.arange(len(Mo) - 3, len(Mo))
pbt = fit_pax(train); bt_pred = pred_pax(pbt, t[test], moy[test])
naive = np.repeat(Mo.pax.values[train][-3:].mean(), 3)
bt = pd.DataFrame({"actual": Mo.pax.values[test], "model": bt_pred, "naive_last3": naive}, index=Mo.index[test])
bt_err = bt.model.sum() / bt.actual.sum() - 1; nv_err = bt.naive_last3.sum() / bt.actual.sum() - 1
display(bt); bt.to_csv(OUTPUT_DIR / "forecast_backtest.csv")
note("Backtest", "Passengers Mar-May 2025", f"Trend + seasonal model {bt_err:+.1%} on the 3-month total vs {nv_err:+.1%} for a naive 'last 3 months' forecast.")
'''),
    ("code", r'''
P = fit_pax(np.arange(len(Mo)))
fc_idx = pd.date_range("2025-06-01", "2025-12-01", freq="MS"); tf = np.arange(len(Mo), len(Mo) + len(fc_idx))
pax_fc = pred_pax(P, tf, fc_idx.month)
fit_in = pred_pax(P, t, moy); resid = np.log(Mo.pax.values) - np.log(fit_in)
post = Mo.loc["2024-11-01":]; fare_hi = post.revenue.sum() / post.pax.sum()
recent = Mo.loc["2025-03-01":]; fare_lo = recent.revenue.sum() / recent.pax.sum()
fare_resid = np.log(post.fare / fare_hi).values
rng = np.random.default_rng(42); N = 2000
sims = {}
for name, level in {"A · Fares hold (post-Nov 2024 level)": fare_hi, "B · Fares settle (Mar-May 2025 level)": fare_lo}.items():
    pe = np.exp(rng.choice(resid, (N, len(fc_idx)))); fe = np.exp(rng.choice(fare_resid, (N, len(fc_idx))))
    pax = pax_fc * pe; rev = pax * level * fe
    sims[name] = {"pax": pax, "revenue": rev}
rows = []
for name, s in sims.items():
    for metric, arr in s.items():
        for i, m in enumerate(fc_idx):
            rows.append(dict(scenario=name, month=m, metric={"pax": "Passengers", "revenue": "Revenue"}[metric], kind="Forecast",
                             actual=None, p10=np.percentile(arr[:, i], 10), p50=np.percentile(arr[:, i], 50), p90=np.percentile(arr[:, i], 90)))
    for metric, col in (("Passengers", "pax"), ("Revenue", "revenue")):
        for m, v in Mo[col].items():
            rows.append(dict(scenario=name, month=m, metric=metric, kind="Actual", actual=v, p10=None, p50=None, p90=None))
FC = pd.DataFrame(rows); FC.to_csv(OUTPUT_DIR / "pbi_forecast.csv", index=False, date_format="%Y-%m-%d")
tot = {name: {k: np.percentile(v.sum(axis=1), [10, 50, 90]) for k, v in s.items()} for name, s in sims.items()}
ann = []
ytd25 = f[f.date.dt.year == 2025]
for name, d in tot.items():
    for k, nice in (("pax", "Passengers"), ("revenue", "Revenue")):
        base = ytd25.PaxCount.sum() if k == "pax" else ytd25.Revenue.sum()
        ann.append(dict(scenario=name, metric=f"{nice} 2025 full year", p10=base + d[k][0], p50=base + d[k][1], p90=base + d[k][2]))
        ann.append(dict(scenario=name, metric=f"{nice} Jun-Dec 2025", p10=d[k][0], p50=d[k][1], p90=d[k][2]))
FA = pd.DataFrame(ann); FA.to_csv(OUTPUT_DIR / "pbi_forecast_2025.csv", index=False); display(FA)
rev24 = f[f.date.dt.year == 2024].Revenue.sum()
a = FA[(FA.metric == "Revenue 2025 full year") & FA.scenario.str.startswith("A")].iloc[0]
b = FA[(FA.metric == "Revenue 2025 full year") & FA.scenario.str.startswith("B")].iloc[0]
note("Forecast", "2025 revenue", f"Full-year 2025 revenue {Cr(a.p50)} if fares hold (80% range {Cr(a.p10)}-{Cr(a.p90)}), {Cr(b.p50)} if they settle at the Mar-May level, "
     f"vs {Cr(rev24)} in 2024 ({a.p50/rev24-1:+.0%} / {b.p50/rev24-1:+.0%}).")
pa = FA[(FA.metric == "Passengers 2025 full year") & FA.scenario.str.startswith("A")].iloc[0]
note("Forecast", "2025 passengers", f"About {pa.p50/1e6:.2f} M passengers in 2025 ({pa.p50/f[f.date.dt.year == 2024].PaxCount.sum()-1:+.0%} vs 2024). "
     "The summer months (Jul-Oct) are the weakest in the seasonal pattern.")
'''),
    ("code", r'''
fig, ax = plt.subplots(figsize=(11, 3.8))
ax.plot(Mo.index, Mo.revenue / 1e7, color=NAVY, marker="o", label="Actual")
for (name, s), c in zip(sims.items(), [VIOLET, ORANGE]):
    q = np.percentile(s["revenue"], [10, 50, 90], axis=0) / 1e7
    ax.plot(fc_idx, q[1], color=c, lw=2, label=name); ax.fill_between(fc_idx, q[0], q[2], color=c, alpha=.15)
ax.set_ylabel("₹ crore"); ax.legend(fontsize=8); ax.set_title("Monthly revenue: actual and forecast (P10-P90)"); save(fig, "f01_revenue_forecast")
F = pd.DataFrame(findings); F.to_csv(OUTPUT_DIR / "forecast_findings.csv", index=False); F
'''),
]

# ------------------------------------------------------------------ 04 levers
n04 = [
    ("md", """
# 04 · Profit levers (sized on the last 12 months, Jun 2024–May 2025)

Each lever is sized transparently from actual flights, holding everything else equal:
1. **Fill seats** on "Fill seats" routes (good RASK, low load factor) up to the network load factor, at each route's own fare.
2. **Lift yield** on "Raise yield" routes (full planes, low RASK) by 5% in fares, assuming the Nov 2024 evidence holds (demand did not fall).
3. **Re-deploy capacity** from the weakest "Review" routes (bottom quartile RASK) to Star routes at the Star routes' average RASK.
4. **International load factor** from its current level to halfway towards the domestic level.
"""),
    ("code", SETUP), ("code", LOAD),
    ("code", r'''
L12 = f[f.date > DATA_END - pd.DateOffset(months=12)]
NET12 = kpis(L12)
R = L12.groupby("route").apply(kpis, include_groups=False)
R["quadrant"] = np.select([(R.lf >= NET12.lf) & (R.rask >= NET12.rask), (R.lf < NET12.lf) & (R.rask >= NET12.rask),
                           (R.lf >= NET12.lf) & (R.rask < NET12.rask)], ["Star", "Fill seats", "Raise yield"], "Review route")
fs = R[R.quadrant == "Fill seats"]
lever1 = ((NET12.lf - fs.lf).clip(lower=0) * fs.seats * fs.fare).sum()
ry = R[R.quadrant == "Raise yield"]; lever2 = 0.05 * ry.revenue.sum()
rv = R[R.quadrant == "Review route"]; weak = rv[rv.rask <= rv.rask.quantile(.25)]
# Value re-deployed seat-km at the NETWORK average RASK (conservative: Star-route RASK is inflated by the PNQ-BOM pricing outlier)
lever3 = (weak.ask.sum() * NET12.rask) - weak.revenue.sum()
I = kpis(L12[L12.market == "International"]); D = kpis(L12[L12.market == "Domestic"])
lever4 = ((D.lf - I.lf) / 2) * I.seats * I.fare
LV = pd.DataFrame([
    dict(lever="Fill seats on high-RASK routes", uplift=lever1, basis=f"{len(fs)} routes lifted to network LF {NET12.lf:.1%}", confidence="Medium"),
    dict(lever="5% fare rise on full, low-RASK routes", uplift=lever2, basis=f"{len(ry)} 'Raise yield' routes; Nov 2024 fare rise did not cut demand", confidence="Medium"),
    dict(lever="Re-deploy weakest route capacity", uplift=lever3, basis=f"{len(weak)} bottom-quartile review routes ({weak.flights.sum():,.0f} flights) flown at network-average RASK", confidence="Low-medium"),
    dict(lever="International load factor halfway to domestic", uplift=lever4, basis=f"LF {I.lf:.0%} to {(I.lf + D.lf) / 2:.0%}", confidence="Medium"),
])
LV["uplift_pct_of_revenue"] = LV.uplift / NET12.revenue
LV.to_csv(OUTPUT_DIR / "pbi_levers.csv", index=False); display(LV)
note("Levers", "Sized on Jun 2024-May 2025", " | ".join(f"{r.lever}: +{Cr(r.uplift)} ({r.uplift_pct_of_revenue:.1%})" for _, r in LV.iterrows()) +
     f". Base revenue {Cr(NET12.revenue)}.")
F = pd.DataFrame(findings); F.to_csv(OUTPUT_DIR / "lever_findings.csv", index=False); F
'''),
    ("code", r'''
# ---- facts for the Power BI report text (read by _build/build_report.py) ----
E = json.load(open(OUTPUT_DIR / "eda_numbers.json"))
Y24, Y25 = {k: v["2024"] for k, v in E["Y"].items()}, {k: v["2025"] for k, v in E["Y"].items()}
FA = pd.read_csv(OUTPUT_DIR / "pbi_forecast_2025.csv")
fa = FA[(FA.metric == "Revenue 2025 full year") & FA.scenario.str.startswith("A")].iloc[0]
fb = FA[(FA.metric == "Revenue 2025 full year") & FA.scenario.str.startswith("B")].iloc[0]
Q = pd.DataFrame(E["quadrants"]); Mk = pd.DataFrame(E["market"])
BT = pd.read_csv(OUTPUT_DIR / "forecast_backtest.csv")
pct = lambda a, b: f"{a / b - 1:+.0%}"
facts = {
    "pax_yoy": pct(Y25["pax"], Y24["pax"]), "rev_yoy": pct(Y25["revenue"], Y24["revenue"]),
    "fare_step": f"{E['post']['fare'] / E['pre']['fare'] - 1:.0%}", "lf_yoy_pp": f"{(Y25['lf'] - Y24['lf']) * 100:+.1f}",
    "lf_2025": f"{Y25['lf']:.1%}", "rask_2025": f"Rs {Y25['rask']:.3f}", "rask_yoy": pct(Y25["rask"], Y24["rask"]),
    "rask_status": "on target" if Y25["rask"] >= Y24["rask"] * 1.05 else "below target",
    "f25_a": f"Rs {fa.p50 / 1e7:.1f} Cr", "f25_b": f"Rs {fb.p50 / 1e7:.1f} Cr",
    "bt_err": f"{BT.model.sum() / BT.actual.sum() - 1:+.1%}", "bt_naive": f"{BT.naive_last3.sum() / BT.actual.sum() - 1:+.1%}",
    "findings": [
        ["1. Growth is price-led. ", f"Jan to May 2025 vs 2024: passengers {pct(Y25['pax'], Y24['pax'])}, revenue {pct(Y25['revenue'], Y24['revenue'])}. "
         f"Fares rose {E['post']['fare'] / E['pre']['fare'] - 1:.0%} from Nov 2024 and load factor still went up."],
        ["2. Pune is the network. ", "31% of revenue departs PNQ; 86% of flights touch PNQ, BOM or BLR. 45 of 179 routes make 80% of revenue."],
        ["3. 53 star routes carry 40% of revenue. ", f"48 routes sit below the network on both load factor and RASK (19% of revenue), led by BLR-BOM and DEL-GOX."],
        ["4. RASK is on target. ", f"Rs {Y25['rask']:.3f} per seat-km in 2025, {pct(Y25['rask'], Y24['rask'])} vs last year; yield explains almost 90% of the gain."],
        ["5. International underperforms. ", f"4% of flights, 7% of revenue, but load factor {Mk['lf']['International']:.0%} vs {Mk['lf']['Domestic']:.0%} domestic."],
        ["6. Summer is the soft spot. ", "Jul to Oct 2024 ran at 55.9% load factor and the lowest RASK; there is no weekday pattern."],
        ["7. 2025 outlook: ", f"about Rs {fa.p50 / 1e7:.1f} Cr revenue if fares hold, Rs {fb.p50 / 1e7:.1f} Cr if they settle, vs Rs 40.1 Cr in 2024."],
        ["8. Biggest lever: ", f"move capacity off the weakest routes (+Rs {LV.uplift.iloc[2] / 1e7:.2f} Cr a year), then a 5% fare rise on full, low-RASK routes (+Rs {LV.uplift.iloc[1] / 1e7:.2f} Cr)."],
    ],
    "data_notes": [
        ["Distances corrected. ", "5,660 flights (14%) on 19 routes carried another route's distance (PNQ-BOM as 1,138 km, the Delhi-Mumbai distance). Great-circle distance from airport coordinates replaces them."],
        ["PNQ-BOM pricing. ", "124 km but priced above BLR-BOM (834 km): its fare looks based on the wrong distance, so its RASK (Rs 1.68) is an outlier."],
        ["Scaled figures. ", "No flight exceeds 66.7% load and fares average Rs 293 per passenger: passengers and revenue look scaled. Comparisons hold; absolute values are illustrative."],
        ["Fare outliers flagged. ", "86 flights priced above 3x their route's median fare (0.5% of revenue) are flagged, not removed."],
        ["Repeated flight numbers. ", "930 flights share a number, date and route with another flight but differ in seats, passengers and revenue: kept as separate flights."],
        ["Definitions. ", "ASK = seats x km, RPK = passengers x km, RASK = revenue / ASK. Dates run 1 Jan 2024 to 31 May 2025; year-on-year compares Jan to May."],
    ],
}
json.dump(facts, open(OUTPUT_DIR / "report_facts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
facts["findings"][:3]
'''),
]

for name, cells in {"00_load_clean": n00, "01_audit": n01, "02_eda": n02, "03_forecast": n03, "04_levers": n04}.items():
    nbf.write(nb(cells), HERE / f"{name}.ipynb")
print("written 5 notebooks")
