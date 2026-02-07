# Hybrid Renewable Energy Options Dashboard

A Python-based Hybrid Renewable Energy (Solar + Wind + BESS + Grid) cost calculator built to replicate Excel-based Time-of-Day (TOD) logic with a clean backend and an interactive Streamlit dashboard.

This project converts a complex Excel model into a **reliable calculation engine** with a **thin UI layer**, suitable for internal analysis, demos, and controlled deployment.

---

## Features

- Excel-faithful energy and cost calculations
- Time-of-Day (TOD) slot logic (A, C, B, D)
- Hybrid configurations: Solar, Wind, BESS, Grid
- Slot-wise and annual cost breakdown
- Correct RE% computation (no percentage summation bugs)
- Interactive Streamlit dashboard
- Safe demo mode for public deployment

---

## Project Structure

├── core/ # Business logic (single source of truth)
│ ├── loader.py
│ ├── tod.py
│ ├── excel_option_engine.py
│ └── tariff_costing.py (optional)
│
├── dashboard/ # Streamlit UI
│ ├── app.py
│ ├── components/
│ └── services/
│
├── data/
│ └── demo/ # Safe demo Excel file
│
├── docs/ # Project documentation
│ ├── ARCHITECTURE.md
│ ├── USER_GUIDE.md
│ └── DEPLOYMENT.md
│
├── tests/ # Tests (optional / future)
├── requirements.txt
└── README.md

---

## Architecture Overview

- **core/**  
  Owns all numerical logic:
  - Energy aggregation (hourly → annual)
  - TOD slot mapping
  - BESS dispatch logic
  - Slot-based tariffs
  - Cost computation
  - Correct Total-row handling

- **dashboard/**  
  Pure presentation layer:
  - Input collection
  - KPI rendering
  - Tables and charts

- **dashboard/services/**  
  Thin orchestration layer between UI and core.

For details, see `docs/ARCHITECTURE.md`.

---

## Getting Started

### Prerequisites
- Python 3.10+
- Virtual environment recommended

### Installation

```bash
pip install -r requirements.txt