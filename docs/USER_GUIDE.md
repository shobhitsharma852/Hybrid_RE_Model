# User Guide

## Overview
This application allows users to evaluate Hybrid Renewable Energy configurations combining Solar, Wind, BESS, and Grid using Time-of-Day (TOD) based logic.

The tool replicates Excel-based costing logic while providing a clean, interactive interface.

---

## Getting Started

### Step 1: Select Data Source
Choose one of the following:
- **Use demo file**  
  Loads a safe, preconfigured Excel file included with the application.
- **Upload my Excel**  
  Upload your own Excel file in the supported format.

Both options follow the same calculation pipeline.

---

## Input Parameters

### Plant Sizing
- **Load (MW)**  
  Average plant load in MW.
- **Solar mode**  
  Select FT / SAT / EW depending on plant configuration.
- **Solar DC size (MWp)**  
  Installed solar capacity.
- **Solar loss (%)**  
  Aggregate system losses.
- **Wind (MW)**  
  Installed wind capacity.
- **Wind loss (%)**  
  Aggregate wind losses.

---

### Tariff Inputs
All tariffs are Time-of-Day (TOD) based.

For each source (Solar, Wind, BESS, Grid):
- Select **Typical** to use default rates
- Select **Custom** to define slot-wise rates for A, C, B, D

---

## Outputs

### KPI Summary
Displayed at the top of the dashboard:
- Total Load (kWh)
- Total Renewable Energy (kWh)
- RE Percentage
- Grid Import (kWh)
- Total Cost (₹)

---

### Annual TOD Table
Shows annual values for each TOD slot (A, C, B, D) and a Total row:
- Energy breakdown (kWh)
- Slot-wise RE percentage
- Tariffs (₹/kWh)
- Cost breakdown (₹)

---

### Charts
- Energy distribution by TOD slot
- Cost distribution by source

---

## Interpretation Notes
- RE % is calculated from total load and grid import, not summed across slots.
- BESS discharges only in the configured discharge slot (Excel parity).
- All costs are computed on an annual basis.

---

## Supported Use Cases
- Feasibility studies
- Cost comparison of hybrid configurations
- Internal scenario analysis
- Excel-to-Python model validation

---

## Limitations
- No real-time optimization
- No market bidding logic
- No financial structuring beyond energy-based costing
