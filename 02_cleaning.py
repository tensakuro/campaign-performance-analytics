# ============================================================
# STEP 2 — Data Cleaning & Preparation
# Campaign Performance Analytics & Sales Dashboard
# ============================================================

import pandas as pd
import numpy as np

# ── Load raw data ─────────────────────────────────────────────
df = pd.read_csv("data/sales_data.csv", encoding="latin-1")

print("=" * 60)
print("DATA CLEANING REPORT")
print("=" * 60)

rows_before = len(df)
print(f"Records BEFORE cleaning: {rows_before:,}")

# ── 1. Standardize column names FIRST ────────────────────────
# Must happen before EVERYTHING else — all steps below use
# clean underscore names
# Replace BOTH spaces and hyphens with underscores
df.columns = (
    df.columns
      .str.strip()
      .str.replace(" ", "_")
      .str.replace("-", "_")   # ← fixes Sub-Category → Sub_Category
) 
print(f"\n✅ Column names standardized.")
print(f"   Columns: {df.columns.tolist()}")

# ── 2. Fix numeric data types ─────────────────────────────────
# Some CSVs export Sales as "$1,234.56" — strip symbols first
for col in ["Sales", "Profit", "Discount", "Quantity"]:
    if col in df.columns:
        df[col] = (
            df[col].astype(str)
                   .str.replace(r"[\$,]", "", regex=True)
                   .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

print("✅ Numeric columns type-enforced.")

# ── 3. Parse dates — FIXED ───────────────────────────────────
# ROOT CAUSE OF THE ERROR:
#   Superstore CSV uses MM/DD/YYYY (e.g. "11/08/2016")
#   dayfirst=True misreads this — treats 11 as day, 08 as month
#   Result: column stays as 'object' dtype → subtraction crashes
#
# FIX: Auto-detect format from first value, parse with exact format.

def parse_date_column(series, col_name):
    """
    Auto-detects date format from first valid value,
    then parses entire column with that exact format.
    Falls back to inferred parsing if detection fails.
    """
    sample = series.dropna().iloc[0] if not series.dropna().empty else None

    if sample is None:
        print(f"   ⚠️  {col_name}: all values null — skipping.")
        return pd.to_datetime(series, errors="coerce")

    sample = str(sample).strip()

    # Detect format from sample value
    fmt = None
    if "/" in sample:
        parts = sample.split("/")
        if len(parts) == 3:
            fmt = "%m/%d/%Y" if len(parts[2]) == 4 else "%m/%d/%y"
    elif "-" in sample:
        parts = sample.split("-")
        fmt = "%Y-%m-%d" if len(parts[0]) == 4 else "%d-%m-%Y"

    # Try exact format first (fastest + most reliable)
    if fmt:
        parsed    = pd.to_datetime(series, format=fmt, errors="coerce")
        fail_rate = parsed.isna().mean()

        if fail_rate <= 0.05:
            print(f"   ✅ {col_name}: format='{fmt}' | "
                  f"nulls: {parsed.isna().sum()}")
            return parsed
        else:
            print(f"   ⚠️  {col_name}: format '{fmt}' had "
                  f"{fail_rate:.0%} failures — trying inferred parsing.")

    # Fallback: try common formats one by one
    # infer_datetime_format was removed in pandas 2.2+
    fallback_formats = [
        "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d",
        "%d-%m-%Y", "%Y/%m/%d", "%d-%b-%Y",
        "%m-%d-%Y", "%b %d, %Y",
    ]
    for fallback_fmt in fallback_formats:
        parsed     = pd.to_datetime(series, format=fallback_fmt, errors="coerce")
        null_count = parsed.isna().sum()
        if null_count / len(series) <= 0.05:   # less than 5% failed
            print(f"   ✅ {col_name}: fallback format='{fallback_fmt}' | "
                  f"nulls: {null_count}")
            return parsed

    # Last resort — let pandas guess with no format hint
    parsed     = pd.to_datetime(series, errors="coerce")
    null_count = parsed.isna().sum()
    status     = "✅" if null_count == 0 else f"⚠️  {null_count} nulls"
    print(f"   {status} {col_name}: last-resort parse | nulls: {null_count}")
    return parsed


print("\n── Parsing dates ──")
for col in ["Order_Date", "Ship_Date"]:
    if col in df.columns:
        df[col] = parse_date_column(df[col], col)

# Confirm dtypes — must be datetime64, not object
print("\n── Date dtype confirmation ──")
for col in ["Order_Date", "Ship_Date"]:
    if col in df.columns:
        dtype = df[col].dtype
        ok    = "✅" if "datetime" in str(dtype) else "❌ STILL STRING — check CSV"
        print(f"   {col}: {dtype}  {ok}")
        if "datetime" in str(dtype) and df[col].notna().any():
            print(f"   Sample: {df[col].dropna().iloc[0]}")

# ── 4. Feature engineering ────────────────────────────────────
# Use dtype check — never assume .dt is available
print("\n── Feature Engineering ──")

order_is_dt = pd.api.types.is_datetime64_any_dtype(df["Order_Date"])
ship_is_dt  = pd.api.types.is_datetime64_any_dtype(df["Ship_Date"])

if order_is_dt:
    df["Order_Year"]       = df["Order_Date"].dt.year
    df["Order_Month"]      = df["Order_Date"].dt.month
    df["Order_Month_Name"] = df["Order_Date"].dt.strftime("%b")
    df["Order_Quarter"]    = df["Order_Date"].dt.quarter
    print("✅ Time features extracted: Year, Month, Month_Name, Quarter")
else:
    print("❌ Order_Date not datetime — time features skipped.")

if order_is_dt and ship_is_dt:
    df["Delivery_Days"] = (df["Ship_Date"] - df["Order_Date"]).dt.days

    negative = (df["Delivery_Days"] < 0).sum()
    if negative > 0:
        print(f"⚠️  {negative} records: Ship_Date before Order_Date "
              f"— setting to NaN.")
        df.loc[df["Delivery_Days"] < 0, "Delivery_Days"] = np.nan

    print(f"✅ Delivery_Days | "
          f"Avg: {df['Delivery_Days'].mean():.1f} | "
          f"Max: {df['Delivery_Days'].max():.0f} days")
else:
    print("❌ Cannot calculate Delivery_Days — date parse failed.")

# ── 5. Remove duplicates ──────────────────────────────────────
before        = len(df)
df            = df.drop_duplicates(subset=["Order_ID", "Product_ID"])
dupes_removed = before - len(df)
print(f"\n✅ Duplicates removed: {dupes_removed:,} "
      f"(subset: Order_ID + Product_ID)")

# ── 6. Handle missing values ──────────────────────────────────
nulls_before    = df.isnull().sum()
cols_with_nulls = nulls_before[nulls_before > 0]

if cols_with_nulls.empty:
    print("✅ No missing values found.")
else:
    print(f"\n⚠️  Columns with nulls:\n{cols_with_nulls.to_string()}")

    # Numeric → median
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].apply(lambda col: col.fillna(col.median()))

    # Categorical → mode (NaN in categories breaks groupby silently)
    cat_cols = df.select_dtypes(include="object").columns
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            mode_val = df[col].mode()[0]
            df[col]  = df[col].fillna(mode_val)
            print(f"   '{col}' → mode: '{mode_val}'")

    print("✅ Missing values handled.")

