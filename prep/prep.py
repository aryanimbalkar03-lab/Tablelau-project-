"""
Credit Portfolio Risk & Operations Control Tower — Data Preparation
===================================================================
Downloads the LendingClub dataset (~2.26M loans, ~1.6 GB) from Kaggle,
selects and cleans 29 columns, engineers features (fico midpoint, term_months),
and outputs two CSVs for Tableau:
    1. loans_clean.csv   — main data source (~2.26M rows)
    2. dq_summary.csv    — data-quality summary (second Tableau source for D6)

Reconciliation: The script prints ROW_COUNT and TOTAL_FUNDED_AMT.
These two numbers MUST match between Python output and Tableau extract.

Usage:
    pip install -r requirements.txt
    python prep/prep.py
"""

import os
import sys
import time
import kagglehub
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────
# 1. Download dataset from Kaggle
# ─────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STEP 1: Downloading LendingClub dataset from Kaggle...")
print("=" * 70)

t0 = time.time()
path = kagglehub.dataset_download("wordsforthewise/lending-club")
print(f"  Download path: {path}")
print(f"  Download time: {time.time() - t0:.1f}s")

# Find the accepted loans CSV (kagglehub may nest files in subdirectories)
raw_csv = None

# Search recursively for the accepted CSV
for root, dirs, files in os.walk(path):
    for f in files:
        if "accepted" in f.lower() and f.lower().endswith(".csv"):
            raw_csv = os.path.join(root, f)
            break
    if raw_csv:
        break

# Fallback: try .csv.gz files
if raw_csv is None:
    for root, dirs, files in os.walk(path):
        for f in files:
            if "accepted" in f.lower() and f.lower().endswith(".csv.gz"):
                raw_csv = os.path.join(root, f)
                break
        if raw_csv:
            break

if raw_csv is None:
    print(f"ERROR: Could not find accepted loans CSV in {path}")
    print(f"  Files found: {os.listdir(path)}")
    sys.exit(1)

print(f"  Source file: {raw_csv}")
print(f"  File size: {os.path.getsize(raw_csv) / 1e9:.2f} GB")

# ─────────────────────────────────────────────────────────────────────
# 2. Load and clean data
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 2: Loading and cleaning data...")
print("=" * 70)

cols = [
    'id', 'loan_amnt', 'funded_amnt', 'term', 'int_rate', 'installment',
    'grade', 'sub_grade', 'home_ownership', 'annual_inc', 'verification_status',
    'issue_d', 'loan_status', 'purpose', 'addr_state', 'dti', 'delinq_2yrs',
    'fico_range_low', 'fico_range_high', 'open_acc', 'revol_util', 'out_prncp',
    'total_pymnt', 'total_rec_prncp', 'total_rec_int', 'total_rec_late_fee',
    'recoveries', 'last_pymnt_d', 'application_type'
]

t0 = time.time()
df = pd.read_csv(raw_csv, usecols=cols, low_memory=False)
print(f"  Loaded {len(df):,} rows in {time.time() - t0:.1f}s")

# Drop footer/summary rows (id is not numeric in those rows)
before = len(df)
df = df[pd.to_numeric(df['id'], errors='coerce').notna()]
print(f"  Dropped {before - len(df):,} non-data rows (footers)")

# ─────────────────────────────────────────────────────────────────────
# 3. Feature engineering
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 3: Engineering features...")
print("=" * 70)

# Parse dates
df['issue_date'] = pd.to_datetime(df['issue_d'], format='%b-%Y', errors='coerce')
df['last_pymnt_date'] = pd.to_datetime(df['last_pymnt_d'], format='%b-%Y', errors='coerce')

# Extract term in months
df['term_months'] = df['term'].str.extract(r'(\d+)').astype(float).astype('Int64')

# FICO midpoint
df['fico'] = (df['fico_range_low'] + df['fico_range_high']) / 2

# Drop raw columns that have been transformed
df = df.drop(columns=['term', 'issue_d', 'last_pymnt_d', 'fico_range_low', 'fico_range_high'])

print(f"  Columns after engineering: {len(df.columns)}")
print(f"  Date range: {df['issue_date'].min()} to {df['issue_date'].max()}")
print(f"  Terms: {df['term_months'].value_counts().to_dict()}")

# ─────────────────────────────────────────────────────────────────────
# 4. Data quality summary (for Dashboard 6)
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 4: Generating data quality summary...")
print("=" * 70)

