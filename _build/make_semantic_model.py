"""Writes the AirlineDataAnalysis-PBI PBIP skeleton and semantic model (TMDL).
Run with Power BI Desktop CLOSED on this project:  python _build/make_semantic_model.py
Rules mirror analysis/src/metrics.py exactly."""
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "AirlineDataAnalysis-PBI"
_facts = ROOT / "analysis" / "output" / "report_facts.json"
FACTS = json.loads(_facts.read_text(encoding="utf-8")) if _facts.exists() else {}
RPT, SM = ROOT / f"{NAME}.Report", ROOT / f"{NAME}.SemanticModel"
DEFN = SM / "definition"
T = "\t"
RUPEE = "\u20b9"


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def platform(kind: str) -> str:
    return json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                       "metadata": {"type": kind, "displayName": NAME},
                       "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}}, indent=2)


def lt() -> str:
    return f"lineageTag: {uuid.uuid4()}"


# ---------------------------------------------------------------- PBIP + report skeleton (pages come from build_report.py)
w(ROOT / f"{NAME}.pbip", json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                     "settings": {"enableAutoRecovery": True}}, indent=2))
w(RPT / "definition.pbir", json.dumps({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
if not (RPT / ".platform").exists():
    w(RPT / ".platform", platform("Report"))
w(RPT / "definition" / "version.json", json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2))
if not (RPT / "definition" / "report.json").exists():
    src = Path(r"D:\Wolf\PBI\RetailPulse-PBI\RetailPulse-PBI.Report")
    rep = json.loads((src / "definition" / "report.json").read_text(encoding="utf-8"))
    w(RPT / "definition" / "report.json", json.dumps(rep, indent=2))
    base = src / "StaticResources" / "SharedResources" / "BaseThemes"
    for f in base.glob("*.json"):
        w(RPT / "StaticResources" / "SharedResources" / "BaseThemes" / f.name, f.read_text(encoding="utf-8"))
    w(RPT / "definition" / "pages" / "pages.json", json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json", "pageOrder": []}, indent=2))

# ---------------------------------------------------------------- semantic model skeleton
w(SM / "definition.pbism", json.dumps({"version": "4.2", "settings": {}}, indent=2))
if not (SM / ".platform").exists():
    w(SM / ".platform", platform("SemanticModel"))
w(DEFN / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n\n")
if not (DEFN / "cultures" / "en-IN.tmdl").exists():   # keep Desktop's linguistic metadata (synonyms used by Copilot)
    w(DEFN / "cultures" / "en-IN.tmdl", "cultureInfo en-IN\n")
TABLES = ["Flights", "Origin Airport", "Destination Airport", "Date", "_Measures", "Forecast", "Forecast 2025", "Levers", "Scenario",
          "Refresh Info"]
q = lambda n: f"'{n}'" if " " in n else n
w(DEFN / "model.tmdl",
  "model Model\n\tculture: en-IN\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-IN\n"
  "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
  "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
  'annotation PBI_QueryOrder = ["ProjectFolder","SourceFile","AirportsRef","Flights","Origin Airport","Destination Airport","Forecast","Forecast 2025","Levers"]\n\n'
  'annotation PBI_ProTooling = ["DevMode"]\n\n'
  + "".join(f"ref table {q(t)}\n" for t in TABLES) + "\nref cultureInfo en-IN\n")

# ---------------------------------------------------------------- parameters + shared (not loaded) airports query
proj = str(ROOT)
src_csv = str(ROOT / "Raw Data" / "Flight Data Assessment 2025.csv")


def param(name, value):
    return (f'expression {name} = "{value}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
            f"{T}{lt()}\n\n{T}annotation PBI_NavigationStepName = Navigation\n\n{T}annotation PBI_ResultType = Text\n\n")


airports_m = "\n".join([
    "let",
    '    Source = Csv.Document(File.Contents(ProjectFolder & "\\reference\\airports.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
    "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
    '    Typed = Table.TransformColumnTypes(Promoted, {{"IATA", type text}, {"Airport", type text}, {"City", type text}, {"State", type text}, '
    '{"Country", type text}, {"Region", type text}, {"Latitude", type number}, {"Longitude", type number}}, "en-US")',
    "in",
    "    Typed"])
ind = lambda m, n: "\n".join(T * n + ln for ln in m.splitlines())
w(DEFN / "expressions.tmdl",
  param("ProjectFolder", proj) + param("SourceFile", src_csv)
  + f"/// Airport reference list (not loaded): feeds Flights and both airport tables.\nexpression AirportsRef =\n{ind(airports_m, 3)}\n"
  + f"{T}{lt()}\n\n{T}annotation PBI_ResultType = Table\n")

# ---------------------------------------------------------------- Flights fact
flights_m = r'''let
    Source = Csv.Document(File.Contents(SourceFile), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"FlightID", Int64.Type}, {"DepartureDate", type text}, {"Origin", type text}, {"Destination", type text}, {"FlightNumber", Int64.Type}, {"Distance", Int64.Type}, {"DomesticFlag", Int64.Type}, {"Capacity", Int64.Type}, {"PaxCount", Int64.Type}, {"Revenue", Int64.Type}}, "en-US"),
    Dated = Table.AddColumn(Typed, "Departure Date", each Date.FromText([DepartureDate], [Format = "dd-MM-yyyy", Culture = "en-GB"]), type date),
    Airports = Table.Buffer(Table.SelectColumns(AirportsRef, {"IATA", "Latitude", "Longitude", "Country"})),
    JoinO = Table.NestedJoin(Dated, {"Origin"}, Airports, {"IATA"}, "o", JoinKind.LeftOuter),
    ExpO = Table.ExpandTableColumn(JoinO, "o", {"Latitude", "Longitude", "Country"}, {"o_lat", "o_lon", "o_country"}),
    JoinD = Table.NestedJoin(ExpO, {"Destination"}, Airports, {"IATA"}, "d", JoinKind.LeftOuter),
    ExpD = Table.ExpandTableColumn(JoinD, "d", {"Latitude", "Longitude", "Country"}, {"d_lat", "d_lon", "d_country"}),
    GreatCircle = Table.AddColumn(ExpD, "Great Circle Km", each
        let r = Number.PI / 180,
            a = Number.Power(Number.Sin(([d_lat] - [o_lat]) * r / 2), 2)
                + Number.Cos([o_lat] * r) * Number.Cos([d_lat] * r) * Number.Power(Number.Sin(([d_lon] - [o_lon]) * r / 2), 2)
        in 6371 * 2 * Number.Asin(Number.Sqrt(a)), type number),
    Corrected = Table.AddColumn(GreatCircle, "Distance Corrected", each
        let ratio = [Distance] / [Great Circle Km] in not (ratio >= 0.9 and ratio <= 1.25), type logical),
    DistKm = Table.AddColumn(Corrected, "Distance Km", each
        if [Distance Corrected] then Number.Round([Great Circle Km], 0, RoundingMode.ToEven) else [Distance], Int64.Type),
    Route = Table.AddColumn(DistKm, "Route", each [Origin] & "-" & [Destination], type text),
    Market = Table.AddColumn(Route, "Market", each if [o_country] <> "India" or [d_country] <> "India" then "International" else "Domestic", type text),
    ASK = Table.AddColumn(Market, "ASK", each [Capacity] * [Distance Km], Int64.Type),
    RPK = Table.AddColumn(ASK, "RPK", each [PaxCount] * [Distance Km], Int64.Type),
    Fare = Table.AddColumn(RPK, "Fare", each [Revenue] / [PaxCount], type number),
    RouteMedians = Table.Group(Fare, {"Route"}, {{"Route Median Fare", each List.Median([Fare]), type number}}),
    JoinMed = Table.NestedJoin(Fare, {"Route"}, RouteMedians, {"Route"}, "m", JoinKind.LeftOuter),
    ExpMed = Table.ExpandTableColumn(JoinMed, "m", {"Route Median Fare"}),
    Outlier = Table.AddColumn(ExpMed, "Fare Outlier", each [Fare] > 3 * [Route Median Fare], type logical),
    Cleaned = Table.RemoveColumns(Outlier, {"DepartureDate", "o_lat", "o_lon", "o_country", "d_lat", "d_lon", "d_country", "Distance", "DomesticFlag", "Great Circle Km", "Fare", "Route Median Fare"})
in
    Cleaned'''


def column(name, dtype, fmt=None, hidden=False, summarize="none", folder=None, sort_by=None):
    s = f"{T}column {q(name)}\n{T * 2}dataType: {dtype}\n"
    if fmt: s += f"{T * 2}formatString: {fmt}\n"
    if hidden: s += f"{T * 2}isHidden\n"
    if folder: s += f"{T * 2}displayFolder: {folder}\n"
    if sort_by: s += f"{T * 2}sortByColumn: {q(sort_by)}\n"
    s += f"{T * 2}{lt()}\n{T * 2}summarizeBy: {summarize}\n{T * 2}sourceColumn: {name}\n\n{T * 2}annotation SummarizationSetBy = User\n\n"
    return s


fcols = [("FlightID", "int64", "0", False), ("Origin", "string", None, False), ("Destination", "string", None, False),
         ("FlightNumber", "int64", "0", False),
         ("Capacity", "int64", "#,##0", False), ("PaxCount", "int64", "#,##0", False), ("Revenue", "int64", "#,##0", False),
         ("Departure Date", "dateTime", "dd-mmm-yyyy", False),
         ("Distance Corrected", "boolean", None, False), ("Distance Km", "int64", "#,##0", False), ("Route", "string", None, False),
         ("Market", "string", None, False), ("ASK", "int64", "#,##0", True), ("RPK", "int64", "#,##0", True),
         ("Fare Outlier", "boolean", None, False)]
fl = "/// One row per flight (Raw Data CSV). Distance and fare-outlier rules: see analysis/src/metrics.py.\ntable Flights\n" + f"{T}{lt()}\n\n"
fl += "".join(column(n, d, f, h) for n, d, f, h in fcols)
fl += f"{T}partition Flights = m\n{T * 2}mode: import\n{T * 2}source =\n{ind(flights_m, 4)}\n\n{T}annotation PBI_ResultType = Table\n"
w(DEFN / "tables" / "Flights.tmdl", fl)


# ---------------------------------------------------------------- airport dimensions (role-playing)
def airport_table(name):
    m = "let\n    Source = AirportsRef,\n    Label = Table.AddColumn(Source, \"Airport Label\", each [IATA] & \" \u00b7 \" & [City], type text)\nin\n    Label"
    cols = [("IATA", "string", None, False), ("Airport", "string", None, False), ("City", "string", None, False),
            ("State", "string", None, False), ("Country", "string", None, False), ("Region", "string", None, False),
            ("Airport Label", "string", None, False)]
    m = m.replace("\nin\n    Label", ",\n    Trimmed = Table.RemoveColumns(Label, {\"Latitude\", \"Longitude\"})\nin\n    Trimmed")
    s = f"table {q(name)}\n{T}{lt()}\n\n" + "".join(column(n, d, f, h) for n, d, f, h in cols)
    s = s.replace(f"{T}column Latitude\n{T * 2}dataType: double\n", f"{T}column Latitude\n{T * 2}dataType: double\n{T * 2}dataCategory: Latitude\n")
    s = s.replace(f"{T}column Longitude\n{T * 2}dataType: double\n", f"{T}column Longitude\n{T * 2}dataType: double\n{T * 2}dataCategory: Longitude\n")
    s += f"{T}partition {q(name)} = m\n{T * 2}mode: import\n{T * 2}source =\n{ind(m, 4)}\n\n{T}annotation PBI_ResultType = Table\n"
    return s


w(DEFN / "tables" / "Origin Airport.tmdl", airport_table("Origin Airport"))
w(DEFN / "tables" / "Destination Airport.tmdl", airport_table("Destination Airport"))

# ---------------------------------------------------------------- Date (calculated, ends on the last flight date)
date_dax = ('ADDCOLUMNS ( CALENDAR ( DATE ( YEAR ( MIN ( Flights[Departure Date] ) ), 1, 1 ), MAX ( Flights[Departure Date] ) ), '
            '"Year", YEAR ( [Date] ), "Quarter", "Q" & QUARTER ( [Date] ), "Month No", MONTH ( [Date] ), '
            '"Month", FORMAT ( [Date], "MMM" ), "Month Start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ), '
            '"Year Month", FORMAT ( [Date], "MMM yy" ), "Year Month Key", YEAR ( [Date] ) * 100 + MONTH ( [Date] ), '
            '"Weekday No", WEEKDAY ( [Date], 2 ), "Weekday", FORMAT ( [Date], "ddd" ) )')
dcols = [("Date", "dateTime", "dd-mmm-yyyy", None), ("Year", "int64", "0", None), ("Quarter", "string", None, None),
         ("Month No", "int64", "0", None), ("Month", "string", None, "Month No"), ("Month Start", "dateTime", "mmm yyyy", None),
         ("Year Month", "string", None, "Year Month Key"), ("Year Month Key", "int64", "0", None),
         ("Weekday No", "int64", "0", None), ("Weekday", "string", None, "Weekday No")]
ds = f"table Date\n{T}{lt()}\n{T}dataCategory: Time\n\n"
for n, d, f, sb in dcols:
    s = f"{T}column {q(n)}\n{T * 2}dataType: {d}\n"
    if n == "Date": s += f"{T * 2}isKey\n"
    if f: s += f"{T * 2}formatString: {f}\n"
    if sb: s += f"{T * 2}sortByColumn: {q(sb)}\n"
    s += f"{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}isNameInferred\n{T * 2}sourceColumn: [{n}]\n\n"
    ds += s
ds += f"{T}partition Date = calculated\n{T * 2}mode: import\n{T * 2}source = {date_dax}\n"
w(DEFN / "tables" / "Date.tmdl", ds)

# ---------------------------------------------------------------- measures
R0, R3, PCT, PP, INT, DEC1 = f"{RUPEE}#,##0", f"{RUPEE}0.000", "0.0%", "+0.0;-0.0;0.0", "#,##0", "#,##0.0"
NET = "ALLSELECTED ( Flights[Route] )"
MEASURES = [
    # 1 Volume
    ("Flights", "COUNTROWS ( Flights )", INT, "1 Volume", "Number of flights."),
    ("Passengers", "SUM ( Flights[PaxCount] )", INT, "1 Volume", "Passengers carried."),
    ("Seats", "SUM ( Flights[Capacity] )", INT, "1 Volume", "Seats flown."),
    ("Revenue", "SUM ( Flights[Revenue] )", R0, "1 Volume", "Revenue as recorded."),
    ("ASK", "SUM ( Flights[ASK] )", INT, "1 Volume", "Available seat-km: seats x distance (corrected)."),
    ("RPK", "SUM ( Flights[RPK] )", INT, "1 Volume", "Revenue passenger-km: passengers x distance (corrected)."),
    ("Routes Served", "DISTINCTCOUNT ( Flights[Route] )", INT, "1 Volume", "Distinct origin-destination routes."),
    ("Airports Served", "DISTINCTCOUNT ( Flights[Origin] )", INT, "1 Volume", "Distinct departure airports."),
    # 2 Efficiency
    ("Load Factor %", "DIVIDE ( [Passengers], [Seats] )", PCT, "2 Efficiency", "Passengers / seats."),
    ("Seat-km Load Factor %", "DIVIDE ( [RPK], [ASK] )", PCT, "2 Efficiency", "RPK / ASK: load factor weighted by distance."),
    ("Avg Fare", "DIVIDE ( [Revenue], [Passengers] )", R0, "2 Efficiency", "Revenue per passenger."),
    ("Revenue per Flight", "DIVIDE ( [Revenue], [Flights] )", R0, "2 Efficiency", "Revenue per flight."),
    ("Avg Passengers per Flight", "DIVIDE ( [Passengers], [Flights] )", DEC1, "2 Efficiency", ""),
    ("Yield per RPK", "DIVIDE ( [Revenue], [RPK] )", R3, "2 Efficiency", "Revenue per revenue passenger-km."),
    ("RASK", "DIVIDE ( [Revenue], [ASK] )", R3, "2 Efficiency",
     "HEADLINE KPI. Revenue per available seat-km = Seat-km load factor x Yield per RPK."),
    ("Avg Stage Length Km", "DIVIDE ( [ASK], [Seats] )", INT, "2 Efficiency", "Average distance per seat flown."),
    # 3 Network
    ("Revenue Share %", "DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALLSELECTED () ) )", PCT, "3 Network",
     "Share of the revenue in the current selection (works for routes, airports and markets)."),
    ("Review Route Revenue", 'IF ( [Route Quadrant] = "Review route", [Revenue] )', R0, "3 Network",
     "Revenue of routes below the network on both load factor and RASK."),
    ("Route Revenue Rank", f"IF ( NOT ISBLANK ( [Revenue] ), RANKX ( {NET}, [Revenue], , DESC, DENSE ) )", "0", "3 Network", ""),
    ("Network Load Factor %", "CALCULATE ( [Load Factor %], REMOVEFILTERS ( Flights[Route] ) )", PCT, "3 Network", "Whole-network benchmark: ignores route filters, keeps market/year/date slicers."),
    ("Network RASK", "CALCULATE ( [RASK], REMOVEFILTERS ( Flights[Route] ) )", R3, "3 Network", "Whole-network benchmark: ignores route filters, keeps market/year/date slicers."),
    ("LF vs Network (pp)", "IF ( NOT ISBLANK ( [Flights] ), ( [Load Factor %] - [Network Load Factor %] ) * 100 )", PP, "3 Network", ""),
    ("Route Quadrant",
     "VAR lf = [Load Factor %] VAR r = [RASK] VAR nlf = [Network Load Factor %] VAR nr = [Network RASK] RETURN "
     "IF ( NOT ISBLANK ( [Flights] ), SWITCH ( TRUE (), lf >= nlf && r >= nr, \"Star\", lf < nlf && r >= nr, \"Fill seats\", "
     "lf >= nlf && r < nr, \"Raise yield\", \"Review route\" ) )", None, "3 Network",
     "Route position vs network: load factor and RASK above or below the network average."),
    ("Underperforming Routes",
     f"COUNTROWS ( FILTER ( {NET}, NOT ISBLANK ( [Flights] ) && [Load Factor %] < [Network Load Factor %] && [RASK] < [Network RASK] ) )", INT, "3 Network",
     "Routes below the network on both load factor and RASK."),
    ("Distance-Corrected Flights", "CALCULATE ( [Flights], Flights[Distance Corrected] = TRUE () )", INT, "3 Network",
     "Flights whose recorded distance was replaced by the great-circle distance."),
    ("Fare Outlier Flights", "CALCULATE ( [Flights], Flights[Fare Outlier] = TRUE () )", INT, "3 Network",
     "Flights with fare per passenger above 3x the route median."),
    # 4 Trends (like-for-like: Date table ends on the last flight date)
    ("Revenue PY", "CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", R0, "4 Trends", ""),
    ("Revenue YoY %", "DIVIDE ( [Revenue] - [Revenue PY], [Revenue PY] )", PCT, "4 Trends", ""),
    ("Passengers PY", "CALCULATE ( [Passengers], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", INT, "4 Trends", ""),
    ("Passengers YoY %", "DIVIDE ( [Passengers] - [Passengers PY], [Passengers PY] )", PCT, "4 Trends", ""),
    ("Flights PY", "CALCULATE ( [Flights], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", INT, "4 Trends", ""),
    ("Flights YoY %", "DIVIDE ( [Flights] - [Flights PY], [Flights PY] )", PCT, "4 Trends", ""),
    ("Load Factor PY", "CALCULATE ( [Load Factor %], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", PCT, "4 Trends", ""),
    ("Load Factor YoY (pp)", "IF ( NOT ISBLANK ( [Load Factor PY] ), ( [Load Factor %] - [Load Factor PY] ) * 100 )", PP, "4 Trends", ""),
    ("Avg Fare PY", "CALCULATE ( [Avg Fare], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", R0, "4 Trends", ""),
    ("Avg Fare YoY %", "DIVIDE ( [Avg Fare] - [Avg Fare PY], [Avg Fare PY] )", PCT, "4 Trends", ""),
    # 5 KPI
    ("RASK PY", "CALCULATE ( [RASK], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", R3, "5 KPI", "RASK for the same period last year."),
    ("RASK YoY %", "DIVIDE ( [RASK] - [RASK PY], [RASK PY] )", PCT, "5 KPI", ""),
    ("RASK Target Growth %", "0.05", PCT, "5 KPI", "Assumed growth target over last year. Edit to change the target."),
    ("RASK Target", "[RASK PY] * ( 1 + [RASK Target Growth %] )", R3, "5 KPI", "Last year's RASK plus the target growth."),
    ("RASK vs Target %", "DIVIDE ( [RASK] - [RASK Target], [RASK Target] )", PCT, "5 KPI", ""),
    ("RASK Status",
     "VAR v = [RASK] VAR t = [RASK Target] RETURN SWITCH ( TRUE (), ISBLANK ( t ), \"No target\", v >= t, \"On target\", "
     "v >= t * 0.95, \"Watch\", \"Below\" )", None, "5 KPI", "Traffic-light status of RASK vs target."),
    ("RASK Status Color",
     "VAR v = [RASK] VAR t = [RASK Target] RETURN SWITCH ( TRUE (), ISBLANK ( t ), \"#5B6B7F\", v >= t, \"#1E7F4B\", "
     "v >= t * 0.95, \"#B26B00\", \"#C0392B\" )", None, "5 KPI", ""),
    ("Seat-km Load Factor PY", "CALCULATE ( [Seat-km Load Factor %], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", PCT, "5 KPI", ""),
    ("Yield per RPK PY", "CALCULATE ( [Yield per RPK], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )", R3, "5 KPI", ""),
]
# ---- 7 Display: card text in ₹ Cr / M, change lines with arrows, index and unit measures (scorecard review, Nov 2026)
UP, DOWN = "▲ ", "▼ "
GOOD, BAD, NEUTRAL = "#1E7F4B", "#C0392B", "#5B6B7F"      # WCAG AA (≥4.5:1) on white for small text
CR = f"{RUPEE}#,##0.00 \\C\\r"
PERIOD = "Jan 2024 – May 2025"


def delta(name, cur, py, pp=False, label="vs last year"):
    """Text + colour measures for a card's change line, e.g. '▲ 24.6% vs last year'."""
    d = f"( {cur} - {py} ) * 100" if pp else f"DIVIDE ( {cur} - {py}, {py} )"
    fmt = f'FORMAT ( ABS ( d ), "0.0" ) & " pp"' if pp else 'FORMAT ( ABS ( d ), "0.0%" )'
    txt = (f"VAR p = {py} VAR d = {d} RETURN IF ( NOT HASONEVALUE ( 'Date'[Year] ), \"{PERIOD}\", "
           f"IF ( ISBLANK ( p ), \"No prior year\", IF ( d >= 0, \"{UP}\", \"{DOWN}\" ) & {fmt} & \" {label}\" ) )")
    col_ = (f"VAR p = {py} RETURN IF ( NOT HASONEVALUE ( 'Date'[Year] ) || ISBLANK ( p ), \"{NEUTRAL}\", "
            f"IF ( {cur} >= p, \"{GOOD}\", \"{BAD}\" ) )")
    return [(f"Δ {name}", txt, None, "7 Display", f"Card change line for {name}: arrow and change {label}."),
            (f"Δ {name} Color", col_, None, "7 Display", f"Colour of the {name} change line: green up, red down, grey when not comparable.")]


def card(name, expr, desc):
    return (f"Card {name}", expr, None, "7 Display", desc)


base24 = "CALCULATE ( {m}, REMOVEFILTERS ( 'Date' ), 'Date'[Year] = 2024 )"
MEASURES += [
    ("Revenue ₹ Cr", "DIVIDE ( [Revenue], 10000000 )", CR, "7 Display", "Revenue in crore, for charts and tables."),
    ("Review Route Revenue ₹ Cr", "DIVIDE ( [Review Route Revenue], 10000000 )", CR, "7 Display", "Review-route revenue in crore."),
    ("Δ LF vs Network", 'VAR d = [LF vs Network (pp)] RETURN IF ( ISBLANK ( d ), BLANK (), FORMAT ( d, "+0.0;-0.0;0.0" ) & " pp vs network" )', None, "7 Display",
     "Card line: load factor gap to the network, in points."),
    ("Passengers (K)", "DIVIDE ( [Passengers], 1000 )", "#,##0", "7 Display", "Passengers in thousands, for monthly charts."),
    card("Revenue", f'FORMAT ( DIVIDE ( [Revenue], 10000000 ), "{RUPEE}#,##0.00", "en-US" ) & " Cr"', "Revenue for cards, in crore."),
    card("Passengers", 'FORMAT ( DIVIDE ( [Passengers], 1000000 ), "0.00" ) & " M"', "Passengers for cards, in millions."),
    card("Flights", 'FORMAT ( [Flights], "#,##0", "en-US" )', "Flights for cards."),
    card("Load Factor", 'FORMAT ( [Load Factor %], "0.0%" )', "Load factor for cards."),
    card("Avg Fare", f'FORMAT ( [Avg Fare], "{RUPEE}#,##0", "en-US" )', "Average fare for cards."),
    card("RASK", f'FORMAT ( [RASK], "{RUPEE}0.000" )', "RASK for cards."),
    card("RASK Target", f'FORMAT ( [RASK Target], "{RUPEE}0.000" )', "RASK target for cards."),
    card("Yield", f'FORMAT ( [Yield per RPK], "{RUPEE}0.000" )', "Yield per RPK for cards."),
    card("Seat-km LF", 'FORMAT ( [Seat-km Load Factor %], "0.0%" )', "Seat-km load factor for cards."),
    *delta("Revenue", "[Revenue]", "[Revenue PY]"),
    *delta("Passengers", "[Passengers]", "[Passengers PY]"),
    *delta("Flights", "[Flights]", "[Flights PY]"),
    *delta("Load Factor", "[Load Factor %]", "[Load Factor PY]", pp=True),
    *delta("Avg Fare", "[Avg Fare]", "[Avg Fare PY]"),
    *delta("RASK", "[RASK]", "[RASK PY]"),
    *delta("Yield", "[Yield per RPK]", "[Yield per RPK PY]"),
    *delta("Seat-km LF", "[Seat-km Load Factor %]", "[Seat-km Load Factor PY]", pp=True),
    ("Δ RASK Target", "VAR v = [RASK] VAR t = [RASK Target] RETURN IF ( ISBLANK ( t ), \"No target\", "
     "FORMAT ( ABS ( DIVIDE ( v - t, t ) ), \"0.0%\" ) & IF ( v >= t, \" ahead of target\", \" behind target\" ) )",
     None, "7 Display", "Card change line: RASK distance from target."),
    ("Δ RASK Target Color", f'IF ( [RASK] >= [RASK Target], "{GOOD}", "{BAD}" )', None, "7 Display", "Colour of the target line."),
    ("RASK Index", f"DIVIDE ( [RASK], {base24.format(m='[RASK]')} ) * 100", "0", "5 KPI", "RASK indexed to the 2024 average (= 100)."),
    ("Yield Index", f"DIVIDE ( [Yield per RPK], {base24.format(m='[Yield per RPK]')} ) * 100", "0", "5 KPI", "Yield per RPK indexed to the 2024 average (= 100)."),
    ("Seat-km LF Index", f"DIVIDE ( [Seat-km Load Factor %], {base24.format(m='[Seat-km Load Factor %]')} ) * 100", "0", "5 KPI",
     "Seat-km load factor indexed to the 2024 average (= 100)."),
    ("Route Quadrant Color", f'SWITCH ( [Route Quadrant], "Star", "#1673C8", "Review route", "#E4572E", "#A7B4C4" )', None, "3 Network",
     "Scatter colour: blue star routes, red review routes, grey mixed."),
    ("Selected Route", 'SELECTEDVALUE ( Flights[Route], "All routes" )', None, "7 Display", "Route in the current filter context (drillthrough title)."),
    ("Footer Text", '"Source: Flight Data Assessment 2025 (" & "' + PERIOD + '" & ")  ·  Refreshed " & '
     'FORMAT ( MAX ( \'Refresh Info\'[Refreshed] ), "d mmm yyyy" ) & "  ·  Values look scaled: compare % changes"',
     None, "7 Display", "Footer: source, refresh date and the main caveat."),
]
FILL = {  # descriptions for measures that had none
    "Avg Passengers per Flight": "Passengers / flights.", "Route Revenue Rank": "Dense rank of a route by revenue within the selection.",
    "LF vs Network (pp)": "Load factor minus the network load factor, in percentage points.",
    "Revenue PY": "Revenue for the same period last year.", "Revenue YoY %": "Revenue change vs the same period last year.",
    "Passengers PY": "Passengers for the same period last year.", "Passengers YoY %": "Passenger change vs the same period last year.",
    "Flights PY": "Flights for the same period last year.", "Flights YoY %": "Flight change vs the same period last year.",
    "Load Factor PY": "Load factor for the same period last year.", "Load Factor YoY (pp)": "Load factor change vs last year, in points.",
    "Avg Fare PY": "Average fare for the same period last year.", "Avg Fare YoY %": "Average fare change vs the same period last year.",
    "RASK YoY %": "RASK change vs the same period last year.", "RASK vs Target %": "RASK distance from target, as a %.",
    "RASK Status Color": "Colour for the RASK status: green on target, amber within 5%, red below.",
    "Seat-km Load Factor PY": "Seat-km load factor for the same period last year.", "Yield per RPK PY": "Yield per RPK for the same period last year.",
}
MEASURES = [(n, e, f, folder, desc or FILL.get(n, "")) for n, e, f, folder, desc in MEASURES]
ms = f"/// Central home for report measures\ntable _Measures\n{T}{lt()}\n\n"
for n, e, f, folder, desc in MEASURES:
    if desc: ms += f"{T}/// {desc}\n"
    ms += f"{T}measure '{n}' = {e}\n"
    if f: ms += f"{T * 2}formatString: {f}\n"
    ms += f"{T * 2}displayFolder: {folder}\n{T * 2}{lt()}\n\n"
ms += (f"{T}column Hidden\n{T * 2}isHidden\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}isNameInferred\n{T * 2}sourceColumn: [Hidden]\n\n"
       f"{T}partition _Measures = calculated\n{T * 2}mode: import\n{T * 2}source = ROW ( \"Hidden\", BLANK () )\n")
w(DEFN / "tables" / "_Measures.tmdl", ms)

# ---------------------------------------------------------------- relationships
w(DEFN / "relationships.tmdl",
  "relationship Flights_Date\n\tfromColumn: Flights.'Departure Date'\n\ttoColumn: Date.Date\n\n"
  "relationship Flights_Origin\n\tfromColumn: Flights.Origin\n\ttoColumn: 'Origin Airport'.IATA\n\n"
  "relationship Flights_Destination\n\tfromColumn: Flights.Destination\n\ttoColumn: 'Destination Airport'.IATA\n")
print(f"model written: {len(MEASURES)} measures, tables {TABLES}")

# ---------------------------------------------------------------- forecast + levers (from analysis notebooks 03 and 04)
BS = chr(92)


RENAME = {"scenario": "Scenario", "month": "Month", "metric": "Metric", "kind": "Kind", "actual": "Actual", "p10": "P10", "p50": "P50",
          "p90": "P90", "lever": "Lever", "uplift": "Uplift", "basis": "Basis", "confidence": "Confidence",
          "uplift_pct_of_revenue": "Uplift % of Revenue"}


def csv_table(name, file, cols, blanks=()):
    mt = {"string": "type text", "dateTime": "type date", "double": "Currency.Type"}   # fixed decimal, not floating point
    types = ", ".join('{"%s", %s}' % (c, mt[d]) for c, d, _ in cols)
    blank = ('    Blanks = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {%s}),\n' % ", ".join('"%s"' % b for b in blanks)
             if blanks else "    Blanks = Promoted,\n")
    m = ("let\n"
         f'    Source = Csv.Document(File.Contents(ProjectFolder & "{BS}analysis{BS}output{BS}{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
         "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n" + blank +
         f'    Typed = Table.TransformColumnTypes(Blanks, {{{types}}}, "en-US"),\n'
         '    Renamed = Table.RenameColumns(Typed, {%s})\nin\n    Renamed' % ", ".join('{"%s", "%s"}' % (c, RENAME[c]) for c, _, _ in cols))
    s = f"/// From analysis/output/{file}. Re-run the notebooks, then refresh.\ntable {q(name)}\n{T}{lt()}\n\n"
    s += "".join(column(RENAME[c], "decimal" if d == "double" else d, f_) for c, d, f_ in cols)
    s += f"{T}partition {q(name)} = m\n{T * 2}mode: import\n{T * 2}source =\n{ind(m, 4)}\n\n{T}annotation PBI_ResultType = Table\n"
    w(DEFN / "tables" / f"{name}.tmdl", s)


csv_table("Forecast", "pbi_forecast.csv",
          [("scenario", "string", None), ("month", "dateTime", "mmm yyyy"), ("metric", "string", None), ("kind", "string", None),
           ("actual", "double", "#,##0"), ("p10", "double", "#,##0"), ("p50", "double", "#,##0"), ("p90", "double", "#,##0")],
          blanks=("actual", "p10", "p50", "p90"))
csv_table("Forecast 2025", "pbi_forecast_2025.csv",
          [("scenario", "string", None), ("metric", "string", None), ("p10", "double", "#,##0"), ("p50", "double", "#,##0"), ("p90", "double", "#,##0")])
csv_table("Levers", "pbi_levers.csv",
          [("lever", "string", None), ("uplift", "double", "#,##0"), ("basis", "string", None), ("confidence", "string", None),
           ("uplift_pct_of_revenue", "double", "0.0%")])
w(DEFN / "tables" / "Scenario.tmdl",
  f"/// Shared scenario list so one slicer filters both forecast tables.\ntable Scenario\n{T}{lt()}\n\n"
  f"{T}column Scenario\n{T * 2}dataType: string\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n{T * 2}isNameInferred\n{T * 2}sourceColumn: [Scenario]\n\n"
  f"{T}partition Scenario = calculated\n{T * 2}mode: import\n{T * 2}source = DISTINCT ( SELECTCOLUMNS ( 'Forecast 2025', \"Scenario\", 'Forecast 2025'[Scenario] ) )\n")
SC = 'VAR sc = SELECTEDVALUE ( Scenario[Scenario], "A · Fares hold (post-Nov 2024 level)" )'
MT = 'VAR mt = SELECTEDVALUE ( Forecast[Metric], "Revenue" )'
_f = lambda c: f"CALCULATE ( SUM ( Forecast[{c.capitalize()}] ), TREATAS ( {{ sc }}, Scenario[Scenario] ), TREATAS ( {{ mt }}, Forecast[Metric] ) )"
UNIT = 'IF ( mt = "Revenue", 10000000, 1000 )'   # chart in ₹ Cr, or thousands of passengers


def fc(c):
    """Forecast series in chart units. P10/P50/P90 also take the last actual month, so the forecast joins the history line."""
    if c == "actual":
        return f"{SC} {MT} RETURN DIVIDE ( {_f('actual')}, {UNIT} )"
    last = (f"CALCULATE ( MAX ( Forecast[Month] ), REMOVEFILTERS ( Forecast[Month], Forecast[Month Label] ), "
            f"NOT ISBLANK ( Forecast[Actual] ), TREATAS ( {{ sc }}, Scenario[Scenario] ), TREATAS ( {{ mt }}, Forecast[Metric] ) )")
    return (f"{SC} {MT} VAR v = {_f(c)} VAR lastA = {last} "
            f"RETURN DIVIDE ( IF ( ISBLANK ( v ) && MAX ( Forecast[Month] ) = lastA, {_f('actual')}, v ), {UNIT} )")
f25 = lambda metric, c="p50": f"{SC} RETURN CALCULATE ( SUM ( 'Forecast 2025'[{c.capitalize()}] ), 'Forecast 2025'[Metric] = \"{metric}\", TREATAS ( {{ sc }}, Scenario[Scenario] ) )"
FC_MEASURES = [
    ("Fcst Actual", fc("actual"), DEC1, "6 Forecast", "History rows of the forecast table (defaults: scenario A, Revenue)."),
    ("Fcst P50", fc("p50"), DEC1, "6 Forecast", "Forecast median."),
    ("Fcst P10", fc("p10"), DEC1, "6 Forecast", "Low case."),
    ("Fcst P90", fc("p90"), DEC1, "6 Forecast", "High case."),
    ("F25 Revenue", f25("Revenue 2025 full year"), R0, "6 Forecast", "Full-year 2025 revenue: actual Jan-May + forecast median Jun-Dec."),
    ("F25 Revenue (Cr)", f'"{RUPEE}" & FORMAT ( DIVIDE ( [F25 Revenue], 10000000 ), "0.0" ) & " Cr"', None, "6 Forecast", "Full-year 2025 revenue forecast as text, in crore."),
    ("F25 Revenue Range",
     f'{SC} VAR lo = CALCULATE ( SUM ( \'Forecast 2025\'[P10] ), \'Forecast 2025\'[Metric] = "Revenue 2025 full year", TREATAS ( {{ sc }}, Scenario[Scenario] ) ) '
     f'VAR hi = CALCULATE ( SUM ( \'Forecast 2025\'[P90] ), \'Forecast 2025\'[Metric] = "Revenue 2025 full year", TREATAS ( {{ sc }}, Scenario[Scenario] ) ) '
     f'RETURN "{RUPEE}" & FORMAT ( DIVIDE ( lo, 10000000 ), "0.0" ) & "–" & FORMAT ( DIVIDE ( hi, 10000000 ), "0.0" ) & " Cr"', None, "6 Forecast", "80% range of 2025 revenue."),
    ("F25 Revenue vs 2024 %", 'VAR b = CALCULATE ( [Revenue], \'Date\'[Year] = 2024 ) RETURN DIVIDE ( [F25 Revenue] - b, b )', PCT, "6 Forecast", "2025 revenue forecast vs 2024 actual."),
    ("F25 Passengers", f25("Passengers 2025 full year"), INT, "6 Forecast", "Full-year 2025 passengers (median)."),
    ("F25 Passengers vs 2024 %", 'VAR b = CALCULATE ( [Passengers], \'Date\'[Year] = 2024 ) RETURN DIVIDE ( [F25 Passengers] - b, b )', PCT, "6 Forecast", "2025 passenger forecast vs 2024 actual."),
    ("Lever Uplift", "SUM ( Levers[Uplift] )", R0, "6 Forecast", "Annual revenue uplift, sized on Jun 2024-May 2025."),
    ("Lever Uplift %", "SUM ( Levers[Uplift % of Revenue] )", PCT, "6 Forecast", "Lever uplift as a share of annual revenue."),
    ("Lever Uplift (Cr)", f'"{RUPEE}" & FORMAT ( DIVIDE ( [Lever Uplift], 10000000 ), "0.00" ) & " Cr"', None, "6 Forecast", "Total lever uplift per year, in crore."),
    ("F25 Passengers (M)", 'FORMAT ( DIVIDE ( [F25 Passengers], 1000000 ), "0.00" ) & " M"', None, "6 Forecast", "Full-year 2025 passengers, in millions."),
    ("Lever Uplift ₹ Cr", "DIVIDE ( [Lever Uplift], 10000000 )", CR, "6 Forecast", "Annual lever uplift in crore, for the lever chart."),
    ("Δ F25 Revenue", f'"{UP}" & FORMAT ( [F25 Revenue vs 2024 %], "0.0%" ) & " vs 2024 (" & FORMAT ( DIVIDE ( CALCULATE ( [Revenue], REMOVEFILTERS ( \'Date\' ), \'Date\'[Year] = 2024 ), 10000000 ), "{RUPEE}0.0" ) & " Cr)"',
     None, "7 Display", "Card change line: 2025 forecast vs 2024 actual revenue."),
    ("Δ F25 Passengers", f'"{UP}" & FORMAT ( [F25 Passengers vs 2024 %], "0.0%" ) & " vs 2024"', None, "7 Display",
     "Card change line: 2025 forecast vs 2024 passengers."),
    ("Δ Lever Share", '"≈ " & FORMAT ( DIVIDE ( [Lever Uplift], [F25 Revenue] ), "0.0%" ) & " of 2025 revenue"', None, "7 Display",
     "Card line: lever uplift as a share of forecast 2025 revenue."),
    ("Card Backtest", f'"{FACTS.get("bt_err", "-0.5%")}"', None, "7 Display",
     "Passenger model error on the held-out Mar–May 2025 (from notebook 03)."),
    ("Δ Backtest", f'"Naive forecast: {FACTS.get("bt_naive", "-4.9%")}"', None, "7 Display", "Card line: the naive benchmark's error."),
    ("Δ Neutral Color", f'"{NEUTRAL}"', None, "7 Display", "Grey for card lines that carry context, not a change."),
    ("Δ Good Color", f'"{GOOD}"', None, "7 Display", "Green for card lines that are good news."),
    ("Δ Range", '"80% of simulated outcomes"', None, "7 Display", "Card line for the forecast range."),
]
ms = (DEFN / "tables" / "_Measures.tmdl").read_text(encoding="utf-8")
add = ""
for n, e, f_, folder, desc in FC_MEASURES:
    if desc: add += f"{T}/// {desc}\n"
    add += f"{T}measure '{n}' = {e}\n" + (f"{T * 2}formatString: {f_}\n" if f_ else "") + f"{T * 2}displayFolder: {folder}\n{T * 2}{lt()}\n\n"
w(DEFN / "tables" / "_Measures.tmdl", ms.replace(f"{T}column Hidden\n", add + f"{T}column Hidden\n"))


def add_calc_column(table, name, expr, dtype="string", sort_by=None):
    """Insert a DAX calculated column before the table's partition."""
    p = DEFN / "tables" / f"{table}.tmdl"
    s = p.read_text(encoding="utf-8")
    c = f"{T}column {q(name)} = {expr}\n{T * 2}dataType: {dtype}\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n"
    if sort_by: c += f"{T * 2}sortByColumn: {q(sort_by)}\n"
    c += f"\n{T * 2}annotation SummarizationSetBy = Automatic\n\n"
    w(p, s.replace(f"{T}partition ", c + f"{T}partition ", 1))


add_calc_column("Forecast", "Month Label", 'FORMAT ( Forecast[Month], "MMM yy" )', sort_by="Month")
add_calc_column("Levers", "Lever Label", 'Levers[Lever] & " (" & LOWER ( Levers[Confidence] ) & ")"')
w(DEFN / "tables" / "Refresh Info.tmdl",
  f"/// When the model was last refreshed (calculated at refresh time), for the report footer.\ntable 'Refresh Info'\n{T}isHidden\n{T}{lt()}\n\n"
  f"{T}column Refreshed\n{T * 2}dataType: dateTime\n{T * 2}formatString: dd-mmm-yyyy\n{T * 2}isHidden\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n"
  f"{T * 2}isNameInferred\n{T * 2}sourceColumn: [Refreshed]\n\n"
  f"{T}partition 'Refresh Info' = calculated\n{T * 2}mode: import\n{T * 2}source = ROW ( \"Refreshed\", NOW () )\n")
rel = (DEFN / "relationships.tmdl").read_text(encoding="utf-8")
w(DEFN / "relationships.tmdl", rel + "\nrelationship Forecast_Scenario\n\tfromColumn: Forecast.Scenario\n\ttoColumn: Scenario.Scenario\n"
  "\nrelationship Forecast2025_Scenario\n\tfromColumn: 'Forecast 2025'.Scenario\n\ttoColumn: Scenario.Scenario\n")
print(f"forecast tables + {len(FC_MEASURES)} measures added")

# ---------------------------------------------------------------- 8 Titles: action titles that follow the slicers
ROUTES_ALL = "CALCULATETABLE ( VALUES ( Flights[Route] ), REMOVEFILTERS ( Flights[Route] ) )"
Y25 = "'Date'[Year] = 2025"
pct = lambda x: f'FORMAT ( {x}, "0%" )'
TITLE_MEASURES = [
    ("Title Network",
     "VAR city = MAXX ( TOPN ( 1, VALUES ( 'Origin Airport'[City] ), [Revenue], DESC ), 'Origin Airport'[City] ) "
     "VAR share = DIVIDE ( CALCULATE ( [Revenue], 'Origin Airport'[City] = city ), [Revenue] ) "
     f"RETURN city & \" is the hub (\" & {pct('share')} & \" of revenue); \" & [Underperforming Routes] & \" routes trail the network\"",
     "Page 1 headline: busiest departure city, its revenue share and the routes below the network."),
    ("Title Top Routes",
     f"VAR r = {ROUTES_ALL} VAR t8 = TOPN ( 8, r, [Revenue], DESC ) "
     "VAR s = DIVIDE ( CALCULATE ( [Revenue], t8 ), CALCULATE ( [Revenue], REMOVEFILTERS ( Flights[Route] ) ) ) "
     "VAR hub = MAXX ( TOPN ( 1, CALCULATETABLE ( VALUES ( Flights[Origin] ), REMOVEFILTERS ( Flights[Route] ) ), [Revenue], DESC ), Flights[Origin] ) "
     "VAR n = COUNTROWS ( FILTER ( t8, CONTAINSSTRING ( Flights[Route], hub ) ) ) "
     "VAR city = LOOKUPVALUE ( 'Origin Airport'[City], 'Origin Airport'[IATA], hub ) "
     f"RETURN \"Top 8 routes earn \" & {pct('s')} & \" of revenue; \" & n & \" of them touch \" & city",
     "Top-routes chart title: revenue share of the top 8 routes and how many touch the hub."),
    ("Title Route Map",
     f"VAR r = {ROUTES_ALL} VAR star = FILTER ( r, [Route Quadrant] = \"Star\" ) VAR rev = FILTER ( r, [Route Quadrant] = \"Review route\" ) "
     "VAR tot = CALCULATE ( [Revenue], REMOVEFILTERS ( Flights[Route] ) ) "
     f"RETURN COUNTROWS ( star ) & \" star routes (blue) earn \" & {pct('DIVIDE ( CALCULATE ( [Revenue], star ), tot )')} & \" of revenue; \" & "
     f"COUNTROWS ( rev ) & \" review routes (red) earn \" & {pct('DIVIDE ( CALCULATE ( [Revenue], rev ), tot )')}",
     "Route-map title: star and review route counts and their revenue shares."),
    ("Title Regions",
     "VAR regs = CALCULATETABLE ( VALUES ( 'Origin Airport'[Region] ), REMOVEFILTERS ( 'Origin Airport'[Region] ) ) "
     "VAR reg = MAXX ( TOPN ( 1, regs, [Revenue], DESC ), 'Origin Airport'[Region] ) "
     "VAR share = DIVIDE ( CALCULATE ( [Revenue], 'Origin Airport'[Region] = reg ), CALCULATE ( [Revenue], REMOVEFILTERS ( 'Origin Airport'[Region] ) ) ) "
     "VAR city = MAXX ( TOPN ( 1, CALCULATETABLE ( VALUES ( 'Origin Airport'[City] ), 'Origin Airport'[Region] = reg ), [Revenue], DESC ), 'Origin Airport'[City] ) "
     f"RETURN reg & \" departures earn \" & {pct('share')} & \" of revenue, led by \" & city",
     "Region chart title: top departure region, its share and its top city."),
    ("Title Demand",
     f"VAR r = CALCULATE ( [Revenue YoY %], {Y25} ) VAR p = CALCULATE ( [Passengers YoY %], {Y25} ) "
     "RETURN IF ( r > p, \"Growth is price-led: \", \"Growth is volume-led: \" ) & \"revenue \" & FORMAT ( r, \"+0%;-0%\" ) & "
     "\" on passengers \" & FORMAT ( p, \"+0%;-0%\" ) & \" (Jan–May 2025 vs 2024)\"",
     "Page 2 headline: revenue vs passenger growth, Jan–May 2025 vs 2024."),
    ("Title Pax Months",
     'VAR m = FILTER ( CALCULATETABLE ( VALUES ( \'Date\'[Year Month Key] ), \'Date\'[Year] = 2025 ), NOT ISBLANK ( [Passengers PY] ) ) VAR n = COUNTROWS ( FILTER ( m, [Passengers] > [Passengers PY] ) ) VAR k = COUNTROWS ( m ) RETURN SWITCH ( TRUE (), k = 0, "Passengers per month: no 2024 flights to compare with", n = k && k = COUNTROWS ( CALCULATETABLE ( VALUES ( \'Date\'[Year Month Key] ), \'Date\'[Year] = 2025 ) ), "Passengers grew steadily: every 2025 month beat the same month of 2024", n = k, "Passengers beat 2024 in all " & k & " comparable months of 2025", "Passengers beat 2024 in " & n & " of " & k & " comparable months of 2025" )',
     "Monthly passenger chart title: months of 2025 that beat the same month of 2024."),
    ("Title Fare Step",
     'VAR b = CALCULATE ( [Avg Fare], DATESBETWEEN ( \'Date\'[Date], DATE ( 2024, 1, 1 ), DATE ( 2024, 10, 31 ) ) ) VAR a = CALCULATE ( [Avg Fare], DATESBETWEEN ( \'Date\'[Date], DATE ( 2024, 11, 1 ), DATE ( 2025, 5, 31 ) ) ) VAR d = DIVIDE ( a - b, b ) VAR lo = MINX ( CALCULATETABLE ( VALUES ( \'Date\'[Year Month Key] ), DATESBETWEEN ( \'Date\'[Date], DATE ( 2024, 11, 1 ), DATE ( 2025, 5, 31 ) ) ), [Avg Fare] ) RETURN SWITCH ( TRUE (), ISBLANK ( d ), "Average fare by month", d >= 0.05, "Fares stepped up " & FORMAT ( d, "0%" ) & " from Nov 2024" & IF ( lo > b, " and stayed up", "" ), d <= -0.05, "Fares are " & FORMAT ( -d, "0%" ) & " lower since Nov 2024 than in Jan–Oct 2024", "Fares held level after Nov 2024 (" & FORMAT ( d, "+0%;-0%" ) & " vs Jan–Oct 2024)" )',
     "Fare chart title: average fare Nov 2024–May 2025 vs Jan–Oct 2024."),
    ("Title LF Months",
     'VAR m = FILTER ( CALCULATETABLE ( VALUES ( \'Date\'[Year Month Key] ), \'Date\'[Year] = 2025 ), NOT ISBLANK ( [Load Factor PY] ) ) VAR n = COUNTROWS ( FILTER ( m, [Load Factor %] > [Load Factor PY] ) ) VAR k = COUNTROWS ( m ) RETURN SWITCH ( TRUE (), k = 0, "Load factor by month: no 2024 flights to compare with", n = k && k = COUNTROWS ( CALCULATETABLE ( VALUES ( \'Date\'[Year Month Key] ), \'Date\'[Year] = 2025 ) ), "Load factor beat 2024 in every month of 2025", n = k, "Load factor beat 2024 in all " & k & " comparable months of 2025", "Load factor beat 2024 in " & n & " of " & k & " comparable months of 2025" )',
     "Load-factor chart title: months of 2025 above the same month of 2024."),
    ("Title Weekday",
     "VAR t = VALUES ( 'Date'[Weekday] ) VAR mn = MINX ( t, [Avg Passengers per Flight] ) VAR mx = MAXX ( t, [Avg Passengers per Flight] ) "
     "RETURN IF ( DIVIDE ( mx - mn, mn ) < 0.05, \"No weekday peak: \" & FORMAT ( mn, \"0\" ) & \"–\" & FORMAT ( mx, \"0\" ) & \" passengers per flight every day\", "
     f"\"The busiest weekday carries \" & {pct('DIVIDE ( mx - mn, mn )')} & \" more passengers per flight than the quietest\" )",
     "Weekday chart title: spread of passengers per flight across weekdays."),
    ("Title RASK",
     f"VAR v = CALCULATE ( [RASK], {Y25} ) VAR y = CALCULATE ( [RASK YoY %], {Y25} ) VAR t = CALCULATE ( [RASK Target], {Y25} ) "
     f"RETURN \"RASK is \" & FORMAT ( v, \"{RUPEE}0.000\" ) & \" in 2025, \" & IF ( y >= 0, \"up \", \"down \" ) & {pct('ABS ( y )')} & "
     f"\" and \" & IF ( v >= t, \"ahead of\", \"behind\" ) & \" its \" & FORMAT ( t, \"{RUPEE}0.000\" ) & \" target\"",
     "Page 3 headline: 2025 RASK, change vs last year and position vs target."),
    ("Title RASK Market",
     f"VAR d = CALCULATE ( [RASK], {Y25}, Flights[Market] = \"Domestic\" ) VAR i = CALCULATE ( [RASK], {Y25}, Flights[Market] = \"International\" ) "
     "VAR d0 = CALCULATE ( [RASK], 'Date'[Year] = 2024, Flights[Market] = \"Domestic\" ) VAR i0 = CALCULATE ( [RASK], 'Date'[Year] = 2024, Flights[Market] = \"International\" ) "
     f"VAR one = SELECTEDVALUE ( Flights[Market] ) VAR v = CALCULATE ( [RASK], {Y25} ) VAR v0 = CALCULATE ( [RASK], 'Date'[Year] = 2024 ) "
     f"RETURN IF ( NOT ISBLANK ( one ), one & \" RASK \" & FORMAT ( v, \"{RUPEE}0.000\" ) & \" in 2025 vs \" & FORMAT ( v0, \"{RUPEE}0.000\" ) & \" in 2024\", "
     f"\"Domestic RASK \" & FORMAT ( d, \"{RUPEE}0.000\" ) & \" vs international \" & FORMAT ( i, \"{RUPEE}0.000\" ) & \" in 2025\" & "
     "IF ( d > d0 && i > i0, \"; both up on 2024\", \"\" ) )",
     "RASK-by-market chart title: 2025 RASK by market and whether both improved on 2024."),
    ("Title Market Gap",
     "VAR d = CALCULATE ( [RASK], Flights[Market] = \"Domestic\" ) VAR i = CALCULATE ( [RASK], Flights[Market] = \"International\" ) "
     "VAR one = SELECTEDVALUE ( Flights[Market] ) "
     f"RETURN IF ( NOT ISBLANK ( one ), one & \" earns \" & FORMAT ( [RASK], \"{RUPEE}0.000\" ) & \" per seat-km on \" & FORMAT ( [Avg Stage Length Km], \"#,##0\", \"en-US\" ) & \" km stages\", "
     f"\"International earns \" & FORMAT ( i, \"{RUPEE}0.000\" ) & \" per seat-km vs \" & FORMAT ( d, \"{RUPEE}0.000\" ) & \" domestic\" )",
     "Market table title: RASK gap between international and domestic."),
    ("Title Forecast", '"2025 revenue heads for " & [F25 Revenue (Cr)] & "; levers add " & [Lever Uplift (Cr)] & " a year"',
     "Page 5 headline: 2025 revenue for the selected fare scenario and the lever total."),
    ("Title Route Detail",
     "VAR q = [Route Quadrant] RETURN \"Route detail: \" & [Selected Route] & IF ( HASONEVALUE ( Flights[Route] ), \", \" & "
     "SWITCH ( q, \"Star\", \"a star route\", \"Review route\", \"a route to review\", \"Fill seats\", \"a route to fill\", \"Raise yield\", \"a route to re-price\", \"\" ), \"\" )",
     "Drill-through headline: the route and its position against the network."),
]
ms = (DEFN / "tables" / "_Measures.tmdl").read_text(encoding="utf-8")
add = "".join(f"{T}/// {d}\n{T}measure '{n}' = {e}\n{T * 2}displayFolder: 8 Titles\n{T * 2}{lt()}\n\n" for n, e, d in TITLE_MEASURES)
w(DEFN / "tables" / "_Measures.tmdl", ms.replace(f"{T}column Hidden\n", add + f"{T}column Hidden\n"))
print(f"{len(TITLE_MEASURES)} title measures added")


# ---------------------------------------------------------------- BPA hardening (rules in D:\Wolf\PBI\_knowledge\bpa_check.py)
TABLE_DESC = {
    "Date": "Calendar from 1 Jan 2024 to the last flight date (31 May 2025); marked date table.",
    "Origin Airport": "Departure airport dimension (role-playing copy of reference/airports.csv).",
    "Destination Airport": "Arrival airport dimension (role-playing copy of reference/airports.csv).",
}
COL_DESC = {
    ("Flights", "FlightID"): "Unique flight identifier from the source.",
    ("Flights", "FlightNumber"): "Commercial flight number.",
    ("Flights", "Capacity"): "Seats available on the flight.",
    ("Flights", "PaxCount"): "Passengers carried.",
    ("Flights", "Revenue"): "Revenue recorded for the flight (looks scaled; compare % changes).",
    ("Flights", "Distance Corrected"): "TRUE when the recorded distance was replaced by the great-circle distance.",
    ("Flights", "Distance Km"): "Flight distance used for ASK/RPK (recorded, or great-circle when corrected).",
    ("Flights", "Route"): "Origin-destination pair, e.g. PNQ-BLR.",
    ("Flights", "Market"): "Domestic, or International when either airport is outside India.",
    ("Flights", "Fare Outlier"): "TRUE when fare per passenger is above 3x the route median.",
    ("Date", "Date"): "Calendar date (key).", ("Date", "Year"): "Calendar year.", ("Date", "Quarter"): "Calendar quarter, Q1-Q4.",
    ("Date", "Month No"): "Month number, 1-12 (sorts Month).", ("Date", "Month"): "Month name, e.g. Jan.",
    ("Date", "Month Start"): "First day of the month.", ("Date", "Year Month"): "Month label, e.g. Jan 24.",
    ("Date", "Year Month Key"): "yyyymm number (sorts Year Month).", ("Date", "Weekday No"): "Weekday number, Monday = 1.",
    ("Date", "Weekday"): "Weekday name, e.g. Mon.",
    ("Forecast", "Kind"): "Actual or Forecast row.", ("Forecast", "Metric"): "Revenue or Passengers.",
    ("Forecast", "Month"): "Month of the history or forecast value.", ("Forecast", "Actual"): "Actual monthly value (history rows).",
    ("Forecast", "P10"): "Forecast low case (10th percentile).", ("Forecast", "P50"): "Forecast median.",
    ("Forecast", "P90"): "Forecast high case (90th percentile).", ("Forecast", "Month Label"): "Month label for the forecast axis, e.g. Jun 25.",
    ("Forecast 2025", "Metric"): "Full-year or Jun-Dec total being forecast.", ("Forecast 2025", "P10"): "Low case (10th percentile).",
    ("Forecast 2025", "P50"): "Median.", ("Forecast 2025", "P90"): "High case (90th percentile).",
    ("Levers", "Lever"): "Revenue lever.", ("Levers", "Uplift"): "Annual revenue uplift in rupees.",
    ("Levers", "Basis"): "How the lever was sized.", ("Levers", "Confidence"): "Confidence in the sizing.",
    ("Levers", "Uplift % of Revenue"): "Uplift as a share of annual revenue.", ("Levers", "Lever Label"): "Lever name with its confidence, for charts.",
    ("Scenario", "Scenario"): "Fare scenario (A: fares hold, B: fares settle).",
}
for side in ("Origin", "Destination"):
    COL_DESC.update({(f"{side} Airport", "IATA"): "Three-letter airport code (key).", (f"{side} Airport", "Airport"): "Airport name.",
                     (f"{side} Airport", "City"): "City served.", (f"{side} Airport", "State"): "State or province.",
                     (f"{side} Airport", "Country"): "Country.", (f"{side} Airport", "Region"): "Region of India, or International.",
                     (f"{side} Airport", "Airport Label"): "Code and city, e.g. PNQ · Pune."})
HIDE = {("Flights", "Origin"), ("Flights", "Destination"), ("Flights", "Departure Date"), ("Forecast", "Scenario"), ("Forecast 2025", "Scenario")}
KEYS = {("Origin Airport", "IATA"), ("Destination Airport", "IATA"), ("Scenario", "Scenario")}
CATEGORY = {"City": "City", "State": "StateOrProvince", "Country": "Country"}
NOT_MDX = {("Flights", "ASK"), ("Flights", "RPK"), ("_Measures", "Hidden"), ("Refresh Info", "Refreshed")}
IGNORE = {"_Measures": ["ENSURE_TABLES_HAVE_RELATIONSHIPS", "REMOVE_UNNECESSARY_COLUMNS"],     # measure-only table, placeholder column
          "Levers": ["ENSURE_TABLES_HAVE_RELATIONSHIPS"],                                    # disconnected lever list by design
          "Refresh Info": ["ENSURE_TABLES_HAVE_RELATIONSHIPS"]}                              # one-row refresh timestamp


def harden(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    tname, out = None, []
    for ln in lines:
        mt_ = re.match(r"^table (?:'(.+)'|(\S+))", ln)
        if mt_:
            tname = mt_.group(1) or mt_.group(2)
            if tname in TABLE_DESC and not (out and out[-1].startswith("///")):
                out.append(f"/// {TABLE_DESC[tname]}")
            out.append(ln)
            continue
        mc = re.match(r"^\tcolumn (?:'(.+?)'|(\S+))", ln)
        if mc:
            cname = mc.group(1) or mc.group(2)
            key = (tname, cname)
            if key in COL_DESC and not (out and out[-1].startswith("\t///")):
                out.append(f"\t/// {COL_DESC[key]}")
            out.append(ln)
            extra = []
            if key in HIDE: extra.append("isHidden")
            if key in KEYS: extra.append("isKey")
            if cname in CATEGORY and tname.endswith("Airport"): extra.append(f"dataCategory: {CATEGORY[cname]}")
            if key in HIDE or key in NOT_MDX: extra.append("isAvailableInMdx: false")
            out += [f"{T * 2}{x}" for x in extra]
            continue
        if re.match(r"^\t\tisHidden$", ln) and out and any(out[-k] == f"{T * 2}isHidden" for k in range(1, 4) if len(out) >= k):
            continue   # avoid a duplicate isHidden
        out.append(ln)
    s = "\n".join(out)
    if tname in IGNORE:
        s = s.rstrip("\n") + "\n\n\tannotation BestPracticeAnalyzer_IgnoreRules = " + json.dumps({"RuleIDs": IGNORE[tname]}) + "\n"
    w(path, s)


for f in (DEFN / "tables").glob("*.tmdl"):
    harden(f)
print("BPA hardening applied")
