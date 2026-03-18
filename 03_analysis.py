# ============================================================
# STEP 3 — Campaign Performance Analysis
# Campaign Performance Analytics & Sales Dashboard
# ============================================================

import pandas as pd
import numpy as np
import json


# ── Helper: safely convert pandas scalar to Python float ─────
# FIX 12: np.float64(pandas_NA) raises TypeError — use this instead
def to_float(val, default=0.0):
    try:
        result = float(val)
        return default if (result != result) else result  # NaN check
    except (TypeError, ValueError):
        return default


# ── Load cleaned data ─────────────────────────────────────────
df = pd.read_csv("data/sales_data_clean.csv")

# FIX 1: Try ISO format first (how cleaning saves it),
# fall back to MM/DD/YYYY if ISO produces all NaT
# Avoids silent all-NaT when format doesn't match
parsed = pd.to_datetime(df["Order_Date"], format="%Y-%m-%d", errors="coerce")
if parsed.isna().mean() > 0.05:                    # >5% failed → wrong format
    parsed = pd.to_datetime(
        df["Order_Date"], format="%m/%d/%Y", errors="coerce"
    )
df["Order_Date"] = parsed
print(f"Order_Date parsed: {df['Order_Date'].notna().sum():,} valid, "
      f"{df['Order_Date'].isna().sum()} nulls")

# FIX 2: Normalize Is_Campaign_Order — CSV round-trip gives "True"/"1"/True
if "Is_Campaign_Order" in df.columns:
    df["Is_Campaign_Order"] = (
        df["Is_Campaign_Order"]
          .astype(str).str.strip().str.lower()
          .map({"true": True, "1": True, "false": False, "0": False})
          .fillna(False)
          .astype(bool)
    )

