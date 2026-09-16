"""
ASG Airlines Data Engineering Pipeline
Step 4: Data Quality Checks Script

This script performs comprehensive data quality audits on the raw dataset 
'data/raw/UseCase - Airlines.xlsx' across sheets: flights, payments, bookings, and passengers.
Identified quality issues are compiled and saved to 'data/processed/data_quality_report.csv'.

IMPORTANT: This module ONLY inspects and logs data quality issues.
The raw dataset remains 100% unaltered.
"""

import os
import sys
import logging
import re
from typing import Dict, List, Any
import pandas as pd


# Configure Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "data_quality.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_DataQuality")


def get_raw_data_path() -> str:
    """Returns absolute path to raw dataset."""
    return os.path.join(PROJECT_ROOT, "data", "raw", "UseCase - Airlines.xlsx")


def load_sheets() -> Dict[str, pd.DataFrame]:
    """Loads raw Excel sheets into memory."""
    raw_path = get_raw_data_path()
    logger.info(f"Loading raw workbook from: {raw_path}")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw data file missing at: {raw_path}")

    excel_file = pd.ExcelFile(raw_path, engine="openpyxl")
    sheets = {sheet: pd.read_excel(excel_file, sheet_name=sheet) for sheet in excel_file.sheet_names}
    logger.info(f"Successfully loaded {len(sheets)} sheets: {list(sheets.keys())}")
    return sheets


