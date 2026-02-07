# Architecture

## Goal
Convert the Excel-based Hybrid Renewable Energy (Solar + Wind + BESS + Grid) cost calculator into a clean Python backend (**core**) with a thin UI layer (**dashboard**) that is safe to deploy and easy to maintain.

---

## Layers

### 1) core/ (Business Logic)
Owns all numerical correctness and Excel parity.

Responsible for:
- Reading and normalizing Excel input data
- Building the hourly reference energy model
- Mapping Time-of-Day (TOD) slots and base grid tariffs
- Producing the annual TOD summary table

**Key flow**
1. `core/loader.py`  
   Reads the Excel workbook and constructs a unified hourly reference dataframe (`model_df`).

2. `core/tod.py`  
   Assigns TOD slots (A, C, B, D) and base grid TOD rates.

3. `core/excel_option_engine.py` (**single source of truth**)  
   Responsible for:
   - Hourly → Monthly → Annual energy aggregation  
   - TOD slot logic (A, C, B, D)  
   - BESS dispatch logic  
   - Slot-based tariff application (Solar, Wind, BESS, Grid)  
   - Slot-wise cost calculation  
   - Correct Total-row computation (percentages are recomputed, never summed)

All downstream modules (dashboard, KPIs, charts) consume the engine output directly and must not recompute energy or cost logic.

4. `core/tariff_costing.py` (optional)  
   Reserved for future tariff extensions and advanced costing utilities.

---

### 2) dashboard/ (Streamlit UI)
Pure presentation layer.

Responsible for:
- Collecting user inputs (plant sizing, rates, demo/upload choice)
- Triggering calculations via the service layer
- Rendering KPIs, tables, and charts

No business logic is implemented in this layer.

---

### 3) dashboard/services/
Thin orchestration layer between UI and core.

Responsible for:
- Calling the core calculation engine
- Passing sizing and rate inputs to the engine
- Extracting KPI-level summaries from engine output

No energy or cost calculations are implemented here.

---

## Data Source Modes

- **Demo file**  
  Uses a safe, version-controlled Excel file stored under `data/demo/`.

- **Upload**  
  User uploads an Excel file which is temporarily stored and processed using the same calculation pipeline.

Both modes follow identical calculation logic.

---

## Optional / Archived Modules
`archive/` contains older experiments and alternate implementations.  
These are kept only for reference and are not used in the deployed application.

---

## Design Rule
If a change affects energy, cost, or KPIs, it must be implemented in `core/`.
