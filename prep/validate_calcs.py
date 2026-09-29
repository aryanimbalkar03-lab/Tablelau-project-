"""
Calculation Validation Script
=============================
Independently computes all key metrics in Python to validate against Tableau.
Run AFTER prep.py has generated loans_clean.csv.

Usage:
    python prep/validate_calcs.py

Output:
    Prints a validation table and saves docs/calc_validation.md
"""

import os
import sys
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
csv_path = os.path.join(data_dir, 'loans_clean.csv')

if not os.path.exists(csv_path):
    print(f"ERROR: {csv_path} not found. Run prep.py first.")
    sys.exit(1)

print("Loading loans_clean.csv...")
df = pd.read_csv(csv_path, low_memory=False)
df['issue_date'] = pd.to_datetime(df['issue_date'])
df['last_pymnt_date'] = pd.to_datetime(df['last_pymnt_date'], errors='coerce')
print(f"  Loaded {len(df):,} rows\n")

# ─────────────────────────────────────────────────────────────────────
# Replicate Tableau calculated fields
# ─────────────────────────────────────────────────────────────────────
CUTOFF = pd.Timestamp('2018-12-31')

DEFAULT_STATUSES = [
    'Charged Off',
    'Default',
    'Does not meet the credit policy. Status:Charged Off'
]
LIVE_STATUSES = [
    'Current',
    'In Grace Period',
    'Late (16-30 days)',
    'Late (31-120 days)'
]

# FLAGS
df['default_flag'] = df['loan_status'].isin(DEFAULT_STATUSES).astype(int)

# Calculate maturity using DateOffset (month-based arithmetic)
df['maturity_date'] = df.apply(
    lambda row: row['issue_date'] + pd.DateOffset(months=int(row['term_months']))
    if pd.notna(row['issue_date']) and pd.notna(row['term_months']) else pd.NaT,
    axis=1
)
df['mature_flag'] = (df['maturity_date'] <= CUTOFF).astype(int)
df['live_flag'] = df['loan_status'].isin(LIVE_STATUSES).astype(int)
df['live_exposure'] = np.where(df['live_flag'] == 1, df['out_prncp'], 0)

# NET LOSS
df['net_loss'] = np.where(
    df['default_flag'] == 1,
    df['funded_amnt'] - df['total_rec_prncp'] - df['recoveries'],
    0
)

# ─────────────────────────────────────────────────────────────────────
# Core Risk Metrics
# ─────────────────────────────────────────────────────────────────────
results = {}

# 1. Row Count
results['Row Count'] = len(df)

# 2. Total Funded $
results['Total Funded $'] = df['funded_amnt'].sum()

# 3. Default Rate (Mature)
mature = df[df['mature_flag'] == 1]
results['Default Rate (Mature)'] = mature['default_flag'].mean()

# 4. PD by Grade (LOD)
pd_by_grade = mature.groupby('grade')['default_flag'].mean()
results['PD Grade A'] = pd_by_grade.get('A', np.nan)
results['PD Grade B'] = pd_by_grade.get('B', np.nan)
results['PD Grade C'] = pd_by_grade.get('C', np.nan)
results['PD Grade D'] = pd_by_grade.get('D', np.nan)
results['PD Grade E'] = pd_by_grade.get('E', np.nan)
results['PD Grade F'] = pd_by_grade.get('F', np.nan)
results['PD Grade G'] = pd_by_grade.get('G', np.nan)

# 5. LGD (Portfolio)
defaults = df[df['default_flag'] == 1]
if len(defaults) > 0:
    total_loss_on_defaults = (defaults['funded_amnt'] - defaults['total_rec_prncp']).sum()
    total_recoveries = defaults['recoveries'].sum()
    lgd = 1 - (total_recoveries / total_loss_on_defaults) if total_loss_on_defaults != 0 else np.nan
else:
    lgd = np.nan
results['LGD (Portfolio)'] = lgd

