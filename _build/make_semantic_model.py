"""Writes the AirlineDataAnalysis-PBI PBIP skeleton and semantic model (TMDL).
Run with Power BI Desktop CLOSED on this project:  python _build/make_semantic_model.py
Rules mirror analysis/src/metrics.py exactly."""
import json
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
    Cleaned = Table.RemoveColumns(Outlier, {"DepartureDate", "o_lat", "o_lon", "o_country", "d_lat", "d_lon", "d_country"})
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
         ("FlightNumber", "int64", "0", False), ("Distance", "int64", "#,##0", True), ("DomesticFlag", "int64", "0", True),
         ("Capacity", "int64", "#,##0", False), ("PaxCount", "int64", "#,##0", False), ("Revenue", "int64", "#,##0", False),
         ("Departure Date", "dateTime", "dd-mmm-yyyy", False), ("Great Circle Km", "double", "#,##0", True),
         ("Distance Corrected", "boolean", None, False), ("Distance Km", "int64", "#,##0", False), ("Route", "string", None, False),
         ("Market", "string", None, False), ("ASK", "int64", "#,##0", True), ("RPK", "int64", "#,##0", True),
         ("Fare", "double", "#,##0.00", True), ("Route Median Fare", "double", "#,##0.00", True), ("Fare Outlier", "boolean", None, False)]
fl = "/// One row per flight (Raw Data CSV). Distance and fare-outlier rules: see analysis/src/metrics.py.\ntable Flights\n" + f"{T}{lt()}\n\n"
fl += "".join(column(n, d, f, h) for n, d, f, h in fcols)
fl += f"{T}partition Flights = m\n{T * 2}mode: import\n{T * 2}source =\n{ind(flights_m, 4)}\n\n{T}annotation PBI_ResultType = Table\n"
w(DEFN / "tables" / "Flights.tmdl", fl)


# ---------------------------------------------------------------- airport dimensions (role-playing)
def airport_table(name):
    m = "let\n    Source = AirportsRef,\n    Label = Table.AddColumn(Source, \"Airport Label\", each [IATA] & \" \u00b7 \" & [City], type text)\nin\n    Label"
    cols = [("IATA", "string", None, False), ("Airport", "string", None, False), ("City", "string", None, False),
            ("State", "string", None, False), ("Country", "string", None, False), ("Region", "string", None, False),
            ("Latitude", "double", "0.0000", True), ("Longitude", "double", "0.0000", True), ("Airport Label", "string", None, False)]
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
     f"COUNTROWS ( FILTER ( {NET}, [Load Factor %] < [Network Load Factor %] && [RASK] < [Network RASK] ) )", INT, "3 Network",
     "Routes below the network on both load factor and RASK."),
    ("Distance-Corrected Flights", "CALCULATE ( [Flights], Flights[Distance Corrected] = TRUE () ) + 0", INT, "3 Network",
     "Flights whose recorded distance was replaced by the great-circle distance."),
    ("Fare Outlier Flights", "CALCULATE ( [Flights], Flights[Fare Outlier] = TRUE () ) + 0", INT, "3 Network",
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
    card("Revenue", f'FORMAT ( [Revenue] / 10000000, "{RUPEE}#,##0.00", "en-US" ) & " Cr"', "Revenue for cards, in crore."),
    card("Passengers", 'FORMAT ( [Passengers] / 1000000, "0.00" ) & " M"', "Passengers for cards, in millions."),
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


def csv_table(name, file, cols, blanks=()):
    mt = {"string": "type text", "dateTime": "type date", "double": "type number"}
    types = ", ".join('{"%s", %s}' % (c, mt[d]) for c, d, _ in cols)
    blank = ('    Blanks = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {%s}),\n' % ", ".join('"%s"' % b for b in blanks)
             if blanks else "    Blanks = Promoted,\n")
    m = ("let\n"
         f'    Source = Csv.Document(File.Contents(ProjectFolder & "{BS}analysis{BS}output{BS}{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
         "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n" + blank +
         f'    Typed = Table.TransformColumnTypes(Blanks, {{{types}}}, "en-US")\nin\n    Typed')
    s = f"/// From analysis/output/{file}. Re-run the notebooks, then refresh.\ntable {q(name)}\n{T}{lt()}\n\n"
    s += "".join(column(c, d, f_) for c, d, f_ in cols)
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
  f"{T}partition Scenario = calculated\n{T * 2}mode: import\n{T * 2}source = DISTINCT ( SELECTCOLUMNS ( 'Forecast 2025', \"Scenario\", 'Forecast 2025'[scenario] ) )\n")
SC = 'VAR sc = SELECTEDVALUE ( Scenario[Scenario], "A · Fares hold (post-Nov 2024 level)" )'
MT = 'VAR mt = SELECTEDVALUE ( Forecast[metric], "Revenue" )'
_f = lambda c: f"CALCULATE ( SUM ( Forecast[{c}] ), TREATAS ( {{ sc }}, Scenario[Scenario] ), TREATAS ( {{ mt }}, Forecast[metric] ) )"
UNIT = 'IF ( mt = "Revenue", 10000000, 1000 )'   # chart in ₹ Cr, or thousands of passengers


def fc(c):
    """Forecast series in chart units. P10/P50/P90 also take the last actual month, so the forecast joins the history line."""
    if c == "actual":
        return f"{SC} {MT} RETURN DIVIDE ( {_f('actual')}, {UNIT} )"
    last = (f"CALCULATE ( MAX ( Forecast[month] ), REMOVEFILTERS ( Forecast[month], Forecast[Month Label] ), "
            f"NOT ISBLANK ( Forecast[actual] ), TREATAS ( {{ sc }}, Scenario[Scenario] ), TREATAS ( {{ mt }}, Forecast[metric] ) )")
    return (f"{SC} {MT} VAR v = {_f(c)} VAR lastA = {last} "
            f"RETURN DIVIDE ( IF ( ISBLANK ( v ) && MAX ( Forecast[month] ) = lastA, {_f('actual')}, v ), {UNIT} )")
