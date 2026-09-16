# ASG Airlines End-to-End Data Engineering Project

## Overview
This project establishes an end-to-end Data Engineering pipeline for **ASG Airlines**. The primary goal is to ingest, validate, clean, transform, and analyze multi-sheet airline dataset covering flights, bookings, passengers, and payment details.

## Project Structure
```text
ASG-Airlines-Data-Engineering/
├── data/
│   ├── raw/
│   │   └── UseCase - Airlines.xlsx  # Original raw multi-sheet Excel file (Untouched)
│   └── processed/                  # Target storage for cleaned/transformed datasets
├── docs/                           # Documentation and data dictionary
├── logs/                           # Automated ingestion and pipeline log files
│   └── ingestion.log
├── notebooks/                      # Jupyter notebooks for data analysis & exploration
│   └── 01_data_ingestion.ipynb
├── powerbi/                        # Power BI reports and dashboards
├── src/                            # Production Python source code
│   └── ingestion.py
└── README.md                       # Project documentation
```

## Step 3: Data Ingestion
The ingestion module (`src/ingestion.py`) performs the following operations without altering the raw Excel dataset:
- Loads Excel workbook using `pandas` and `openpyxl`.
- Dynamically detects all sheets (`flights`, `payments`, `bookings`, `passengers`).
- Inspects schema, row counts, column names, and data types.
- Logs execution details to console and `logs/ingestion.log`.

## How to Run

### Prerequisites
- Python 3.10+ (or Python Launcher `py`)
- Required packages: `pandas`, `openpyxl`

```bash
pip install pandas openpyxl
```

### Running Ingestion Script
```bash
py src/ingestion.py
```
or
```bash
python src/ingestion.py
```

### Running Ingestion Notebook
Open `notebooks/01_data_ingestion.ipynb` using Jupyter Notebook, VS Code, or JupyterLab.
