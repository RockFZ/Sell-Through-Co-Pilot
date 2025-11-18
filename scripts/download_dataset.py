#!/usr/bin/env python3
"""
Download and integrate public retail datasets into the Sell-Through Co-Pilot pipeline.

Supports:
- Kaggle datasets (requires API credentials)
- Direct URL downloads
- UCI datasets
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src import config, validation  # pylint: disable=wrong-import-position


def download_file(url: str, output_path: Path, chunk_size: int = 8192) -> None:
    """Download a file from URL to local path."""
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            f.write(chunk)
    print(f"Saved to {output_path}")


def download_kaggle_dataset(
    dataset_name: str, output_dir: Path, kaggle_username: str | None = None, kaggle_key: str | None = None
) -> None:
    """Download dataset from Kaggle using API."""
    try:
        import kaggle
    except ImportError:
        print("ERROR: kaggle package not installed. Run: pip install kaggle")
        sys.exit(1)

    if kaggle_username and kaggle_key:
        import os

        os.environ["KAGGLE_USERNAME"] = kaggle_username
        os.environ["KAGGLE_KEY"] = kaggle_key

    print(f"Downloading Kaggle dataset: {dataset_name}")
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(dataset_name, path=str(output_dir), unzip=True)
    print(f"Dataset extracted to {output_dir}")


def transform_rossmann_data(data_dir: Path, output_dir: Path) -> Dict[str, pd.DataFrame]:
    """Transform Rossmann Store Sales data to our schema."""
    print("Transforming Rossmann data...")

    train_path = data_dir / "train.csv"
    store_path = data_dir / "store.csv"

    if not train_path.exists():
        raise FileNotFoundError(f"Expected {train_path} not found")

    train_df = pd.read_csv(train_path)
    train_df["Date"] = pd.to_datetime(train_df["Date"])

    # Create products table (treat Store as product variant)
    if store_path.exists():
        store_df = pd.read_csv(store_path)
        products = store_df.copy()
        products["product_id"] = "STORE-" + products["Store"].astype(str)
        products["sku"] = products["product_id"]
        products["name"] = "Store " + products["Store"].astype(str)
        products["category"] = "Retail Store"
        products["unit_cost"] = 0.0  # Not available in dataset
        products["unit_price"] = train_df["Sales"].mean() / train_df["Customers"].mean() if "Customers" in train_df.columns else 10.0
        products["case_pack"] = 1
        products["min_inventory"] = 0
        products["max_inventory"] = 1000
    else:
        # Fallback: create products from train data
        unique_stores = train_df["Store"].unique()
        products = pd.DataFrame(
            {
                "product_id": ["STORE-" + str(s) for s in unique_stores],
                "sku": ["STORE-" + str(s) for s in unique_stores],
                "name": ["Store " + str(s) for s in unique_stores],
                "category": ["Retail Store"] * len(unique_stores),
                "unit_cost": [0.0] * len(unique_stores),
                "unit_price": [10.0] * len(unique_stores),
                "case_pack": [1] * len(unique_stores),
                "min_inventory": [0] * len(unique_stores),
                "max_inventory": [1000] * len(unique_stores),
            }
        )

    # Create sales history
    sales_history = train_df[["Date", "Store", "Sales", "Customers"]].copy()
    sales_history = sales_history.rename(
        columns={"Date": "date", "Store": "product_id", "Sales": "units_sold"}
    )
    sales_history["product_id"] = "STORE-" + sales_history["product_id"].astype(str)
    sales_history["channel"] = "store"  # Default channel

    # Create promo calendar
    promo_dates = train_df[train_df["Promo"] == 1].copy()
    if not promo_dates.empty:
        promo_calendar = []
        for _, row in promo_dates.iterrows():
            promo_calendar.append(
                {
                    "product_id": "STORE-" + str(row["Store"]),
                    "promo_id": f"PROMO-{row['Date']}",
                    "start_date": row["Date"],
                    "end_date": row["Date"],
                    "discount_pct": 10.0,  # Default discount
                    "description": "Store Promotion",
                }
            )
        promo_calendar = pd.DataFrame(promo_calendar)
    else:
        promo_calendar = pd.DataFrame(
            columns=["product_id", "promo_id", "start_date", "end_date", "discount_pct", "description"]
        )

    # Create placeholder tables
    returns = pd.DataFrame(columns=["date", "product_id", "units_returned", "days_to_return"])
    lead_times = pd.DataFrame(
        {
            "product_id": products["product_id"],
            "supplier_id": ["SUP-1"] * len(products),
            "supplier_name": ["Default Supplier"] * len(products),
            "avg_lead_time_days": [7.0] * len(products),
            "lead_time_std_days": [2.0] * len(products),
            "min_order_qty": [1] * len(products),
        }
    )
    current_inventory = pd.DataFrame(
        {
            "product_id": products["product_id"],
            "on_hand_units": [100.0] * len(products),
            "on_order_units": [0.0] * len(products),
            "reserved_units": [0.0] * len(products),
            "warehouse": ["MAIN"] * len(products),
        }
    )
    ad_spend = pd.DataFrame(columns=["date", "channel", "planned_spend", "description"])

    return {
        "products": products,
        "sales_history": sales_history,
        "returns": returns,
        "lead_times": lead_times,
        "promo_calendar": promo_calendar,
        "ad_spend": ad_spend,
        "current_inventory": current_inventory,
    }


def transform_online_retail_data(data_path: Path) -> Dict[str, pd.DataFrame]:
    """Transform UCI Online Retail data to our schema."""
    print("Transforming Online Retail data...")

    df = pd.read_csv(data_path, encoding="latin-1")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format="%m/%d/%Y %H:%M", errors="coerce")
    df = df.dropna(subset=["InvoiceDate"])

    # Create products table
    products = (
        df.groupby(["StockCode", "Description"])
        .agg({"UnitPrice": "mean", "Quantity": "sum"})
        .reset_index()
    )
    products = products.rename(columns={"StockCode": "product_id", "Description": "name"})
    products["sku"] = products["product_id"]
    products["category"] = "Retail"
    products["unit_cost"] = products["UnitPrice"] * 0.6  # Estimate cost at 60% of price
    products["unit_price"] = products["UnitPrice"]
    products["case_pack"] = 1
    products["min_inventory"] = 0
    products["max_inventory"] = 1000
    products = products[["product_id", "sku", "name", "category", "unit_cost", "unit_price", "case_pack", "min_inventory", "max_inventory"]]

    # Create sales history
    df["date"] = df["InvoiceDate"].dt.date
    sales_history = df.groupby(["date", "StockCode", "Country"]).agg({"Quantity": "sum"}).reset_index()
    sales_history = sales_history.rename(
        columns={"date": "date", "StockCode": "product_id", "Quantity": "units_sold", "Country": "channel"}
    )
    sales_history["date"] = pd.to_datetime(sales_history["date"])

    # Create placeholder tables
    returns = pd.DataFrame(columns=["date", "product_id", "units_returned", "days_to_return"])
    lead_times = pd.DataFrame(
        {
            "product_id": products["product_id"],
            "supplier_id": ["SUP-1"] * len(products),
            "supplier_name": ["Default Supplier"] * len(products),
            "avg_lead_time_days": [7.0] * len(products),
            "lead_time_std_days": [2.0] * len(products),
            "min_order_qty": [1] * len(products),
        }
    )
    current_inventory = pd.DataFrame(
        {
            "product_id": products["product_id"],
            "on_hand_units": [100.0] * len(products),
            "on_order_units": [0.0] * len(products),
            "reserved_units": [0.0] * len(products),
            "warehouse": ["MAIN"] * len(products),
        }
    )
    promo_calendar = pd.DataFrame(
        columns=["product_id", "promo_id", "start_date", "end_date", "discount_pct", "description"]
    )
    ad_spend = pd.DataFrame(columns=["date", "channel", "planned_spend", "description"])

    return {
        "products": products,
        "sales_history": sales_history,
        "returns": returns,
        "lead_times": lead_times,
        "promo_calendar": promo_calendar,
        "ad_spend": ad_spend,
        "current_inventory": current_inventory,
    }


def save_transformed_data(frames: Dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Save transformed dataframes to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in frames.items():
        output_path = output_dir / f"{name}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved {name}: {len(df)} rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=["rossmann", "online-retail", "kaggle"],
        required=True,
        help="Dataset to download and transform",
    )
    parser.add_argument(
        "--kaggle-dataset",
        type=str,
        help="Kaggle dataset name (e.g., 'c/rossmann-store-sales')",
    )
    parser.add_argument(
        "--kaggle-username",
        type=str,
        help="Kaggle username for API authentication",
    )
    parser.add_argument(
        "--kaggle-key",
        type=str,
        help="Kaggle API key",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Direct URL to download dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.RAW_DATA_DIR,
        help="Directory to save transformed data",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=Path("data/temp"),
        help="Temporary directory for downloads",
    )
    args = parser.parse_args()

    args.temp_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset == "rossmann":
        if args.kaggle_dataset:
            download_kaggle_dataset(args.kaggle_dataset, args.temp_dir, args.kaggle_username, args.kaggle_key)
        elif args.url:
            zip_path = args.temp_dir / "rossmann.zip"
            download_file(args.url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(args.temp_dir)
        else:
            print("ERROR: Need --kaggle-dataset or --url for Rossmann data")
            sys.exit(1)

        frames = transform_rossmann_data(args.temp_dir, args.output_dir)
        save_transformed_data(frames, args.output_dir)

    elif args.dataset == "online-retail":
        if args.url:
            data_path = args.temp_dir / "online_retail.csv"
            download_file(args.url, data_path)
        else:
            # Try default UCI URL
            default_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx"
            data_path = args.temp_dir / "online_retail.xlsx"
            try:
                download_file(default_url, data_path)
                # Convert Excel to CSV if needed
                if data_path.suffix == ".xlsx":
                    df = pd.read_excel(data_path)
                    csv_path = args.temp_dir / "online_retail.csv"
                    df.to_csv(csv_path, index=False)
                    data_path = csv_path
            except Exception as e:
                print(f"ERROR: Could not download from default URL: {e}")
                print("Please provide --url with direct link to dataset")
                sys.exit(1)

        frames = transform_online_retail_data(data_path)
        save_transformed_data(frames, args.output_dir)

    elif args.dataset == "kaggle":
        if not args.kaggle_dataset:
            print("ERROR: --kaggle-dataset required for Kaggle downloads")
            sys.exit(1)
        download_kaggle_dataset(args.kaggle_dataset, args.temp_dir, args.kaggle_username, args.kaggle_key)
        print("Downloaded Kaggle dataset. Manual transformation may be required.")
        print(f"Files saved to: {args.temp_dir}")

    # Validate transformed data
    print("\nValidating transformed data...")
    try:
        validation.validate_all_raw_files(args.output_dir)
        print("✓ All files validated successfully")
    except Exception as e:
        print(f"⚠ Validation warnings: {e}")

    print(f"\n✓ Dataset transformation complete. Files saved to {args.output_dir}")


if __name__ == "__main__":
    main()

