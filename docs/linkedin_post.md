# LinkedIn post: AirlineDataAnalysis-PBI

**Attach, in this order:**
1. `docs/key_insights.png` (portrait, shows best in the feed)
2. `docs/approach_diagram.png`
3. `docs/dashboard/01_network_routes.png`
4. `docs/dashboard/02_demand_trends.png`
5. `docs/dashboard/03_kpi_rask.png`
6. `docs/dashboard/05_forecast_levers.png`

Replace `<GitHub link>` before posting. About 2,200 characters, under LinkedIn's 3,000 limit.

---

## Post text (copy from here)

Revenue up 71%. Passengers up only 25%. That gap was the whole story in 40,175 flights.

My second Power BI project: an airline network of 179 routes and 38 airports, January 2024 to May 2025. I set three questions:
1. Which routes and airports really drive the network?
2. How is demand moving, 2025 vs 2024?
3. What one KPI shows how well capacity turns into revenue?

First, the audit. 14% of flights carried another route's distance. Pune to Mumbai was recorded as 1,138 km (that's Delhi to Mumbai; the real answer is 124). I rebuilt every distance from airport coordinates before calculating a single per-km number. Python and Power BI now agree on every total, down to the last seat-km.

What the data said:

💸 Growth was price-led. Fares stepped up 39% from November 2024, and load factor still rose from 57.4% to 60.5%. Demand didn't flinch at the price rise.

📍 Pune is the network. 31% of revenue departs PNQ, and 86% of flights touch Pune, Mumbai or Bengaluru. 45 of 179 routes make 80% of revenue.

🎯 53 "star" routes carry 40% of revenue. 48 routes trail the network on both load factor and revenue per seat-km (19% of revenue), led by Bengaluru–Mumbai and Delhi–Goa.

✈️ International is 4% of flights and 7% of revenue, but planes fly 49% full vs 59% domestic.

📅 July to October is the soft season. Weekday barely matters: ±1.5%.

The KPI: RASK, revenue per available seat-km = load factor × yield. It's the airline industry's standard for "did we earn on the capacity we flew?" 2025 so far: ₹0.176, up 15% and on target, with higher yield explaining ~90% of the gain.

Forecast for 2025 (passengers backtested within 0.5%): about ₹64 Cr of revenue if fares hold, ₹60 Cr if they settle.

The levers, sized on the last 12 months:
→ Move capacity off the weakest routes: +₹1.4 Cr a year
→ 5% fare rise on full but low-earning routes: +₹0.7 Cr
→ Lift international load factor halfway to domestic: +₹0.5 Cr

Lesson from project two: a per-km KPI is only as good as its kilometres. Check the denominator first.

Built with Power BI (DAX, Power Query, 5 report pages) and Python (pandas, scipy, statsmodels).

Full project and notebooks: <GitHub link>

What's the first metric you'd sanity-check in an airline dataset?

#PowerBI #DataAnalytics #DAX #Python #AviationAnalytics #Forecasting #BusinessIntelligence #DataQuality

---

## Shorter alternative (about 850 characters)

Revenue +71%, passengers +25%: in 40,175 airline flights, the gap was the story.

Fares rose 39% from November 2024 and planes still got fuller (57.4% → 60.5%).

Pune drives 31% of revenue. 53 star routes earn 40%, while 48 routes trail on both load factor and revenue per seat-km.

Before any of that: 14% of flights carried another route's distance (Pune–Mumbai listed as 1,138 km). I rebuilt them from airport coordinates, so the per-km KPI (RASK) is actually right: ₹0.176, +15%, on target.

2025 outlook: about ₹64 Cr if fares hold. Biggest lever: move capacity off the weakest routes, +₹1.4 Cr a year.

Project two in Power BI + Python: <GitHub link>

#PowerBI #DataAnalytics #Python #AviationAnalytics
