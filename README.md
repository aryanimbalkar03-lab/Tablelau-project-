# Credit Portfolio Risk & Operations Control Tower (Tableau)

[**Live Dashboard on Tableau Public**](https://public.tableau.com/views/CreditPortfolioRiskOperationsControlTower/ExecutiveControlTower?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)

A six-dashboard Tableau suite on 2,260,668 LendingClub loans (2007 to 2018 Q4). It turns a raw loan tape into one governed set of risk and operations metrics: expected loss, vintage performance, pricing adequacy, concentration, stress testing, delinquency monitoring and a data-quality layer.

## Problem
Loan operations and risk teams get static monthly reports. They cannot see which vintages are deteriorating, whether pricing covers realised loss, how concentrated the book is, how much expected loss moves under stress, or how trustworthy the data is. Each team also defines 'default rate' differently.
Objective: one governed data model with one definition per KPI, feeding self-serve dashboards for executives, risk analysts and operations.

## Data and scope
*   Source: public LendingClub accepted-loans file (accepted_2007_to_2018Q4.csv), loaded with kagglehub.
*   prep/prep.py keeps 29 columns, removes footer rows, parses dates, derives term_months and a FICO midpoint, and writes loans_clean.csv and dq_summary.csv.
*   Real consumer-loan data, not a bank's internal data. The snapshot ends 31 Dec 2018.

## Metric definitions (one definition per KPI)
*   **Default:** loan_status is Charged Off, Default, or 'Does not meet the credit policy'
*   **Mature loan:** Issue date + term is on or before 31 Dec 2018. Depends only on issue date and term, never on outcome.
*   **Default Rate (Mature):** Defaulted loans / loans, mature loans only
*   **PD by Grade:** Default Rate (Mature) at grade level
*   **LGD (Portfolio):** 1 - recoveries / (funded - principal repaid), over all defaulted loans
*   **Live exposure:** Outstanding principal of loans that are Current, In Grace Period, Late
*   **Expected Loss:** Sum of live exposure * PD by Grade * LGD. A lifetime expected loss on the remaining balance.
*   **EL Rate:** Expected Loss / live exposure (lifetime, not annual)
*   **Weighted Coupon:** Funded-weighted interest rate, mature loans
*   **Annualised Loss Rate:** Net loss on mature defaulted loans / sum(funded * term in years), mature loans
*   **Pricing Cushion:** Weighted Coupon - Annualised Loss Rate. Gross: excludes funding cost, operating cost and prepayment.
*   **Break-even Multiplier:** Weighted Coupon / Annualised Loss Rate
*   **Stressed EL:** Sum of live exposure * min(1, PD * multiplier) * min(1, LGD + add-on)
*   **HHI:** Sum of (state share)^2 * 10,000, on the selected basis

## Dashboards
*   **Executive Control Tower:** KPI strip, quarterly issuance with the 36-month default rate, View By toggle (Grade / Purpose / State).
*   **Vintage and Cohort:** vintage x grade heatmap (36-month loans), moving average, default rate by term.
*   **Pricing vs Loss:** coupon vs annualised loss by grade, pricing cushion, FICO x DTI matrix, coupon vs default scatter.
*   **Geography and Concentration:** state map, Pareto, HHI and top-5 share, with a basis toggle.
*   **Stress Test and Delinquency Watchlist:** PD multiplier and LGD add-on controls, stressed expected loss, delinquency heatmap, top-20 state x sub-grade watchlist.
*   **Data Quality and Definitions:** null % by field, outlier counts, metric dictionary, live reconciliation.

## Validation
Every key metric is computed independently in Python and compared with Tableau.

| Metric | Python | Tableau | Match |
| :--- | :--- | :--- | :--- |
| Row count | 2,260,668 | 2,260,668 | PASS |
| Total funded | $34.0B | $34.0B | PASS |
| Default Rate (Mature) | 14.86% | 14.86% | PASS |
| PD Grade A / Grade G | 5.50% / 37.35% | 5.50% / 37.35% | PASS |
| LGD (Portfolio) | 89.18% | 89.18% | PASS |
| Expected Loss | $1.3B | $1.3B | PASS |
| Weighted Coupon (mature) | 12.53% | 12.53% | PASS |
| Annualised Loss Rate | 2.44% | 2.44% | PASS |
| Pricing Cushion | 10.09% | 10.09% | PASS |
| HHI (funded / live) | 527.6 / 507.1 | 527.6 / 507.1 | PASS |

## Key findings
*   The gross pricing cushion is positive in every grade, from **+6.46%** (A) to **+18.19%** (F), and **+10.09%** for the portfolio.
*   Annualised loss would need to rise about **5.13x** before the gross cushion reaches zero.
*   Vintage view (36-month loans): 2007 shows **29.56%** but on only a tiny cohort of loans. Post-2014 originations stabilized near 14-15%.
*   Concentration: top-5 states hold **41.9%** of funded volume and **41.26%** of live exposure. HHI is **527.6** (funded) and **507.1** (live). This is low concentration.
*   Delinquency and stress: delinquent loans are **4.04%** of the live book. At PD x1.5 and LGD +5 pp, expected loss moves from **$1.3B** to **$2.05B** (+58.4%).
*   Lowest-cushion FICO x DTI cell: The 660-699 FICO band combined with >30% DTI carries disproportionate lifetime risk.

## Limitations
*   Snapshot data: no monthly performance panel, so no roll rates or age-based vintage curves.
*   PD is the observed lifetime default rate of mature cohorts (originated 2007 to 2015 for 36-month loans). It is applied to a live book that is mostly 2016 to 2018 originations. Live loans are also survivors, so lifetime PD on their remaining balance probably overstates risk.
*   LGD is one portfolio-level figure; recoveries on recent charge-offs may be incomplete.
*   Pricing cushion is gross of funding cost, operating cost and prepayment.
*   Tableau Public allows extracts only, with no live connections or row-level security.

## Reproduce
1. pip install -r requirements.txt
2. python prep/prep.py
3. Connect Tableau to loans_clean.csv (extract) and dq_summary.csv, and rebuild from docs/tableau_build_guide.md.
4. python prep/validate_calcs.py and python prep/readme_numbers.py data/loans_clean.csv

