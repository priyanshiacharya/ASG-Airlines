"""
ASG Airlines Data Engineering Pipeline
Step 3: Data Ingestion Script

This script ingests the raw Excel workbook 'data/raw/UseCase - Airlines.xlsx',
inspects all sheets, logs dataset schemas, row/column counts, and validates 
file readability without modifying the raw data.
"""

import os
import sys
import logging
from typing import Dict
import pandas as pd


# Configure Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "ingestion.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_Ingestion")


def get_raw_data_path() -> str:
    """
    Constructs and returns the absolute path to the raw Excel dataset.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(project_root, "data", "raw", "UseCase - Airlines.xlsx")
    return file_path


def load_raw_workbook(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Reads the raw Excel workbook and loads all sheets into a dictionary of DataFrames.

    Args:
        file_path (str): Path to the Excel workbook.

    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping sheet names to DataFrames.
    """
    logger.info(f"Attempting to load Excel workbook from: {file_path}")

    if not os.path.exists(file_path):
        error_msg = f"Raw Excel file not found at path: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        # Load Excel File using openpyxl engine
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = excel_file.sheet_names
        logger.info(f"Excel file loaded successfully. Found {len(sheet_names)} sheet(s): {sheet_names}")

        sheets_data = {}
        for sheet in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            sheets_data[sheet] = df
            logger.info(f"Sheet '{sheet}' loaded with shape {df.shape} (Rows: {df.shape[0]}, Columns: {df.shape[1]})")

        return sheets_data

    except Exception as e:
        logger.error(f"Failed to read Excel workbook: {str(e)}", exc_info=True)
        raise e


def inspect_schemas(sheets_data: Dict[str, pd.DataFrame]) -> None:
    """
    Logs basic schema details for each loaded sheet, including shape, columns, and data types.

    Args:
        sheets_data (Dict[str, pd.DataFrame]): Dictionary of sheet DataFrames.
    """
    print("\n" + "=" * 60)
    print("           ASG AIRLINES DATASET INGESTION SUMMARY")
    print("=" * 60)

    for sheet_name, df in sheets_data.items():
        print(f"\n--- SHEET: {sheet_name} ---")
        print(f"Row Count    : {df.shape[0]}")
        print(f"Column Count : {df.shape[1]}")
        print("Column Names & Data Types:")
        for col, dtype in df.dtypes.items():
            print(f"  - {col}: {dtype}")
        
        logger.info(f"Schema inspection completed for sheet '{sheet_name}'.")

    print("\n" + "=" * 60)
    print("Ingestion completed successfully. Raw data preserved untouched.")
    print("=" * 60 + "\n")


def run_ingestion() -> Dict[str, pd.DataFrame]:
    """
    Main orchestration function for data ingestion.

    Returns:
        Dict[str, pd.DataFrame]: Dictionary of ingested DataFrames.
    """
    logger.info("Starting ASG Airlines Data Ingestion Process...")
    raw_path = get_raw_data_path()
    
    try:
        raw_data = load_raw_workbook(raw_path)
        inspect_schemas(raw_data)
        logger.info("Data Ingestion step finished cleanly.")
        return raw_data
    except Exception as e:
        logger.critical(f"Data Ingestion failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_ingestion()