# 6. Expected Loss $
# Map PD to each row by grade
df['pd_grade'] = df['grade'].map(pd_by_grade)
df['row_el'] = df['live_exposure'] * df['pd_grade'] * lgd
results['Expected Loss $'] = df['row_el'].sum()

# 7. EL Rate
total_live_exposure = df['live_exposure'].sum()
results['EL Rate'] = df['row_el'].sum() / total_live_exposure if total_live_exposure > 0 else np.nan
results['Live Exposure $'] = total_live_exposure

# 8. Weighted Coupon
results['Weighted Coupon'] = (df['int_rate'] * df['funded_amnt']).sum() / df['funded_amnt'].sum() / 100

# 9. Annualised Loss Rate (mature loans only)
mature_funded_years = (mature['funded_amnt'] * mature['term_months'] / 12).sum()
results['Annualised Loss Rate'] = mature['net_loss'].sum() / mature_funded_years if mature_funded_years > 0 else np.nan

# 10. Pricing Cushion
results['Pricing Cushion'] = results['Weighted Coupon'] - results['Annualised Loss Rate']

# 11. Stress Test at PD=2.0x, LGD+0.10
pd_mult = 2.0
lgd_addon = 0.10
df['stressed_el'] = df['live_exposure'] * np.minimum(1, df['pd_grade'] * pd_mult) * np.minimum(1, lgd + lgd_addon)
results['Stressed EL $ (2.0x, +0.10)'] = df['stressed_el'].sum()
results['Stress Delta $'] = results['Stressed EL $ (2.0x, +0.10)'] - results['Expected Loss $']

# 12. HHI by State
state_share = df.groupby('addr_state')['funded_amnt'].sum() / df['funded_amnt'].sum()
hhi = (state_share ** 2).sum()
results['HHI (State)'] = hhi
results['Top State'] = state_share.idxmax()
results['Top State Share'] = state_share.max()

# Top 5 states
top5 = state_share.nlargest(5)
results['Top 5 States Share'] = top5.sum()

# ─────────────────────────────────────────────────────────────────────
# Print Results
# ─────────────────────────────────────────────────────────────────────
print("=" * 70)
print("CALCULATION VALIDATION — PYTHON VALUES")
print("=" * 70)
print(f"{'Metric':<40} {'Value':>25}")
print("-" * 67)

for metric, value in results.items():
    if isinstance(value, float):
        if 'Rate' in metric or 'PD' in metric or 'LGD' in metric or 'Cushion' in metric or 'Share' in metric or 'EL Rate' == metric:
            print(f"  {metric:<38} {value:>24.6f}  ({value*100:.4f}%)")
        elif 'HHI' in metric:
            print(f"  {metric:<38} {value:>24.6f}")
        else:
            print(f"  {metric:<38} {value:>24,.2f}")
    elif isinstance(value, (int, np.integer)):
        print(f"  {metric:<38} {value:>24,}")
    else:
        print(f"  {metric:<38} {str(value):>24}")

print("=" * 70)

# ─────────────────────────────────────────────────────────────────────
# PD by Grade breakdown
# ─────────────────────────────────────────────────────────────────────
print("\nPD BY GRADE (Default Rate for Mature Loans):")
print("-" * 50)
for grade in sorted(pd_by_grade.index):
    count = len(mature[mature['grade'] == grade])
    defaults_in_grade = mature[(mature['grade'] == grade) & (mature['default_flag'] == 1)]
    print(f"  Grade {grade}: {pd_by_grade[grade]*100:.4f}%  "
          f"({len(defaults_in_grade):,} defaults / {count:,} mature loans)")

# ─────────────────────────────────────────────────────────────────────
# FICO x DTI mispricing analysis
# ─────────────────────────────────────────────────────────────────────
print("\nFICO x DTI ANALYSIS (Mature Loans):")
print("-" * 70)

# Create bands
df['fico_band'] = pd.cut(df['fico'], bins=[0, 660, 700, 740, 1000],
                         labels=['<660', '660-699', '700-739', '740+'], right=False)
