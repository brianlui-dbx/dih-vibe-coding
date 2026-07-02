#!/usr/bin/env python3
"""Synthetic grocery POS transaction generator for the Sobeys retail-sales demo.

Writes newline-delimited JSON (one JSON object per line), sharded across N files,
into an output directory. Deterministic given ``--seed``. Injects a small fraction
of malformed rows so the downstream medallion pipeline has something real to catch:
Silver data-quality Expectations and Auto Loader's ``_rescued_data`` column.

Standard library only (random, json, uuid, datetime, argparse, os) — runs with zero
extra installs.

Record schema (one grocery POS line item per row):
    transaction_id   STRING  uuid4
    store_id         INT     1001-1050
    store_province   STRING  Canadian province (Atlantic + ON weighted, Sobeys heartland)
    transaction_ts   STRING  ISO-8601 (raw; typed to TIMESTAMP in Silver)
    product_id       STRING  SKU
    product_name     STRING
    product_category STRING  Produce | Dairy | Bakery | Meat & Seafood | Frozen |
                             Beverages | Pantry | Household | Snacks | Deli
    quantity         INT
    unit_price       DOUBLE
    amount           DOUBLE  quantity * unit_price
    loyalty_id       STRING  nullable, ~60% present (Scene+ member id)
    payment_method   STRING  debit | credit | cash | mobile
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta

# --- Store footprint: Sobeys is Atlantic-Canada-rooted, so weight NS/NB/NL/PE + ON. ---
STORE_IDS = list(range(1001, 1051))  # 50 stores
PROVINCE_WEIGHTS = {
    "NS": 22, "NB": 13, "NL": 9, "PE": 5,   # Atlantic (Sobeys heartland)
    "ON": 24, "QC": 11, "AB": 9, "BC": 7,   # rest of the country
}

PAYMENT_METHODS = ["debit", "credit", "cash", "mobile"]
PAYMENT_WEIGHTS = [40, 34, 11, 15]

# quantity: most baskets are small; long tail up to a case of 12
QUANTITY_CHOICES = [1, 2, 3, 4, 5, 6, 8, 10, 12]
QUANTITY_WEIGHTS = [34, 26, 15, 9, 6, 4, 3, 2, 1]

# Short codes used to mint SKUs, per category.
CATEGORY_CODES = {
    "Produce": "PRD", "Dairy": "DRY", "Bakery": "BKY", "Meat & Seafood": "MSF",
    "Frozen": "FRZ", "Beverages": "BEV", "Pantry": "PAN", "Household": "HHD",
    "Snacks": "SNK", "Deli": "DEL",
}

# category -> (unit_price_low, unit_price_high, [product names])
CATEGORY_PRODUCTS = {
    "Produce": (0.99, 9.99, [
        "Bananas 1kg", "Gala Apples 1.5kg", "Romaine Lettuce", "Roma Tomatoes 1kg",
        "Baby Carrots 454g", "Seedless Grapes", "Avocado 4pk", "Yellow Onions 1.36kg",
    ]),
    "Dairy": (1.49, 12.99, [
        "2% Milk 4L", "Salted Butter 454g", "Large Eggs Dozen", "Old Cheddar 400g",
        "Greek Yogurt 750g", "Sour Cream 500ml", "Cream Cheese 250g",
    ]),
    "Bakery": (1.99, 8.99, [
        "Whole Wheat Bread", "Bagels 6pk", "Croissants 4pk", "Dinner Rolls 12pk",
        "Cinnamon Buns 6pk", "Baguette",
    ]),
    "Meat & Seafood": (4.99, 29.99, [
        "Boneless Chicken Breast 1kg", "Lean Ground Beef 1kg", "Atlantic Salmon Fillet",
        "Pork Tenderloin", "Peameal Bacon 500g", "Cooked Shrimp 340g", "AAA Sirloin Steak",
    ]),
    "Frozen": (2.49, 14.99, [
        "Frozen Blueberries 600g", "Pizza Pepperoni", "French Fries 1kg",
        "Frozen Peas 750g", "Ice Cream 1.5L", "Chicken Nuggets 907g",
    ]),
    "Beverages": (0.99, 15.99, [
        "Orange Juice 1.75L", "Cola 12pk Cans", "Sparkling Water 1L", "Ground Coffee 930g",
        "Green Tea 40ct", "Apple Juice 2L", "Energy Drink 4pk",
    ]),
    "Pantry": (0.99, 11.99, [
        "Basmati Rice 2kg", "Spaghetti 900g", "Canned Tomatoes 796ml", "Peanut Butter 1kg",
        "Olive Oil 1L", "Cereal 525g", "Black Beans 540ml", "All-Purpose Flour 2.5kg",
    ]),
    "Household": (2.99, 24.99, [
        "Bath Tissue 12 Rolls", "Paper Towels 6pk", "Dish Soap 740ml",
        "Laundry Detergent 1.47L", "Trash Bags 40ct", "Aluminum Foil 30m",
    ]),
    "Snacks": (1.29, 7.99, [
        "Potato Chips 200g", "Tortilla Chips 300g", "Chocolate Chip Cookies",
        "Mixed Nuts 300g", "Granola Bars 12pk", "Pretzels 350g",
    ]),
    "Deli": (2.99, 19.99, [
        "Sliced Turkey Breast 175g", "Black Forest Ham 175g", "Rotisserie Chicken",
        "Hummus 500g", "Bocconcini 200g", "Kalamata Olives 375ml",
    ]),
}

# Roughly 2-3% of rows are corrupted (see corrupt() for the failure modes).
MALFORMED_RATE = 0.025

# Fixed 30-day window so timestamps are reproducible regardless of wall clock.
WINDOW_DAYS = 30
REFERENCE_END = datetime(2026, 6, 30, 23, 59, 59)
WINDOW_SECONDS = WINDOW_DAYS * 24 * 3600


def build_catalog():
    """Flatten CATEGORY_PRODUCTS into a stable list of products, each with its SKU."""
    catalog = []
    for category, (low, high, names) in CATEGORY_PRODUCTS.items():
        code = CATEGORY_CODES[category]
        for i, name in enumerate(names, start=1):
            catalog.append({
                "product_id": f"SKU-{code}-{i:03d}",
                "product_name": name,
                "product_category": category,
                "price_low": low,
                "price_high": high,
            })
    return catalog


def assign_store_provinces(rng):
    """Pin each store to one province (weighted) so a store never spans provinces."""
    provinces = list(PROVINCE_WEIGHTS)
    weights = list(PROVINCE_WEIGHTS.values())
    return {sid: rng.choices(provinces, weights=weights, k=1)[0] for sid in STORE_IDS}


def make_record(rng, catalog, store_provinces):
    """Build one clean, grocery-realistic POS record."""
    store_id = rng.choice(STORE_IDS)
    product = rng.choice(catalog)
    quantity = rng.choices(QUANTITY_CHOICES, weights=QUANTITY_WEIGHTS, k=1)[0]
    unit_price = round(rng.uniform(product["price_low"], product["price_high"]), 2)
    ts = REFERENCE_END - timedelta(seconds=rng.randint(0, WINDOW_SECONDS))

    loyalty_id = None
    if rng.random() < 0.60:  # ~60% of transactions are tied to a Scene+ member
        loyalty_id = f"SCENE{rng.randint(1_000_000_000, 9_999_999_999)}"

    return {
        # Deterministic uuid4 sourced from the seeded RNG (uuid.uuid4() is not seedable).
        "transaction_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
        "store_id": store_id,
        "store_province": store_provinces[store_id],
        "transaction_ts": ts.isoformat(timespec="seconds"),
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "product_category": product["product_category"],
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": round(quantity * unit_price, 2),
        "loyalty_id": loyalty_id,
        "payment_method": rng.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0],
    }


def corrupt(rng, rec):
    """Mutate a record into one realistic failure mode.

    Value violations exercise Silver Expectations; the type-mismatch case puts a
    string into a numeric field so Auto Loader routes it to ``_rescued_data``.
    """
    kind = rng.choice([
        "null_store_id",     # -> valid_store_id (DROP ROW)
        "nonpositive_sale",  # -> positive_amount / positive_quantity (warn)
        "unparseable_ts",    # -> CAST to TIMESTAMP is NULL -> valid_transaction_ts (DROP ROW)
        "missing_category",  # -> known_category (warn)
        "type_mismatch",     # -> string in a numeric field -> _rescued_data
    ])
    if kind == "null_store_id":
        rec["store_id"] = None
    elif kind == "nonpositive_sale":
        rec["quantity"] = rng.choice([0, -1, -2, -3])
        rec["amount"] = round(rec["quantity"] * rec["unit_price"], 2)
    elif kind == "unparseable_ts":
        rec["transaction_ts"] = rng.choice(
            ["not-a-timestamp", "2026-13-45T99:99:99", "31/02/2026", "N/A"]
        )
    elif kind == "missing_category":
        rec["product_category"] = None
    elif kind == "type_mismatch":
        field = rng.choice(["quantity", "unit_price", "store_id"])
        rec[field] = rng.choice(["N/A", "unknown", "--"])
    return kind


def shard_sizes(rows, files):
    """Split ``rows`` as evenly as possible into ``files`` buckets (remainder up front)."""
    base, extra = divmod(rows, files)
    return [base + (1 if i < extra else 0) for i in range(files)]


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate synthetic grocery POS transactions as newline-delimited JSON."
    )
    p.add_argument("--rows", type=int, default=10000, help="Total records to generate (default 10000).")
    p.add_argument("--out", default="./sample_data", help="Output directory (default ./sample_data).")
    p.add_argument("--files", type=int, default=4, help="Number of shard files (default 4).")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility (default 42).")
    return p.parse_args()


def main():
    args = parse_args()
    if args.rows < 1:
        raise SystemExit("--rows must be >= 1")
    if args.files < 1:
        raise SystemExit("--files must be >= 1")

    rng = random.Random(args.seed)
    catalog = build_catalog()
    store_provinces = assign_store_provinces(rng)

    os.makedirs(args.out, exist_ok=True)

    sizes = shard_sizes(args.rows, args.files)
    malformed = 0
    files_written = 0

    for shard_no, size in enumerate(sizes, start=1):
        if size == 0:
            continue  # more files than rows: skip empty shards
        path = os.path.join(args.out, f"part-{shard_no:04d}.json")
        with open(path, "w", encoding="utf-8") as fh:
            for _ in range(size):
                rec = make_record(rng, catalog, store_provinces)
                if rng.random() < MALFORMED_RATE:
                    corrupt(rng, rec)
                    malformed += 1
                fh.write(json.dumps(rec) + "\n")
        files_written += 1

    pct = (malformed / args.rows) * 100 if args.rows else 0.0
    print("POS data generation complete.")
    print(f"  rows written : {args.rows}")
    print(f"  files        : {files_written} (part-0001.json .. part-{files_written:04d}.json)")
    print(f"  malformed    : {malformed} ({pct:.2f}%)")
    print(f"  out dir      : {os.path.abspath(args.out)}")
    print(f"  seed         : {args.seed}")


if __name__ == "__main__":
    main()
