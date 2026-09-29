# Metric Dictionary — Credit Portfolio Risk Control Tower

## 1. Overview
This dictionary defines every metric used in the Credit Portfolio Risk & Operations Control Tower. Each metric has a single, governed definition. All teams must use these definitions to ensure consistency across reports.

## 2. Flags (Binary Indicators)

| Attribute | Detail |
|-----------|--------|
| **Name** | Default Flag |
| **Type** | Row-level calculated field |
| **Formula** | `IF [loan_status] IN ("Charged Off","Default","Does not meet the credit policy. Status:Charged Off") THEN 1 ELSE 0 END` |
| **Returns** | 0 or 1 |
| **Business Meaning** | Identifies loans that have failed to meet their repayment obligations. A loan is flagged as default if it has been charged off or explicitly defaulted. |
| **Used In** | D1 (Executive), D2 (Vintage), D3 (Pricing), D5 (Watchlist) |
| **Depends On** | loan_status (raw field) |
| **Known Limits** | Some policy-exception statuses may not be captured |

| Attribute | Detail |
|-----------|--------|
| **Name** | Mature Flag |
| **Type** | Row-level calculated field |
| **Formula** | `IF DATEADD('month',[term_months],[issue_date]) <= #2018-12-31# THEN 1 ELSE 0 END` |
| **Returns** | 0 or 1 |
| **Business Meaning** | Identifies loans that have reached the end of their planned term. **CRITICAL:** This flag prevents survivorship bias. By looking only at mature loans when calculating default rates, we ensure we are not artificially lowering the default rate by including young loans that haven't had time to default yet. |
| **Used In** | D2, D3 |
| **Depends On** | term, issue_d |
| **Known Limits** | Requires accurate issue dates and terms; reduces the sample size of recent vintages. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Live Flag |
| **Type** | Row-level calculated field |
| **Formula** | `IF [loan_status] IN ("Current", "In Grace Period", "Late (16-30 days)", "Late (31-120 days)") THEN 1 ELSE 0 END` |
| **Returns** | 0 or 1 |
| **Business Meaning** | Identifies loans that are currently active and have not yet reached a terminal status (like fully paid or charged off). |
| **Used In** | D5 |
| **Depends On** | loan_status |
| **Known Limits** | "Late" statuses are considered live until officially charged off. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Live Exposure |
| **Type** | Row-level calculated field |
| **Formula** | `IF [Live Flag]=1 THEN [out_prncp] ELSE 0 END` |
| **Returns** | Currency ($) |
| **Business Meaning** | The outstanding principal balance on loans that are currently active. This is the actual amount of money currently at risk in the portfolio. |
| **Used In** | D1, D5 |
| **Depends On** | Live Flag, out_prncp |
| **Known Limits** | Does not account for potential future interest, only outstanding principal. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Vintage |
| **Type** | Dimension (Date) |
| **Formula** | `DATETRUNC('quarter', [issue_d])` or `DATETRUNC('year', [issue_d])` |
| **Returns** | Date |
| **Business Meaning** | Grouping of loans based on the time period they were issued (e.g., Q1 2018, Q2 2018). Tracking by vintage allows for apples-to-apples performance comparisons over time, rather than mixing old and new loans. |
| **Used In** | D2 |
| **Depends On** | issue_d |
| **Known Limits** | None |

## 3. Core Risk Metrics

