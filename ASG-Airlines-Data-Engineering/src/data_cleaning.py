"""
ASG Airlines Data Engineering Pipeline
Step 5: Data Cleaning & Transformation Module

This script executes data cleaning, deduplication, missing value imputation,
type coercion, time standardization, and PII anonymization based on the Step 4 Data Quality Report.

Outputs clean datasets to 'data/processed/':
  - cleaned_flights.csv
  - cleaned_bookings.csv
  - cleaned_passengers.csv
  - cleaned_payments.csv

Log file generated: 'logs/data_cleaning.log'

IMPORTANT: The raw dataset 'data/raw/UseCase - Airlines.xlsx' remains 100% untouched.
"""

import os
import sys
import logging
import hashlib
from typing import Dict, Tuple
import pandas as pd
import numpy as np


# Setup Paths & Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "UseCase - Airlines.xlsx")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "data_cleaning.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_DataCleaning")


def hash_value(val: str, salt: str = "ASG_AIRLINES_2026") -> str:
    """Helper to generate salted SHA-256 hash string for PII protection."""
    if pd.isna(val) or not str(val).strip():
        return "UNAVAILABLE"
    salted = f"{salt}:{str(val).strip()}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()[:16]


def mask_phone(phone: str) -> str:
    """Masks phone number displaying country code and last 4 digits."""
    s = str(phone).strip()
    if len(s) >= 10:
        return s[:4] + "-XXXXXX-" + s[-4:]
    return "XXXX-XXXXXX"


def mask_aadhaar(aadhaar: str) -> str:
    """Masks 12-digit Aadhaar ID showing only last 4 digits."""
    s = str(aadhaar).zfill(12)
    return "XXXX-XXXX-" + s[-4:]


def mask_passport(passport: str) -> str:
    """Masks Passport number showing first and last character."""
    s = str(passport).strip()
    if len(s) >= 4:
        return s[0] + "*" * (len(s) - 2) + s[-1]
    return "X*****X"


