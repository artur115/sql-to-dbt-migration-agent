"""Build the fictional customer's warehouse: data/warehouse.duckdb, schema `raw`.

"Harbor & Pine Outfitters" is made up. Every row is synthetic and seeded, so
runs reproduce. The generator plants the mess a real retail warehouse has:
re-delivered order rows, status values with drifting case and whitespace,
orders with no customer, refunds as negative payments and late returns.
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

SEED = 20261126
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "warehouse.duckdb"

REGIONS = ["northeast", "southeast", "midwest", "southwest", "west"]
SEGMENTS = ["consumer", "consumer", "consumer", "pro", "wholesale"]
CATEGORIES = {
    "tents": (180, 640), "packs": (60, 260), "footwear": (90, 220),
    "apparel": (25, 140), "cookware": (15, 120), "climbing": (40, 380),
}
CHANNELS = ["web", "web", "web", "app", "store", "marketplace"]
STATUSES = ["shipped", "shipped", "shipped", "delivered", "delivered", "cancelled", "returned"]
SOURCES = ["paid_search", "organic", "email", "social", "direct", "affiliate"]


def status_variant(rng: random.Random, status: str) -> str:
    # Upstream systems disagree on case and trailing spaces.
    r = rng.random()
    if r < 0.15:
        return status.upper()
    if r < 0.25:
        return status.capitalize() + " "
    return status


def build(n_customers: int = 4000, n_products: int = 300, n_orders: int = 30000) -> None:
    rng = random.Random(SEED)
    start = datetime(2025, 1, 1)

    customers = []
    for cid in range(1, n_customers + 1):
        signup = start + timedelta(days=rng.randint(0, 540))
        customers.append((cid, rng.choice(REGIONS), rng.choice(SEGMENTS), signup.date(),
                          rng.random() < 0.6))  # marketing opt-in

    products = []
    for pid in range(1, n_products + 1):
        cat = rng.choice(list(CATEGORIES))
        lo, hi = CATEGORIES[cat]
        products.append((pid, cat, round(rng.uniform(lo, hi), 2), rng.random() < 0.9))

    orders, items, payments, returns = [], [], [], []
    pay_id = 1
    ret_id = 1
    for oid in range(1, n_orders + 1):
        cust = rng.randint(1, n_customers) if rng.random() > 0.03 else None  # guest checkout
        ts = start + timedelta(days=rng.randint(0, 690), minutes=rng.randint(0, 1439))
        status = rng.choice(STATUSES)
        channel = rng.choice(CHANNELS)
        promo = rng.choice([None, None, None, "SPRING10", "TRAIL15", "VIP20"])
        orders.append((oid, cust, ts, status_variant(rng, status), channel, promo, ts))
        if rng.random() < 0.02:  # re-delivered row: same order, later load time
            orders.append((oid, cust, ts, status_variant(rng, status), channel, promo,
                           ts + timedelta(hours=rng.randint(1, 30))))

        total = 0.0
        for line in range(1, rng.randint(1, 4) + 1):
            p = products[rng.randint(0, n_products - 1)]
            qty = rng.choice([1, 1, 1, 2, 2, 3])
            price = round(p[2] * rng.uniform(0.85, 1.0), 2)
            items.append((oid, line, p[0], qty, price))
            total += qty * price
            if status == "returned" and rng.random() < 0.7:
                lag = rng.randint(3, 75)  # some returns land after the 60-day window
                returns.append((ret_id, oid, p[0], qty, ts + timedelta(days=lag),
                                rng.choice(["fit", "damaged", "changed_mind", "late_delivery"])))
                ret_id += 1

        if status != "cancelled":
            disc = {"SPRING10": 0.10, "TRAIL15": 0.15, "VIP20": 0.20}.get(promo, 0)
            amount = round(total * (1 - disc), 2)
            payments.append((pay_id, oid, amount, rng.choice(["card", "card", "paypal", "gift_card"]),
                             ts + timedelta(minutes=rng.randint(1, 90))))
            pay_id += 1
            if status == "returned":
                payments.append((pay_id, oid, -round(amount * rng.uniform(0.3, 1.0), 2), "refund",
                                 ts + timedelta(days=rng.randint(5, 40))))
                pay_id += 1

    sessions = []
    for sid in range(1, 60001):
        cust = rng.randint(1, n_customers) if rng.random() < 0.55 else None
        ts = start + timedelta(days=rng.randint(0, 690), minutes=rng.randint(0, 1439))
        sessions.append((sid, cust, ts, rng.choice(SOURCES), rng.randint(1, 18)))

    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute("CREATE SCHEMA raw")
    ddl = {
        "customers": "customer_id INTEGER, region VARCHAR, segment VARCHAR, signup_date DATE, marketing_opt_in BOOLEAN",
        "products": "product_id INTEGER, category VARCHAR, list_price DECIMAL(10,2), is_active BOOLEAN",
        "orders": "order_id INTEGER, customer_id INTEGER, order_ts TIMESTAMP, status VARCHAR, channel VARCHAR, promo_code VARCHAR, _loaded_at TIMESTAMP",
        "order_items": "order_id INTEGER, line_no INTEGER, product_id INTEGER, quantity INTEGER, unit_price DECIMAL(10,2)",
        "payments": "payment_id INTEGER, order_id INTEGER, amount DECIMAL(12,2), method VARCHAR, paid_ts TIMESTAMP",
        "returns": "return_id INTEGER, order_id INTEGER, product_id INTEGER, quantity INTEGER, return_ts TIMESTAMP, reason VARCHAR",
        "web_sessions": "session_id INTEGER, customer_id INTEGER, started_at TIMESTAMP, source VARCHAR, pageviews INTEGER",
    }
    rows = {"customers": customers, "products": products, "orders": orders, "order_items": items,
            "payments": payments, "returns": returns, "web_sessions": sessions}
    for name, cols in ddl.items():
        con.execute(f"CREATE TABLE raw.{name} ({cols})")
        names = [c.strip().split()[0] for c in re.split(r",(?![^()]*\))", cols)]
        frame = pd.DataFrame(rows[name], columns=names)  # noqa: F841 (read by DuckDB)
        con.execute(f"INSERT INTO raw.{name} SELECT * FROM frame")
    con.close()
    print({k: len(v) for k, v in rows.items()})


if __name__ == "__main__":
    build()