# ── 7. Outlier treatment (IQR winsorizing) ───────────────────
# Cap at bounds, don't delete — preserves real high-value orders
print("\n── Outlier Treatment (IQR Capping) ──")

outlier_log = {}
for col in ["Sales", "Profit"]:
    if col not in df.columns:
        continue
    Q1    = df[col].quantile(0.25)
    Q3    = df[col].quantile(0.75)
    IQR   = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR

    n_out          = ((df[col] < lower) | (df[col] > upper)).sum()
    df[col]        = df[col].clip(lower=lower, upper=upper)
    outlier_log[col] = n_out
    print(f"   {col:<8}: {n_out:>4} outliers capped "
          f"[{lower:>10,.1f} → {upper:>10,.1f}]")

print("✅ Outliers capped via IQR winsorization.")

# ── 8. Business metrics ───────────────────────────────────────
df["Profit_Margin_%"] = np.where(
    df["Sales"] != 0,
    (df["Profit"] / df["Sales"] * 100).round(2),
    0.0
)

df["Revenue_per_Unit"] = np.where(
    df["Quantity"] != 0,
    (df["Sales"] / df["Quantity"]).round(2),
    0.0
)

df["Is_Campaign_Order"] = (df["Discount"] > 0).astype(bool)

# Built once here — reused by files 3 and 4, never recreated
df["Discount_Band"] = pd.cut(
    df["Discount"],
    bins   = [-0.001, 0, 0.1, 0.2, 0.3, 0.5, 1.0],
    labels = ["No Discount", "1-10%", "11-20%", "21-30%", "31-50%", "51%+"]
)

