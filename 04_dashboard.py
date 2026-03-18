# ============================================================
# STEP 4 — Campaign Performance Dashboard (Final Optimized)
# ============================================================

import warnings
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# ── Style ───────────────────────────────────────────────────
sns.set_theme(style="whitegrid")

COLORS = {
    "blue": "#2563EB",
    "green": "#16A34A",
    "red": "#DC2626",
    "orange": "#EA580C",
    "purple": "#7C3AED",
    "teal": "#0D9488",
}

# ── Load data ───────────────────────────────────────────────
df = pd.read_csv("data/sales_data_clean.csv", parse_dates=["Order_Date"])

# ── Precompute (IMPORTANT for performance) ───────────────────
kpi_sales = df["Sales"].sum()
kpi_profit = df["Profit"].sum()
kpi_orders = df["Order_ID"].nunique()
kpi_campaign = df["Is_Campaign_Order"].sum()
kpi_campaign_pct = df["Is_Campaign_Order"].mean()

monthly = (
    df.groupby(["Order_Year", "Order_Month"], observed=True)["Sales"]
    .sum()
    .reset_index()
)

monthly["Period"] = pd.to_datetime(
    monthly["Order_Year"].astype(str) + "-"
    + monthly["Order_Month"].astype(str).str.zfill(2)
)

monthly = monthly.sort_values("Period")

region_sales = df.groupby("Region", observed=True)["Sales"].sum().sort_values()
seg_sales = df.groupby("Segment", observed=True)["Sales"].sum()
cat_profit = df.groupby("Category", observed=True)["Profit"].sum()
top_sub = df.groupby("Sub_Category", observed=True)["Sales"].sum().nlargest(10)

resp = df.groupby("Region", observed=True)["Is_Campaign_Order"].mean() * 100
qtr = df.groupby(["Order_Quarter", "Segment"], observed=True)["Sales"].sum().unstack()
heat_data = df.groupby(["Region", "Category"], observed=True)["Profit_Margin_%"].mean().unstack()

# ─────────────────────────────────────────────────────────────
# DASHBOARD 1
# ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
gs = gridspec.GridSpec(3, 4, figure=fig)

fig.suptitle("Executive Dashboard", fontsize=15)

kpis = [
    ("Revenue", f"${kpi_sales:,.0f}", COLORS["blue"]),
    ("Profit", f"${kpi_profit:,.0f}", COLORS["green"]),
    ("Orders", f"{kpi_orders:,}", COLORS["purple"]),
    ("Campaign", f"{kpi_campaign:,} ({kpi_campaign_pct:.0%})", COLORS["orange"]),
]

for i, (label, value, color) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i])
    ax.set_facecolor(color)
    ax.text(0.5, 0.6, value, ha="center", va="center", fontsize=16, color="white")
    ax.text(0.5, 0.3, label, ha="center", va="center", fontsize=9, color="white")
    ax.axis("off")

# Monthly trend
ax1 = fig.add_subplot(gs[1:, :2])
ax1.plot(
    monthly["Period"].to_list(),
    monthly["Sales"].to_numpy(),
    linewidth=2
)
ax1.set_title("Monthly Sales Trend")
ax1.tick_params(axis="x", rotation=45)

# Region sales
ax2 = fig.add_subplot(gs[1:, 2:])
ax2.barh(
    region_sales.index.to_list(),
    region_sales.to_numpy()
)
ax2.set_title("Sales by Region")

plt.savefig("dashboard_1.png", dpi=120, bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────
# DASHBOARD 2
# ─────────────────────────────────────────────────────────────
fig2, axes = plt.subplots(2, 2, figsize=(14, 10))

# Segment pie
axes[0, 0].pie(
    seg_sales.to_numpy(),
    labels=seg_sales.index.to_list(),
    autopct="%1.1f%%"
)
axes[0, 0].set_title("Sales by Segment")

# Category profit
axes[0, 1].bar(
    cat_profit.index.to_list(),
    cat_profit.to_numpy()
)
axes[0, 1].set_title("Profit by Category")

# Scatter
sample = df.sample(min(2000, len(df)), random_state=42)
axes[1, 0].scatter(
    sample["Discount"].to_numpy(),
    sample["Profit"].to_numpy(),
    alpha=0.5
)
axes[1, 0].set_title("Discount vs Profit")

# Top sub-categories
axes[1, 1].barh(
    top_sub.index.to_list(),
    top_sub.to_numpy()
)
axes[1, 1].set_title("Top Sub-Categories")

plt.savefig("dashboard_2.png", dpi=120, bbox_inches="tight")
plt.close()

# ─────────────────────────────────────────────────────────────
# DASHBOARD 3
# ─────────────────────────────────────────────────────────────
fig3, axes3 = plt.subplots(1, 3, figsize=(16, 5))

# Response rate
axes3[0].bar(
    resp.index.to_list(),
    resp.to_numpy()
)
axes3[0].set_title("Campaign Response")

# Quarterly
qtr.plot(kind="bar", ax=axes3[1])
axes3[1].set_title("Quarterly Sales")

# Heatmap
sns.heatmap(
    heat_data.to_numpy(),
    xticklabels=heat_data.columns.to_list(),
    yticklabels=heat_data.index.to_list(),
    annot=True,
    fmt=".1f",
    cmap="RdYlGn",
    ax=axes3[2]
)
axes3[2].set_title("Profit Margin Heatmap")

plt.savefig("dashboard_3.png", dpi=120, bbox_inches="tight")
plt.close()

print("✅ All dashboards generated successfully")