def run_data_quality_checks(sheets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Executes schema, missing values, duplicates, flight ID, time, categorical, numeric,
    and PII quality checks across all dataset sheets.

    Returns:
        pd.DataFrame: Quality issues report table.
    """
    issues: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. MISSING VALUES & DUPLICATES ANALYSIS
    # -------------------------------------------------------------
    for sheet_name, df in sheets.items():
        total_rows = len(df)
        logger.info(f"Auditing sheet '{sheet_name}' ({total_rows} rows, {len(df.columns)} columns)...")

        # Full row duplicates
        full_dups = df.duplicated().sum()
        if full_dups > 0:
            pct = round((full_dups / total_rows) * 100, 2)
            issues.append({
                "Issue": "Full Duplicate Rows",
                "Sheet": sheet_name,
                "Column": "ALL",
                "Number of affected records": int(full_dups),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Deduplicate exact matching rows."
            })
            logger.warning(f"Sheet '{sheet_name}': Found {full_dups} ({pct}%) full duplicate rows.")

        # ID column duplicate check
        primary_key_map = {
            "flights": "flight_id",
            "payments": "payment_id",
            "bookings": "booking_id",
            "passengers": "passenger_id"
        }
        pk_col = primary_key_map.get(sheet_name)
        if pk_col and pk_col in df.columns:
            id_dups = df.duplicated(subset=[pk_col]).sum()
            if id_dups > 0:
                pct = round((id_dups / total_rows) * 100, 2)
                issues.append({
                    "Issue": f"Duplicate Primary Key ({pk_col})",
                    "Sheet": sheet_name,
                    "Column": pk_col,
                    "Number of affected records": int(id_dups),
                    "Percentage affected": pct,
                    "Recommended action for Step 5": f"Investigate and deduplicate/reconcile duplicate {pk_col} entries."
                })
                logger.warning(f"Sheet '{sheet_name}': Found {id_dups} duplicate {pk_col} entries.")

        # Missing values per column
        for col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                pct = round((null_count / total_rows) * 100, 2)
                issues.append({
                    "Issue": "Missing Value (NaN)",
                    "Sheet": sheet_name,
                    "Column": col,
                    "Number of affected records": int(null_count),
                    "Percentage affected": pct,
                    "Recommended action for Step 5": f"Impute missing values or flag as 'UNKNOWN'."
                })
                logger.warning(f"Sheet '{sheet_name}', Column '{col}': {null_count} missing values ({pct}%).")

    # -------------------------------------------------------------
    # 2. FLIGHTS SPECIFIC QUALITY CHECKS
    # -------------------------------------------------------------
    if "flights" in sheets:
        df_f = sheets["flights"]
        total_f = len(df_f)

        # Flight ID format rule: standard pattern ^[A-Z0-9]{2}\d{3}$ (2 chars prefix + 3 digits)
        flight_id_regex = r"^[A-Z0-9]{2}\d{3}$"
        invalid_ids = df_f[~df_f["flight_id"].astype(str).str.match(flight_id_regex, na=False)]
        if len(invalid_ids) > 0:
            pct = round((len(invalid_ids) / total_f) * 100, 2)
            issues.append({
                "Issue": "Malformed Flight ID Format",
                "Sheet": "flights",
                "Column": "flight_id",
                "Number of affected records": len(invalid_ids),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Standardize flight ID strings according to regex format ^[A-Z0-9]{2}\\d{3}$."
            })

        # Conflicting Duplicate Flight IDs (same flight_id with different times/details)
        dup_id_df = df_f[df_f.duplicated(subset=["flight_id"], keep=False)]
        unique_dup_ids = dup_id_df["flight_id"].unique()
        conflicting_count = 0
        for fid in unique_dup_ids:
            subset = dup_id_df[dup_id_df["flight_id"] == fid]
            if len(subset.drop_duplicates()) > 1:
                conflicting_count += (len(subset) - 1)

        if conflicting_count > 0:
            pct = round((conflicting_count / total_f) * 100, 2)
            issues.append({
                "Issue": "Conflicting Duplicate Flight IDs",
                "Sheet": "flights",
                "Column": "flight_id",
                "Number of affected records": conflicting_count,
                "Percentage affected": pct,
                "Recommended action for Step 5": "Resolve conflicting flight details for identical flight_ids."
            })
            logger.warning(f"Flights: Found {conflicting_count} records with conflicting duplicate flight_ids.")

        # Time Quality: Arrival before Departure (Negative flight duration)
        negative_duration = df_f[df_f["arrival_time"] < df_f["departure_time"]]
        if len(negative_duration) > 0:
            pct = round((len(negative_duration) / total_f) * 100, 2)
            issues.append({
                "Issue": "Invalid Flight Time (Arrival < Departure)",
                "Sheet": "flights",
                "Column": "arrival_time / departure_time",
                "Number of affected records": len(negative_duration),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Adjust date component for cross-day flights or correct timestamp corruption."
            })
            logger.warning(f"Flights: Found {len(negative_duration)} records where arrival_time < departure_time.")

        # Categorical Consistency: Airline values
        airline_unknowns = df_f[df_f["airline"] == "UNKNOWN"]
        if len(airline_unknowns) > 0:
            pct = round((len(airline_unknowns) / total_f) * 100, 2)
            issues.append({
                "Issue": "Unresolved Airline Code ('UNKNOWN')",
                "Sheet": "flights",
                "Column": "airline",
                "Number of affected records": len(airline_unknowns),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Impute airline name from flight_id prefix mapping (e.g. 6F -> IndiGo)."
            })

    # -------------------------------------------------------------
    # 3. PAYMENTS SPECIFIC QUALITY CHECKS
    # -------------------------------------------------------------
    if "payments" in sheets:
        df_p = sheets["payments"]
        total_p = len(df_p)

        # Invalid amount strings (e.g. 'INVALID')
        invalid_amount_str = df_p[df_p["amount"].astype(str).str.upper() == "INVALID"]
        if len(invalid_amount_str) > 0:
            pct = round((len(invalid_amount_str) / total_p) * 100, 2)
            issues.append({
                "Issue": "Invalid String in Numeric Amount ('INVALID')",
                "Sheet": "payments",
                "Column": "amount",
                "Number of affected records": len(invalid_amount_str),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Coerce invalid strings to NaN and impute median amount per payment method."
            })
            logger.warning(f"Payments: Found {len(invalid_amount_str)} 'INVALID' amount records.")

    # -------------------------------------------------------------
    # 4. BOOKINGS SPECIFIC QUALITY CHECKS
    # -------------------------------------------------------------
    if "bookings" in sheets:
        df_b = sheets["bookings"]
        total_b = len(df_b)

        # Invalid booking status strings
        invalid_status = df_b[df_b["status"].astype(str).str.upper() == "INVALID"]
        if len(invalid_status) > 0:
            pct = round((len(invalid_status) / total_b) * 100, 2)
            issues.append({
                "Issue": "Invalid Booking Status ('INVALID')",
                "Sheet": "bookings",
                "Column": "status",
                "Number of affected records": len(invalid_status),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Map 'INVALID' booking status to 'UNKNOWN' or resolve via payment logs."
            })
            logger.warning(f"Bookings: Found {len(invalid_status)} 'INVALID' status records.")

    # -------------------------------------------------------------
    # 5. PASSENGERS SPECIFIC QUALITY CHECKS
    # -------------------------------------------------------------
    if "passengers" in sheets:
        df_pass = sheets["passengers"]
        total_pass = len(df_pass)

        # Aadhaar ID length inconsistency (< 12 digits due to integer conversion)
        aadhaar_short = df_pass[df_pass["aadhaar_id"].astype(str).str.len() < 12]
        if len(aadhaar_short) > 0:
            pct = round((len(aadhaar_short) / total_pass) * 100, 2)
            issues.append({
                "Issue": "Truncated Aadhaar ID Length (< 12 digits)",
                "Sheet": "passengers",
                "Column": "aadhaar_id",
                "Number of affected records": len(aadhaar_short),
                "Percentage affected": pct,
                "Recommended action for Step 5": "Pad truncated numeric Aadhaar IDs with leading zeros to 12 digits."
            })

    # -------------------------------------------------------------
    # 6. PII IDENTIFICATION
    # -------------------------------------------------------------
    pii_columns = [
        ("passengers", "first_name", "Direct PII (First Name)"),
        ("passengers", "last_name", "Direct PII (Last Name)"),
        ("passengers", "email", "Direct PII (Email Address)"),
        ("passengers", "phone", "Direct PII (Phone Number)"),
        ("passengers", "aadhaar_id", "Sensitive Government ID PII (Aadhaar Number)"),
        ("passengers", "date_of_birth", "Demographic PII (Date of Birth)"),
        ("bookings", "passport_number", "Sensitive Government Document PII (Passport Number)"),
        ("bookings", "emergency_contact_name", "Third-Party Contact PII (Emergency Name)"),
        ("bookings", "emergency_contact_phone", "Third-Party Contact PII (Emergency Phone)")
    ]

    for sheet_name, col, pii_type in pii_columns:
        if sheet_name in sheets and col in sheets[sheet_name].columns:
            cnt = len(sheets[sheet_name])
            issues.append({
                "Issue": f"PII Column Identified: {pii_type}",
                "Sheet": sheet_name,
                "Column": col,
                "Number of affected records": cnt,
                "Percentage affected": 100.0,
                "Recommended action for Step 5": "Apply masking or hashing (anonymization) for production compliance."
            })

    report_df = pd.DataFrame(issues)
    return report_df


def save_data_quality_report(report_df: pd.DataFrame) -> str:
    """Saves report dataframe to CSV."""
    report_path = os.path.join(PROCESSED_DIR, "data_quality_report.csv")
    report_df.to_csv(report_path, index=False)
    logger.info(f"Data Quality Report saved to: {report_path}")
    return report_path


def run_data_quality_pipeline() -> pd.DataFrame:
    """Main execution entry point."""
    logger.info("Starting ASG Airlines Data Quality Audit...")
    sheets = load_sheets()
    report_df = run_data_quality_checks(sheets)
    report_path = save_data_quality_report(report_df)
    
    print("\n" + "=" * 80)
    print("                     DATA QUALITY AUDIT SUMMARY REPORT")
    print("=" * 80)
    print(report_df.to_string(index=False))
    print("=" * 80)
    print(f"Report CSV created successfully at: {report_path}\n")
    
    logger.info("Data Quality Audit complete.")
    return report_df


if __name__ == "__main__":
    run_data_quality_pipeline()