print("\n✅ Business metrics added:")
print("   Profit_Margin_%   | Revenue_per_Unit")
print("   Is_Campaign_Order | Discount_Band")

# ── 9. Range validation ───────────────────────────────────────
print("\n── Column Range Validation ──")

checks = {
    "Profit_Margin_%"  : (-100, 100),
    "Revenue_per_Unit" : (0,    None),
    "Delivery_Days"    : (0,    365),
}
for col, (vmin, vmax) in checks.items():
    if col not in df.columns:
        continue
    cmin, cmax = df[col].min(), df[col].max()
    issues = []
    if vmin is not None and cmin < vmin:
        issues.append(f"min {cmin:.1f} < expected {vmin}")
    if vmax is not None and cmax > vmax:
        issues.append(f"max {cmax:.1f} > expected {vmax}")
    status = "⚠️  " + ", ".join(issues) if issues else "✅"
    print(f"   {col:<22}: {cmin:>8.1f} → {cmax:>8.1f}  {status}")

# ── Cleaning Summary Report ───────────────────────────────────
rows_after = len(df)

print("\n" + "=" * 60)
print("CLEANING SUMMARY REPORT")
print("=" * 60)
print(f"  Records before         : {rows_before:,}")
print(f"  Records after          : {rows_after:,}")
print(f"  Rows removed           : {rows_before - rows_after:,}")
print(f"  Duplicates removed     : {dupes_removed:,}")
print(f"  Sales outliers capped  : {outlier_log.get('Sales',  0):,}")
print(f"  Profit outliers capped : {outlier_log.get('Profit', 0):,}")
print(f"\n  Profit_Margin_%  : "
      f"{df['Profit_Margin_%'].min():.1f}% → "
      f"{df['Profit_Margin_%'].max():.1f}%")
print(f"  Revenue_per_Unit : "
      f"${df['Revenue_per_Unit'].min():.2f} → "
      f"${df['Revenue_per_Unit'].max():.2f}")
if "Delivery_Days" in df.columns:
    print(f"  Delivery_Days    : "
          f"{df['Delivery_Days'].min():.0f} → "
          f"{df['Delivery_Days'].max():.0f} days")
print(f"  Campaign Orders  : "
      f"{df['Is_Campaign_Order'].sum():,} "
      f"({df['Is_Campaign_Order'].mean():.1%})")
print(f"\n  Final shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"  Columns ({len(df.columns)}):")
for i, col in enumerate(df.columns, 1):
    print(f"    {i:>2}. {col}")

# ── Save cleaned data ─────────────────────────────────────────
df.to_csv("data/sales_data_clean.csv", index=False)
print("\n✅ Cleaned data saved → data/sales_data_clean.csv")
print("✅ Cleaning Complete — move to 03_analysis.py")
