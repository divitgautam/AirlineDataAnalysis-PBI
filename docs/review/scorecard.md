# Scorecard: AirlineDataAnalysis-PBI

Reviewer: Claude, using the expert rubric `D:\Wolf\PBI\_knowledge\dashboard_scorecard.md` (v1).

**Evidence:**
- the PDF export (`docs/dashboard/AirlineDataAnalysis-PBI.pdf`) and the page images
- the TMDL model
- the Best Practice Analyzer check (`D:\Wolf\PBI\_knowledge\bpa_check.py`; results in `docs/review/bpa_results.json`)
- Performance Analyzer in Desktop
- Python reconciliation (notebook 00)
- a colour-blindness simulation of every key colour pair
- slicer tests: Market = International, Fare scenario = B, and a drill-through to a review route

| # | Criterion | Before | After | What changed |
|---|---|---|---|---|
| 1 | Purpose and message | 0.75 | 1.0 | Titles are action titles driven by 14 DAX measures, so their numbers follow the Market, Year and Scenario slicers (e.g. "Pune is the hub (64% of revenue); 4 routes trail the network" for International). Wording adapts to the data ("stepped up", "lower", "held level"; "4 of 5 comparable months"). Every title was checked against Python. Testing found and fixed a bug: routes with no flights were counted as "trailing". |
| 2 | Data trust and accuracy | 0.75 | 1.0 | Every page has a footer with the source, period, refresh date and caveat. Python = Power BI reconciliation is unchanged. Static narrative panels are labelled "(all flights)". |
| 3 | KPI design | 0.75 | 1.0 | Every KPI card has a ▲▼ change line vs last year or vs target; status uses AA colours; RASK decomposes into seat-km load factor and yield. |
| 4 | Chart choice and honesty | 0.5 | 1.0 | No dual axes (the RASK drivers share an index, 2024 = 100). The PNQ-BOM exclusion is stated. Bars are sorted and start at zero. The forecast has an 80% band. Lines are straight, not smoothed (24 Nov 2026: the Fluent 2 base theme smooths them by default; the theme now overrides it). |
| 5 | Layout and hierarchy | 0.75 | 1.0 | Stratified pages on one template; no scrolling or clipped visuals in the export. |
| 6 | Colour and accessibility | 0.5 | 1.0 | Alt text on all 111 visuals. AA contrast on status and change text. Simulated ΔE ≥ 26 (deuteranopia) on key pairs, with ▲▼ as a second cue. Phone layouts for every page. |
| 7 | Declutter, text, formatting | 0.5 | 1.0 | One unit system (₹ Cr, M, ₹ per seat-km); direct labels; one-line legends. |
| 8 | Interaction, navigation, devices | 0.5 | 1.0 | Route drill-through (tested on PNQ-BLR and BLR-BOM) with a dynamic headline. Route tooltip page. Page navigator. Market slicer synced across pages 1–3. Phone layouts. |
| 9 | Insight and action | 0.75 | 1.0 | Recommended plan of ₹2.95 Cr a year (4.6–4.9% of 2025 revenue across the two fare scenarios). Lever confidence shown. Backtest −0.5% vs a naive −4.9%. |
| 10 | Model and engineering | 0.75 | 1.0 | Best Practice Analyzer: 27 of 27 rules pass. 3 documented exceptions: the measure table, and two disconnected tables (Levers, Refresh Info). Changes: unused columns removed, fixed decimal instead of floating point, foreign keys hidden, keys marked, geographic data categories, IsAvailableInMdx off on hidden columns, DIVIDE everywhere, no BLANK-to-0 conversions, capitalised names, and descriptions on every visible table, column and measure (119 measures). DAX queries take 52–74 ms per visual. Generators rebuild everything. |
| | Gates applied | max 7 | none | No clipped text, misleading encodings or unreconciled numbers. |
| | **Total** | **6.5 / 10** | **10 / 10** | |

**What remains outside the rubric:**
- **Report-page tooltip:** synthetic hover in Desktop could not trigger it. Its configuration is identical to what Desktop writes; check it with a real mouse once.
- **BPA coverage:** the checker implements the core Microsoft BPA rules in Python, not the full Tabular Editor 2 rule file. Installing Tabular Editor and running the official rules would confirm the result independently.