df['dti_band'] = pd.cut(df['dti'], bins=[-1, 10, 20, 30, 100],
                        labels=['<10', '10-19', '20-29', '30+'], right=False)

mature_bands = df[df['mature_flag'] == 1].groupby(['fico_band', 'dti_band']).agg(
    default_rate=('default_flag', 'mean'),
    weighted_coupon_pct=('int_rate', 'mean'),  # approximate
    count=('default_flag', 'count'),
    funded=('funded_amnt', 'sum')
).reset_index()

print(f"{'FICO':<10} {'DTI':<10} {'DefRate':>10} {'AvgRate':>10} {'Cushion':>10} {'Count':>10}")
for _, row in mature_bands.iterrows():
    coupon = row['weighted_coupon_pct'] / 100
    cushion = coupon - row['default_rate']
    flag = " *** MISPRICED" if cushion < 0 else ""
    print(f"  {row['fico_band']:<8} {row['dti_band']:<8} "
          f"{row['default_rate']*100:>9.2f}% {row['weighted_coupon_pct']:>9.2f}% "
          f"{cushion*100:>9.2f}% {row['count']:>9,}{flag}")

# ─────────────────────────────────────────────────────────────────────
# Vintage Analysis
# ─────────────────────────────────────────────────────────────────────
print("\nVINTAGE ANALYSIS (Quarterly Default Rate — Mature Loans):")
print("-" * 60)

df['vintage'] = df['issue_date'].dt.to_period('Q')
vintage_dr = df[df['mature_flag'] == 1].groupby('vintage').agg(
    default_rate=('default_flag', 'mean'),
    count=('default_flag', 'count'),
    funded=('funded_amnt', 'sum')
).reset_index()

for _, row in vintage_dr.iterrows():
    bar = '#' * int(row['default_rate'] * 200)
    print(f"  {row['vintage']}  {row['default_rate']*100:>7.3f}%  {row['count']:>8,} loans  {bar}")

# ─────────────────────────────────────────────────────────────────────
# Pricing Cushion by Grade
# ─────────────────────────────────────────────────────────────────────
print("\nPRICING CUSHION BY GRADE (Mature Loans):")
print("-" * 60)

for grade in sorted(mature['grade'].unique()):
    g = mature[mature['grade'] == grade]
    coupon = (g['int_rate'] * g['funded_amnt']).sum() / g['funded_amnt'].sum() / 100
    loss_rate = g['net_loss'].sum() / (g['funded_amnt'] * g['term_months'] / 12).sum()
    cushion = coupon - loss_rate
    flag = " *** NEGATIVE CUSHION" if cushion < 0 else ""
    print(f"  Grade {grade}: Coupon={coupon*100:.2f}%  LossRate={loss_rate*100:.2f}%  "
          f"Cushion={cushion*100:.2f}%{flag}")

# ─────────────────────────────────────────────────────────────────────
# Find Break-Even PD Multiplier
# ─────────────────────────────────────────────────────────────────────
print("\nSTRESS TEST — BREAK-EVEN PD MULTIPLIER:")
print("-" * 60)
weighted_coupon = results['Weighted Coupon']
for mult in [x/10 for x in range(10, 31)]:
    stressed = df['live_exposure'] * np.minimum(1, df['pd_grade'] * mult) * lgd
    el_rate = stressed.sum() / total_live_exposure if total_live_exposure > 0 else 0
    cushion = weighted_coupon - el_rate
    marker = " <-- BREAK-EVEN" if abs(cushion) < 0.005 else ""
    if cushion < 0 and marker == "":
        marker = " <-- CUSHION GONE"
    print(f"  PD Mult={mult:.1f}x  StressedELRate={el_rate*100:.4f}%  "
          f"Cushion={cushion*100:.4f}%{marker}")
    if cushion < -0.02:
        break

