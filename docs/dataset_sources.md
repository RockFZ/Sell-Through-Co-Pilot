# Recommended Public Datasets for Sell-Through Co-Pilot

## Top Recommendations

### 1. **Rossmann Store Sales** (Kaggle)
- **URL**: https://www.kaggle.com/c/rossmann-store-sales
- **Size**: ~1M+ sales records across 1,115 stores
- **Features**: 
  - Daily sales by store/product
  - Promotions (Promo flag)
  - Store metadata (competition, state, etc.)
  - School holidays
- **Why it fits**: Real retail data with promotions, time-series structure
- **Download**: Requires Kaggle account + API key

### 2. **Walmart Store Sales Forecasting** (Kaggle)
- **URL**: https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting
- **Size**: Weekly sales for 45 stores, multiple departments
- **Features**:
  - Weekly sales by store/department
  - Holiday indicators
  - Temperature, fuel price, CPI
- **Why it fits**: Multi-store, multi-product structure

### 3. **Retail Sales Dataset** (UCI / Kaggle)
- **URL**: Various sources
- **Features**: Product sales, inventory levels, promotions
- **Why it fits**: Often includes inventory and promotional data

### 4. **Online Retail Dataset** (UCI)
- **URL**: https://archive.ics.uci.edu/ml/datasets/Online+Retail
- **Size**: ~540K transactions
- **Features**:
  - Invoice date, quantity, price
  - Product descriptions
  - Customer IDs
  - Country
- **Why it fits**: Real e-commerce transaction data

### 5. **Favorita Store Sales** (Kaggle)
- **URL**: https://www.kaggle.com/c/favorita-grocery-sales-forecasting
- **Size**: 4+ years of daily sales, 54 products, 50+ stores
- **Features**:
  - Daily sales by store/product
  - Promotions
  - Holiday calendar
  - Oil prices, local events
- **Why it fits**: Large-scale, includes promotions, long time-series

---

## Integration Strategy

### Option 1: Kaggle API (Recommended)
```bash
pip install kaggle
# Set up API credentials
kaggle competitions download -c rossmann-store-sales
```

### Option 2: Direct Download Script
Create a download utility that:
- Downloads from public URLs
- Transforms to our schema
- Validates data quality
- Integrates into pipeline

### Option 3: Synthetic Data Generator
Use statistical models to generate realistic data based on:
- Real-world patterns (seasonality, promotions)
- Industry benchmarks
- Academic research on retail demand

---

## Schema Mapping

### Rossmann → Our Schema
| Rossmann | Our Schema | Notes |
|----------|------------|-------|
| `Date` | `date` | Direct mapping |
| `Store` | `product_id` | Treat store as product variant |
| `Sales` | `units_sold` | May need to normalize |
| `Promo` | `promo_calendar` | Boolean → discount % |
| `StateHoliday` | `promo_calendar` | Holiday promotions |
| `SchoolHoliday` | `promo_calendar` | Additional promo context |

### Online Retail → Our Schema
| Online Retail | Our Schema | Notes |
|---------------|------------|-------|
| `InvoiceDate` | `date` | Direct mapping |
| `StockCode` | `product_id` | Direct mapping |
| `Quantity` | `units_sold` | Direct mapping |
| `UnitPrice` | `unit_price` | Direct mapping |
| `Description` | `name` | Product name |

---

## Next Steps

1. **Choose a dataset** based on:
   - Data quality and completeness
   - Relevance to our use case
   - Ease of integration
   - License compatibility

2. **Create download script** (`scripts/download_dataset.py`):
   - Handle authentication (Kaggle API)
   - Download and extract data
   - Transform to our schema
   - Validate and load into `data/raw/`

3. **Update pipeline** to handle:
   - Different data formats
   - Missing fields (with defaults)
   - Data quality checks

4. **Test integration**:
   - Run full pipeline on new dataset
   - Verify simulation outputs
   - Compare with synthetic data results


