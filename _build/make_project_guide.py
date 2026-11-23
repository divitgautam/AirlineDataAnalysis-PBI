"""Builds docs/AirlineDataAnalysis-PBI_Project_Guide.pdf: a step-by-step guide to how this project was built.
HTML + CSS (Runway theme) printed to PDF by Microsoft Edge (headless). Tables are read from the project itself:
audit results, DAX measures (TMDL), notebook outputs, git history. Run: python _build/make_project_guide.py"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_build"))
import airline_theme as t  # noqa: E402

NAME = "AirlineDataAnalysis-PBI"
OUT = ROOT / "docs" / f"{NAME}_Project_Guide.pdf"
HTML = ROOT / "docs" / "guide" / "project_guide.html"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
E = html.escape

# ------------------------------------------------------------------ data pulled from the project
audit = pd.read_csv(ROOT / "analysis/output/audit_findings.csv", encoding="utf-8")
levers = pd.read_csv(ROOT / "analysis/output/pbi_levers.csv")
bt = pd.read_csv(ROOT / "analysis/output/forecast_backtest.csv")
facts = json.loads((ROOT / "analysis/output/report_facts.json").read_text(encoding="utf-8"))
tmdl = (ROOT / f"{NAME}.SemanticModel/definition/tables/_Measures.tmdl").read_text(encoding="utf-8")
measures = []
# Desktop writes single-word names unquoted (measure RASK = ...) and others quoted (measure 'Load Factor %' = ...)
for m in re.finditer(r"(?:\t/// (?P<d>[^\n]*)\n)?\tmeasure (?:'(?P<q>[^']+)'|(?P<u>[^'\s=][^=\n]*?)) = (?P<e>[^\n]*)\n(?P<props>(?:\t\t[^\n]*\n)*)", tmdl):
    folder = re.search(r"displayFolder: (.*)", m["props"])
    measures.append(dict(name=m["q"] or m["u"], expr=m["e"], desc=m["d"] or "", folder=folder.group(1) if folder else ""))
assert len(measures) == len(re.findall(r"^\tmeasure ", tmdl, re.M)), "measure parser missed some definitions"
commits = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%h|%ad|%s", "--date=short"],
                         capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()
n_measures = len(measures)
fig = lambda p: (ROOT / p).as_uri()

# ------------------------------------------------------------------ small HTML helpers
def table(df, cols=None, cls=""):
    cols = cols or list(df.columns)
    head = "".join(f"<th>{E(c)}</th>" for c in cols)
    rows = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in df[cols].itertuples(index=False))
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'


def section(num, title, lead, body):
    return (f'<section class="page"><div class="sec-head"><span class="sec-num">{num}</span><div><h2>{E(title)}</h2>'
            f'<p class="lead">{lead}</p></div></div>{body}</section>')


def flow(steps, cls="flow"):
    """Horizontal or wrapped chain of boxes with arrows: steps = [(title, text), ...]."""
    items = []
    for i, (a, b) in enumerate(steps):
        items.append(f'<div class="node"><div class="node-t">{a}</div><div class="node-b">{b}</div></div>')
        if i < len(steps) - 1:
            items.append('<div class="arrow">&#10140;</div>')
    return f'<div class="{cls}">{"".join(items)}</div>'


def callout(title, text, kind="info"):
    return f'<div class="callout {kind}"><b>{title}</b> {text}</div>'


def code(text):
    return f"<pre><code>{E(text)}</code></pre>"


status_badge = lambda s: f'<span class="badge {s.lower()}">{s}</span>'

# ------------------------------------------------------------------ diagrams (inline SVG)
def star_schema_svg():
    W, H = 900, 430
    boxes = {
        "Flights": (330, 150, 240, 150, t.BLUE, ["FlightID, Route, Market", "Seats, Passengers, Revenue", "Distance Km (corrected)",
                                                  "ASK, RPK, Fare Outlier"]),
        "Date": (360, 10, 180, 92, t.NAVY, ["Date, Year, Month", "Weekday, Year Month"]),
        "Origin Airport": (20, 160, 220, 110, t.NAVY, ["IATA, City, State", "Country, Region", "Latitude, Longitude"]),
        "Destination Airport": (660, 160, 220, 110, t.NAVY, ["Same columns", "(role-playing copy)"]),
        "_Measures": (360, 340, 180, 76, t.AMBER, [f"{n_measures} DAX measures", f"in {len({m['folder'] for m in measures})} folders"]),
        "Forecast / Forecast 2025 / Levers": (630, 330, 260, 86, t.SLATE, ["From notebooks 03-04", "(CSV, ProjectFolder)"]),
        "Scenario": (660, 10, 160, 70, t.SLATE, ["Shared slicer list"]),
    }
    lines = [((450, 102), (450, 150), "1 : *  Departure Date"), ((240, 215), (330, 215), "1 : *  Origin"),
             ((660, 215), (570, 215), "1 : *  Destination"), ((740, 80), (760, 330), "1 : *  scenario")]
    s = [f'<svg viewBox="0 0 {W} {H}" class="diagram" xmlns="http://www.w3.org/2000/svg">']
    for (x1, y1), (x2, y2), lab in lines:
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t.CYAN}" stroke-width="2.5" stroke-dasharray="6 4"/>')
        s.append(f'<text x="{(x1 + x2) / 2 + 6}" y="{(y1 + y2) / 2 - 6}" font-size="11" fill="{t.MUTED}">{E(lab)}</text>')
    for name, (x, y, w, h, c, rows) in boxes.items():
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{c}" stroke-width="2"/>')
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="10" fill="{c}"/><rect x="{x}" y="{y + 16}" width="{w}" height="10" fill="{c}"/>')
        s.append(f'<text x="{x + 12}" y="{y + 18}" font-size="13" font-weight="700" fill="#fff" font-family="Bahnschrift">{E(name)}</text>')
        for i, r in enumerate(rows):
            s.append(f'<text x="{x + 12}" y="{y + 44 + i * 17}" font-size="12" fill="{t.INK}">{E(r)}</text>')
    s.append("</svg>")
    return "".join(s)


def rask_tree():
    return ('<div class="eq">'
            '<div class="eqbox big">RASK<br><small>revenue / ASK</small></div><div class="op">=</div>'
            '<div class="eqbox">Seat-km load factor<br><small>RPK / ASK</small></div><div class="op">&times;</div>'
            '<div class="eqbox">Yield per RPK<br><small>revenue / RPK</small></div></div>'
            '<div class="eq sub"><div class="eqbox s">ASK = seats &times; km</div><div class="eqbox s">RPK = passengers &times; km</div>'
            '<div class="eqbox s">km = corrected distance</div></div>')


def palette():
    sw = [("Night-sky navy", t.NAVY), ("Sky blue", t.BLUE), ("Contrail cyan", t.CYAN), ("Runway amber", t.AMBER),
          ("Coral (below target)", t.CORAL), ("Green (on target)", t.GREEN), ("Cloud background", t.BG)]
    return '<div class="swatches">' + "".join(
        f'<div class="sw"><div class="chip" style="background:{c}"></div><b>{E(n)}</b><br><code>{c}</code></div>' for n, c in sw) + "</div>"


# ------------------------------------------------------------------ content
measure_rows = pd.DataFrame(measures)
key_names = ["Revenue", "ASK", "RPK", "Load Factor %", "RASK", "Yield per RPK", "Revenue Share %", "Network RASK",
             "Route Quadrant", "Review Route Revenue", "Revenue YoY %", "RASK Target", "RASK Status", "Fcst P50", "F25 Revenue"]
km = measure_rows.set_index("name").loc[[n for n in key_names if n in set(measure_rows.name)]].reset_index()
km["expr"] = km.expr.map(lambda e: f"<code>{E(e[:150] + ('…' if len(e) > 150 else ''))}</code>")
km["name"] = km.name.map(lambda n: f"<b>{E(n)}</b>")
folders = measure_rows.groupby("folder").name.apply(lambda s: ", ".join(s)).reset_index()
folders.columns = ["Folder", "Measures"]
folders["Measures"] = folders.Measures.map(E)

aud = audit.copy()
aud["status"] = aud.status.map(status_badge)
aud["detail"] = aud.detail.map(E)
aud.columns = ["#", "Check", "Status", "Count", "Finding"]

lv = levers.copy()
lv["uplift"] = lv.uplift.map(lambda v: f"&#8377;{v / 1e7:,.2f} Cr")
lv["uplift_pct_of_revenue"] = lv.uplift_pct_of_revenue.map(lambda v: f"{v:.1%}")
lv = lv[["lever", "uplift", "uplift_pct_of_revenue", "basis", "confidence"]]
lv.columns = ["Lever", "Uplift / year", "% revenue", "How it was sized", "Confidence"]

btab = bt.assign(month=pd.to_datetime(bt.month).dt.strftime("%b %Y"))
btab = btab.assign(actual=btab.actual.map("{:,.0f}".format), model=btab.model.map("{:,.0f}".format),
                   naive_last3=btab.naive_last3.map("{:,.0f}".format))
btab.columns = ["Month", "Actual passengers", "Model", "Naive (last 3 months)"]

com = pd.DataFrame([c.split("|", 2) for c in commits], columns=["Commit", "Date", "Message"])
com["Commit"] = com.Commit.map(lambda c: f"<code>{c}</code>")

recon = pd.DataFrame([("Flights", "40,175"), ("Passengers", "2,214,543"), ("Seats", "3,767,214"), ("Revenue", "&#8377;64,89,72,690"),
                      ("ASK (seat-km)", "4,142,864,685"), ("RPK", "2,424,978,029"), ("Routes", "179"),
                      ("Distance-corrected flights", "5,660"), ("Fare outliers", "86")], columns=["Total", "Python = Power BI"])

bugs = pd.DataFrame([
    ("Share column showed 100% on every airport row", "Share measure used ALLSELECTED(Route), so each airport was 100% of itself",
     "DIVIDE([Revenue], CALCULATE([Revenue], ALLSELECTED()))"),
    ("&quot;Weakest routes&quot; picked tiny routes", "Bottom-10 by RASK favours thin routes", "Top 10 by [Review Route Revenue]: biggest routes in the review quadrant"),
    ("Routes flipped in and out of &quot;review&quot;", "Network averages were recalculated inside the visual's own Top-N filter",
     "Network LF / RASK use REMOVEFILTERS(Flights[Route])"),
    ("Table showed only the Route column", "PBIR tableEx dropped measure columns in Desktop", "Switched to a matrix (pivotTable)"),
    ("Route map squashed", "PNQ-BOM RASK 1.68 (fare based on the wrong distance)", "Y axis fixed at 0-0.6, outlier noted"),
    ("Cards showed &#8377;29M and 2M", "Auto display units", "Text measures in crore / millions"),
    ("CSV paths lost a letter (&quot;nalysis&quot;)", "Python read \\a as a control character", "Build paths with chr(92)"),
    ("PDF had 1 of 5 pages", "Read the export while Power BI was still writing it", "Wait until the file stops growing"),
], columns=["Symptom", "Cause", "Fix"])

nbs = pd.DataFrame([
    ("00_load_clean", "Apply the cleaning rules; assert every total equals Power BI", "data/flights.parquet"),
    ("01_audit", "14 data-quality checks (6 pass, 7 warn, 1 fail)", "audit_findings.csv, figures a06/a09"),
    ("02_eda", "The brief's three questions: quadrants, hubs, trends, RASK", "eda_findings.csv, route_scorecard.csv, figures e01/e02"),
    ("03_forecast", "Passengers (trend + seasonality) x fare scenarios, backtested", "pbi_forecast*.csv, forecast_backtest.csv, figure f01"),
    ("04_levers", "Four revenue levers + facts for the report text", "pbi_levers.csv, report_facts.json"),
], columns=["Notebook", "What it does", "Outputs"])
nbs["Notebook"] = nbs.Notebook.map(lambda n: f"<code>{n}.ipynb</code>")

pq_steps = [("Csv.Document", "read the raw CSV via the <code>SourceFile</code> parameter"), ("Types", "integers, text"),
            ("Date.FromText", "dd-MM-yyyy &rarr; date"), ("Join airports x2", "origin and destination coordinates + country"),
            ("Great-circle km", "haversine on lat/lon"), ("Distance Corrected", "recorded / great-circle outside 0.9-1.25"),
            ("Distance Km", "recorded, or great-circle when corrected"), ("Route, Market", "PNQ-BLR; Domestic / International"),
            ("ASK, RPK, Fare", "seats &times; km, passengers &times; km, revenue / passengers"),
            ("Route median fare", "Table.Group + join"), ("Fare Outlier", "fare &gt; 3 &times; route median")]

pages_tbl = pd.DataFrame([
    ("1. Network & Routes", "Q1", "Top routes, route map (LF vs RASK), airports by region, biggest routes to review"),
    ("2. Demand Trends", "Q2", "2025 vs 2024 cards, monthly passengers and fare, LF by month, weekday"),
    ("3. KPI: RASK", "Q3", "RASK vs target, monthly RASK and seat-km LF, domestic vs international drivers"),
    ("4. Key Insights", "All", "Eight findings and six data notes, generated from the notebooks"),
    ("5. Forecast & Levers", "Next steps", "Jun-Dec 2025 forecast (two fare scenarios, P10-P90), revenue levers"),
], columns=["Page", "Answers", "Contents"])

files_tbl = pd.DataFrame([
    (f"{NAME}.pbip", "Open this in Power BI Desktop"), (f"{NAME}.SemanticModel/", "Model as TMDL (tables, Power Query, DAX, relationships)"),
    (f"{NAME}.Report/", "Report as PBIR JSON (pages, visuals, Runway theme, header SVG)"), ("Raw Data/", "Source CSV (not in Git)"),
    ("reference/airports.csv", "38 airports with city, region, country and coordinates"),
    ("analysis/src/metrics.py", "Cleaning rules and metrics: the Python mirror of Power Query"),
    ("analysis/*.ipynb", "Five notebooks (built by _make_notebooks.py)"), ("analysis/output/", "CSVs, figures, facts that feed the report"),
    ("_build/make_semantic_model.py", "Writes the PBIP skeleton and the whole model"), ("_build/build_report.py", "Writes the 5 report pages"),
    ("_build/pbir_kit.py", "Shared PBIR helpers (pages, cards, slicers, theme)"), ("_build/airline_theme.py", "Runway theme: palette, fonts, header art"),
    ("_build/make_*_diagram / card / guide", "LinkedIn visuals and this guide"), ("docs/", "Images, PDF export, LinkedIn post, this guide"),
], columns=["Path", "Purpose"])
files_tbl["Path"] = files_tbl.Path.map(lambda p: f"<code>{E(p)}</code>")

workflow = [("1 &middot; Setup", "folder, Git, parameters"), ("2 &middot; Profile", "shape, types, ranges"), ("3 &middot; Audit", "14 checks"),
            ("4 &middot; Clean", "distance &amp; fare rules"), ("5 &middot; Model", "TMDL star schema"), ("6 &middot; Measures", f"{n_measures} DAX"),
            ("7 &middot; Report", "5 PBIR pages"), ("8 &middot; Verify", "Python = Power BI"), ("9 &middot; Analyse", "EDA, forecast, levers"),
            ("10 &middot; Theme", "Runway template"), ("11 &middot; Publish", "LinkedIn, GitHub, guide")]

body = []
# ---- cover
body.append(f'''<section class="cover">
  <img class="cover-band" src="{fig('docs/theme/header_runway.svg')}">
  <div class="cover-inner">
    <div class="kicker">Project guide</div>
    <h1>{NAME}</h1>
    <p class="cover-sub">How an airline network analysis was built in Power BI and Python, step by step:
    from a raw CSV of 40,175 flights to a verified 5-page report, a forecast, revenue levers and a published portfolio piece.</p>
    <div class="stats">
      <div><b>40,175</b><span>flights</span></div><div><b>179</b><span>routes</span></div><div><b>38</b><span>airports</span></div>
      <div><b>17</b><span>months of data</span></div><div><b>{n_measures}</b><span>DAX measures</span></div><div><b>5</b><span>report pages</span></div>
    </div>
    <img class="cover-img" src="{fig('docs/dashboard/01_network_routes.png')}">
    <p class="meta">Divit Gautam &middot; November 2026 &middot; Power BI Desktop (PBIP), DAX, Power Query, Python</p>
  </div></section>''')

# ---- contents
toc = ["The brief and the answers", "Workflow at a glance", "Step 1 &middot; Project setup", "Step 2 &middot; Profiling the data",
       "Step 3 &middot; Data audit", "Step 4 &middot; Cleaning rules in Power Query", "Step 5 &middot; Data model",
       "Step 6 &middot; DAX measures and the RASK KPI", "Step 7 &middot; Building the report", "Step 8 &middot; Verification and fixes",
       "Step 9 &middot; Python analysis", "Step 10 &middot; Forecast and revenue levers", "Step 11 &middot; The Runway theme",
       "Step 12 &middot; Publishing", "How to reproduce", "Lessons learned", "Appendix &middot; File map"]
body.append(section("&#9776;", "Contents", "Each step maps to files you can open in VS Code.",
                    "<ol class='toc'>" + "".join(f"<li>{x}</li>" for x in toc) + "</ol>"))

# ---- brief
body.append(section("0", "The brief and the answers",
    "The dataset came without questions, so the brief was set first: three questions an airline network team would ask.",
    table(pd.DataFrame([
        ("1. Network &amp; route performance", "Which routes and airports drive revenue; which underperform on load factor and fare?",
         "Pune is the hub (31% of revenue). 45 of 179 routes make 80%. 53 star routes earn 40%; 48 routes trail on both LF and RASK (19%)."),
        ("2. Demand trends", "How are passengers, load factor and revenue moving, 2025 vs 2024?",
         f"Jan-May: passengers {facts['pax_yoy']}, revenue {facts['rev_yoy']}. Fares +{facts['fare_step']} from Nov 2024; LF {facts['lf_yoy_pp']} pp."),
        ("3. KPI design", "One KPI linking capacity to revenue", f"RASK = revenue per available seat-km: {facts['rask_2025'].replace('Rs ', '&#8377;')} in 2025, {facts['rask_yoy']}, on target."),
    ], columns=["Question", "What it asks", "Answer"]), cls="wide")
    + callout("Why set a brief?", "Without one, a dashboard becomes a chart gallery. Three explicit questions decide every page, measure and visual that follows.")))

# ---- workflow
body.append(section("&#9654;", "Workflow at a glance", "Eleven steps, in the order they were done. Steps 4-8 loop until Python and Power BI agree exactly.",
    flow(workflow, "flow wrap") + f'<img class="full" src="{fig("docs/approach_diagram.png")}">'))

# ---- step 1 setup
body.append(section("1", "Project setup", "Every Power BI project gets its own folder, its own Git repository and path parameters.",
    "<h3>Folder convention</h3>" + code(f"D:\\Wolf\\PBI\\{NAME}\\\n  Raw Data\\Flight Data Assessment 2025.csv   (source, kept out of Git)\n"
                                         f"  reference\\airports.csv                      (built for this project)\n  {NAME}.pbip / .SemanticModel / .Report\n"
                                         "  analysis\\   _build\\   docs\\") +
    "<h3>Power Query parameters</h3><p>No hard-coded paths. Every query reads its location from two parameters, so moving or cloning the project "
    "means editing two values in <i>Transform data &rarr; Manage Parameters</i>.</p>" +
    table(pd.DataFrame([("ProjectFolder", "D:\\Wolf\\PBI\\AirlineDataAnalysis-PBI", "airports.csv, forecast and lever CSVs"),
                        ("SourceFile", "...\\Raw Data\\Flight Data Assessment 2025.csv", "Flights table")], columns=["Parameter", "Value", "Used by"])) +
    "<h3>Git</h3><p>Repository inside the project folder, repo-local author, and a <code>.gitignore</code> that keeps the raw data, "
    "<code>.pbix</code> copies, Desktop cache and parquet files out.</p>" +
    callout("Airport reference data.", "The CSV has only IATA codes. A 38-row airport table (city, state, country, region, latitude, longitude) "
            "was built so routes can be grouped by region and distances checked against geography.")))

# ---- step 2 profiling
dd = pd.DataFrame([("FlightID", "int", "Unique flight key (not in date order)"), ("DepartureDate", "text dd-mm-yyyy", "1 Jan 2024 to 31 May 2025, no gaps"),
                   ("Origin / Destination", "IATA code", "38 airports, 179 routes"), ("FlightNumber", "int", "Reused across up to 9 routes"),
                   ("Distance", "km", "Recorded distance (14% wrong, see step 3)"), ("DomesticFlag", "0/1", "0 = touches AUH, DOH, JED, KWI or RUH"),
                   ("Capacity", "seats", "87, 93, 95 or 99 (4 odd values)"), ("PaxCount", "passengers", "1 to 66"), ("Revenue", "rupees", "&#8377;347 to &#8377;1,25,813 per flight")],
                  columns=["Column", "Type", "What it holds"])
body.append(section("2", "Profiling the data", "First pass in Python: shape, types, ranges and anything that looks wrong.",
    table(dd) + "<h3>What profiling flagged</h3><ul>"
    "<li>No missing values, no duplicate IDs, every date valid.</li>"
    "<li>17 routes carry two different distances (AMD-BOM as 444 and 756 km).</li>"
    "<li>Load factor never exceeds 66.7%: passenger counts look scaled.</li>"
    "<li>Fare per passenger ranges from &#8377;21 to &#8377;3,639 (median &#8377;268).</li></ul>" +
    f'<img class="half" src="{fig("analysis/output/figures/a09_load_factor_ceiling.png")}">'))

# ---- step 3 audit
body.append(section("3", "Data audit", "14 checks, each recorded with a status. Notebook <code>01_audit.ipynb</code>; results in <code>audit_findings.csv</code>.",
    table(aud, cls="small") +
    f'<div class="two"><img src="{fig("analysis/output/figures/a06_distance_check.png")}"><div>'
    + callout("The distance problem.", "86% of flights carry their true great-circle distance, so the field is real. The other 14% carry "
              "<i>another route's</i> distance: PNQ-BOM recorded as 1,138 km is the Delhi-Mumbai distance; the true figure is 124 km.", "warn")
    + callout("Why it matters.", "RASK divides revenue by seat-km. With wrong kilometres, every per-km number for the Mumbai and Pune routes would be wrong.")
    + "</div></div>"))

# ---- step 4 cleaning
body.append(section("4", "Cleaning rules in Power Query", "The rules live in the model (Power Query M) and are mirrored line for line in <code>analysis/src/metrics.py</code>.",
    flow([(a, b) for a, b in pq_steps], "flow vertical") +
    "<h3>The two rules, in plain words</h3><ol>"
    "<li><b>Distance:</b> keep the recorded km when it is within 0.9-1.25&times; the great-circle distance; otherwise use the great-circle km.</li>"
    "<li><b>Fare outlier:</b> flag a flight whose fare per passenger is above 3&times; its route's median. "
    "A per-km test was tried first and rejected: short routes naturally earn more per km, so it flagged every Pune-Mumbai flight.</li></ol>" +
    code('GreatCircle = 6371 * 2 * Number.Asin(Number.Sqrt(\n'
         '    Number.Power(Number.Sin((d_lat - o_lat) * r / 2), 2)\n'
         '  + Number.Cos(o_lat * r) * Number.Cos(d_lat * r) * Number.Power(Number.Sin((d_lon - o_lon) * r / 2), 2)))\n'
         'Distance Km = if not (ratio >= 0.9 and ratio <= 1.25) then Number.Round(GreatCircle) else [Distance]') +
    callout("No rows removed.", "930 flights share a flight number, date and route with another flight but have different seats, passengers and revenue: they are separate operations.")))

# ---- step 5 model
body.append(section("5", "Data model", "A star schema written as TMDL by <code>_build/make_semantic_model.py</code>, then opened in Power BI Desktop.",
    star_schema_svg() +
    "<ul><li><b>Role-playing airports:</b> the same reference list loads twice, as Origin and Destination, each with a one-to-many link.</li>"
    "<li><b>Date table</b> ends on the last flight (31 May 2025), so 2025 vs 2024 compares Jan-May with Jan-May.</li>"
    "<li><b>Auto date/time off</b>: no hidden date tables.</li>"
    "<li><b>Forecast tables</b> read the notebooks' CSVs; a shared <i>Scenario</i> table lets one slicer drive both.</li></ul>" +
    callout("Why write TMDL instead of clicking?", "The model is generated from one script, so it can be rebuilt, reviewed in Git and reused for the next project.")))

# ---- step 6 measures
body.append(section("6", "DAX measures and the RASK KPI", f"{n_measures} measures in a dedicated <code>_Measures</code> table, grouped into folders.",
    rask_tree() + "<h3>Measure folders</h3>" + table(folders, cls="small") + "<h3>Key measures</h3>" + table(km[["name", "expr"]].rename(columns={"name": "Measure", "expr": "DAX"}), cls="small code")))

# ---- step 7 report
body.append(section("7", "Building the report", "Pages are generated as PBIR JSON by <code>_build/build_report.py</code>, then loaded with <i>Apply external changes</i>.",
    table(pages_tbl) + flow([("build_report.py", "pages &amp; visuals"), ("pbir_kit.py", "cards, slicers, theme"), ("pbi report validate", "schema check"),
                             ("Power BI Desktop", "Apply external changes"), ("Ctrl+S", "save, then regenerate")]) +
    '<div class="grid2">' + "".join(f'<figure><img src="{fig(f"docs/dashboard/{p}.png")}"><figcaption>{c}</figcaption></figure>'
                                    for p, c in [("02_demand_trends", "Page 2: Demand Trends"), ("03_kpi_rask", "Page 3: KPI: RASK")]) + "</div>"))

# ---- step 8 verification
body.append(section("8", "Verification and fixes", "Nothing ships until Python and Power BI agree exactly, and every page has been looked at in Desktop.",
    "<div class='two'><div>" + table(recon) + "</div><div>" +
    callout("Exact, not approximate.", "Notebook <code>00_load_clean</code> asserts these totals. Seat-km matching to the unit proves Power Query and Python compute the corrected distances identically.", "ok") +
    "</div></div><h3>Problems found in Desktop, and how they were fixed</h3>" + table(bugs, cls="small")))

# ---- step 8b expert review: the 10-point scorecard (docs/review/scorecard.md)
sc_path = ROOT / "docs" / "review" / "scorecard.md"
if sc_path.exists():
    rows = [r.strip().strip("|").split("|") for r in sc_path.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\|\s*\d+\s*\|", r)]
    sc = pd.DataFrame([[c.strip() for c in r[:5]] for r in rows], columns=["#", "Criterion", "Before", "After", "What changed"])
    tot = re.search(r"\*\*Total\*\*\s*\|\s*\*\*([\d.]+)[^|]*\|\s*\*\*([\d.]+)", sc_path.read_text(encoding="utf-8"))
    lead = (f"Scored against <code>D:\\Wolf\\PBI\\_knowledge\\dashboard_scorecard.md</code>: {tot.group(1)} before the review, "
            f"{tot.group(2)} after." if tot else "Scored against the 10-point dashboard scorecard.")
    body.append(section("8b", "Expert review: the 10-point scorecard", lead,
        table(sc, cls="small") +
        callout("How it was run.", "Score from evidence (the PDF export, the TMDL, Performance Analyzer, the Python reconciliation), "
                "fix the cheapest high-value items, re-export, re-score. Gates cap the total for wrong numbers, misleading charts, "
                "clipped text or accessibility failures.", "ok")))

# ---- step 9 python
body.append(section("9", "Python analysis", "Five notebooks, generated by <code>analysis/_make_notebooks.py</code> and run with nbconvert.",
    table(nbs) + f'<div class="two"><img src="{fig("analysis/output/figures/e01_route_quadrants.png")}"><img src="{fig("analysis/output/figures/e02_monthly_trend.png")}"></div>' +
    callout("Route quadrants.", "Each route is compared with the network average on load factor and RASK: Star, Fill seats, Raise yield, or Review route.")))

# ---- step 10 forecast & levers
body.append(section("10", "Forecast and revenue levers", "Revenue = passengers &times; fare, forecast separately because they behave differently.",
    flow([("Passengers", "log-linear trend + seasonal index (shrunk 50%)"), ("Backtest", "train to Feb 2025, test Mar-May"),
          ("Fares", "two scenarios after the Nov 2024 step"), ("Bootstrap", "2,000 draws of residuals"), ("Outputs", "P10 / P50 / P90 by month")]) +
    "<div class='two'><div>" + table(btab, cls="small") +
    callout("Backtest.", f"Model {facts['bt_err']} on the 3-month total vs {facts['bt_naive']} for a naive forecast.", "ok") +
    f"</div><img src='{fig('analysis/output/figures/f01_revenue_forecast.png')}'></div>" +
    "<h3>Revenue levers (sized on Jun 2024 - May 2025)</h3>" + table(lv, cls="small")))

# ---- step 11 theme
body.append(section("11", "The Runway theme", "A template built for airline analysis, kept in one file: <code>_build/airline_theme.py</code>.",
    palette() + "<ul><li><b>Typography:</b> Bahnschrift (the DIN-style face used on airport signage) for titles and numbers, Segoe UI for text.</li>"
    "<li><b>Header artwork:</b> an SVG band with dotted flight paths, a plane emblem and an amber runway line, registered inside the report.</li>"
    "<li><b>Reuse:</b> the shared kit's <code>set_theme()</code> lets each project have its own look; the LinkedIn visuals import the same palette.</li></ul>" +
    f'<img class="full" src="{fig("docs/dashboard/05_forecast_levers.png")}">'))

# ---- step 12 publishing
body.append(section("12", "Publishing", "Every finished project goes to LinkedIn and GitHub, and gets this guide.",
    "<div class='two'><div><h3>LinkedIn</h3><ul><li>Post (full and short) in <code>docs/linkedin_post.md</code></li>"
    "<li>Portrait insights card (1080&times;1350) and approach diagram (1920&times;1080)</li><li>Dashboard pages from the PDF export</li></ul>"
    "<h3>GitHub</h3><ul><li>README with answers, findings, pages and how to run</li><li>Raw data and personal details excluded</li>"
    "<li>Commits below; push to an empty repo</li></ul></div>" +
    f'<img src="{fig("docs/key_insights.png")}" class="portrait"></div>' + table(com, cls="small")))

# ---- reproduce
body.append(section("&#8635;", "How to reproduce", "From a fresh clone, in this order.",
    code("# 1. Python environment\npip install -r requirements.txt\n\n# 2. Put the source file in place\nRaw Data\\Flight Data Assessment 2025.csv\n\n"
         "# 3. Rebuild the notebooks and run them (00 asserts the totals)\ncd analysis\npython _make_notebooks.py\n"
         "jupyter nbconvert --to notebook --execute --inplace 00_load_clean.ipynb 01_audit.ipynb 02_eda.ipynb 03_forecast.ipynb 04_levers.ipynb\n\n"
         "# 4. Rebuild the model (Power BI Desktop closed) and the pages\ncd ..\npython _build/make_semantic_model.py\npython _build/build_report.py\n\n"
         "# 5. Open AirlineDataAnalysis-PBI.pbip, set ProjectFolder and SourceFile, click Refresh\n\n"
         "# 6. LinkedIn visuals and this guide\npython _build/make_approach_diagram.py\npython _build/make_insights_card.py\npython _build/make_project_guide.py")))

# ---- lessons
body.append(section("&#9733;", "Lessons learned", "What to carry into the next project.",
    "<ol class='lessons'>"
    "<li><b>Check the denominator first.</b> A per-km KPI is only as good as its kilometres; geography caught a silent lookup error.</li>"
    "<li><b>Compare like with like.</b> Short routes earn more per km; outliers must be judged within their route.</li>"
    "<li><b>Benchmarks must ignore the visual's own filter.</b> Use REMOVEFILTERS on the dimension, not ALLSELECTED.</li>"
    "<li><b>Price can move without volume falling.</b> Fares rose 39% and load factor still rose: test elasticity before assuming it.</li>"
    "<li><b>Generate, don't click.</b> Model, pages, notebooks, visuals and this guide are scripts, so the next project starts from them.</li>"
    "<li><b>Change model queries with Desktop closed;</b> measures can be changed live; pages go in through <i>Apply external changes</i>.</li>"
    "<li><b>Say what the data can't support.</b> Load factor tops out at 66.7% and fares average &#8377;293: comparisons hold, rupees are illustrative.</li></ol>"))

# ---- appendix
body.append(section("A", "Appendix · File map", "Open the project folder in VS Code to follow along.", table(files_tbl)))

CSS = f"""
@page {{ size: A4; margin: 14mm 14mm 16mm 14mm;
  @bottom-left {{ content: "{NAME} · Project guide"; font: 8pt 'Segoe UI'; color: {t.MUTED}; }}
  @bottom-right {{ content: counter(page); font: 8pt 'Bahnschrift'; color: {t.MUTED}; }} }}
