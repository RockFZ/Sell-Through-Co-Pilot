# The Simulation: How It Works and How Orbit & Robyn Are Used

## Overview

The simulation is a **day-by-day inventory play-out** that combines:
- **Orbit** (demand forecasting)
- **Robyn** (marketing lift factors)
- **ERP reorder rules** (inventory management)

It simulates what happens to inventory over a planning horizon (e.g., 21-30 days), tracking stock levels, sales, stockouts, and purchase orders.

---

## The Big Picture: Data Flow

```
┌─────────────────────┐
│ Historical Sales    │ ───┐
│ Data                │    │
└─────────────────────┘    │
                            ▼
                    ┌───────────────┐
                    │  Uber Orbit   │
                    │  (Forecasting)│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Baseline      │
                    │ Forecasts     │
                    │ (e.g., 11.5   │
                    │  units/day)   │
                    └───────┬───────┘
                            │
                            │
┌─────────────────────┐     │
│ Promos + Ad Spend   │ ────┼──┐
└─────────────────────┘     │  │
                            │  │
                    ┌───────┴──┴───┐
                    │  Meta Robyn   │
                    │  (MMM)        │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Lift Factors   │
                    │ (e.g., 1.218x) │
                    └───────┬───────┘
                            │
                            │
                    ┌───────┴───────┐
                    │   COMBINED     │
                    │ Projected      │
                    │ Demand =       │
                    │ Forecast × Lift│
                    │ (e.g., 14.0    │
                    │  units/day)    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Day-by-Day     │
                    │ Simulation     │
                    │ (Inventory      │
                    │  Play-out)     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Outcomes:      │
                    │ - Sales        │
                    │ - Stockouts    │
                    │ - Orders       │
                    │ - Inventory    │
                    └────────────────┘
```

---

## Part 1: How Orbit is Used

### What Orbit Does

**Orbit** is a Bayesian time-series forecasting library that predicts **baseline demand** (what customers would buy without promotions or advertising).

### Where Orbit is Called

**File:** `scripts/run_slow_simulation.py` (line 74)

```python
# Generate forecasts using Orbit
forecasts = forecast_bundle(snapshot["daily_demand"], config=orbit_cfg)
```

### What Orbit Receives

**Input:** Historical sales data
```python
daily_demand = DataFrame([
    {"date": "2024-01-01", "product_id": "SKU-001", "units_sold": 10},
    {"date": "2024-01-02", "product_id": "SKU-001", "units_sold": 12},
    {"date": "2024-01-03", "product_id": "SKU-001", "units_sold": 11},
    ...
])
```

### What Orbit Produces

**Output:** Forecasts for future dates
```python
forecasts = {
    "SKU-001": DataFrame([
        {"date": "2024-02-01", "forecast_units": 11.5, "forecast_lower": 8.0, "forecast_upper": 15.0},
        {"date": "2024-02-02", "forecast_units": 11.5, "forecast_lower": 8.0, "forecast_upper": 15.0},
        ...
    ])
}
```

**Key Point:** Orbit predicts **baseline demand** - what would happen if there were no promotions or ads.

### How Orbit is Used in Simulation

**File:** `src/simulations/inventory_engine.py` (lines 83-90)

```python
# Get Orbit forecast for this product and date
product_forecast = forecasts[product_id].set_index("date")
forecast_row = product_forecast.loc[date]
baseline_demand = forecast_row["forecast_units"]  # From Orbit (e.g., 11.5 units)
```

---

## Part 2: How Robyn is Used

### What Robyn Does

**Robyn** is a Marketing Mix Modeling (MMM) library that calculates **lift factors** - how much promotions and advertising increase demand above baseline.

### Where Robyn is Called

**File:** `scripts/run_slow_simulation.py` (lines 84-91)