| Attribute | Detail |
|-----------|--------|
| **Name** | Default Rate (Mature) |
| **Type** | Aggregate calculated field |
| **Formula** | `SUM(IIF([Mature Flag]=1,[Default Flag],0)) / SUM(IIF([Mature Flag]=1,1,0))` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | The percentage of loans that have completed their full term and ended in default. By restricting to mature loans only, this metric avoids counting loans that are still active and haven't had the chance to default yet (survivorship bias). |
| **Used In** | D1, D2, D3 |
| **Depends On** | Mature Flag, Default Flag |
| **Known Limits** | Excludes immature loans; may underrepresent recent vintages. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Net Loss $ |
| **Type** | Aggregate calculated field |
| **Formula** | `IF [Default Flag]=1 THEN [funded_amnt]-[total_rec_prncp]-[recoveries] ELSE 0 END` |
| **Returns** | Currency ($) |
| **Business Meaning** | The actual dollar amount lost on defaulted loans, calculated as the original funded amount minus principal recovered and any additional recoveries (e.g., from collections). Only calculated for loans that actually defaulted. |
| **Used In** | D1, D3 |
| **Depends On** | Default Flag, funded_amnt, total_rec_prncp, recoveries |
| **Known Limits** | Recovery data may be incomplete for recently charged-off loans. |

| Attribute | Detail |
|-----------|--------|
| **Name** | PD by Grade (LOD) |
| **Type** | Level of Detail (LOD) Expression |
| **Formula** | `{ FIXED [grade] : SUM(IIF([Mature Flag]=1,[Default Flag],0)) / SUM(IIF([Mature Flag]=1,1,0)) }` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | Probability of Default (PD). The historical default rate fixed at the loan Grade level (A, B, C, etc.). In plain English, a FIXED LOD means Tableau calculates the default rate for each grade exactly once, and attaches that overall average to every individual loan within that grade, regardless of how the view is filtered. |
| **Used In** | Risk calculations |
| **Depends On** | grade, Default Rate (Mature) |
| **Known Limits** | Assumes historical PD by grade is perfectly predictive of future PD. |

| Attribute | Detail |
|-----------|--------|
| **Name** | LGD (Portfolio, LOD) |
| **Type** | Level of Detail (LOD) Expression |
| **Formula** | `{ FIXED : 1 - SUM(IIF([Default Flag]=1,[recoveries],0)) / SUM(IIF([Default Flag]=1,[funded_amnt]-[total_rec_prncp],0)) }` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | Loss Given Default (LGD). Simply put: when a loan defaults, what percentage of the loan amount do we actually lose? This portfolio-wide LOD calculates a single average LGD across the entire dataset to use as a baseline assumption. |
| **Used In** | Risk calculations |
| **Depends On** | Default Flag, Net Loss $, funded_amnt |
| **Known Limits** | A single portfolio average might obscure variations in recovery rates between different segments. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Row EL |
| **Type** | Row-level calculated field |
| **Formula** | `[Live Exposure] * [PD by Grade (LOD)] * [LGD (Portfolio, LOD)]` |
| **Returns** | Currency ($) |
| **Business Meaning** | Expected Loss (EL). This represents the anticipated dollar loss for each individual loan. It follows the standard banking formula: Expected Loss = Probability of Default (PD) × Loss Given Default (LGD) × Exposure at Default (EAD, represented here by the funded amount). |
| **Used In** | D1, D3, D4 |
| **Depends On** | PD by Grade (LOD), LGD (Portfolio, LOD), funded_amnt |
| **Known Limits** | Heavily dependent on the accuracy of the historical PD and LGD assumptions. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Expected Loss $ |
| **Type** | Aggregate calculated field |
| **Formula** | `SUM([Row EL])` |
| **Returns** | Currency ($) |
| **Business Meaning** | The total anticipated dollar loss for a group of loans (e.g., a specific segment, vintage, or the whole portfolio). |
| **Used In** | D1, D2, D3, D4, D5 |
| **Depends On** | Row EL |
| **Known Limits** | See Row EL limits. |

| Attribute | Detail |
|-----------|--------|
| **Name** | EL Rate |
| **Type** | Aggregate calculated field |
| **Formula** | `[Expected Loss $] / SUM([funded_amnt])` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | The Expected Loss expressed as a percentage of the total funded amount. It allows us to compare expected losses across segments of different sizes. |
| **Used In** | D3, D4 |
| **Depends On** | Expected Loss $, funded_amnt |
| **Known Limits** | See Row EL limits. |

