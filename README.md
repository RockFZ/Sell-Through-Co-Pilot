# Sell-Through Co-Pilot — Milestone 2

Inventory optimization system integrating **Uber Orbit** (demand forecasting), **Meta Robyn** (marketing mix modeling), and an **XGBoost surrogate model** for fast scenario analysis.

## Repository Structure

- `data/raw/`: Raw CSV files (products, sales, promotions, inventory, etc.)
- `data/processed/`: Processed Parquet tables and trained surrogate model
- `src/`: Core Python package
  - `forecast/`: Orbit integration for demand forecasting
  - `promo/`: Robyn integration for promotional lift modeling
  - `surrogate/`: XGBoost surrogate model for fast predictions
  - `simulations/`: Inventory simulation engine
  - `demo/`: Backend for Gradio demo interface
- `scripts/`: CLI entry points for pipeline, training, and demo
- `docs/`: Documentation and reports

## Quick Start

### 1. Setup Environment

```bash
# Create and activate conda environment (recommended)
conda create -n DEMO python=3.11 -y
conda activate DEMO

# Or use virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Note for macOS:** Install OpenMP for XGBoost:
```bash
brew install libomp
```

### 2. Prepare Data and Train Model

```bash
# Run data pipeline to generate processed tables
python scripts/run_data_pipeline.py --output-summary data/processed/summary.json

# Run simulation to generate training data
python scripts/run_slow_simulation.py --horizon-days 21

# Train surrogate model
python scripts/train_surrogate.py --use-gpu
```

### 3. Run the Demo

```bash
python scripts/run_gradio_demo.py
```

The demo will launch at `http://localhost:7860`. Open this URL in your browser to interact with the model.

## Demo Features

- **Product Selection**: Choose from available products
- **Scenario Testing**: Adjust discount %, ad spend multiplier, and starting inventory
- **Real-time Predictions**: See results in under 1 millisecond
- **Model Transparency**: View features sent to the model
- **Baseline Comparison**: Compare scenarios against baseline predictions

## Key Workflows

### Data Pipeline
```bash
python scripts/run_data_pipeline.py
```
Generates: `daily_demand.parquet`, `product_features.parquet`, `expanded_promos.parquet`

### Simulation
```bash
python scripts/run_slow_simulation.py --horizon-days 21
```
Generates: `slow_simulations/sim_log.parquet` (training data)

### Model Training
```bash
python scripts/train_surrogate.py --use-gpu
```
Trains XGBoost models for: `realized_demand`, `lost_sales`, `service_level`, `lost_sales_rate`, `order_qty`

## Performance

- **Surrogate Model**: <1ms inference time
- **Full Simulation**: ~12 seconds per scenario
- **Speedup**: 12,000x faster than full simulation

## Documentation

- Demo script: `docs/demo_script.md`
- Milestone 2 report: `docs/milestone2_report.md`
- Implementation details: `docs/milestone2_implementation.md`