f25 = lambda metric, c="p50": f"{SC} RETURN CALCULATE ( SUM ( 'Forecast 2025'[{c}] ), 'Forecast 2025'[metric] = \"{metric}\", TREATAS ( {{ sc }}, Scenario[Scenario] ) )"
FC_MEASURES = [
    ("Fcst Actual", fc("actual"), DEC1, "6 Forecast", "History rows of the forecast table (defaults: scenario A, Revenue)."),
    ("Fcst P50", fc("p50"), DEC1, "6 Forecast", "Forecast median."),
    ("Fcst P10", fc("p10"), DEC1, "6 Forecast", "Low case."),
    ("Fcst P90", fc("p90"), DEC1, "6 Forecast", "High case."),
    ("F25 Revenue", f25("Revenue 2025 full year"), R0, "6 Forecast", "Full-year 2025 revenue: actual Jan-May + forecast median Jun-Dec."),
    ("F25 Revenue (Cr)", f'"{RUPEE}" & FORMAT ( [F25 Revenue] / 10000000, "0.0" ) & " Cr"', None, "6 Forecast", "Full-year 2025 revenue forecast as text, in crore."),
    ("F25 Revenue Range",
     f'{SC} VAR lo = CALCULATE ( SUM ( \'Forecast 2025\'[p10] ), \'Forecast 2025\'[metric] = "Revenue 2025 full year", TREATAS ( {{ sc }}, Scenario[Scenario] ) ) '
     f'VAR hi = CALCULATE ( SUM ( \'Forecast 2025\'[p90] ), \'Forecast 2025\'[metric] = "Revenue 2025 full year", TREATAS ( {{ sc }}, Scenario[Scenario] ) ) '
     f'RETURN "{RUPEE}" & FORMAT ( lo / 10000000, "0.0" ) & "–" & FORMAT ( hi / 10000000, "0.0" ) & " Cr"', None, "6 Forecast", "80% range of 2025 revenue."),
    ("F25 Revenue vs 2024 %", 'DIVIDE ( [F25 Revenue], CALCULATE ( [Revenue], \'Date\'[Year] = 2024 ) ) - 1', PCT, "6 Forecast", "2025 revenue forecast vs 2024 actual."),
    ("F25 Passengers", f25("Passengers 2025 full year"), INT, "6 Forecast", "Full-year 2025 passengers (median)."),
    ("F25 Passengers vs 2024 %", 'DIVIDE ( [F25 Passengers], CALCULATE ( [Passengers], \'Date\'[Year] = 2024 ) ) - 1', PCT, "6 Forecast", "2025 passenger forecast vs 2024 actual."),
    ("Lever Uplift", "SUM ( Levers[uplift] )", R0, "6 Forecast", "Annual revenue uplift, sized on Jun 2024-May 2025."),
    ("Lever Uplift %", "SUM ( Levers[uplift_pct_of_revenue] )", PCT, "6 Forecast", "Lever uplift as a share of annual revenue."),
    ("Lever Uplift (Cr)", f'"{RUPEE}" & FORMAT ( [Lever Uplift] / 10000000, "0.00" ) & " Cr"', None, "6 Forecast", "Total lever uplift per year, in crore."),
    ("F25 Passengers (M)", 'FORMAT ( [F25 Passengers] / 1000000, "0.00" ) & " M"', None, "6 Forecast", "Full-year 2025 passengers, in millions."),
    ("Lever Uplift ₹ Cr", "DIVIDE ( [Lever Uplift], 10000000 )", CR, "6 Forecast", "Annual lever uplift in crore, for the lever chart."),
    ("Δ F25 Revenue", f'"{UP}" & FORMAT ( [F25 Revenue vs 2024 %], "0.0%" ) & " vs 2024 (" & FORMAT ( CALCULATE ( [Revenue], REMOVEFILTERS ( \'Date\' ), \'Date\'[Year] = 2024 ) / 10000000, "{RUPEE}0.0" ) & " Cr)"',
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


add_calc_column("Forecast", "Month Label", 'FORMAT ( Forecast[month], "MMM yy" )', sort_by="month")
add_calc_column("Levers", "Lever Label", 'Levers[lever] & " (" & LOWER ( Levers[confidence] ) & ")"')
w(DEFN / "tables" / "Refresh Info.tmdl",
  f"/// When the model was last refreshed (calculated at refresh time), for the report footer.\ntable 'Refresh Info'\n{T}isHidden\n{T}{lt()}\n\n"
  f"{T}column Refreshed\n{T * 2}dataType: dateTime\n{T * 2}formatString: dd-mmm-yyyy\n{T * 2}isHidden\n{T * 2}{lt()}\n{T * 2}summarizeBy: none\n"
  f"{T * 2}isNameInferred\n{T * 2}sourceColumn: [Refreshed]\n\n"
  f"{T}partition 'Refresh Info' = calculated\n{T * 2}mode: import\n{T * 2}source = ROW ( \"Refreshed\", NOW () )\n")
rel = (DEFN / "relationships.tmdl").read_text(encoding="utf-8")
w(DEFN / "relationships.tmdl", rel + "\nrelationship Forecast_Scenario\n\tfromColumn: Forecast.scenario\n\ttoColumn: Scenario.Scenario\n"
  "\nrelationship Forecast2025_Scenario\n\tfromColumn: 'Forecast 2025'.scenario\n\ttoColumn: Scenario.Scenario\n")
print(f"forecast tables + {len(FC_MEASURES)} measures added")