# ─────────────────────────────────────────────────────────────────────
# Save to docs/calc_validation.md
# ─────────────────────────────────────────────────────────────────────
docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
os.makedirs(docs_dir, exist_ok=True)

md_path = os.path.join(docs_dir, 'calc_validation.md')

with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# Calculation Validation — Python vs Tableau\n\n")
    f.write("> This document independently validates every key metric.\n")
    f.write("> After building the Tableau workbook, fill in the Tableau column and confirm all values match.\n\n")

    f.write("## Reconciliation\n\n")
    f.write("| Metric | Python Value | Tableau Value | Match? |\n")
    f.write("|--------|-------------|---------------|--------|\n")
    f.write(f"| Row Count | {len(df):,} | *(fill in)* | |\n")
    f.write(f"| Total Funded $ | {df['funded_amnt'].sum():,.2f} | *(fill in)* | |\n\n")

    f.write("## Core Metrics\n\n")
    f.write("| Metric | Python Value | Tableau Value | Match? |\n")
    f.write("|--------|-------------|---------------|--------|\n")

    format_map = {
        'Default Rate (Mature)': lambda v: f"{v*100:.4f}%",
        'LGD (Portfolio)': lambda v: f"{v*100:.4f}%",
        'Expected Loss $': lambda v: f"${v:,.2f}",
        'EL Rate': lambda v: f"{v*100:.4f}%",
        'Live Exposure $': lambda v: f"${v:,.2f}",
        'Weighted Coupon': lambda v: f"{v*100:.4f}%",
        'Annualised Loss Rate': lambda v: f"{v*100:.4f}%",
        'Pricing Cushion': lambda v: f"{v*100:.4f}%",
        'HHI (State)': lambda v: f"{v:.6f}",
    }

    for metric in ['Default Rate (Mature)', 'LGD (Portfolio)', 'Expected Loss $',
                    'EL Rate', 'Live Exposure $', 'Weighted Coupon',
                    'Annualised Loss Rate', 'Pricing Cushion', 'HHI (State)']:
        fmt = format_map.get(metric, lambda v: f"{v}")
        f.write(f"| {metric} | {fmt(results[metric])} | *(fill in)* | |\n")

    f.write("\n## PD by Grade\n\n")
    f.write("| Grade | Python PD | Tableau PD | Match? |\n")
    f.write("|-------|----------|-----------|--------|\n")
    for grade in sorted(pd_by_grade.index):
        f.write(f"| {grade} | {pd_by_grade[grade]*100:.4f}% | *(fill in)* | |\n")

    f.write("\n## Pricing Cushion by Grade\n\n")
    f.write("| Grade | Coupon | Loss Rate | Cushion | Negative? |\n")
    f.write("|-------|--------|-----------|---------|----------|\n")
    for grade in sorted(mature['grade'].unique()):
        g = mature[mature['grade'] == grade]
        coupon = (g['int_rate'] * g['funded_amnt']).sum() / g['funded_amnt'].sum() / 100
        loss_rate = g['net_loss'].sum() / (g['funded_amnt'] * g['term_months'] / 12).sum()
        cushion = coupon - loss_rate
        neg = "⚠️ YES" if cushion < 0 else "No"
        f.write(f"| {grade} | {coupon*100:.2f}% | {loss_rate*100:.2f}% | {cushion*100:.2f}% | {neg} |\n")

    f.write("\n## Top 5 States by Funded Amount\n\n")
    f.write("| Rank | State | Share | Cumulative |\n")
    f.write("|------|-------|-------|------------|\n")
    cum = 0
    for i, (state, share) in enumerate(top5.items(), 1):
        cum += share
        f.write(f"| {i} | {state} | {share*100:.2f}% | {cum*100:.2f}% |\n")

    f.write(f"\n**HHI (State)**: {hhi:.6f}\n")

    f.write("\n---\n*Generated by validate_calcs.py*\n")

print(f"\nValidation report saved: {md_path}")
print("\nDone! Compare these values with your Tableau workbook.")