```python
# Generate lift table using Robyn
lifts = build_lift_table(
    sim_inputs["expanded_promos"],      # Promotional calendar
    snapshot["ad_spend"],               # Advertising spend
    snapshot["product_features"]["product_id"],
    horizon_dates,                      # Future dates to simulate
    config=robyn_cfg,
    historical_sales=snapshot["daily_demand"],
)
```

### What Robyn Receives

**Input 1:** Promotional calendar
```python
expanded_promos = DataFrame([
    {"date": "2024-02-01", "product_id": "SKU-001", "discount_pct": 10.0},
    {"date": "2024-02-02", "product_id": "SKU-001", "discount_pct": 0.0},
    ...
])
```

**Input 2:** Advertising spend
```python
ad_spend = DataFrame([
    {"date": "2024-02-01", "channel": "social", "planned_spend": 100},
    {"date": "2024-02-02", "channel": "social", "planned_spend": 50},
    ...
])
```

### What Robyn Produces

**Output:** Lift factors per product-date
```python
lifts = DataFrame([
    {
        "date": "2024-02-01",
        "product_id": "SKU-001",
        "promo_lift": 1.16,      # 10% discount = 16% increase
        "ad_lift": 1.05,          # $100 ad spend = 5% increase
        "total_lift": 1.218       # Combined: 1.16 × 1.05 = 1.218
    },
    ...
])
```

**Key Point:** Robyn calculates **lift multipliers** - how much promotions and ads boost demand.

### How Robyn is Used in Simulation

**File:** `src/simulations/inventory_engine.py` (lines 88-90)

```python
# Get Robyn lift for this product and date
lift_row = lift_lookup.loc[(product_id, date)]
total_lift = float(lift_row.get("total_lift", 1.0))  # From Robyn (e.g., 1.218)
```

---

## Part 3: How They Combine

### The Integration Formula

**File:** `src/simulations/inventory_engine.py` (line 90)

```python
# Combine Orbit forecast + Robyn lift
projected_demand = forecast_row["forecast_units"] * total_lift
```

**Example:**
- Orbit says: "Baseline demand = 11.5 units/day"
- Robyn says: "10% discount + $100 ads = 1.218x lift"
- **Result:** Projected demand = 11.5 × 1.218 = **14.0 units/day**

This **projected demand** is then used in the day-by-day simulation.

---

## Part 4: The Day-by-Day Simulation Process

### Overview

The simulation runs **day-by-day** for each product, tracking:
- Inventory levels (on-hand, in-transit, reserved)
- Demand realization (how much was actually sold)
- Lost sales (unfulfilled demand)
- Purchase orders (when and how much to order)

### Initialization (Before Day 1)

**File:** `src/simulations/inventory_engine.py` (lines 75-81)

```python
# Initialize inventory state
state = {
    "on_hand": 85.0,        # Current stock
    "in_transit": 0.0,      # Orders on the way
    "reserved": 5.0,        # Reserved for other orders
    "backlog": 0.0,         # Unfulfilled demand
}

# Track when orders will arrive
arrivals = {}  # {date: quantity}

# Get product attributes
lead_time = 7  # Days for orders to arrive
```

### Day-by-Day Loop

**File:** `src/simulations/inventory_engine.py` (lines 85-132)

For each day in the simulation horizon:

#### Step 1: Get Projected Demand (Orbit + Robyn)

```python
# Get Orbit forecast (baseline demand)
forecast_row = product_forecast.loc[date]
baseline_demand = forecast_row["forecast_units"]  # e.g., 11.5 units

# Get Robyn lift (promo + ad multiplier)
lift_row = lift_lookup.loc[(product_id, date)]
total_lift = lift_row.get("total_lift", 1.0)  # e.g., 1.218

# Combine: Projected Demand = Baseline × Lift
projected_demand = baseline_demand * total_lift  # e.g., 14.0 units
```

#### Step 2: Receive Incoming Orders

```python
# Check if any orders arrive today
inbound = arrivals.pop(date, 0.0)  # e.g., 20 units arriving

if inbound:
    state["on_hand"] += inbound      # Add to inventory
    state["in_transit"] -= inbound   # Remove from in-transit
```