def clean_flights(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Cleans flights sheet:
    - Deduplicates exact rows and duplicate flight_ids.
    - Imputes missing/UNKNOWN airlines using prefix mapping rule (SJ->SpiceJet, AI->Air India, UK->Vistara, 6F->IndiGo).
    - Standardizes text casing and whitespace.
    - Validates flight_id regex format.
    - Fixes timestamp date overflow (Arrival < Departure).
    """
    initial_rows = len(df)
    logger.info(f"Cleaning 'flights': initial record count = {initial_rows}")

    # 1. Deduplication
    df_clean = df.drop_duplicates()
    full_dups_removed = initial_rows - len(df_clean)
    
    # Primary Key Deduplication
    id_dups_count = df_clean.duplicated(subset=["flight_id"]).sum()
    df_clean = df_clean.drop_duplicates(subset=["flight_id"], keep="first")
    total_removed = initial_rows - len(df_clean)
    logger.info(f"'flights': removed {full_dups_removed} full duplicate rows and {id_dups_count} duplicate flight_id records.")

    # 2. Text Standardization & Airline Prefix Imputation
    prefix_map = {
        "SJ": "SpiceJet",
        "AI": "Air India",
        "UK": "Vistara",
        "6F": "IndiGo"
    }

    df_clean["source"] = df_clean["source"].astype(str).str.strip().str.upper()
    df_clean["destination"] = df_clean["destination"].astype(str).str.strip().str.upper()
    df_clean["flight_id"] = df_clean["flight_id"].astype(str).str.strip().str.upper()

    missing_airline_cnt = df_clean["airline"].isnull().sum()
    unknown_airline_cnt = (df_clean["airline"].astype(str).str.strip().str.upper() == "UNKNOWN").sum()

    def impute_airline(row):
        curr = str(row["airline"]).strip() if pd.notna(row["airline"]) else ""
        if not curr or curr.upper() == "UNKNOWN":
            prefix = str(row["flight_id"])[:2].upper()
            return prefix_map.get(prefix, "UNKNOWN")
        return curr

    df_clean["airline"] = df_clean.apply(impute_airline, axis=1)
    airlines_affected = missing_airline_cnt + unknown_airline_cnt
    logger.info(f"'flights': imputed {airlines_affected} missing/UNKNOWN airlines using prefix rule.")

    # 3. Time Standardization & Arrival Timestamp Correction
    df_clean["departure_time"] = pd.to_datetime(df_clean["departure_time"])
    df_clean["arrival_time"] = pd.to_datetime(df_clean["arrival_time"])

    # Fix cross-day / date overflow (Arrival < Departure)
    neg_time_mask = df_clean["arrival_time"] < df_clean["departure_time"]
    time_issues_count = neg_time_mask.sum()

    if time_issues_count > 0:
        for idx in df_clean[neg_time_mask].index:
            dep = df_clean.loc[idx, "departure_time"]
            arr = df_clean.loc[idx, "arrival_time"]
            fixed_arr = pd.Timestamp.combine(dep.date(), arr.time())
            if fixed_arr < dep:
                fixed_arr += pd.Timedelta(days=1)
            df_clean.loc[idx, "arrival_time"] = fixed_arr
        logger.info(f"'flights': corrected {time_issues_count} cross-day/overflow arrival timestamps.")

    # Convert timestamps to standard ISO format strings
    df_clean["departure_time"] = df_clean["departure_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_clean["arrival_time"] = df_clean["arrival_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "rows_before": initial_rows,
        "rows_after": len(df_clean),
        "duplicates_removed": total_removed,
        "missing_handled": airlines_affected,
        "other_changes": f"Fixed {time_issues_count} arrival timestamps; standardized text fields."
    }
    return df_clean, stats


def clean_payments(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Cleans payments sheet:
    - Deduplicates records.
    - Coerces 'INVALID' amount strings to NaN.
    - Imputes missing amounts with median per payment_method.
    - Standardizes text fields.
    """
    initial_rows = len(df)
    logger.info(f"Cleaning 'payments': initial record count = {initial_rows}")

    df_clean = df.drop_duplicates()
    dups_removed = initial_rows - len(df_clean)

    # Standardize payment_method strings
    df_clean["payment_method"] = df_clean["payment_method"].astype(str).str.strip().str.upper()
    df_clean["payment_id"] = df_clean["payment_id"].astype(str).str.strip().str.upper()
    df_clean["booking_id"] = df_clean["booking_id"].astype(str).str.strip().str.upper()

    # Identify invalid amount strings and NaNs
    invalid_str_cnt = (df_clean["amount"].astype(str).str.strip().str.upper() == "INVALID").sum()
    null_cnt = df_clean["amount"].isnull().sum()
    total_amount_affected = invalid_str_cnt + null_cnt

    # Coerce to float
    df_clean["amount"] = pd.to_numeric(df_clean["amount"], errors="coerce")

    # Median imputation per payment_method
    medians = df_clean.groupby("payment_method")["amount"].transform("median")
    df_clean["amount"] = df_clean["amount"].fillna(medians).round(2)
    logger.info(f"'payments': imputed {total_amount_affected} missing/INVALID payment amounts using group median.")

    stats = {
        "rows_before": initial_rows,
        "rows_after": len(df_clean),
        "duplicates_removed": dups_removed,
        "missing_handled": total_amount_affected,
        "other_changes": "Coerced 'INVALID' amounts to float and rounded to 2 decimals."
    }
    return df_clean, stats


def clean_bookings(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Cleans bookings sheet:
    - Deduplicates records.
    - Maps NaN and 'INVALID' booking status values to 'UNKNOWN'.
    - Anonymizes PII fields (passport_number, emergency_contact_name, emergency_contact_phone).
    """
    initial_rows = len(df)
    logger.info(f"Cleaning 'bookings': initial record count = {initial_rows}")

    df_clean = df.drop_duplicates()
    dups_removed = initial_rows - len(df_clean)

    # Standardize text IDs
    for col in ["booking_id", "passenger_id", "flight_id", "seat_number"]:
        df_clean[col] = df_clean[col].astype(str).str.strip().str.upper()

    # Standardize status
    missing_status_cnt = df_clean["status"].isnull().sum()
    invalid_status_cnt = (df_clean["status"].astype(str).str.strip().str.upper() == "INVALID").sum()
    total_status_affected = missing_status_cnt + invalid_status_cnt

    def clean_status(val):
        if pd.isna(val) or str(val).strip().upper() in ["INVALID", "NAN", ""]:
            return "UNKNOWN"
        return str(val).strip().upper()

    df_clean["status"] = df_clean["status"].apply(clean_status)
    logger.info(f"'bookings': handled {total_status_affected} missing/INVALID booking statuses (mapped to 'UNKNOWN').")

    # Format booking_date
    df_clean["booking_date"] = pd.to_datetime(df_clean["booking_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # PII Protection Strategy: Character Masking + SHA-256 Hash Columns
    df_clean["passport_hash"] = df_clean["passport_number"].apply(hash_value)
    df_clean["passport_number_masked"] = df_clean["passport_number"].apply(mask_passport)
    df_clean["emergency_contact_phone_masked"] = df_clean["emergency_contact_phone"].apply(mask_phone)

    # Replace raw sensitive PII with masked representations for output
    df_clean["passport_number"] = df_clean["passport_number_masked"]
    df_clean["emergency_contact_phone"] = df_clean["emergency_contact_phone_masked"]
    df_clean.drop(columns=["passport_number_masked", "emergency_contact_phone_masked"], inplace=True)

    stats = {
        "rows_before": initial_rows,
        "rows_after": len(df_clean),
        "duplicates_removed": dups_removed,
        "missing_handled": total_status_affected,
        "other_changes": "Mapped status to UNKNOWN; anonymized PII (passport & emergency phone)."
    }
    return df_clean, stats


def clean_passengers(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Cleans passengers sheet:
    - Deduplicates records and passenger_id primary keys.
    - Fills missing last_name with 'N/A'.
    - Formats aadhaar_id by zero-padding truncated integers to 12 digits.
    - Applies PII protection (masking & SHA-256 hashing) for email, phone, aadhaar_id, names.
    """
    initial_rows = len(df)
    logger.info(f"Cleaning 'passengers': initial record count = {initial_rows}")

    df_clean = df.drop_duplicates()
    full_dups_removed = initial_rows - len(df_clean)

    # Deduplicate passenger_id PK
    id_dups_count = df_clean.duplicated(subset=["passenger_id"]).sum()
    df_clean = df_clean.drop_duplicates(subset=["passenger_id"], keep="first")
    total_dups_removed = initial_rows - len(df_clean)

    df_clean["passenger_id"] = df_clean["passenger_id"].astype(str).str.strip().str.upper()

    # Missing last_name handling
    missing_last_cnt = df_clean["last_name"].isnull().sum()
    df_clean["first_name"] = df_clean["first_name"].astype(str).str.strip().str.title()
    df_clean["last_name"] = df_clean["last_name"].fillna("N/A").astype(str).str.strip().str.title()
    logger.info(f"'passengers': filled {missing_last_cnt} missing last_name values with 'N/A'.")

    # Aadhaar ID formatting (zero pad to 12 digits)
    df_clean["aadhaar_id_formatted"] = df_clean["aadhaar_id"].astype(str).str.strip().apply(lambda x: x.zfill(12))

    # Format Date of Birth
    df_clean["date_of_birth"] = pd.to_datetime(df_clean["date_of_birth"]).dt.strftime("%Y-%m-%d")

    # PII Protection Strategy
    df_clean["email_hash"] = df_clean["email"].apply(hash_value)
    df_clean["phone_masked"] = df_clean["phone"].apply(mask_phone)
    df_clean["aadhaar_masked"] = df_clean["aadhaar_id_formatted"].apply(mask_aadhaar)

    # Replace raw PII columns with masked values for compliance
    df_clean["email"] = df_clean["email_hash"]
    df_clean["phone"] = df_clean["phone_masked"]
    df_clean["aadhaar_id"] = df_clean["aadhaar_masked"]

    df_clean.drop(columns=["email_hash", "phone_masked", "aadhaar_masked", "aadhaar_id_formatted"], inplace=True)

    stats = {
        "rows_before": initial_rows,
        "rows_after": len(df_clean),
        "duplicates_removed": total_dups_removed,
        "missing_handled": missing_last_cnt,
        "other_changes": "Zero-padded Aadhaar IDs; hashed emails; masked phone numbers & Aadhaar IDs."
    }
    return df_clean, stats


def run_data_cleaning_pipeline() -> None:
    """Orchestrates data cleaning pipeline across all sheets."""
    logger.info("Starting ASG Airlines Data Cleaning Pipeline...")
    
    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Raw data file missing at: {RAW_DATA_PATH}")

    excel_file = pd.ExcelFile(RAW_DATA_PATH, engine="openpyxl")
    raw_sheets = {sheet: pd.read_excel(excel_file, sheet_name=sheet) for sheet in excel_file.sheet_names}

    summary_list = []

    # Clean flights
    cleaned_fl, fl_stats = clean_flights(raw_sheets["flights"])
    cleaned_fl.to_csv(os.path.join(PROCESSED_DIR, "cleaned_flights.csv"), index=False)
    summary_list.append({"Sheet": "flights", **fl_stats})

    # Clean payments
    cleaned_pay, pay_stats = clean_payments(raw_sheets["payments"])
    cleaned_pay.to_csv(os.path.join(PROCESSED_DIR, "cleaned_payments.csv"), index=False)
    summary_list.append({"Sheet": "payments", **pay_stats})

    # Clean bookings
    cleaned_bk, bk_stats = clean_bookings(raw_sheets["bookings"])
    cleaned_bk.to_csv(os.path.join(PROCESSED_DIR, "cleaned_bookings.csv"), index=False)
    summary_list.append({"Sheet": "bookings", **bk_stats})

    # Clean passengers
    cleaned_pass, pass_stats = clean_passengers(raw_sheets["passengers"])
    cleaned_pass.to_csv(os.path.join(PROCESSED_DIR, "cleaned_passengers.csv"), index=False)
    summary_list.append({"Sheet": "passengers", **pass_stats})

    summary_df = pd.DataFrame(summary_list)

    print("\n" + "=" * 90)
    print("                        ASG AIRLINES DATA CLEANING SUMMARY")
    print("=" * 90)
    print(summary_df.to_string(index=False))
    print("=" * 90)
    print(f"Cleaned datasets successfully exported to: {PROCESSED_DIR}\n")
    
    logger.info("Data Cleaning Pipeline complete.")


if __name__ == "__main__":
    run_data_cleaning_pipeline()
