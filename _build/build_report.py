"""Builds the AirlineDataAnalysis-PBI report pages (PBIR JSON) in the InXiteOut palette.
Run: python _build/build_report.py   (then "Apply external changes" in Power BI Desktop)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pbir_kit as k
from pbir_kit import (L, C, col, mea, qref, cat_filter, series_color_by_value, series_color_by_measure, Page,
                      NAVY, TEAL, AMBER, CORAL, SLATE, GREEN, INK, MUTED, WHITE, LINE, W, H, M, G)

ROOT = Path(__file__).resolve().parents[1]
k.init(ROOT / "AirlineDataAnalysis-PBI.Report")
OUT = ROOT / "analysis" / "output"
facts = json.loads((OUT / "report_facts.json").read_text(encoding="utf-8")) if (OUT / "report_facts.json").exists() else {}

ROUTE, MARKET = col("Flights", "Route"), col("Flights", "Market")
YEAR, YM, MONTH, WEEKDAY = col("Date", "Year"), col("Date", "Year Month"), col("Date", "Month"), col("Date", "Weekday")
O_CITY, O_REGION = col("Origin Airport", "Airport Label"), col("Origin Airport", "Region")
NO_AXIS_TITLES = {"categoryAxis": [{"properties": {"showAxisTitle": L(False)}}],
                  "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True)}}]}
LABELS = {"labels": [{"properties": {"show": L(True), "fontSize": L(9)}}]}
LEGEND_TOP = {"legend": [{"properties": {"show": L(True), "position": L("Top")}}]}
Y2025 = [cat_filter("year_2025", "Date", "Year", ["2025L"])]
MARKET_COLORS = [series_color_by_value("Flights", "Market", "Domestic", TEAL),
                 series_color_by_value("Flights", "Market", "International", AMBER)]
YEAR_COLORS = [{"properties": {"fill": C(AMBER)}, "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": YEAR,
                                                                                                    "Right": {"Literal": {"Value": "2024L"}}}}}]}},
               {"properties": {"fill": C(TEAL)}, "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": YEAR,
                                                                                                   "Right": {"Literal": {"Value": "2025L"}}}}}]}}]
row2_y, row2_h = 184, 262
row3_y = row2_y + row2_h + G
row3_h = H - M - row3_y
fx = lambda key, default="…": facts.get(key, default)


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


pages = []
# =====================================================================
# PAGE 1 - Network and route performance  (brief Q1)
# =====================================================================
p = Page("network", "1. Network & Routes")
p.header("Network & Route Performance",
         "40,175 flights  |  179 routes  |  38 airports  |  Jan 2024 to May 2025  |  RASK = revenue per available seat-km")
p.slicer("slc_market", MARKET, "Market", 900, 170)
p.slicer("slc_year", YEAR, "Year", 1086, 178)
p.cards([
    ("card_rev", mea("Revenue"), "Revenue"),
    ("card_flights", mea("Flights"), "Flights"),
    ("card_pax", mea("Passengers"), "Passengers"),
    ("card_lf", mea("Load Factor %"), "Load Factor"),
    ("card_fare", mea("Avg Fare"), "Avg Fare"),
    ("card_rask", mea("RASK"), "RASK (₹ / seat-km)"),
])
c2a = round((W - 2 * M - G) * 0.42)
c2b = W - 2 * M - G - c2a
p.add("bar_top_routes", "clusteredBarChart", M, row2_y, c2a, row2_h,
      roles={"Category": [ROUTE], "Y": [(mea("Revenue"), "Revenue")]},
      title="Top 10 routes by revenue", subtitle="Share of network revenue on hover",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(mea("Revenue"), "Descending")],
      filters=[top_n_filter("top10_routes", "Flights", "Route", "Revenue", 10)])
p.add("scatter_routes", "scatterChart", M + c2a + G, row2_y, c2b, row2_h,
      roles={"Category": [ROUTE], "X": [(mea("Load Factor %"), "Load factor")], "Y": [(mea("RASK"), "RASK")],
             "Size": [(mea("Revenue"), "Revenue")]},
      title="Route map: load factor vs RASK", subtitle="Each bubble is a route, sized by revenue. Lower-left = review. PNQ-BOM (RASK 1.68) off-scale",
      objects={"dataPoint": [{"properties": {"fill": C(TEAL)}}],
               "categoryAxis": [{"properties": {"showAxisTitle": L(True), "titleText": L("Load factor"), "start": L(0.3), "end": L(0.7)}}],
               "valueAxis": [{"properties": {"showAxisTitle": L(True), "titleText": L("RASK (₹ per seat-km)"), "start": L(0), "end": L(0.6)}}]})
mw = round((W - 2 * M - G) * 0.58)
p.add("mx_airports", "pivotTable", M, row3_y, mw, row3_h,
      roles={"Rows": [O_REGION, O_CITY],
             "Values": [(mea("Revenue"), "Revenue"), (mea("Flights"), "Flights"), (mea("Load Factor %"), "Load factor"),
                        (mea("Avg Fare"), "Avg fare"), (mea("RASK"), "RASK"), (mea("Revenue Share %"), "Share")]},
      title="Departure airports by region", subtitle="Expand a region to see its airports",
      sort=[(mea("Revenue"), "Descending")])
p.add("tbl_weak_routes", "pivotTable", M + mw + G, row3_y, W - 2 * M - mw - G, row3_h,
      roles={"Rows": [ROUTE], "Values": [(mea("Review Route Revenue"), "Revenue"), (mea("Load Factor %"), "LF"), (mea("RASK"), "RASK")]},
      objects={"subTotals": [{"properties": {"rowSubtotals": L(False)}}], "total": [{"properties": {"show": L(False)}}]},
      title="Biggest routes to review", subtitle="Below the network on both load factor and RASK, by revenue",
      sort=[(mea("Review Route Revenue"), "Descending")],
      filters=[top_n_filter("top10_review", "Flights", "Route", "Review Route Revenue", 10)])
pages.append(p)

# =====================================================================
# PAGE 2 - Demand trends  (brief Q2)
# =====================================================================
p = Page("trends", "2. Demand Trends")
p.header("Demand Trends: 2025 vs 2024",
         "Cards compare Jan to May 2025 with Jan to May 2024 (like-for-like)  |  Load factor = passengers / seats")
p.slicer("slc_market", MARKET, "Market", 1086, 178)
p.cards([
    ("card_pax_yoy", mea("Passengers YoY %"), "Passengers vs LY"),
    ("card_flights_yoy", mea("Flights YoY %"), "Flights vs LY"),
    ("card_rev_yoy", mea("Revenue YoY %"), "Revenue vs LY"),
    ("card_fare_yoy", mea("Avg Fare YoY %"), "Avg Fare vs LY"),
    ("card_lf_yoy", mea("Load Factor YoY (pp)"), "Load Factor vs LY (pp)"),
    ("card_lf_2025", mea("Load Factor %"), "Load Factor 2025"),
], filters=Y2025)
p.add("combo_monthly", "lineClusteredColumnComboChart", M, row2_y, W - 2 * M, row2_h,
      roles={"Category": [YM], "Y": [(mea("Passengers"), "Passengers")], "Y2": [(mea("Avg Fare"), "Avg fare")]},
      title="Monthly passengers and average fare", subtitle="Fares stepped up in Nov 2024 while traffic kept growing",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "dataPoint": [series_color_by_measure(mea("Passengers"), TEAL), series_color_by_measure(mea("Avg Fare"), CORAL)],
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(YM, "Ascending")])
c3 = (W - 2 * M - 2 * G) / 3
x1, x2, x3 = M, round(M + c3 + G), round(M + 2 * (c3 + G))
p.add("line_lf_month", "lineChart", x1, row3_y, round(c3), row3_h,
      roles={"Category": [MONTH], "Y": [(mea("Load Factor %"), "Load factor")], "Series": [YEAR]},
      title="Load factor by month", subtitle="2024 vs 2025",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP, "dataPoint": YEAR_COLORS,
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(MONTH, "Ascending")])
p.add("col_weekday", "clusteredColumnChart", x2, row3_y, round(c3), row3_h,
      roles={"Category": [WEEKDAY], "Y": [(mea("Avg Passengers per Flight"), "Passengers per flight")]},
      title="Passengers per flight by weekday", subtitle="Demand is flat across the week",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(TEAL)}}]},
      sort=[(WEEKDAY, "Ascending")])
p.textbox("txt_trends", x3, row3_y, round(c3), row3_h, "What this tells us", [
    (f"{fx('pax_yoy')} ", "more passengers and "),
    (f"{fx('rev_yoy')} ", f"more revenue in Jan to May 2025 than a year earlier."),
    ("Fares drove it: ", f"median fare jumped about {fx('fare_step', '35%')} in Nov 2024 and has held since."),
    ("Load factor ", f"rose {fx('lf_yoy_pp')} pp to {fx('lf_2025')}, so higher fares did not empty the planes."),
    ("No weekday peak: ", "schedule by route and month, not by day of week."),
])
pages.append(p)

# =====================================================================
# PAGE 3 - KPI: RASK  (brief Q3)
# =====================================================================
p = Page("kpi_rask", "3. KPI: RASK")
p.header("KPI: Revenue per Available Seat-Km (RASK)",
         "RASK = revenue / (seats x km) = seat-km load factor x yield per RPK  |  Target = same period last year + 5%  |  Cards: Jan to May 2025")
p.slicer("slc_market", MARKET, "Market", 1086, 178)
p.cards([
    ("card_rask", mea("RASK"), "RASK 2025 YTD"),
    ("card_target", mea("RASK Target"), "Target (PY + 5%)"),
    ("card_vs_target", mea("RASK vs Target %"), "vs Target"),
    ("card_yoy", mea("RASK YoY %"), "vs Last Year"),
    ("card_status", mea("RASK Status"), "Status"),
    ("card_yield", mea("Yield per RPK"), "Yield per RPK"),
], filters=Y2025, small=("card_status",))
for v in p.visuals:
    if v["name"] == "card_status":
        v["visual"]["objects"]["value"] = [{"properties": {"fontSize": L(16), "fontColor": {"solid": {"color": {"expr": mea("RASK Status Color")}}}},
                                            "selector": {"id": "default"}}]
        v["visual"]["objects"]["accentBar"] = [{"properties": {"show": L(True), "color": {"solid": {"color": {"expr": mea("RASK Status Color")}}}},
                                                "selector": {"id": "default"}}]
kw = 300
p.add("kpi_rask", "kpi", M, row2_y, kw, row2_h,
      roles={"Indicator": [(mea("RASK"), "RASK")], "Goal": [(mea("RASK Target"), "Target")], "TrendLine": [YEAR]},
      title="RASK vs target", subtitle="Latest year (2025 YTD) against goal",
      objects={"goals": [{"properties": {"showGoal": L(True), "showDistance": L(True)}}],
               "trendline": [{"properties": {"show": L(False)}}]},
      sort=[(YEAR, "Ascending")])
p.add("combo_rask_month", "lineClusteredColumnComboChart", M + kw + G, row2_y, W - 2 * M - kw - G, row2_h,
      roles={"Category": [YM], "Y": [(mea("RASK"), "RASK")], "Y2": [(mea("Seat-km Load Factor %"), "Seat-km load factor")]},
      title="Monthly RASK and seat-km load factor", subtitle="RASK moves with fares (yield) more than with load factor",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "dataPoint": [series_color_by_measure(mea("RASK"), TEAL), series_color_by_measure(mea("Seat-km Load Factor %"), CORAL)],
               "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(YM, "Ascending")])
mw = 700
p.add("mx_market", "pivotTable", M, row3_y, mw, row3_h,
      roles={"Rows": [MARKET],
             "Values": [(mea("Flights"), "Flights"), (mea("Avg Stage Length Km"), "Stage km"),
                        (mea("Seat-km Load Factor %"), "Seat-km LF"), (mea("Yield per RPK"), "Yield / RPK"),
                        (mea("RASK"), "RASK"), (mea("Revenue Share %"), "Revenue share")]},
      title="RASK drivers: domestic vs international", subtitle="Longer stages earn less per km: compare like with like",
      sort=[(mea("Revenue"), "Descending")])
p.textbox("txt_kpi", M + mw + G, row3_y, W - 2 * M - mw - G, row3_h, "Why RASK", [
    "It is the airline industry's standard measure of how well capacity turns into revenue: every seat flown, every km.",
    ("Formula: ", "RASK = seat-km load factor x yield per RPK, so it rises by filling seats or by earning more per passenger-km."),
    ("2025 YTD: ", f"{fx('rask_2025')} per seat-km, {fx('rask_yoy')} vs last year ({fx('rask_status', 'see status card')})."),
    ("Watch: ", "short routes earn more per km. Compare routes of similar length, not the whole network."),
    "Edit the measure [RASK Target Growth %] to change the target.",
])
pages.append(p)

# =====================================================================
# PAGE 4 - Key insights (text comes from analysis/output/report_facts.json)
# =====================================================================
if facts.get("findings"):
    p = Page("insights", "4. Key Insights")
    p.header("Key Insights and Data Notes", "Findings from 40,175 flights, Jan 2024 to May 2025, ranked by business impact")
    half = (W - 2 * M - G) // 2
    p.textbox("txt_findings", M, 80, half, H - 80 - M, "Business findings", [tuple(x) for x in facts["findings"]], accent=TEAL,
              size="11pt", gap=True)
    p.textbox("txt_dq", M + half + G, 80, W - 2 * M - half - G, H - 80 - M, "Data and model notes",
              [tuple(x) for x in facts["data_notes"]], accent=CORAL, size="11pt", gap=True)
    pages.append(p)

# =====================================================================
# PAGE 5 - Forecast Jun-Dec 2025 and profit levers (analysis/03_forecast, 04_levers)
# =====================================================================
def default_slicer(pg, name, t, c, label, x, w, value):
    flt = {"Version": 2, "From": [{"Name": "s", "Entity": t, "Type": 0}],
           "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": c}}],
                                           "Values": [[{"Literal": {"Value": f"'{value}'"}}]]}}}]}
    pg.add(name, "slicer", x, 8, w, 56, roles={"Values": [col(t, c)]},
           objects={"data": [{"properties": {"mode": L("Dropdown")}}],
                    "selection": [{"properties": {"singleSelect": L(True), "strictSingleSelect": L(True)}}],
                    "general": [{"properties": {"filter": {"filter": flt}}}],
                    "header": [{"properties": {"show": L(True), "text": L(label), "fontColor": C(MUTED), "textSize": L(9)}}],
                    "items": [{"properties": {"fontColor": C(INK), "textSize": L(10)}}]},
           container={"background": [{"properties": {"show": L(True), "color": C(WHITE), "transparency": L(0)}}],
                      "border": [{"properties": {"show": L(True), "color": C(LINE), "radius": L(6)}}],
                      "padding": [{"properties": {"top": L(2), "bottom": L(2), "left": L(8), "right": L(8)}}]})


p = Page("forecast", "5. Forecast & Levers")
p.header("Forecast 2025 and Revenue Levers",
         "Passengers: trend + seasonality, backtested  |  Fares: two scenarios after the Nov 2024 step  |  Median with 80% range")
default_slicer(p, "slc_scenario", "Scenario", "Scenario", "Fare scenario", 790, 280, "A · Fares hold (post-Nov 2024 level)")
default_slicer(p, "slc_metric", "Forecast", "metric", "Chart metric", 1086, 178, "Revenue")
p.cards([
    ("card_f_rev", mea("F25 Revenue (Cr)"), "2025 Revenue"),
    ("card_f_range", mea("F25 Revenue Range"), "80% Range"),
    ("card_f_rev_yoy", mea("F25 Revenue vs 2024 %"), "vs 2024"),
    ("card_f_pax", mea("F25 Passengers (M)"), "2025 Passengers"),
    ("card_f_pax_yoy", mea("F25 Passengers vs 2024 %"), "Passengers vs 2024"),
    ("card_lever_total", mea("Lever Uplift (Cr)"), "Levers, per year"),
], small=("card_f_range",))
FA_, F50, F10, F90 = mea("Fcst Actual"), mea("Fcst P50"), mea("Fcst P10"), mea("Fcst P90")
p.add("line_forecast", "lineChart", M, row2_y, W - 2 * M, row2_h,
      roles={"Category": [col("Forecast", "month")],
             "Y": [(FA_, "Actual"), (F50, "Forecast (median)"), (F10, "Low case (P10)"), (F90, "High case (P90)")]},
      title="Monthly history and forecast to Dec 2025", subtitle="Switch the chart metric between revenue and passengers",
      objects={**NO_AXIS_TITLES, **LEGEND_TOP,
               "categoryAxis": [{"properties": {"showAxisTitle": L(False), "axisType": L("Continuous")}}],
               "dataPoint": [series_color_by_measure(FA_, NAVY), series_color_by_measure(F50, TEAL),
                             series_color_by_measure(F10, "#D9CCFF"), series_color_by_measure(F90, "#D9CCFF")],
               "lineStyles": [{"properties": {"strokeWidth": L(2)}, "selector": {"metadata": qref(FA_)}},
                              {"properties": {"strokeWidth": L(3)}, "selector": {"metadata": qref(F50)}},
                              {"properties": {"strokeWidth": L(1), "lineStyle": L("dashed")}, "selector": {"metadata": qref(F10)}},
                              {"properties": {"strokeWidth": L(1), "lineStyle": L("dashed")}, "selector": {"metadata": qref(F90)}}]},
      sort=[(col("Forecast", "month"), "Ascending")])
lw = round((W - 2 * M - G) * 0.55)
p.add("bar_levers", "clusteredBarChart", M, row3_y, lw, row3_h,
      roles={"Category": [col("Levers", "lever")], "Y": [(mea("Lever Uplift"), "Revenue uplift per year")],
             "Tooltips": [(mea("Lever Uplift %"), "% of revenue")]},
      title="Revenue levers", subtitle="Sized on Jun 2024 to May 2025; hover for % of revenue",
      objects={**NO_AXIS_TITLES, **LABELS, "dataPoint": [{"properties": {"fill": C(AMBER)}}],
               "valueAxis": [{"properties": {"show": L(False)}}]},
      sort=[(mea("Lever Uplift"), "Descending")])
p.textbox("txt_forecast_notes", M + lw + G, row3_y, W - 2 * M - lw - G, row3_h, "How to read this page", [
    ("2025 revenue: ", f"{fx('f25_a', 'see card')} if fares hold, {fx('f25_b', '…')} if they settle at the Mar to May level."),
    ("Backtest: ", f"the passenger model was {fx('bt_err', 'within 1%')} on Mar to May 2025, vs {fx('bt_naive', '-5%')} for a naive forecast."),
    ("Biggest lever: ", "move capacity off the weakest routes, then lift fares 5% on full, low-RASK routes."),
    ("Caveat: ", "passengers and revenue look scaled, so use the % changes, not the rupee amounts, for decisions."),
    ("To update: ", "re-run analysis notebooks 03 and 04, then refresh this report."),
])
pages.append(p)

k.finish(pages)
