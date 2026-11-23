"""Builds the AirlineDataAnalysis-PBI report pages (PBIR JSON) in the Runway aviation theme (_build/airline_theme.py).
Run: python _build/build_report.py   (then "Apply external changes" in Power BI Desktop)

v2 (Nov 2026, after the dashboard scorecard review): action titles, ₹ Cr / M units everywhere, change lines (▲▼) on every
KPI card, no dual-axis charts (index chart instead), route tooltip + drillthrough pages, footer with source/refresh/caveat,
page navigator, alt text on every visual."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pbir_kit as k
import airline_theme
airline_theme.apply(k)   # 'Runway' aviation theme; must run before the names below are imported
from pbir_kit import (L, C, col, mea, qref, cat_filter, series_color_by_value, series_color_by_measure, Page, NO_CHROME,
                      NAVY, TEAL, AMBER, CORAL, SLATE, GREEN, INK, MUTED, WHITE, LINE, W, H, M, G)

ROOT = Path(__file__).resolve().parents[1]
k.init(ROOT / "AirlineDataAnalysis-PBI.Report")
OUT = ROOT / "analysis" / "output"
facts = json.loads((OUT / "report_facts.json").read_text(encoding="utf-8")) if (OUT / "report_facts.json").exists() else {}
fx = lambda key, default="…": facts.get(key, default).replace("Rs ", "₹")

RED, GREY = airline_theme.CORAL, "#A7B4C4"
ROUTE, MARKET, REGION = col("Flights", "Route"), col("Flights", "Market"), col("Origin Airport", "Region")
YEAR, YM, MONTH, WEEKDAY = col("Date", "Year"), col("Date", "Year Month"), col("Date", "Month"), col("Date", "Weekday")
NO_AXIS_TITLES = {"categoryAxis": [{"properties": {"showAxisTitle": L(False)}}],
                  "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True)}}]}
LABELS = {"labels": [{"properties": {"show": L(True), "fontSize": L(9)}}]}
LEGEND_TOP = {"legend": [{"properties": {"show": L(True), "position": L("Top")}}]}
NO_LEGEND = {"legend": [{"properties": {"show": L(False)}}]}
Y2025 = [cat_filter("year_2025", "Date", "Year", ["2025L"])]
YEAR_COLORS = [{"properties": {"fill": C(GREY)}, "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": YEAR,
                                                                                                   "Right": {"Literal": {"Value": "2024L"}}}}}]}},
               {"properties": {"fill": C(TEAL)}, "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": YEAR,
                                                                                                  "Right": {"Literal": {"Value": "2025L"}}}}}]}}]
COMPACT = {"values": [{"properties": {"fontSize": L(9)}}], "rowHeaders": [{"properties": {"fontSize": L(9)}}],
           "columnHeaders": [{"properties": {"fontSize": L(9)}}], "total": [{"properties": {"fontSize": L(9)}}]}
ALL_POINTS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}   # conditional formatting applies to every data point
FOOTER = mea("Footer Text")
TIP = "route_tip"

# vertical grid: header 0-72 | cards 80-176 | row 2 | row 3 | footer H-26
row2_y = 178
row3_end = H - 38
row2_h = 240
row3_y = row2_y + row2_h + G
row3_h = row3_end - row3_y
D = lambda m: mea(f"Δ {m}")
DC = lambda m: mea(f"Δ {m} Color")


def top_n_filter(name, t, c, measure, n, descending=True):
    """Visual-level Top N filter on column t[c] by a _Measures measure."""
    sub = {"Version": 2, "From": [{"Name": "f", "Entity": t, "Type": 0}, {"Name": "m", "Entity": "_Measures", "Type": 0}],
           "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": c}, "Name": "field"}],
           "OrderBy": [{"Direction": 2 if descending else 1,
                        "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}],
           "Top": n}
    return {"name": name, "field": col(t, c), "type": "TopN", "howCreated": "User",
            "filter": {"Version": 2,
                       "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": sub}}, "Type": 2},
                                {"Name": "f", "Entity": t, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": c}}],
                                                       "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}


def line_styles(*fields_widths):
    return [{"properties": {"strokeWidth": L(w_), "showMarker": L(mk)}, "selector": {"metadata": qref(f)}} for f, w_, mk in fields_widths]


pages = []
# =====================================================================
# PAGE 1 - Network and route performance  (brief Q1)
# =====================================================================
p = Page("network", "1 Network")
p1_h2 = 266
p1_r3 = row2_y + p1_h2 + G
p1_h3 = row3_end - p1_r3
p.header("Pune is the hub (31% of revenue); 48 routes trail the network",
         "40,175 flights  |  179 routes  |  38 airports  |  Jan 2024 to May 2025  |  Titles follow the Market and Year filters", title_measure=mea("Title Network"), title_w=812)
p.slicer("slc_market", MARKET, "Market", 900, 170)
p.slicer("slc_year", YEAR, "Year", 1086, 178)
p.cards([
    ("card_rev", mea("Card Revenue"), "Revenue", D("Revenue"), DC("Revenue")),
    ("card_flights", mea("Card Flights"), "Flights", D("Flights"), DC("Flights")),
    ("card_pax", mea("Card Passengers"), "Passengers", D("Passengers"), DC("Passengers")),
    ("card_lf", mea("Card Load Factor"), "Load factor", D("Load Factor"), DC("Load Factor")),
    ("card_fare", mea("Card Avg Fare"), "Average fare", D("Avg Fare"), DC("Avg Fare")),
    ("card_rask", mea("Card RASK"), "RASK (₹ per seat-km)", D("RASK"), DC("RASK")),
])
c2a = round((W - 2 * M - G) * 0.40)
c2b = W - 2 * M - G - c2a
p.add("bar_top_routes", "clusteredBarChart", M, row2_y, c2a, p1_h2,
      roles={"Category": [ROUTE], "Y": [(mea("Revenue ₹ Cr"), "Revenue")]},
      title=mea("Title Top Routes"), subtitle="Revenue, Jan 2024–May 2025 · hover a route for its profile",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}],
               "categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(9), "innerPadding": L(20)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(mea("Revenue ₹ Cr"), "Descending")], tooltip_page=TIP,
      filters=[top_n_filter("top8_routes", "Flights", "Route", "Revenue", 8)])
p.add("scatter_routes", "scatterChart", M + c2a + G, row2_y, c2b, p1_h2,
      roles={"Category": [ROUTE], "X": [(mea("Load Factor %"), "Load factor")], "Y": [(mea("RASK"), "RASK")],
             "Size": [(mea("Revenue"), "Revenue")]},
      title=mea("Title Route Map"),
      subtitle="Each bubble is a route sized by revenue; grey = above the network on one measure. PNQ-BOM left out (RASK ₹1.68, mis-priced)",
      objects={"dataPoint": [{"properties": {"fill": C(TEAL)}},
                             {"properties": {"fill": {"solid": {"color": {"expr": mea("Route Quadrant Color")}}}}, "selector": ALL_POINTS}],
               "categoryAxis": [{"properties": {"showAxisTitle": L(True), "titleText": L("Load factor"), "start": L(0.3), "end": L(0.7)}}],
               "valueAxis": [{"properties": {"showAxisTitle": L(True), "titleText": L("RASK (₹ per seat-km)"), "start": L(0), "end": L(0.6)}}]},
      tooltip_page=TIP, filters=[cat_filter("no_pnq_bom", "Flights", "Route", ["'PNQ-BOM'"], exclude=True)])
mw = round((W - 2 * M - G) * 0.56)
p.add("bar_regions", "clusteredBarChart", M, p1_r3, mw, p1_h3,
      roles={"Category": [REGION], "Y": [(mea("Revenue ₹ Cr"), "Revenue")],
             "Tooltips": [(mea("Revenue Share %"), "Share of revenue"), (mea("Load Factor %"), "Load factor"), (mea("RASK"), "RASK")]},
      title=mea("Title Regions"), subtitle="Revenue by departure region · hover for share, LF and RASK · Central (3 flights) not shown",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}],
               "categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(9), "innerPadding": L(20)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(mea("Revenue ₹ Cr"), "Descending")],
      filters=[cat_filter("no_central", "Origin Airport", "Region", ["'Central'"], exclude=True)])
p.add("tbl_weak_routes", "pivotTable", M + mw + G, p1_r3, W - 2 * M - mw - G, p1_h3,
      roles={"Rows": [ROUTE], "Values": [(mea("Review Route Revenue ₹ Cr"), "Revenue"), (mea("LF vs Network (pp)"), "LF vs network (pp)"),
                                         (mea("RASK"), "RASK")]},
      objects={**COMPACT, "subTotals": [{"properties": {"rowSubtotals": L(False)}}], "total": [{"properties": {"show": L(False)}}]},
      title="Biggest review routes: below the network on LF and RASK", subtitle="Top 5 by revenue · right-click a route › Drill through › Route detail",
      sort=[(mea("Review Route Revenue ₹ Cr"), "Descending")], tooltip_page=TIP,
      filters=[top_n_filter("top5_review", "Flights", "Route", "Review Route Revenue", 5)])
p.footer(FOOTER)
pages.append(p)

# =====================================================================
# PAGE 2 - Demand trends  (brief Q2)
# =====================================================================
p = Page("trends", "2 Demand")
p.header("Growth is price-led: revenue +71% on passengers +25% (Jan–May 2025 vs 2024)",
         "Cards: Jan to May 2025 vs Jan to May 2024 (like-for-like)  |  Load factor = passengers / seats", title_measure=mea("Title Demand"), title_w=998)
p.slicer("slc_market", MARKET, "Market", 1086, 178)
p.cards([
    ("card_pax", mea("Card Passengers"), "Passengers 2025 YTD", D("Passengers"), DC("Passengers")),
    ("card_rev", mea("Card Revenue"), "Revenue 2025 YTD", D("Revenue"), DC("Revenue")),
    ("card_fare", mea("Card Avg Fare"), "Average fare", D("Avg Fare"), DC("Avg Fare")),
    ("card_flights", mea("Card Flights"), "Flights", D("Flights"), DC("Flights")),
    ("card_lf", mea("Card Load Factor"), "Load factor", D("Load Factor"), DC("Load Factor")),
], filters=Y2025)
half = (W - 2 * M - G) // 2
p.add("col_pax_month", "clusteredColumnChart", M, row2_y, half, row2_h,
      roles={"Category": [YM], "Y": [(mea("Passengers (K)"), "Passengers (thousands)")]},
      title=mea("Title Pax Months"), subtitle="Passengers per month, thousands",
      objects={**NO_AXIS_TITLES, "dataPoint": [{"properties": {"fill": C(TEAL)}}]},
      sort=[(YM, "Ascending")])
p.add("line_fare_month", "lineChart", M + half + G, row2_y, W - 2 * M - half - G, row2_h,
      roles={"Category": [YM], "Y": [(mea("Avg Fare"), "Average fare")]},
      title=mea("Title Fare Step"), subtitle="Average fare per passenger, ₹ · Nov 2024–May 2025 vs Jan–Oct 2024",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(AMBER)}}],
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}],
               "valueAxis": [{"properties": {"start": L(0), "showAxisTitle": L(False)}}]},
      sort=[(YM, "Ascending")])
c3 = (W - 2 * M - 2 * G) / 3
x1, x2, x3 = M, round(M + c3 + G), round(M + 2 * (c3 + G))
p.add("line_lf_month", "lineChart", x1, row3_y, round(c3), row3_h,
      roles={"Category": [MONTH], "Y": [(mea("Load Factor %"), "Load factor")], "Series": [YEAR]},
      title=mea("Title LF Months"), subtitle="Load factor by month, 2024 (grey) vs 2025 (blue)",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP, "dataPoint": YEAR_COLORS,
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(MONTH, "Ascending")])
p.add("col_weekday", "clusteredColumnChart", x2, row3_y, round(c3), row3_h,
      roles={"Category": [WEEKDAY], "Y": [(mea("Avg Passengers per Flight"), "Passengers per flight")]},
      title=mea("Title Weekday"), subtitle="Average passengers per flight by weekday",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(WEEKDAY, "Ascending")])
p.textbox("txt_trends", x3, row3_y, round(c3), row3_h, "What this tells us (all flights)", [
    (f"{fx('pax_yoy')} ", "more passengers and "),
    (f"{fx('rev_yoy')} ", "more revenue in Jan to May 2025 than a year earlier."),
    ("Fares drove it: ", f"the median fare jumped about {fx('fare_step', '35%')} in Nov 2024 and has held since."),
    ("Load factor ", f"rose {fx('lf_yoy_pp')} pp to {fx('lf_2025')}, so higher fares did not empty the planes."),
    ("Action: ", "schedule by route and month (July–October is the soft season), not by day of week."),
])
p.footer(FOOTER)
pages.append(p)

# =====================================================================
# PAGE 3 - KPI: RASK  (brief Q3)
# =====================================================================
p = Page("kpi_rask", "3 RASK")
p.header("RASK is ₹0.176 in 2025, up 15% and ahead of its ₹0.160 target",
         "RASK = revenue / (seats x km) = seat-km load factor x yield per RPK  |  Target = same period last year + 5%  |  Cards: Jan to May 2025", title_measure=mea("Title RASK"), title_w=998)
p.slicer("slc_market", MARKET, "Market", 1086, 178)
p.cards([
    ("card_rask", mea("Card RASK"), "RASK 2025 YTD", D("RASK"), DC("RASK")),
    ("card_target", mea("Card RASK Target"), "Target (last year + 5%)", mea("Δ RASK Target"), mea("Δ RASK Target Color")),
    ("card_status", mea("RASK Status"), "Status"),
    ("card_slf", mea("Card Seat-km LF"), "Seat-km load factor", D("Seat-km LF"), DC("Seat-km LF")),
    ("card_yield", mea("Card Yield"), "Yield per RPK", D("Yield"), DC("Yield")),
], filters=Y2025, small=("card_status",))
for v in p.visuals:
    if v["name"] == "card_status":
        v["visual"]["objects"]["value"] = [{"properties": {"fontSize": L(18), "fontColor": {"solid": {"color": {"expr": mea("RASK Status Color")}}}},
                                            "selector": {"id": "default"}}]
        v["visual"]["objects"]["accentBar"] = [{"properties": {"show": L(True), "color": {"solid": {"color": {"expr": mea("RASK Status Color")}}}},
                                                "selector": {"id": "default"}}]
r2h = 306
r3y = row2_y + r2h + G
r3h = row3_end - r3y
lw = round((W - 2 * M - G) * 0.38)
p.add("col_rask_market", "clusteredColumnChart", M, row2_y, lw, r2h,
      roles={"Category": [MARKET], "Y": [(mea("RASK"), "RASK")], "Series": [YEAR]},
      title=mea("Title RASK Market"), subtitle="RASK (₹ per seat-km) by market, 2024 (grey) vs 2025 YTD (blue)",
      objects={**NO_AXIS_TITLES, **LABELS, **LEGEND_TOP, "dataPoint": YEAR_COLORS, "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(MARKET, "Ascending")])
RI, YI, SI = mea("RASK Index"), mea("Yield Index"), mea("Seat-km LF Index")
p.add("line_rask_index", "lineChart", M + lw + G, row2_y, W - 2 * M - lw - G, r2h,
      roles={"Category": [YM], "Y": [(RI, "RASK"), (YI, "Yield per RPK"), (SI, "Seat-km load factor")]},
      title="RASK follows yield, not load factor", subtitle="Index, 2024 average = 100 · one scale, so the lines compare directly",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "dataPoint": [series_color_by_measure(RI, NAVY), series_color_by_measure(YI, airline_theme.AMBER), series_color_by_measure(SI, GREY)],
               "lineStyles": line_styles((RI, 4, True), (YI, 2, False), (SI, 2, False))},
      sort=[(YM, "Ascending")])
mw = 700
p.add("mx_market", "pivotTable", M, r3y, mw, r3h,
      roles={"Rows": [MARKET],
             "Values": [(mea("Flights"), "Flights"), (mea("Avg Stage Length Km"), "Stage km"),
                        (mea("Seat-km Load Factor %"), "Seat-km LF"), (mea("Yield per RPK"), "Yield / RPK"),
                        (mea("RASK"), "RASK"), (mea("Revenue Share %"), "Revenue share")]},
      title=mea("Title Market Gap"), subtitle="Longer stages earn less per km: compare like with like",
      sort=[(mea("Revenue"), "Descending")])
p.textbox("txt_kpi", M + mw + G, r3y, W - 2 * M - mw - G, r3h, "Why RASK (all flights)", [
    ("Formula: ", "seat-km load factor x yield per RPK: it rises by filling seats or by earning more per passenger-km."),
    ("2025: ", f"{fx('rask_2025')} per seat-km, {fx('rask_yoy')} vs last year; yield explains almost 90% of the gain."),
    ("Action: ", "protect yield on full routes; grow load factor on international, where seats sit empty."),
])
p.footer(FOOTER)
pages.append(p)

# =====================================================================
# PAGE 4 - Key insights (text comes from analysis/output/report_facts.json)
# =====================================================================
if facts.get("findings"):
    p = Page("insights", "4 Insights")
    p.header("Eight findings, ranked by business impact", "From 40,175 flights, Jan 2024 to May 2025  |  Data notes explain every rule applied")
    half = (W - 2 * M - G) // 2
    p.textbox("txt_findings", M, 80, half, row3_end - 80, "Business findings", [tuple(x) for x in facts["findings"]], accent=TEAL,
              size="13pt", gap=True)
    p.textbox("txt_dq", M + half + G, 80, W - 2 * M - half - G, row3_end - 80, "Data and model notes",
              [tuple(x) for x in facts["data_notes"]], accent=CORAL, size="13pt", gap=True)
    p.footer(FOOTER)
    pages.append(p)


# =====================================================================
# PAGE 5 - Forecast Jun-Dec 2025 and revenue levers (analysis/03_forecast, 04_levers)
# =====================================================================
def default_slicer(pg, name, t, c, label, x, w, value):
    flt = {"Version": 2, "From": [{"Name": "s", "Entity": t, "Type": 0}],
           "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": c}}],
                                           "Values": [[{"Literal": {"Value": f"'{value}'"}}]]}}}]}
    pg.add(name, "slicer", x, 8, w, 56, roles={"Values": [col(t, c)]}, alt=f"{label} filter",
           objects={"data": [{"properties": {"mode": L("Dropdown")}}],
                    "selection": [{"properties": {"singleSelect": L(True), "strictSingleSelect": L(True)}}],
                    "general": [{"properties": {"filter": {"filter": flt}}}],
                    "header": [{"properties": {"show": L(True), "text": L(label), "fontColor": C(MUTED), "textSize": L(9)}}],
                    "items": [{"properties": {"fontColor": C(INK), "textSize": L(10)}}]},
           container={"background": [{"properties": {"show": L(True), "color": C(WHITE), "transparency": L(0)}}],
                      "border": [{"properties": {"show": L(True), "color": C(LINE), "radius": L(6)}}],
                      "padding": [{"properties": {"top": L(2), "bottom": L(2), "left": L(8), "right": L(8)}}]})


p = Page("forecast", "5 Forecast")
p.header("2025 revenue heads for ₹63.9 Cr; levers add ₹2.95 Cr a year",
         "Passengers: trend + seasonality, backtested  |  Fares: two scenarios after the Nov 2024 step  |  Median with 80% range", title_measure=mea("Title Forecast"), title_w=702)
default_slicer(p, "slc_scenario", "Scenario", "Scenario", "Fare scenario", 790, 280, "A · Fares hold (post-Nov 2024 level)")
default_slicer(p, "slc_metric", "Forecast", "Metric", "Chart metric", 1086, 178, "Revenue")
NEU, GOODC = mea("Δ Neutral Color"), mea("Δ Good Color")
p.cards([
    ("card_f_rev", mea("F25 Revenue (Cr)"), "2025 revenue (forecast)", mea("Δ F25 Revenue"), GOODC),
    ("card_f_range", mea("F25 Revenue Range"), "80% range", mea("Δ Range"), NEU),
    ("card_f_pax", mea("F25 Passengers (M)"), "2025 passengers", mea("Δ F25 Passengers"), GOODC),
    ("card_backtest", mea("Card Backtest"), "Backtest error (Mar–May 2025)", mea("Δ Backtest"), NEU),
    ("card_lever_total", mea("Lever Uplift (Cr)"), "Levers, per year", mea("Δ Lever Share"), NEU),
], small=("card_f_range",))
FA_, F50, F10, F90 = mea("Fcst Actual"), mea("Fcst P50"), mea("Fcst P10"), mea("Fcst P90")
p.add("line_forecast", "lineChart", M, row2_y, W - 2 * M, row2_h,
      roles={"Category": [col("Forecast", "Month Label")],
             "Y": [(FA_, "Actual"), (F50, "Forecast (median)"), (F10, "Low case (P10)"), (F90, "High case (P90)")]},
      title="The forecast continues the post-November fare level", subtitle="₹ Cr per month (thousands of passengers when the metric is switched) · dashed = 80% range",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "dataPoint": [series_color_by_measure(FA_, NAVY), series_color_by_measure(F50, TEAL),
                             series_color_by_measure(F10, airline_theme.BAND_LIGHT), series_color_by_measure(F90, airline_theme.BAND_LIGHT)],
               "lineStyles": [{"properties": {"strokeWidth": L(3)}, "selector": {"metadata": qref(FA_)}},
                              {"properties": {"strokeWidth": L(3)}, "selector": {"metadata": qref(F50)}},
                              {"properties": {"strokeWidth": L(1), "lineStyle": L("dashed")}, "selector": {"metadata": qref(F10)}},
                              {"properties": {"strokeWidth": L(1), "lineStyle": L("dashed")}, "selector": {"metadata": qref(F90)}}]},
      sort=[(col("Forecast", "Month Label"), "Ascending")])
lw = round((W - 2 * M - G) * 0.55)
p.add("bar_levers", "clusteredBarChart", M, row3_y, lw, row3_h,
      roles={"Category": [col("Levers", "Lever Label")], "Y": [(mea("Lever Uplift ₹ Cr"), "Revenue uplift per year")],
             "Tooltips": [(mea("Lever Uplift %"), "% of revenue")]},
      title="Re-deploying weak-route capacity is the biggest lever", subtitle="Revenue uplift per year, sized on Jun 2024 to May 2025 · label shows confidence",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(AMBER)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(mea("Lever Uplift ₹ Cr"), "Descending")])
p.textbox("txt_plan", M + lw + G, row3_y, W - 2 * M - lw - G, row3_h, "Recommended plan (₹2.95 Cr a year, 4.6–4.9% of 2025 revenue)", [
    ("1. ", "Move capacity off the 12 weakest review routes: +₹1.42 Cr."),
    ("2. ", "Raise fares 5% on 35 full, low-RASK routes: +₹0.74 Cr."),
    ("3. ", "Lift international load factor from 50% to 54%: +₹0.47 Cr."),
    ("4. ", "Fill seats on 33 high-RASK routes to the network average: +₹0.32 Cr."),
    ("Caveat: ", "figures look scaled; decide on the % effects. Re-run notebooks 03 and 04, then refresh, to update."),
])
p.footer(FOOTER)
pages.append(p)

# =====================================================================
# Route detail: drillthrough page (right-click a route anywhere)
# =====================================================================
DT_FILTER = "dt_route"
p = Page("route_detail", "Route detail", page_type="Drillthrough", hidden=True,
         binding={"name": "route_detail_binding", "type": "Drillthrough",
                  "parameters": [{"name": "route_param", "boundFilter": DT_FILTER, "fieldExpr": ROUTE}]},
         filters=[{"name": DT_FILTER, "field": ROUTE, "type": "Categorical", "howCreated": "Drillthrough"}])
p.header("Route detail", "Drill-through page: one route against the network  |  Use the back arrow (Ctrl+click in Desktop) to return",
         title_measure=mea("Title Route Detail"), title_w=1000)
p.add("btn_back", "actionButton", W - M - 120, 18, 120, 36, alt="Back to the previous page",
      objects={"icon": [{"properties": {"shapeType": L("back")}, "selector": {"id": "default"}}],
               "text": [{"properties": {"show": L(True), "text": L("Back"), "fontColor": C(WHITE)}, "selector": {"id": "default"}}]},
      container={"visualLink": [{"properties": {"show": L(True), "type": L("Back")}}],
                 "background": [{"properties": {"show": L(False)}}], "border": [{"properties": {"show": L(False)}}],
                 "title": [{"properties": {"show": L(False)}}]})
p.cards([
    ("card_route", mea("Selected Route"), "Route"),
    ("card_quadrant", mea("Route Quadrant"), "Position vs network"),
    ("card_rev", mea("Card Revenue"), "Revenue"),
    ("card_lf", mea("Card Load Factor"), "Load factor", mea("Δ LF vs Network"), mea("Δ Neutral Color")),
    ("card_rask", mea("Card RASK"), "RASK"),
    ("card_fare", mea("Card Avg Fare"), "Average fare"),
], small=("card_quadrant",))
p.add("col_route_rev", "clusteredColumnChart", M, row2_y, half, row2_h,
      roles={"Category": [YM], "Y": [(mea("Revenue ₹ Cr"), "Revenue")]},
      title="Revenue by month", subtitle="₹ Cr", objects={**NO_AXIS_TITLES, "dataPoint": [{"properties": {"fill": C(TEAL)}}]},
      sort=[(YM, "Ascending")])
NLF = mea("Network Load Factor %")
p.add("line_route_lf", "lineChart", M + half + G, row2_y, W - 2 * M - half - G, row2_h,
      roles={"Category": [YM], "Y": [(mea("Load Factor %"), "Route"), (NLF, "Network")]},
      title="Load factor vs the network", subtitle="Route (blue) and network average (grey), by month",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "dataPoint": [series_color_by_measure(mea("Load Factor %"), TEAL), series_color_by_measure(NLF, GREY)],
               "lineStyles": line_styles((mea("Load Factor %"), 3, True), (NLF, 2, False))},
      sort=[(YM, "Ascending")])
p.add("line_route_fare", "lineChart", M, row3_y, half, row3_h,
      roles={"Category": [YM], "Y": [(mea("Avg Fare"), "Average fare")]},
      title="Average fare by month", subtitle="₹ per passenger",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(AMBER)}}],
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(YM, "Ascending")])
p.add("col_route_weekday", "clusteredColumnChart", M + half + G, row3_y, W - 2 * M - half - G, row3_h,
      roles={"Category": [WEEKDAY], "Y": [(mea("Avg Passengers per Flight"), "Passengers per flight")]},
      title="Passengers per flight by weekday", subtitle="Average",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}], "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(WEEKDAY, "Ascending")])
p.footer(FOOTER, nav=False)
pages.append(p)

# =====================================================================
# Route tooltip: report-page tooltip shown when hovering a route
# =====================================================================
TW, TH = 400, 300
p = Page(TIP, "Route tooltip", page_type="Tooltip", hidden=True, binding={"name": "route_tip_binding", "type": "Tooltip"}, size=(TW, TH))
tw = (TW - 2 * 8 - 2 * 6) / 3
p.cards([("tip_route", mea("Selected Route"), "Route"), ("tip_quad", mea("Route Quadrant"), "Position")],
        y=6, h=64, x0=8, width=TW - 16, small=("tip_route", "tip_quad"))
p.cards([("tip_rev", mea("Card Revenue"), "Revenue"), ("tip_lf", mea("Card Load Factor"), "Load factor"), ("tip_rask", mea("Card RASK"), "RASK")],
        y=76, h=64, x0=8, width=TW - 16, small=("tip_rev", "tip_lf", "tip_rask"))
# (values set to 12pt below so ₹ Cr amounts fit)
p.add("tip_line", "lineChart", 8, 146, TW - 16, TH - 152,
      roles={"Category": [col("Date", "Month Start")], "Y": [(mea("Revenue ₹ Cr"), "Revenue")]},
      title="Revenue by month, Jan 2024–May 2025 (₹ Cr)", container={"subTitle": [{"properties": {"show": L(False)}}],
                                                 "padding": [{"properties": {"top": L(4), "bottom": L(4), "left": L(6), "right": L(6)}}]},
      objects={**NO_AXIS_TITLES, "dataPoint": [{"properties": {"fill": C(TEAL)}}], "lineStyles": [{"properties": {"strokeWidth": L(2)}}],
               "categoryAxis": [{"properties": {"show": L(False), "axisType": L("Continuous")}}]},
      sort=[(col("Date", "Month Start"), "Ascending")])
for v in p.visuals:   # compact text for the small canvas
    if v["visual"]["visualType"] == "cardVisual":
        v["visual"]["objects"]["value"] = [{"properties": {"fontSize": L(12)}, "selector": {"id": "default"}}]
        v["visual"]["objects"]["label"] = [{"properties": {"fontSize": L(8)}, "selector": {"id": "default"}}]
pages.append(p)

# keep the Market slicer in sync across the network, demand and RASK pages
for pg in pages:
    for v in pg.visuals:
        if v["name"] == "slc_market":
            v["visual"]["syncGroup"] = {"groupName": "Market", "fieldChanges": True, "filterChanges": True}
k.finish(pages)