**Example:** If you ordered 20 units 7 days ago, they arrive today.

#### Step 3: Calculate Available Inventory

```python
# Available = On-hand minus reserved
available_for_sale = max(state["on_hand"] - state["reserved"], 0.0)
# e.g., 85 - 5 = 80 units available
```

#### Step 4: Fulfill Demand (or Record Lost Sales)

```python
# Can only sell what's available
realized_demand = min(available_for_sale, projected_demand)
# e.g., min(80, 14) = 14 units sold

# Lost sales = demand we couldn't fulfill
lost_sales = max(projected_demand - available_for_sale, 0.0)
# e.g., max(14 - 80, 0) = 0 (no lost sales if we have enough)
```

**Example Scenarios:**
- **Enough stock:** Projected = 14, Available = 80 → Sold = 14, Lost = 0
- **Stockout:** Projected = 14, Available = 5 → Sold = 5, Lost = 9

#### Step 5: Update Inventory State

```python
# Update on-hand inventory
state["on_hand"] = available_for_sale - realized_demand + state["reserved"]
# e.g., 80 - 14 + 5 = 71 units remaining

# Update backlog (unfulfilled demand)
state["backlog"] = min(
    state["backlog"] + lost_sales,
    projected_demand * config.max_backlog_days,
)
```

#### Step 6: Check if Reorder is Needed

```python
# Calculate reorder quantity using min-max policy
order_qty = _calculate_reorder_quantity(product_row, state)

if order_qty > 0:
    # Schedule order arrival
    arrival_date = date + pd.Timedelta(days=lead_time)  # e.g., 7 days from now
    arrivals[arrival_date] = arrivals.get(arrival_date, 0.0) + order_qty
    state["in_transit"] += order_qty
```

**Reorder Logic (Min-Max Policy):**
- If inventory drops below `min_inventory`, order up to `max_inventory`
- Round up to case pack size
- Respect minimum order quantity

#### Step 7: Log Results

```python
results.append({
    "product_id": product_id,
    "date": date,
    "on_hand_start": on_hand_start,      # Inventory at start of day
    "inbound_units": inbound,             # Orders received
    "realized_demand": realized_demand,  # Units sold
    "projected_demand": projected_demand, # Demand from Orbit × Robyn
    "lost_sales": lost_sales,            # Unfulfilled demand
    "on_hand_end": state["on_hand"],     # Inventory at end of day
    "backlog_units": state["backlog"],   # Unfulfilled orders
    "order_qty": order_qty,              # Purchase order placed
    "safety_stock_units": safety_stock,
})
```

### Complete Example: One Day of Simulation

**Day 1 (2024-02-01) for SKU-001:**

**Initial State:**
- On-hand: 85 units
- In-transit: 0 units
- Reserved: 5 units

**Step 1: Get Projected Demand**
- Orbit forecast: 11.5 units/day
- Robyn lift: 1.218x (10% discount + $100 ads)
- **Projected demand: 11.5 × 1.218 = 14.0 units**

**Step 2: Receive Orders**
- No orders arriving today
- Inbound: 0 units

**Step 3: Calculate Available**
- Available = 85 - 5 = 80 units

**Step 4: Fulfill Demand**
- Realized demand = min(80, 14) = **14 units sold**
- Lost sales = max(14 - 80, 0) = **0 units**

**Step 5: Update Inventory**
- On-hand end = 80 - 14 + 5 = **71 units**

**Step 6: Check Reorder**
- Current: 71 units
- Min inventory: 50 units
- Max inventory: 100 units
- **No reorder needed** (above minimum)

**Step 7: Log Results**
```python
{
    "product_id": "SKU-001",
    "date": "2024-02-01",
    "on_hand_start": 85,
    "inbound_units": 0,
    "realized_demand": 14,
    "projected_demand": 14.0,
    "lost_sales": 0,
    "on_hand_end": 71,
    "backlog_units": 0,
    "order_qty": 0,
}
```

