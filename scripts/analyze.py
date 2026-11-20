"""Run the SQL queries, draw the charts and write the report and dashboard.

All numbers in the report are computed here from the database, not typed by hand.
"""
import base64
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB, SQL, OUT = ROOT / "data" / "store.db", ROOT / "sql", ROOT / "reports"
FIG = OUT / "figures"
INK, ACCENT, MUTED, GRID = "#1f2937", "#2563eb", "#9ca3af", "#e5e7eb"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.titleweight": "bold", "axes.titlesize": 11, "figure.dpi": 110})


def q(conn, name):
    return pd.read_sql((SQL / name).read_text(), conn)


def billions(x, _=None):
    return f"Rp{x / 1e9:.1f}B"


def save(fig, name):
    path = FIG / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def charts(d):
    paths = {}
    m = d["monthly"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    colors = [ACCENT if mo in ("2025-03", "2025-11", "2025-12") else MUTED for mo in m["month"]]
    ax.bar(pd.to_datetime(m["month"]).dt.strftime("%b"), m["revenue"], color=colors)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(billions))
    ax.set_title("Net revenue by month, 2025 (sale months highlighted)")
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
    paths["monthly"] = save(fig, "monthly_revenue")

    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(pd.to_datetime(m["month"]).dt.strftime("%b"), m["avg_order_value"] / 1e3, marker="o", color=ACCENT)
    ax.set_title("Average order value (thousand IDR) drops in sale months")
    ax.grid(axis="y", color=GRID)
    paths["aov"] = save(fig, "avg_order_value")

    c = d["category"].sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.barh(c["category"], c["revenue"], color=[ACCENT if x == c["revenue"].max() else MUTED for x in c["revenue"]])
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(billions))
    for y, (rev, share) in enumerate(zip(c["revenue"], c["revenue_share_pct"])):
        ax.text(rev, y, f"  {share:.0f}%", va="center", color=INK)
    ax.set_title("Net revenue by category")
    paths["category"] = save(fig, "category_revenue")

    p = d["payment"].sort_values("return_rate_pct")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh(p["payment_method"], p["return_rate_pct"], color=[ACCENT if x == "COD" else MUTED for x in p["payment_method"]])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Return rate by payment method")
    paths["payment"] = save(fig, "returns_by_payment")

    ct = d["city"].sort_values("avg_shipping_days")
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.barh(ct["city"], ct["pct_over_3_days"], color=[ACCENT if x > 40 else MUTED for x in ct["pct_over_3_days"]])
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Share of orders taking more than 3 days to arrive")
    paths["city"] = save(fig, "late_delivery_by_city")

    cc = d["concentration"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.bar(cc["decile"].astype(str), cc["revenue_share_pct"], color=[ACCENT] + [MUTED] * 9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlabel("Customer decile (1 = top 10% by spend)")
    ax.set_title("Share of revenue by customer decile")
    paths["concentration"] = save(fig, "customer_concentration")
    return paths


def findings(d):
    m, c, p, ct, cc = d["monthly"], d["category"], d["payment"], d["city"], d["concentration"]
    total = m["revenue"].sum()
    sale = m[m["month"].isin(["2025-03", "2025-11", "2025-12"])]
    other = m[~m["month"].isin(sale["month"])]
    top = c.iloc[0]
    cod = p.set_index("payment_method").loc["COD"]
    rest = p[~p["payment_method"].isin(["COD", "Unknown"])]
    rest_rate = (rest["return_rate_pct"] * rest["orders"]).sum() / rest["orders"].sum()
    slow = ct.sort_values("pct_over_3_days", ascending=False).iloc[0]
    fast = ct.sort_values("pct_over_3_days").iloc[0]
    return {
        "total_revenue": total,
        "orders": int(m["orders"].sum()),
        "sale_share": sale["revenue"].sum() / total * 100,
        "sale_order_lift": (sale["orders"].mean() / other["orders"].mean() - 1) * 100,
        "sale_aov_drop": (1 - sale["avg_order_value"].mean() / other["avg_order_value"].mean()) * 100,
        "top_cat": top["category"], "top_cat_share": top["revenue_share_pct"],
        "fashion_return": c.set_index("category").loc["Fashion", "return_rate_pct"],
        "cod_return": cod["return_rate_pct"], "rest_return": rest_rate, "cod_lost": cod["revenue_lost"],
        "slow_city": slow["city"], "slow_pct": slow["pct_over_3_days"], "slow_days": slow["avg_shipping_days"],
        "fast_city": fast["city"], "fast_pct": fast["pct_over_3_days"],
        "top10_share": cc.iloc[0]["revenue_share_pct"], "top20_share": cc.iloc[:2]["revenue_share_pct"].sum(),
    }


def report(f, d, paths):
    idr = lambda x: f"Rp{x / 1e9:,.2f} billion" if x >= 1e9 else f"Rp{x / 1e6:,.0f} million"
    rel = lambda k: paths[k].relative_to(OUT).as_posix()
    md = f"""# 2025 Sales Analysis — Online Store (synthetic data)

> **The data is synthetic.** It was generated by `scripts/generate_data.py` to practise a full analysis
> workflow. The numbers describe that generated data, not a real company.

**Scope:** {f['orders']:,} orders in 2025, {idr(f['total_revenue'])} net revenue after discounts and returns.

## Key findings

1. **Sale months bring more orders, but smaller ones.** March (Ramadan), November (11.11) and December (12.12)
   have {f['sale_order_lift']:.0f}% more orders than other months, yet the average order value is
   {f['sale_aov_drop']:.0f}% lower because of deeper discounts. These 3 months bring {f['sale_share']:.0f}% of
   revenue, against 25% if sales were spread evenly.
2. **{f['top_cat']} is {f['top_cat_share']:.0f}% of revenue.** The business depends heavily on one category.
   Fashion sells the most lines but has the highest return rate ({f['fashion_return']:.1f}%).
3. **Cash on delivery is returned about {f['cod_return'] / f['rest_return']:.1f}× as often.** COD's return rate is
   {f['cod_return']:.1f}% against {f['rest_return']:.1f}% for the other payment methods, costing
   {idr(f['cod_lost'])} in returned sales.
4. **Delivery outside Java is slow.** {f['slow_pct']:.0f}% of {f['slow_city']} orders take more than 3 days
   (average {f['slow_days']:.1f} days), against {f['fast_pct']:.0f}% in {f['fast_city']}.
5. **Revenue is concentrated.** The top 10% of customers bring {f['top10_share']:.0f}% of revenue, and the top 20%
   bring {f['top20_share']:.0f}%.

## Recommendations

| Finding | Recommendation | How to measure |
|---|---|---|
| Sale months drive revenue but lower order value | Use bundles and free-shipping thresholds in sale months instead of only deeper discounts | Average order value in the next sale month |
| Heavy reliance on one category | Grow Home & Living and Sports with cross-sell placements on Electronics pages | Revenue share of the top category |
| COD returns | Offer a small discount for e-wallet payment and confirm COD orders by WhatsApp before shipping | COD return rate |
| Slow delivery to Medan and Makassar | Test a regional warehouse or a second courier for Sumatra and Sulawesi | Share of orders over 3 days |
| Concentrated revenue | Start a loyalty tier for the top 10% of customers | Repeat orders from the top decile |

## Charts

![Monthly revenue]({rel('monthly')})
![Average order value]({rel('aov')})
![Revenue by category]({rel('category')})
![Returns by payment]({rel('payment')})
![Late delivery by city]({rel('city')})
![Customer concentration]({rel('concentration')})

## Tables

### Category performance
{d['category'].to_markdown(index=False, floatfmt=',.1f')}

### Payment method and returns
{d['payment'].to_markdown(index=False, floatfmt=',.1f')}

### Delivery by city
{d['city'].to_markdown(index=False, floatfmt=',.1f')}

### Repeat customers
{d['repeat'].to_markdown(index=False)}

## Method

1. `generate_data.py` writes four raw CSVs (products, customers, orders, order lines), including duplicates,
   missing values, bad prices and inconsistent city names.
2. `clean.py` fixes those problems, logs each rule in [data_quality.md](data_quality.md), and loads the clean
   tables into SQLite.
3. The questions are answered in SQL (`sql/`); `analyze.py` runs the queries, draws the charts and writes this report.
4. `tests/` checks the cleaned data and that the SQL totals match an independent pandas calculation.
"""
    (OUT / "REPORT.md").write_text(md)


def dashboard(f, paths):
    img = lambda k: "data:image/png;base64," + base64.b64encode(paths[k].read_bytes()).decode()
    kpis = [("Net revenue", f"Rp{f['total_revenue'] / 1e9:.1f}B"), ("Orders", f"{f['orders']:,}"),
            (f"{f['top_cat']} share", f"{f['top_cat_share']:.0f}%"), ("COD return rate", f"{f['cod_return']:.1f}%"),
            ("Revenue from top 10% customers", f"{f['top10_share']:.0f}%")]
    cards = "".join(f'<div class="kpi"><span>{k}</span><b>{v}</b></div>' for k, v in kpis)
    figs = "".join(f'<figure><img src="{img(k)}" alt="{k} chart"></figure>' for k in paths)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>2025 Sales Dashboard (synthetic data)</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#f8fafc;color:{INK}}}
main{{max-width:1100px;margin:auto;padding:24px}}h1{{margin:0 0 4px}}.note{{color:#6b7280;margin:0 0 20px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px}}
.kpi{{background:#fff;border:1px solid {GRID};border-radius:10px;padding:14px}}.kpi span{{display:block;color:#6b7280;font-size:13px}}
.kpi b{{font-size:24px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:12px}}
figure{{margin:0;background:#fff;border:1px solid {GRID};border-radius:10px;padding:10px}}img{{width:100%}}</style></head>
<body><main><h1>2025 Sales Dashboard</h1>
<p class="note">Synthetic data generated for practice — not a real company. See REPORT.md for findings.</p>
<div class="kpis">{cards}</div><div class="grid">{figs}</div></main></body></html>"""
    (OUT / "dashboard.html").write_text(html)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as conn:
        d = {"monthly": q(conn, "01_monthly_revenue.sql"), "category": q(conn, "02_category_performance.sql"),
             "payment": q(conn, "03_payment_returns.sql"), "city": q(conn, "04_city_delivery.sql"),
             "concentration": q(conn, "05_customer_concentration.sql"), "repeat": q(conn, "06_repeat_customers.sql")}
    paths = charts(d)
    f = findings(d)
    report(f, d, paths)
    dashboard(f, paths)
    print(f"Report: {OUT / 'REPORT.md'}\nDashboard: {OUT / 'dashboard.html'}")


if __name__ == "__main__":
    main()
