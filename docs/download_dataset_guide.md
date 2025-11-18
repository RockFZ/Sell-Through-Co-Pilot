# Downloading Public Datasets - Quick Guide

## Overview

We've created a script (`scripts/download_dataset.py`) that can download and transform public retail datasets to match our pipeline schema.

## Supported Datasets

### 1. Rossmann Store Sales (Kaggle)
- **Best for**: Large-scale retail forecasting with promotions
- **Size**: 1M+ records, 1,115 stores
- **Features**: Sales, promotions, store metadata

### 2. Online Retail (UCI)
- **Best for**: E-commerce transaction data
- **Size**: ~540K transactions
- **Features**: Product sales, prices, customer data

## Quick Start

### Option 1: Online Retail (Easiest - No Account Needed)

```bash
# Download and transform UCI Online Retail dataset
python scripts/download_dataset.py \
  --dataset online-retail \
  --url https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
```

The script will:
1. Download the dataset
2. Transform it to match our schema
3. Save to `data/raw/`
4. Validate the data

### Option 2: Rossmann via Kaggle API

**First, set up Kaggle API:**
1. Go to https://www.kaggle.com/settings
2. Create API token (downloads `kaggle.json`)
3. Place it in `~/.kaggle/kaggle.json` or set environment variables

**Install Kaggle package:**
```bash
pip install kaggle
```

**Download dataset:**
```bash
python scripts/download_dataset.py \
  --dataset rossmann \
  --kaggle-dataset c/rossmann-store-sales \
  --kaggle-username YOUR_USERNAME \
  --kaggle-key YOUR_KEY
```

### Option 3: Direct URL Download

```bash
# Download from any public URL
python scripts/download_dataset.py \
  --dataset rossmann \
  --url https://example.com/dataset.zip
```

## After Download

Once the dataset is downloaded and transformed:

1. **Verify the data:**
   ```bash
   ls -lh data/raw/
   ```

2. **Run the pipeline:**
   ```bash
   python scripts/run_data_pipeline.py
   ```

3. **Run simulations:**
   ```bash
   python scripts/run_slow_simulation.py --horizon-days 30
   ```

## Data Transformation

The script automatically:
- Maps dataset columns to our schema
- Creates placeholder tables for missing data (returns, lead times, etc.)
- Validates data integrity
- Saves as CSV files in `data/raw/`

## Custom Datasets

To add support for a new dataset:

1. Create a transform function in `scripts/download_dataset.py`
2. Map columns to our schema:
   - `products.csv`: product_id, sku, name, category, unit_cost, unit_price, etc.
   - `sales_history.csv`: date, product_id, channel, units_sold
   - `promo_calendar.csv`: product_id, promo_id, start_date, end_date, discount_pct
   - etc.

3. Add the dataset option to the argument parser

## Troubleshooting

**"kaggle package not installed"**
```bash
pip install kaggle
```

**"Permission denied" (Kaggle)**
- Check your API credentials
- Ensure `kaggle.json` is in `~/.kaggle/`

**"File not found"**
- Check the URL is accessible
- Verify dataset structure matches expected format

**"Validation errors"**
- Some datasets may have missing fields
- The script creates placeholder data for missing tables
- You may need to manually fill in gaps (e.g., returns, lead times)

## Next Steps

After downloading a real dataset:

1. **Compare with synthetic data**: Run both through the pipeline and compare results
2. **Expand scenarios**: Use real data to generate more simulation scenarios
3. **Improve models**: Use real patterns to refine Orbit/Robyn stubs
4. **Scale up**: Generate larger training datasets for surrogate model

## Example: Full Workflow

```bash
# 1. Download dataset
python scripts/download_dataset.py --dataset online-retail

# 2. Run data pipeline
python scripts/run_data_pipeline.py --output-summary data/processed/summary.json

# 3. Run simulation
python scripts/run_slow_simulation.py --horizon-days 30

# 4. Check results
python -c "import pandas as pd; df = pd.read_parquet('data/processed/slow_simulations/sim_log.parquet'); print(f'Generated {len(df)} training examples')"
```