# FIX 3: Cast time columns to Int64 — CSV gives 2017.0 floats
for col in ["Order_Year", "Order_Month", "Order_Quarter"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

print("=" * 60)
print("CAMPAIGN PERFORMANCE ANALYSIS REPORT")
print("=" * 60)

# ── Precompute reusable scalars ───────────────────────────────
total_sales  = to_float(df["Sales"].sum())
total_profit = to_float(df["Profit"].sum())
total_orders = int(df["Order_ID"].nunique())
total_rows   = len(df)
findings: dict = {}

# ─────────────────────────────────────────────────────────────
# ANALYSIS 1 — Campaign vs Non-Campaign
# ─────────────────────────────────────────────────────────────
print("\n📊 1. CAMPAIGN vs NON-CAMPAIGN ORDERS")
print("-" * 50)

campaign_summary = (
    df.groupby("Is_Campaign_Order", observed=True)
      .agg(
          Total_Orders    = ("Order_ID",        "count"),
          Total_Sales     = ("Sales",           "sum"),
          Total_Profit    = ("Profit",          "sum"),
          Avg_Order_Value = ("Sales",           "mean"),
          Avg_Discount    = ("Discount",        "mean"),
          Avg_Margin      = ("Profit_Margin_%", "mean"),
      )
      .round(2)
)

# FIX 4: label_map covers bool, int, and string variants safely
label_map = {
    True: "Campaign", False: "No Campaign",
    1:    "Campaign", 0:    "No Campaign",
}
campaign_summary.index = [
    label_map.get(v, str(v)) for v in campaign_summary.index
]
print(campaign_summary.to_string())

if "Campaign" in campaign_summary.index and \
   "No Campaign" in campaign_summary.index:
    camp_avg   = to_float(campaign_summary.loc["Campaign",    "Avg_Order_Value"])
    nocamp_avg = to_float(campaign_summary.loc["No Campaign", "Avg_Order_Value"])
    lift = ((camp_avg - nocamp_avg) / nocamp_avg * 100) if nocamp_avg != 0 else 0.0
    print(f"\n💡 Campaign Order Value Lift: {lift:+.1f}% vs non-campaign")
    findings["campaign_lift_%"] = round(lift, 1)

# ─────────────────────────────────────────────────────────────
# ANALYSIS 2 — Segment Performance
# ─────────────────────────────────────────────────────────────
print("\n📊 2. PERFORMANCE BY CUSTOMER SEGMENT")
print("-" * 50)

segment_perf = (
    df.groupby("Segment", observed=True)
      .agg(
          Orders        = ("Order_ID",        "count"),
          Total_Sales   = ("Sales",           "sum"),
          Total_Profit  = ("Profit",          "sum"),
          Profit_Margin = ("Profit_Margin_%", "mean"),
          Avg_Discount  = ("Discount",        "mean"),
          Avg_Order_Val = ("Sales",           "mean"),
      )
      .round(2)
      .sort_values("Total_Sales", ascending=False)
)
segment_perf["Sales_Share_%"] = (
    segment_perf["Total_Sales"] / total_sales * 100
).round(1)

print(segment_perf.to_string())
best_segment = str(segment_perf.index[0])
print(f"\n🏆 Top segment : {best_segment} "
      f"({segment_perf.loc[best_segment, 'Sales_Share_%']}% of total)")
findings["best_segment"] = best_segment

# ─────────────────────────────────────────────────────────────
# ANALYSIS 3 — Regional Performance
# ─────────────────────────────────────────────────────────────
print("\n📊 3. REGIONAL CAMPAIGN PERFORMANCE")
print("-" * 50)

# FIX 5: agg_dict was dead code — replace with explicit if/else
# FIX 6: Remove conditional ** unpacking — pyright flags it
has_delivery = "Delivery_Days" in df.columns

if has_delivery:
    regional_perf = (
        df.groupby("Region", observed=True)
          .agg(
              Orders             = ("Order_ID",          "count"),
              Total_Sales        = ("Sales",             "sum"),
              Total_Profit       = ("Profit",            "sum"),
              Avg_Margin         = ("Profit_Margin_%",   "mean"),
              Campaign_Response  = ("Is_Campaign_Order", "mean"),
              Avg_Delivery_Days  = ("Delivery_Days",     "mean"),
          )
          .round(2)
          .sort_values("Total_Sales", ascending=False)
    )
else:
    regional_perf = (
        df.groupby("Region", observed=True)
          .agg(
              Orders            = ("Order_ID",          "count"),
              Total_Sales       = ("Sales",             "sum"),
              Total_Profit      = ("Profit",            "sum"),
              Avg_Margin        = ("Profit_Margin_%",   "mean"),
              Campaign_Response = ("Is_Campaign_Order", "mean"),
          )
          .round(2)
          .sort_values("Total_Sales", ascending=False)
    )

# FIX 7: Is_Campaign_Order mean() already 0-1 float — multiply safely
regional_perf["Campaign_Response_%"] = (
    regional_perf["Campaign_Response"].astype(float) * 100
).round(1)
regional_perf["Sales_Share_%"] = (
    regional_perf["Total_Sales"].astype(float) / total_sales * 100
).round(1)
regional_perf = regional_perf.drop(columns="Campaign_Response")

print(regional_perf.to_string())

best_region  = str(regional_perf.index[0])
worst_region = str(regional_perf.index[-1])
print(f"\n🏆 Top region    : {best_region} "
      f"({regional_perf.loc[best_region,  'Sales_Share_%']}%)")
print(f"📉 Bottom region : {worst_region} "
      f"({regional_perf.loc[worst_region, 'Sales_Share_%']}%)")
findings["best_region"]  = best_region
findings["worst_region"] = worst_region

# ─────────────────────────────────────────────────────────────
# ANALYSIS 4 — Product Performance
# ─────────────────────────────────────────────────────────────
print("\n📊 4. PRODUCT CATEGORY & SUB-CATEGORY PERFORMANCE")
print("-" * 50)

category_perf = (
    df.groupby("Category", observed=True)
      .agg(
          Orders       = ("Order_ID",        "count"),
          Total_Sales  = ("Sales",           "sum"),
          Total_Profit = ("Profit",          "sum"),
          Avg_Margin   = ("Profit_Margin_%", "mean"),
          Avg_Discount = ("Discount",        "mean"),
      )
      .round(2)
      .sort_values("Total_Profit", ascending=False)
)
category_perf["Sales_Share_%"] = (
    category_perf["Total_Sales"].astype(float) / total_sales * 100
).round(1)

print(category_perf.to_string())
best_category = str(category_perf.index[0])
findings["best_category"] = best_category

print("\n📊 Top 5 Sub-Categories by Sales:")
sub_perf = (
    df.groupby("Sub_Category", observed=True)
      .agg(
          Sales  = ("Sales",           "sum"),
          Profit = ("Profit",          "sum"),
          Margin = ("Profit_Margin_%", "mean"),
      )
      .round(2)
      .nlargest(5, "Sales")
)
print(sub_perf.to_string())

# ─────────────────────────────────────────────────────────────
# ANALYSIS 5 — YoY Growth + Monthly Seasonality
# ─────────────────────────────────────────────────────────────
print("\n📊 5. YEAR-OVER-YEAR GROWTH ANALYSIS")
print("-" * 50)

if "Order_Year" not in df.columns or df["Order_Year"].isna().all():
    print("⚠️  Order_Year unavailable — skipping YoY analysis.")
else:
    yearly = (
        df.groupby("Order_Year", observed=True)
          .agg(
              Sales  = ("Sales",    "sum"),
              Profit = ("Profit",   "sum"),
              Orders = ("Order_ID", "count"),
          )
    )
    # FIX 8: Cast to float before pct_change()
    # pct_change() on Int64 returns timedelta — must be float
    yearly["Sales"]  = yearly["Sales"].astype(float)
    yearly["Profit"] = yearly["Profit"].astype(float)
    yearly["Sales_Growth_%"]  = (yearly["Sales"].pct_change()  * 100).round(2)
    yearly["Profit_Growth_%"] = (yearly["Profit"].pct_change() * 100).round(2)
    yearly = yearly.round(2)

    print(yearly.to_string())

    # FIX 9: idxmax() on Int64 index — convert via .item() not int()
    best_year_raw = yearly["Sales"].idxmax()
    best_year     = int(best_year_raw) if pd.notna(best_year_raw) else None
    if best_year:
        print(f"\n🏆 Best year by sales: {best_year}")
        findings["best_year"] = best_year

# Monthly seasonality
print("\n📊 Monthly Seasonality (avg sales per month):")

if "Order_Month" in df.columns and not df["Order_Month"].isna().all():
    # FIX 10: No df.copy() needed — work directly on column
    order_month = df["Order_Month"].astype("Int64")

    monthly_avg = (
        df.assign(Order_Month_Int=order_month)
          .groupby("Order_Month_Int", observed=True)["Sales"]
          .mean()
          .round(2)
    )
    month_names = {
        1: "Jan", 2: "Feb",  3: "Mar", 4: "Apr",
        5: "May", 6: "Jun",  7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    monthly_avg.index = [
        month_names.get(int(m), str(m)) for m in monthly_avg.index
    ]
    print(monthly_avg.to_string())

    peak_month = str(monthly_avg.idxmax())
    print(f"\n🏆 Peak sales month: {peak_month}")
    findings["peak_month"] = peak_month
else:
    print("⚠️  Order_Month unavailable — skipping seasonality.")

# ─────────────────────────────────────────────────────────────
# ANALYSIS 6 — Campaign ROI by Discount Band
# ─────────────────────────────────────────────────────────────
print("\n📊 6. CAMPAIGN ROI ANALYSIS")
print("-" * 50)

# pd.cut Categorical doesn't survive CSV round-trip — always recreate
df["Discount_Band"] = pd.cut(
    df["Discount"],
    bins   = [-0.001, 0, 0.1, 0.2, 0.3, 0.5, 1.0],
    labels = ["No Discount", "1-10%", "11-20%", "21-30%", "31-50%", "51%+"],
)

discount_impact = (
    df.groupby("Discount_Band", observed=True)
      .agg(
          Orders        = ("Order_ID",        "count"),
          Avg_Sales     = ("Sales",           "mean"),
          Avg_Profit    = ("Profit",          "mean"),
          Avg_Margin    = ("Profit_Margin_%", "mean"),
          Total_Revenue = ("Sales",           "sum"),
          Total_Profit  = ("Profit",          "sum"),
          Avg_Discount  = ("Discount",        "mean"),
      )
      .round(2)
)

# FIX 11: Est_Discount_Cost stays as Series — no index mismatch
discount_impact["Est_Discount_Cost"] = (
    discount_impact["Total_Revenue"].astype(float) *
    discount_impact["Avg_Discount"].astype(float)
).round(2)

# FIX: ROI calculation — keep as Series (avoid np.where losing index)
# Use pd.Series.where() instead — preserves index alignment
mask = discount_impact["Est_Discount_Cost"] > 0
roi_vals = (
    discount_impact["Total_Profit"].astype(float) /
    discount_impact["Est_Discount_Cost"].astype(float) * 100
).round(1)
discount_impact["ROI_%"] = roi_vals.where(mask, other=np.nan)

print(discount_impact.to_string())

# FIX: str(NaN label) returns 'nan' not 'N/A' — check explicitly
valid_roi = discount_impact["ROI_%"].dropna()
if not valid_roi.empty:
    best_band_raw = valid_roi.idxmax()
    best_band     = str(best_band_raw) if pd.notna(best_band_raw) else "N/A"
    print(f"\n💡 Highest ROI discount band : {best_band}")
    print("💡 Bands above 30% show profit erosion — cap campaigns at 20%.")
else:
    best_band = "N/A"
    print("⚠️  Could not determine best ROI band.")
findings["best_discount_band"] = best_band

# ─────────────────────────────────────────────────────────────
# SUMMARY + EXPORT
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("KEY FINDINGS SUMMARY")
print("=" * 60)

# FIX 12: overall_margin guard — 0.0 is falsy in Python but not always
# in pandas. Use explicit != 0 check
overall_margin  = (total_profit / total_sales * 100) if total_sales != 0 else 0.0
campaign_orders = int(df["Is_Campaign_Order"].sum())
campaign_pct    = (campaign_orders / total_rows * 100) if total_rows > 0 else 0.0

print(f"  Total Revenue      : ${total_sales:>12,.0f}")
print(f"  Total Profit       : ${total_profit:>12,.0f}")
print(f"  Overall Margin     : {overall_margin:>11.1f}%")
print(f"  Unique Orders      : {total_orders:>12,}")
print(f"  Campaign Orders    : {campaign_orders:>12,} ({campaign_pct:.1f}%)")
print(f"  Best Segment       : {findings.get('best_segment',      'N/A')}")
print(f"  Best Region        : {findings.get('best_region',       'N/A')}")
print(f"  Best Category      : {findings.get('best_category',     'N/A')}")
print(f"  Peak Month         : {findings.get('peak_month',        'N/A')}")
print(f"  Best Discount Band : {findings.get('best_discount_band','N/A')}")

# FIX: Use to_float() helper — avoids TypeError on pandas NA scalars
findings.update({
    "total_revenue"     : round(to_float(total_sales),    2),
    "total_profit"      : round(to_float(total_profit),   2),
    "overall_margin_%"  : round(to_float(overall_margin), 1),
    "campaign_orders_%" : round(to_float(campaign_pct),   1),
})

with open("data/key_findings.json", "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

print("\n✅ Key findings exported → data/key_findings.json")
print("✅ Analysis Complete — move to 04_dashboard.py")