dq = pd.DataFrame({
    'field': df.columns,
    'null_pct': (df.isna().mean() * 100).round(3).values,
    'dtype': df.dtypes.astype(str).values,
    'unique_count': df.nunique().values
})

# Count specific outliers
outlier_rules = {
    'dti': int(((df['dti'] < 0) | (df['dti'] > 60)).sum()) if 'dti' in df.columns else 0,
    'annual_inc': int((df['annual_inc'] <= 0).sum()) if 'annual_inc' in df.columns else 0,
    'revol_util': int((df['revol_util'] > 100).sum()) if 'revol_util' in df.columns else 0,
    'int_rate': int((df['int_rate'] <= 0).sum()) if 'int_rate' in df.columns else 0,
    'loan_amnt': int((df['loan_amnt'] <= 0).sum()) if 'loan_amnt' in df.columns else 0,
}
dq['outliers'] = dq['field'].map(outlier_rules).fillna(0).astype(int)

# Output path — data/ subdirectory
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(output_dir, exist_ok=True)

dq_path = os.path.join(output_dir, 'dq_summary.csv')
dq.to_csv(dq_path, index=False)
print(f"  Saved data quality summary: {dq_path}")
print(f"  Fields with >5% nulls: {(dq['null_pct'] > 5).sum()}")

# Show the DQ summary
print("\n  Data Quality Summary:")
print(dq.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────
# 5. Export cleaned data
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 5: Exporting cleaned data...")
print("=" * 70)

clean_path = os.path.join(output_dir, 'loans_clean.csv')
t0 = time.time()
df.to_csv(clean_path, index=False)
print(f"  Saved: {clean_path}")
print(f"  Export time: {time.time() - t0:.1f}s")
print(f"  File size: {os.path.getsize(clean_path) / 1e9:.2f} GB")

# ─────────────────────────────────────────────────────────────────────
# 6. RECONCILIATION NUMBERS (record these!)
# ─────────────────────────────────────────────────────────────────────
row_count = len(df)
total_funded = df['funded_amnt'].sum()

print("\n" + "=" * 70)
print("RECONCILIATION — RECORD THESE NUMBERS")
print("=" * 70)
print(f"  ROW COUNT       : {row_count:,}")
print(f"  TOTAL FUNDED $  : {total_funded:,.2f}")
print(f"  TOTAL LOAN AMT $: {df['loan_amnt'].sum():,.2f}")
print("=" * 70)
print()
print("These numbers MUST match in Tableau after creating the extract.")
print("Screenshot the Tableau totals and compare for the README.")
print()

# ─────────────────────────────────────────────────────────────────────
# 7. Quick data profile for reference
# ─────────────────────────────────────────────────────────────────────
print("DATA PROFILE:")
print(f"  Grades: {sorted(df['grade'].unique())}")
print(f"  Loan statuses: {df['loan_status'].value_counts().to_dict()}")
print(f"  States: {df['addr_state'].nunique()} unique")
print(f"  Purposes: {df['purpose'].nunique()} unique")
print(f"  FICO range: {df['fico'].min():.0f} - {df['fico'].max():.0f}")
print(f"  DTI range: {df['dti'].min():.1f} - {df['dti'].max():.1f}")
print(f"  Int rate range: {df['int_rate'].min():.2f} - {df['int_rate'].max():.2f}")
print()

# Save reconciliation to a text file for reference
recon_path = os.path.join(output_dir, 'reconciliation.txt')
with open(recon_path, 'w') as f:
    f.write("RECONCILIATION NUMBERS\n")
    f.write("=" * 40 + "\n")
    f.write(f"Row Count      : {row_count:,}\n")
    f.write(f"Total Funded $ : {total_funded:,.2f}\n")
    f.write(f"Total Loan Amt : {df['loan_amnt'].sum():,.2f}\n")
    f.write(f"Date Range     : {df['issue_date'].min()} to {df['issue_date'].max()}\n")
    f.write(f"Grades         : {sorted(df['grade'].unique())}\n")
    f.write(f"States         : {df['addr_state'].nunique()}\n")
    f.write(f"Purposes       : {df['purpose'].nunique()}\n")
    f.write(f"Loan Statuses  : {df['loan_status'].value_counts().to_dict()}\n")

print(f"Reconciliation saved: {recon_path}")
print("\nDone! Next: Open loans_clean.csv in Tableau and start building.")