@page :first {{ margin: 0; @bottom-left {{ content: none; }} @bottom-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', sans-serif; font-size: 9.6pt; color: {t.INK}; margin: 0; line-height: 1.45;
        -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1, h2, h3, .sec-num, .stats b, .node-t, .eqbox {{ font-family: 'Bahnschrift', 'Segoe UI', sans-serif; }}
section.page {{ page-break-before: always; }}
.cover {{ height: 297mm; background: linear-gradient(160deg, {t.NAVY} 0%, {t.NAVY_2} 70%, #1A5694 100%); color: #fff; position: relative; }}
.cover-band {{ width: 100%; display: block; }}
.cover-inner {{ padding: 22mm 18mm 0 18mm; }}
.kicker {{ color: {t.AMBER}; letter-spacing: 3px; text-transform: uppercase; font: 600 11pt 'Bahnschrift'; }}
.cover h1 {{ font-size: 34pt; margin: 6px 0 10px; }}
.cover-sub {{ font-size: 12pt; color: {t.SUBTITLE}; max-width: 150mm; }}
.stats {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 14mm 0 10mm; }}
.stats div {{ background: rgba(255,255,255,.08); border-top: 3px solid {t.AMBER}; border-radius: 6px; padding: 8px 10px; }}
.stats b {{ display: block; font-size: 18pt; }} .stats span {{ color: {t.SUBTITLE}; font-size: 8.5pt; }}
.cover-img {{ width: 100%; border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,.35); }}
.meta {{ color: {t.SUBTITLE}; font-size: 9pt; margin-top: 8mm; }}
.sec-head {{ display: flex; gap: 12px; align-items: flex-start; border-bottom: 3px solid {t.AMBER}; padding-bottom: 6px; margin-bottom: 10px; }}
.sec-num {{ background: {t.NAVY}; color: #fff; min-width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center;
           justify-content: center; font-size: 14pt; }}
h2 {{ margin: 0; font-size: 18pt; color: {t.NAVY}; }} h3 {{ color: {t.BLUE}; font-size: 11.5pt; margin: 12px 0 4px; }}
.lead {{ margin: 2px 0 0; color: {t.MUTED}; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 8.6pt; page-break-inside: auto; }}
th {{ background: {t.NAVY}; color: #fff; text-align: left; padding: 5px 6px; font-weight: 600; }}
td {{ border-bottom: 1px solid {t.LINE}; padding: 4px 6px; vertical-align: top; }}
tr:nth-child(even) td {{ background: {t.ROW_ALT}; }}
table.small {{ font-size: 7.8pt; }} table.code code {{ font-size: 7.2pt; }}
code, pre {{ font-family: Consolas, monospace; }}
pre {{ background: {t.NAVY}; color: #E6F0FA; padding: 8px 10px; border-radius: 6px; font-size: 8pt; white-space: pre-wrap; border-left: 4px solid {t.AMBER}; }}
td code {{ background: #EAF2FB; padding: 0 3px; border-radius: 3px; }}
.badge {{ padding: 1px 6px; border-radius: 8px; font-size: 7.5pt; font-weight: 700; color: #fff; }}
.badge.pass {{ background: {t.GREEN}; }} .badge.warn {{ background: {t.AMBER}; }} .badge.fail {{ background: {t.CORAL}; }}
.callout {{ border-left: 4px solid {t.BLUE}; background: #EAF2FB; padding: 6px 10px; border-radius: 4px; margin: 8px 0; }}
.callout.warn {{ border-color: {t.AMBER}; background: #FFF6E5; }} .callout.ok {{ border-color: {t.GREEN}; background: #E8F6EE; }}
.flow {{ display: flex; align-items: stretch; gap: 4px; margin: 8px 0 12px; }}
.flow.wrap {{ flex-wrap: wrap; row-gap: 8px; }}
.flow .node {{ flex: 1; background: #fff; border: 1.5px solid {t.BLUE}; border-top: 5px solid {t.BLUE}; border-radius: 6px; padding: 5px 7px; min-width: 22mm; }}
.flow .node:nth-child(4n+3) {{ border-top-color: {t.AMBER}; }}
.node-t {{ color: {t.NAVY}; font-size: 9pt; font-weight: 600; }} .node-b {{ color: {t.MUTED}; font-size: 7.8pt; }}
.arrow {{ color: {t.CYAN}; font-size: 14pt; display: flex; align-items: center; }}
.flow.vertical {{ flex-direction: column; gap: 0; }}
.flow.vertical .node {{ display: flex; gap: 10px; border-top-width: 1.5px; border-left: 5px solid {t.BLUE}; }}
.flow.vertical .node-t {{ min-width: 38mm; }} .flow.vertical .arrow {{ transform: rotate(90deg); justify-content: center; height: 14px; font-size: 10pt; }}
img {{ max-width: 100%; }} img.full {{ width: 100%; border: 1px solid {t.LINE}; border-radius: 6px; margin-top: 8px; }}
img.half {{ width: 60%; }} img.portrait {{ width: 70mm; border-radius: 6px; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; align-items: start; }} .two img {{ width: 100%; border: 1px solid {t.LINE}; border-radius: 6px; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }} figure {{ margin: 0; }}
figure img {{ border: 1px solid {t.LINE}; border-radius: 6px; }} figcaption {{ color: {t.MUTED}; font-size: 8pt; text-align: center; }}
svg.diagram {{ width: 100%; height: auto; font-family: 'Segoe UI'; margin: 4px 0 8px; }}
.eq {{ display: flex; align-items: center; justify-content: center; gap: 10px; margin: 8px 0; }}
.eqbox {{ background: {t.BLUE}; color: #fff; border-radius: 8px; padding: 8px 14px; text-align: center; font-size: 11pt; }}
.eqbox.big {{ background: {t.NAVY}; font-size: 14pt; border-bottom: 4px solid {t.AMBER}; }} .eqbox small {{ font: 8pt 'Segoe UI'; color: #DCEBFA; }}
.eqbox.s {{ background: #EAF2FB; color: {t.NAVY}; font-size: 9pt; padding: 4px 10px; }}
.op {{ font: 700 18pt 'Bahnschrift'; color: {t.AMBER}; }}
.swatches {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin: 8px 0; }}
.sw {{ font-size: 7.5pt; }} .chip {{ height: 26px; border-radius: 6px; border: 1px solid {t.LINE}; margin-bottom: 3px; }}
.toc {{ columns: 2; font: 11pt 'Bahnschrift'; color: {t.NAVY}; }} .toc li {{ margin: 6px 0; }}
.lessons li {{ margin: 6px 0; }}
"""
doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{NAME} Project Guide</title><style>{CSS}</style></head><body>{''.join(body)}</body></html>"
HTML.parent.mkdir(parents=True, exist_ok=True)
HTML.write_text(doc, encoding="utf-8")
r = subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                    "--virtual-time-budget=8000", f"--print-to-pdf={OUT}", HTML.as_uri()], capture_output=True, text=True)
print("PDF:", OUT, OUT.stat().st_size if OUT.exists() else "NOT CREATED", r.stderr[-300:] if not OUT.exists() else "")