---

## Part 5: Complete Simulation Flow

### Setup Phase

**File:** `scripts/run_slow_simulation.py` (lines 42-91)

1. **Load Data**
   ```python
   raw_frames = data_loader.load_raw_frames()
   snapshot = transformations.build_planning_snapshot(raw_frames)
   sim_inputs = sim_prep.prepare_simulation_inputs(raw_frames)
   ```

2. **Generate Orbit Forecasts**
   ```python
   forecasts = forecast_bundle(snapshot["daily_demand"], config=orbit_cfg)
   # Output: {product_id: DataFrame with forecasts}
   ```

3. **Generate Robyn Lifts**
   ```python
   lifts = build_lift_table(
       sim_inputs["expanded_promos"],
       snapshot["ad_spend"],
       products,
       horizon_dates,
       config=robyn_cfg,
   )
   # Output: DataFrame with lift factors per product-date
   ```

4. **Prepare Simulation Schedule**
   ```python
   schedule = sim_inputs["simulation_schedule"]
   schedule = schedule[schedule["date"].isin(horizon_dates)]
   ```

### Simulation Phase

**File:** `src/simulations/inventory_engine.py` (lines 51-134)

For each product:
1. Initialize inventory state
2. For each day in horizon:
   - Get Orbit forecast (baseline demand)
   - Get Robyn lift (marketing multiplier)
   - Calculate projected demand = forecast × lift
   - Receive incoming orders
   - Fulfill demand (or record lost sales)
   - Update inventory state
   - Check reorder rules
   - Log results

### Output Phase

**File:** `scripts/run_slow_simulation.py` (lines 117-131)

1. **Simulation Logs**
   ```python
   simulation_log = run_inventory_simulation(...)
   # DataFrame with day-by-day results
   ```

2. **Summary Statistics**
   ```python
   summary = simulation_log.groupby("product_id").agg({
       total_projected_demand=("projected_demand", "sum"),
       total_realized_demand=("realized_demand", "sum"),
       total_lost_sales=("lost_sales", "sum"),
       total_orders=("order_qty", "sum"),
   })
   ```

---

## Part 6: Key Concepts

### 1. Projected Demand vs. Realized Demand

**Projected Demand:**
- What Orbit + Robyn predict (e.g., 14.0 units/day)
- Based on forecasts and lift factors
- **May not be fulfilled** if inventory is insufficient

**Realized Demand:**
- What actually gets sold (e.g., 10 units/day)
- Limited by available inventory
- **Always ≤ Projected Demand**

**Lost Sales:**
- Unfulfilled demand = Projected - Realized
- Example: Projected = 14, Realized = 10 → Lost = 4

### 2. Inventory State Tracking

**On-Hand:**
- Physical inventory in warehouse
- Decreases when items are sold
- Increases when orders arrive

**In-Transit:**
- Orders placed but not yet arrived
- Arrives after lead time (e.g., 7 days)

**Reserved:**
- Inventory reserved for other orders
- Not available for sale

**Backlog:**
- Unfulfilled demand that accumulates
- Capped at `max_backlog_days × projected_demand`

### 3. Reorder Rules (Min-Max Policy)

**Min Inventory:**
- Minimum stock level to maintain
- Triggers reorder when below

**Max Inventory:**
- Target stock level
- Order up to this level

**Example:**
- Min = 50 units, Max = 100 units
- Current = 45 units → Order 55 units (to reach 100)
- Current = 60 units → No order needed

### 4. Lead Time

**Lead Time:**
- Days between placing order and receiving it
- Example: 7 days

**Order Scheduling:**
- Order placed on Day 1
- Arrives on Day 1 + 7 = Day 8
- Tracked in `arrivals` dictionary

---

## Part 7: Example: Complete 3-Day Simulation

### Setup

**Product:** SKU-001
- Initial inventory: 85 units
- Min inventory: 50 units
- Max inventory: 100 units
- Lead time: 7 days
- Reserved: 5 units

