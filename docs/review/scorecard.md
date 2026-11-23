# Scorecard: AirlineDataAnalysis-PBI

Reviewer: Claude, using the expert rubric `D:\Wolf\PBI\_knowledge\dashboard_scorecard.md` (v1).
Evidence: the PDF export (`docs/AirlineDataAnalysis-PBI.pdf`), the page images, the TMDL model, Performance Analyzer in
Desktop, Python reconciliation (notebook 00), and a colour-blindness simulation (Machado 2009) of every key colour pair.

- **Before:** 24 Nov 2026, the published v1 report.
- **After:** the v2 rebuild, the same night.

| # | Criterion | Before | After | What changed |
|---|---|---|---|---|
| 1 | Purpose and message | 0.75 | 0.75 | Every page and chart title now states its finding, and each title's numbers were checked in Python (one wrong claim, "LF rose every month", was caught and fixed). Still open: the titles are static and describe all flights, and the page 1 header says so. Dynamic titles would make it 1.0. |
| 2 | Data trust and accuracy | 0.75 | 1.0 | Every page has a footer with the source, data period, refresh date (from a `Refresh Info` table) and the main caveat. Python = Power BI reconciliation is unchanged. |
| 3 | KPI design | 0.75 | 1.0 | Every KPI card has a ▲▼ change line vs last year (green or red, grey when not comparable). The target card shows the distance to target. RASK decomposes into cards for seat-km LF and yield. |
| 4 | Chart choice and honesty | 0.5 | 1.0 | Both dual-axis charts are gone: one is split into two aligned charts, the other replaced by an index chart (2024 = 100). PNQ-BOM is excluded from the scatter with a stated reason. Bars start at zero and are sorted. The forecast joins the history line and shows an 80% band. |
| 5 | Layout and hierarchy | 0.75 | 1.0 | No scrolling or clipped tables in the export. Layout is stratified (KPIs, then drivers, then detail) on one template with a footer row. The region table became a sorted bar chart. |
| 6 | Colour and accessibility | 0.5 | 1.0 | All 106 visuals have alt text. Status and change colours meet WCAG AA on white (4.2–5.5:1; the "Watch" amber is large text). Simulated ΔE ≥ 26 for deuteranopia on every key pair, and green/red always carries ▲▼ too. Markers on the key lines. |
| 7 | Declutter, text, formatting | 0.5 | 1.0 | Units are consistent: ₹ Cr for revenue, M for passengers, ₹ per seat-km. Direct data labels; legends on top in one line; no truncated labels. |
| 8 | Interaction, navigation, devices | 0.5 | 1.0 | Route drill-through (verified on PNQ-BLR) and a route tooltip page linked to the three route visuals. The tooltip config matches what Desktop writes, but synthetic hover couldn't show it, so check it by hand once. Page navigator on every page, Market slicer synced across pages 1–3, phone layouts for all six pages. |
| 9 | Insight and action | 0.75 | 1.0 | The Forecast page has a recommended plan (₹2.95 Cr a year, ~4.6% of 2025 revenue), lever labels with confidence, a backtest card (−0.5% vs naive −4.9%), and an action line on each text panel. |
| 10 | Model and engineering | 0.75 | 0.75 | All 105 measures have descriptions, in 7 display folders. DAX query time is 52–74 ms per visual (Performance Analyzer). Desktop's linguistic metadata is preserved. Generators rebuild the model and pages. Still open: Tabular Editor Best Practice Analyzer not run (not installed). |
| | Gates applied | max 7 | none | The v1 export clipped table rows. v2 has no clipped text, no misleading encodings and no unreconciled numbers. |
| | **Total** | **6.5 / 10** | **9.5 / 10** | |

**To reach 10:**
1. **Dynamic titles.** Drive the chart titles from measures, so the stated numbers follow the Market and Year slicers.
2. **Best Practice Analyzer.** Install Tabular Editor 2 (free) and run the standard rules, then record the result here.
