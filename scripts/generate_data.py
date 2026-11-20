"""Generate a SYNTHETIC e-commerce dataset for an Indonesian online store (2025).

The data is invented, not real sales. It is seeded so every run produces the same
files, and it includes realistic data-quality problems (duplicates, missing values,
bad prices, inconsistent city names) so the cleaning step has real work to do.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

CITIES = {  # city: (share of customers, base shipping days)
    "Jakarta": (0.28, 1.5), "Tangerang": (0.12, 1.8), "Bekasi": (0.10, 1.9), "Bandung": (0.10, 2.3),
    "Surabaya": (0.12, 2.8), "Medan": (0.08, 4.0), "Semarang": (0.07, 2.9), "Makassar": (0.06, 4.6),
    "Yogyakarta": (0.07, 2.7),
}
CATEGORIES = {  # category: (price range in IDR, popularity, return rate)
    "Electronics": ((150_000, 4_500_000), 0.14, 0.07),
    "Fashion": ((60_000, 450_000), 0.26, 0.11),
    "Beauty": ((35_000, 300_000), 0.20, 0.04),
    "Home & Living": ((40_000, 900_000), 0.16, 0.05),
    "Groceries": ((15_000, 180_000), 0.17, 0.02),
    "Sports": ((80_000, 1_200_000), 0.07, 0.06),
}
PAYMENTS = {"E-wallet": 0.38, "Bank transfer": 0.24, "COD": 0.20, "Credit card": 0.10, "PayLater": 0.08}


def month_weights():
    w = np.ones(12)
    w[2] += 0.45   # March 2025: Ramadan shopping
    w[10] += 0.25  # November: 11.11 sale
    w[11] += 0.55  # December: 12.12 sale and year-end
    w[5] += 0.10   # June: mid-year sale
    return w / w.sum()


def main():
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    # --- products
    rows = []
    pid = 1
    for cat, ((lo, hi), _, _) in CATEGORIES.items():
        for _ in range(30):
            price = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
            rows.append({"product_id": f"P{pid:04d}", "category": cat,
                         "unit_price": int(round(price, -3))})
            pid += 1
    products = pd.DataFrame(rows)

    # --- customers
    n_cust = 2500
    names, shares = list(CITIES), np.array([v[0] for v in CITIES.values()])
    cities = rng.choice(names, size=n_cust, p=shares / shares.sum())
    signup = pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 730, n_cust), unit="D")
    customers = pd.DataFrame({"customer_id": [f"C{i:05d}" for i in range(1, n_cust + 1)],
                              "city": cities, "signup_date": signup.date})
    # inconsistent spellings, as typed by users
    messy = rng.random(n_cust) < 0.04
    customers.loc[messy, "city"] = customers.loc[messy, "city"].map(
        lambda c: rng.choice([c.upper(), c.lower(), f" {c} ", {"Yogyakarta": "Jogja", "Jakarta": "DKI Jakarta"}.get(c, c.lower())]))

    # --- orders
    n_orders = 18_000
    activity = rng.pareto(1.6, n_cust) + 1           # a few customers buy a lot
    cust_idx = rng.choice(n_cust, size=n_orders, p=activity / activity.sum())
    month = rng.choice(12, size=n_orders, p=month_weights()) + 1
    day = np.array([rng.integers(1, pd.Period(f"2025-{m:02d}").days_in_month + 1) for m in month])
    hour_w = np.r_[np.full(7, 1.0), np.full(10, 4.5), np.full(7, 6.5)]  # quiet nights, busy evenings
    hour = rng.choice(24, size=n_orders, p=hour_w / hour_w.sum())
    order_ts = pd.to_datetime({"year": 2025, "month": month, "day": day, "hour": hour}) + \
        pd.to_timedelta(rng.integers(0, 60, n_orders), unit="m")
    pay = rng.choice(list(PAYMENTS), size=n_orders, p=list(PAYMENTS.values()))
    city_of = customers["city"].str.strip().str.title().replace({"Jogja": "Yogyakarta", "Dki Jakarta": "Jakarta"})
    base_days = city_of.iloc[cust_idx].map({k: v[1] for k, v in CITIES.items()}).to_numpy()
    ship_days = np.maximum(1, np.round(rng.gamma(4, base_days / 4))).astype(int)

    orders = pd.DataFrame({"order_id": [f"O{i:06d}" for i in range(1, n_orders + 1)],
                           "customer_id": customers["customer_id"].iloc[cust_idx].to_numpy(),
                           "order_ts": order_ts, "payment_method": pay, "shipping_days": ship_days})

    # --- order items
    cats, pops = list(CATEGORIES), np.array([v[1] for v in CATEGORIES.values()])
    n_lines = rng.choice([1, 2, 3, 4], size=n_orders, p=[0.55, 0.28, 0.12, 0.05])
    line_cat = rng.choice(cats, size=n_lines.sum(), p=pops / pops.sum())
    by_cat = {c: products.index[products["category"] == c].to_numpy() for c in cats}
    prod_idx = np.array([rng.choice(by_cat[c]) for c in line_cat])
    consumable = np.isin(line_cat, ["Groceries", "Beauty"])
    qty = np.where(consumable, rng.choice([1, 1, 1, 2, 2, 3], size=len(line_cat)),
                   rng.choice([1, 1, 1, 1, 2], size=len(line_cat)))
    items = pd.DataFrame({
        "order_id": np.repeat(orders["order_id"].to_numpy(), n_lines),
        "product_id": products["product_id"].to_numpy()[prod_idx],
        "quantity": qty,
        "unit_price": products["unit_price"].to_numpy()[prod_idx],
        "discount": rng.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2], size=len(line_cat)),
    })
    # sale months carry deeper discounts
    sale = orders.set_index("order_id")["order_ts"].dt.month.isin([3, 11, 12])
    deep = items["order_id"].map(sale) & (rng.random(len(items)) < 0.5)
    items.loc[deep, "discount"] = np.maximum(items.loc[deep, "discount"], 0.25)

    # returns depend on category, and on COD (buyers refuse the parcel)
    cat_of = items["product_id"].map(products.set_index("product_id")["category"])
    rr = cat_of.map({k: v[2] for k, v in CATEGORIES.items()}).to_numpy()
    rr = rr * np.where(items["order_id"].map(orders.set_index("order_id")["payment_method"]) == "COD", 2.2, 1.0)
    items["returned"] = rng.random(len(items)) < rr

    # --- inject data-quality problems
    dup = items.sample(frac=0.01, random_state=SEED)                     # duplicated rows
    items = pd.concat([items, dup], ignore_index=True)
    items.loc[items.sample(frac=0.003, random_state=1).index, "unit_price"] = -1  # bad prices
    items.loc[items.sample(frac=0.005, random_state=2).index, "quantity"] = np.nan
    orders.loc[orders.sample(frac=0.006, random_state=3).index, "payment_method"] = np.nan

    products.to_csv(RAW / "products.csv", index=False)
    customers.to_csv(RAW / "customers.csv", index=False)
    orders.to_csv(RAW / "orders.csv", index=False)
    items.sample(frac=1, random_state=SEED).to_csv(RAW / "order_items.csv", index=False)
    print(f"wrote {len(products)} products, {len(customers)} customers, {len(orders)} orders, "
          f"{len(items)} order items to {RAW}")


if __name__ == "__main__":
    main()