**Orbit Forecasts:**
- Day 1: 11.5 units
- Day 2: 11.5 units
- Day 3: 12.0 units

**Robyn Lifts:**
- Day 1: 1.218x (10% discount + $100 ads)
- Day 2: 1.0x (no promo, no ads)
- Day 3: 1.0x (no promo, no ads)

### Day 1

**Projected Demand:** 11.5 × 1.218 = 14.0 units
**Available:** 85 - 5 = 80 units
**Realized:** min(80, 14) = 14 units
**Lost Sales:** max(14 - 80, 0) = 0 units
**On-Hand End:** 80 - 14 + 5 = 71 units
**Reorder:** No (71 > 50)

### Day 2

**Projected Demand:** 11.5 × 1.0 = 11.5 units
**Available:** 71 - 5 = 66 units
**Realized:** min(66, 11.5) = 11.5 units
**Lost Sales:** max(11.5 - 66, 0) = 0 units
**On-Hand End:** 66 - 11.5 + 5 = 59.5 units
**Reorder:** No (59.5 > 50)

### Day 3

**Projected Demand:** 12.0 × 1.0 = 12.0 units
**Available:** 59.5 - 5 = 54.5 units
**Realized:** min(54.5, 12.0) = 12.0 units
**Lost Sales:** max(12.0 - 54.5, 0) = 0 units
**On-Hand End:** 54.5 - 12.0 + 5 = 47.5 units
**Reorder:** Yes (47.5 < 50)
- Order quantity: 100 - 47.5 = 52.5 → Round to 56 (case pack)
- Arrives: Day 3 + 7 = Day 10

### Summary

- Total projected demand: 37.5 units
- Total realized demand: 37.5 units
- Total lost sales: 0 units
- Service level: 100% (all demand fulfilled)
- Orders placed: 56 units (arrives Day 10)

---

## Part 8: Why This Matters

### What the Simulation Produces

**Training Data for XGBoost:**
- Day-by-day outcomes (sales, stockouts, orders)
- Inputs (product features, promos, ads)
- **Labeled examples** for surrogate model training

**Business Insights:**
- Service level (fulfillment rate)
- Lost sales (unfulfilled demand)
- Order quantities (when and how much to order)
- Inventory outcomes (stock levels over time)

### How It Enables Optimization

**Traditional Approach:**
- Run simulation once → Get one outcome
- Too slow for interactive planning

**Our Approach:**
- Run simulation once → Generate training data
- Train XGBoost on outcomes
- Fast predictions for 10,000+ scenarios

---

## Summary

### The Simulation Process

1. **Orbit** predicts baseline demand from historical sales
2. **Robyn** calculates lift factors from promos and ads
3. **Combine:** Projected demand = Orbit forecast × Robyn lift
4. **Simulate:** Day-by-day inventory play-out
   - Receive orders
   - Fulfill demand (or record lost sales)
   - Update inventory
   - Check reorder rules
   - Log results

### Key Outputs

- **Simulation logs:** Day-by-day outcomes
- **Summary metrics:** Total sales, lost sales, orders
- **Training data:** For XGBoost surrogate model

### Why It's Important

- **Accurate:** Uses real Orbit + Robyn models
- **Comprehensive:** Tracks all inventory dynamics
- **Training data:** Generates labeled examples for AI model
- **Foundation:** Enables fast optimization via surrogate model

---

## Code References

- **Orbit Integration:** `src/forecast/orbit_integration.py`
- **Robyn Integration:** `src/promo/robyn_integration.py`
- **Simulation Engine:** `src/simulations/inventory_engine.py`
- **Pipeline Script:** `scripts/run_slow_simulation.py`

---

**Key Takeaway:** The simulation combines Orbit (demand forecasting) and Robyn (marketing lift) to project demand, then simulates day-by-day inventory dynamics to produce complete business outcomes. These outcomes become training data for the XGBoost surrogate model, which enables fast optimization.

