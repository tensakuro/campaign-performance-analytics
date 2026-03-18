# ============================================================
# STEP 1 — Exploratory Data Analysis (EDA)
# Campaign Performance Analytics & Sales Dashboard
# ============================================================

import numpy as np
import pandas as pd

# ── Load dataset ─────────────────────────────────────────────
# FIX 1: Don't parse_dates at load — it fails on mixed formats.
#         Parse explicitly after load for reliability.
df = pd.read_csv("data/sales_data.csv", encoding="latin-1")

# Explicit date parsing with error handling
for col in ["Order Date", "Ship Date"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

# ── Dataset Overview ─────────────────────────────────────────
print("=" * 60)
print("DATASET OVERVIEW")
print("=" * 60)

rows, cols = df.shape
print(f"\nTotal Records  : {rows:,}")
print(f"Total Columns  : {cols}")
print(f"\nColumns        : {df.columns.tolist()}")

# ── Data Types + Nulls ───────────────────────────────────────
print("\n" + "=" * 60)
print("DATA TYPES & NULL VALUES")
print("=" * 60)

nulls = df.isnull().sum()
summary_df = pd.DataFrame(
    {
        "Data Type": df.dtypes.astype(str),  # FIX 2: cast to str for clean print
        "Null Count": nulls,
        "Null %": (nulls / rows * 100).round(2),
        "Unique Val": df.nunique(),  # NEW: unique value count per column
    }
)
print(summary_df.to_string())  # FIX 2: .to_string() forces alignment

# ── Duplicate Check ──────────────────────────────────────────
# FIX 3: Always check duplicates in EDA — it's a resume bullet point
print("\n" + "=" * 60)
print("DUPLICATE CHECK")
print("=" * 60)

total_dupes = df.duplicated().sum()
print(f"Duplicate rows   : {total_dupes:,}")
print(f"Duplicate %      : {total_dupes / rows * 100:.2f}%")
if total_dupes > 0:
    print("⚠️  Duplicates found — will be removed in cleaning step.")
else:
    print("✅ No duplicates found.")

# ── Statistical Summary ──────────────────────────────────────
print("\n" + "=" * 60)
print("STATISTICAL SUMMARY")
print("=" * 60)

num_cols = [c for c in ["Sales", "Quantity", "Discount", "Profit"] if c in df.columns]

if num_cols:
    desc = df[num_cols].describe().round(2)
    print(desc.to_string())

    # FIX 4: Add skewness — shows if data is normally distributed
    # Highly skewed Sales/Profit = outliers present = needs cleaning
    print("\nSkewness (values > 1 or < -1 indicate skewed distribution):")
    skew = df[num_cols].skew().round(3)
    for col, val in skew.items():
        flag = "⚠️  Skewed" if abs(val) > 1 else "✅ Normal"
        print(f"  {col:<12}: {val:>7}  {flag}")

# ── Outlier Detection ────────────────────────────────────────
# FIX 5: IQR-based outlier detection — standard method, shows depth
print("\n" + "=" * 60)
print("OUTLIER DETECTION (IQR Method)")
print("=" * 60)

for col in ["Sales", "Profit"]:
    if col not in df.columns:
        continue
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = df[(df[col] < lower) | (df[col] > upper)]
    pct = len(outliers) / rows * 100
    print(
        f"{col:<8}: {len(outliers):>4} outliers ({pct:.1f}%)  "
        f"| Range: [{lower:,.1f} → {upper:,.1f}]"
    )

# ── Categorical Insights ─────────────────────────────────────
print("\n" + "=" * 60)
print("KEY CATEGORICAL COLUMNS")
print("=" * 60)


# FIX 6: Show values + counts, not raw array dump
def show_category(col, top_n=5):
    if col not in df.columns:
        print(f"  {col}: Not found")
        return
    uniq = df[col].nunique()
    top = df[col].value_counts().head(top_n)
    print(f"\n  {col} ({uniq} unique values):")
    for val, cnt in top.items():
        pct = cnt / rows * 100
        print(f"    {str(val):<25} {cnt:>5,} records  ({pct:.1f}%)")


show_category("Region")
show_category("Segment")
show_category("Category")
show_category("Ship Mode")

# Date range
if "Order Date" in df.columns:
    date_nulls = df["Order Date"].isna().sum()
    print(
        f"\n  Order Date Range : {df['Order Date'].min().date()} "
        f"→ {df['Order Date'].max().date()}"
    )
    print(f"  Date Parse Errors: {date_nulls}")

# ── Campaign Snapshot ────────────────────────────────────────
# FIX 7: Added profit margin + profit % — key business metrics
print("\n" + "=" * 60)
print("CAMPAIGN SNAPSHOT")
print("=" * 60)

total_sales = df["Sales"].sum()
total_profit = df["Profit"].sum()
avg_discount = df["Discount"].mean()
profit_margin = total_profit / total_sales * 100  # NEW
profit_per_ord = total_profit / df["Order ID"].nunique()  # NEW
total_orders = df["Order ID"].nunique()
total_customers = df["Customer ID"].nunique()

# FIX 8: Added campaign baseline comparison
campaign_orders = (df["Discount"] > 0).sum()
non_campaign_sales = df[df["Discount"] == 0]["Sales"].sum()
campaign_sales = df[df["Discount"] > 0]["Sales"].sum()

print(f"  Total Revenue       : ${total_sales:>12,.2f}")
print(f"  Total Profit        : ${total_profit:>12,.2f}")
print(f"  Overall Margin      : {profit_margin:>11.1f}%")  # NEW
print(f"  Avg Profit / Order  : ${profit_per_ord:>12,.2f}")  # NEW
print(f"  Avg Discount Rate   : {avg_discount:>11.1%}")
print(f"  Total Unique Orders : {total_orders:>12,}")
print(f"  Total Customers     : {total_customers:>12,}")
print(
    f"\n  Campaign Orders     : {campaign_orders:>12,}  "
    f"({campaign_orders/rows*100:.1f}% of all orders)"
)  # FIX 8
print(f"  Campaign Sales      : ${campaign_sales:>12,.2f}")
print(f"  Non-Campaign Sales  : ${non_campaign_sales:>12,.2f}")

# ── Data Quality Score ───────────────────────────────────────
# NEW: Summarise overall data quality — good talking point in interview
print("\n" + "=" * 60)
print("DATA QUALITY SCORE")
print("=" * 60)

null_pct = df.isnull().sum().sum() / (rows * cols) * 100
dupe_pct = total_dupes / rows * 100
quality = 100 - null_pct - dupe_pct
print(f"  Null  cell rate  : {null_pct:.2f}%")
print(f"  Duplicate row rate: {dupe_pct:.2f}%")
print(f"  Overall Quality  : {quality:.1f} / 100")
flag = "✅ Good" if quality > 95 else "⚠️  Needs cleaning"
print(f"  Status           : {flag}")

print("\n✅ EDA Complete — move to 02_cleaning.py")