## 4. Pricing Adequacy Metrics

| Attribute | Detail |
|-----------|--------|
| **Name** | Weighted Coupon |
| **Type** | Aggregate calculated field |
| **Formula** | `SUM([int_rate] * [funded_amnt]) / SUM([funded_amnt])` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | To a non-technical person: this is the average interest rate we are charging our borrowers, but it gives more weight to larger loans. A $100k loan at 10% impacts this metric much more than a $1k loan at 20%. |
| **Used In** | D3 |
| **Depends On** | int_rate, funded_amnt |
| **Known Limits** | Assumes interest rate stays fixed and principal is fully outstanding. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Annualised Loss Rate |
| **Type** | Aggregate calculated field |
| **Formula** | `[EL Rate] / AVG([term_months]/12)` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | Converts our total expected lifetime loss into a yearly rate. If a 3-year loan has an expected loss of 6% over its lifetime, the annualized loss rate is 2% per year. This makes losses directly comparable to the annual interest rate (coupon). |
| **Used In** | D3 |
| **Depends On** | EL Rate, term (converted to months) |
| **Known Limits** | Assumes losses occur evenly over the life of the loan. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Pricing Cushion |
| **Type** | Aggregate calculated field |
| **Formula** | `[Weighted Coupon] - [Annualised Loss Rate]` |
| **Returns** | Decimal (format as %) |
| **Business Meaning** | The buffer between what we earn and what we expect to lose. It's the profit margin on credit risk. If we earn 10% in interest but expect 3% in annual losses, our cushion is 7%. A negative cushion means we are mathematically guaranteed to lose money. |
| **Used In** | D3 |
| **Depends On** | Weighted Coupon, Annualised Loss Rate |
| **Known Limits** | Does not account for operational costs or cost of capital. |

## 5. Stress Testing Metrics

The stress testing framework utilizes two parameters to simulate adverse economic conditions:
- **PD Multiplier:** Simulates an increase in default probability. Ranges from 1.0 (baseline) to 3.0 (300% increase), default is 1.0.
- **LGD Add-on:** Simulates a decrease in recovery rates (meaning higher loss given default). Ranges from 0 (baseline) to 0.20 (+20% absolute increase to LGD), default is 0.

| Attribute | Detail |
|-----------|--------|
| **Name** | Row Stressed EL |
| **Type** | Row-level calculated field |
| **Formula** | `([PD by Grade (LOD)] * [PD Multiplier Parameter]) * ([LGD (Portfolio, LOD)] + [LGD Add-on Parameter]) * [funded_amnt]` |
| **Returns** | Currency ($) |
| **Business Meaning** | The expected loss for an individual loan under the hypothetical stressed conditions defined by the user's parameter selections. |
| **Used In** | D1 (What-If Analysis) |
| **Depends On** | PD, LGD, Parameters, funded_amnt |
| **Known Limits** | Theoretical scenario modelling. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Stressed EL $ |
| **Type** | Aggregate calculated field |
| **Formula** | `SUM([Row Stressed EL])` |
| **Returns** | Currency ($) |
| **Business Meaning** | The total expected dollar loss for the portfolio under the stress scenario. |
| **Used In** | D1 |
| **Depends On** | Row Stressed EL |
| **Known Limits** | Same as Row Stressed EL. |

| Attribute | Detail |
|-----------|--------|
| **Name** | Stress Delta $ |
| **Type** | Aggregate calculated field |
| **Formula** | `[Stressed EL $] - [Expected Loss $]` |
| **Returns** | Currency ($) |
| **Business Meaning** | In plain English: "If defaults increase by 2x and recovery rates drop by 10 percentage points, how much more would we lose compared to our baseline expectation?" This isolates the exact financial impact of the stress scenario. |
| **Used In** | D1 |
| **Depends On** | Stressed EL $, Expected Loss $ |
| **Known Limits** | Depends heavily on parameter inputs. |

## 6. Segmentation Bands

