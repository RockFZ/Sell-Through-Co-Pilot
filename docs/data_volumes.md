# Data Volumes: Current vs. Target

## Current Data (Milestone 1)

### Raw Input Data
| Dataset | Rows | Columns | Description |
|---------|------|---------|-------------|
| `products.csv` | 4 | 9 | Product master data (SKU, cost, price, inventory limits) |
| `sales_history.csv` | 56 | 4 | Historical sales by product, channel, date |
| `returns.csv` | 6 | 4 | Return transactions with time-to-return |
| `lead_times.csv` | 4 | 6 | Supplier lead-time statistics |
| `promo_calendar.csv` | 4 | 6 | Promotional campaigns (start/end, discount %) |
| `ad_spend.csv` | 10 | 4 | Advertising spend by channel and date |
| `current_inventory.csv` | 4 | 5 | Current on-hand, on-order, reserved units |

**Total Raw Data:** ~92 rows across 7 files

### Processed Data
| Dataset | Rows | Columns | Purpose |
|---------|------|---------|---------|
| `daily_demand.parquet` | 56 | 4 | Aggregated demand by day/product/channel |
| `product_features.parquet` | 4 | 25 | Enriched product attributes (demand stats, returns, lead times, safety stock) |
| `expanded_promos.parquet` | 14 | 5 | Day-level promotional schedule |
| `simulation_schedule.parquet` | 120 | 18 | 30-day forward planning table |

**Total Processed Data:** ~194 rows

### Simulation Logs (Training Data)
| Metric | Value |
|--------|-------|
| **Total Records** | 84 |
| **Products Simulated** | 4 |
| **Simulation Horizon** | 21 days |
| **Total Projected Demand** | 1,600.9 units |
| **Total Realized Demand** | 935.2 units |
| **Total Lost Sales** | 665.7 units |
| **File Size** | ~15 KB (Parquet) |

**Current Training Dataset:** 84 labeled examples (product × day combinations)

---

## Target Data (Full Project)

### Raw Input Data (Target)
| Dataset | Target Rows | Rationale |
|---------|-------------|-----------|
| `products.csv` | **50-100 SKUs** | Representative product catalog across categories |
| `sales_history.csv` | **~10,000-20,000** | 1-2 years of daily sales history (50 SKUs × 365 days × ~1.5 channels) |
| `returns.csv` | **~500-1,000** | Return transactions over 1-2 years |
| `lead_times.csv` | **50-100** | One row per product-supplier combination |
| `promo_calendar.csv` | **~200-500** | Promotional campaigns over 1-2 years |
| `ad_spend.csv` | **~1,000-2,000** | Daily ad spend across multiple channels |
| `current_inventory.csv` | **50-100** | Current inventory positions per SKU |

**Target Raw Data:** ~12,000-24,000 rows

### Processed Data (Target)
| Dataset | Target Rows | Purpose |
|---------|-------------|---------|
| `daily_demand.parquet` | **~10,000-20,000** | Historical demand patterns for forecasting |
| `product_features.parquet` | **50-100** | Feature vectors per SKU |
| `expanded_promos.parquet` | **~5,000-10,000** | Day-level promo schedule over 1-2 years |
| `simulation_schedule.parquet` | **~1,500-3,000** | 30-day forward plan for all SKUs |

**Target Processed Data:** ~16,500-33,000 rows

### Simulation Logs (Training Data Target)
| Metric | Target | Rationale |
|--------|--------|-----------|
| **Total Records** | **~50,000-100,000** | Sufficient for XGBoost surrogate training |
| **Products Simulated** | **50-100 SKUs** | Representative product mix |
| **Simulation Scenarios** | **3-5 scenarios** | Normal week, big promo, influencer spike, seasonal, etc. |
| **Horizon per Scenario** | **30-90 days** | Various planning horizons |
| **Total Projected Demand** | **~500,000-1,000,000 units** | Realistic demand volumes |
| **File Size** | **~5-10 MB** | Parquet compression |

**Target Training Dataset:** 50,000-100,000 labeled examples

---

## Data Generation Strategy

### Phase 1: Current (Milestone 1) ✅
- **4 products** (proof of concept)
- **21-day simulation** (single scenario)
- **84 training examples**

### Phase 2: Expansion (Milestone 2-3)
- **5-10 products** (expand catalog)
- **Multiple scenarios** (normal, promo, spike)
- **30-90 day horizons** per scenario
- **~1,000-5,000 training examples**

### Phase 3: Full Scale (Milestone 4-5)
- **50-100 products** (full catalog)
- **5+ scenarios** with variations
- **Multiple reorder policies** (min-max, order-up-to, etc.)
- **50,000-100,000 training examples**

---

## Data Quality Considerations

### Current Limitations
- **Synthetic data**: All inputs are manually created examples
- **Limited history**: Only ~56 days of sales history
- **Single scenario**: One simulation run

### Target Improvements
- **Real ERP data**: Swap synthetic for Odoo/ERPNext extracts
- **Extended history**: 1-2 years of actual sales/promo data
- **Multiple scenarios**: Normal operations, promotions, demand spikes, seasonality
- **Policy variations**: Different reorder rules, service levels, constraints

---

## Storage Estimates

| Stage | Current | Target |
|-------|---------|--------|
| **Raw CSVs** | ~10 KB | ~500 KB - 1 MB |
| **Processed Parquet** | ~50 KB | ~2-5 MB |
| **Simulation Logs** | ~15 KB | ~5-10 MB |
| **Total** | **~75 KB** | **~8-16 MB** |

*Note: Parquet compression significantly reduces storage vs. CSV*

---

## Key Metrics for Professor

**Current:**
- ✅ Pipeline operational with 4 products
- ✅ 84 simulation records generated
- ✅ Proof of concept complete

**Target:**
- 🎯 50-100 products for production scale
- 🎯 50,000-100,000 training examples for surrogate model
- 🎯 Multiple scenarios covering normal ops, promos, spikes
- 🎯 Real ERP data integration (Odoo/ERPNext)

**Timeline:**
- **Milestone 1** (Current): 4 products, 84 examples ✅
- **Milestone 2-3**: 10 products, ~5,000 examples
- **Milestone 4-5**: 50-100 products, 50,000-100,000 examples