| Attribute | Detail |
|-----------|--------|
| **Name** | FICO Band |
| **Type** | Dimension (Group or Calc) |
| **Business Meaning** | FICO scores are standard consumer credit scores. We bucket them (e.g., <600, 600-650, 650-700) to create manageable segments for analysis. It matters because it's a primary indicator of borrower creditworthiness at origin. |
| **Used In** | D3, D5 |

| Attribute | Detail |
|-----------|--------|
| **Name** | DTI Band |
| **Type** | Dimension (Group or Calc) |
| **Business Meaning** | Debt-to-Income (DTI) ratio measures what percentage of a borrower's income goes toward debt payments. We bucket it (e.g., <10%, 10-20%, 20%+) to assess affordability. High DTI means the borrower has less financial flexibility and higher risk of default. |
| **Used In** | D3, D5 |

| Attribute | Detail |
|-----------|--------|
| **Name** | Delinquency Bucket |
| **Type** | Dimension (Group or Calc based on loan_status) |
| **Business Meaning** | Stages of late payment (Current, 16-30 days late, 31-120 days late). It tracks the migration of loans from healthy to defaulted, providing early warning signals for future losses. |
| **Used In** | D5 |

## 7. Concentration Metrics

| Attribute | Detail |
|-----------|--------|
| **Name** | State Share |
| **Type** | Table Calculation |
| **Business Meaning** | What percentage of our total loans exist in a specific state. It highlights geographic concentration risk. |
| **Used In** | D4 |

| Attribute | Detail |
|-----------|--------|
| **Name** | HHI |
| **Type** | Table Calculation |
| **Business Meaning** | Herfindahl-Hirschman Index (HHI) measures concentration. In plain English: if all our loans were in one single state, HHI would be 1 (maximum risk). If our loans were perfectly and equally spread across all 50 states, HHI would be close to 0 (minimum risk). |
| **Used In** | D4 |

| Attribute | Detail |
|-----------|--------|
| **Name** | Cum % (Pareto) |
| **Type** | Table Calculation |
| **Business Meaning** | Applies the 80/20 rule to our portfolio. By sorting states from largest to smallest and calculating a running sum of their share, we can quickly see if, for example, 80% of our risk is concentrated in just 20% of the states. |
| **Used In** | D4 |

| Attribute | Detail |
|-----------|--------|
| **Name** | QoQ % |
| **Type** | Table Calculation |
| **Business Meaning** | Quarter-over-Quarter growth. It measures how much a metric (like issuance volume or default rate) changed compared to the immediately preceding quarter, highlighting momentum and trends. |
| **Used In** | D2 |

## 8. Table Calculation Reference

| Calc | Type | Addressing | Partitioning | Used In |
|------|------|-----------|-------------|--------|
| State Share | TOTAL | addr_state | (none) | D4 |
| HHI | WINDOW_SUM | addr_state | (none) | D4 |
| Cum % (Pareto) | RUNNING_SUM | sorted dimension | (none) | D4 |
| QoQ % | LOOKUP | Vintage (quarter) | (none) | D2 |
| 4-Qtr Moving Avg | WINDOW_AVG | Vintage (quarter) | (none) | D2 |

## 9. Parameters

| Parameter | Type | Range | Step | Default | Controls |
|-----------|------|-------|------|---------|----------|
| PD Multiplier | Float | 1.0 – 3.0 | 0.1 | 1.0 | Stress testing EL |
| LGD Add-on | Float | 0 – 0.20 | 0.01 | 0 | Stress testing EL |
| View By | String (List) | Grade, Purpose, State | — | Grade | D1 breakdown toggle |
| Metric Selector | String (List) | Funded $, EL Rate | — | Funded $ | D4 map colour |

## 10. Data Quality Fields (from dq_summary.csv)

| Field | Description |
|-------|------------|
| field | Column name from loans_clean.csv |
| null_pct | Percentage of null values (0-100) |
| outliers | Count of values outside expected range |
