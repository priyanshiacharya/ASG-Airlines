"""
ASG Airlines Data Engineering Pipeline
Step 9: Final Clean Dataset Generation Module

This script synthesizes validated outputs from Steps 5–8 to generate:
  1. 'data/processed/final_flights.csv': The primary analytics-ready flights dataset for Power BI.
  2. 'data/processed/rejected_flights.csv': Audit trail of rejected records (duplicates / conflicting records).

Log file generated: 'logs/final_dataset.log'
"""

import os
import sys
import logging
from typing import Dict, Any, Tuple
import pandas as pd


# Configure Paths & Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
RAW_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "UseCase - Airlines.xlsx")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "final_dataset.log")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_FinalDataset")


def build_final_dataset() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Constructs final_flights.csv and rejected_flights.csv, performing final integrity verification.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]: Final DF, Rejected DF, Summary stats dictionary.
    """
    logger.info("Starting Final Clean Dataset Generation Pipeline...")

    fl_ready_path = os.path.join(PROCESSED_DIR, "flight_data_ready.csv")
    if not os.path.exists(fl_ready_path):
        raise FileNotFoundError(f"Input ready dataset missing at: {fl_ready_path}")

    df_fl_ready = pd.read_csv(fl_ready_path)
    total_ready = len(df_fl_ready)

    # 1. Verify Required Schema Columns
    required_columns = [
        "flight_id", "airline", "source", "destination", "route",
        "departure_time", "arrival_time", "departure_hour", "arrival_hour",
        "departure_period", "overnight_flag", "flight_duration_minutes",
        "flight_duration_hours", "duration_status"
    ]

    missing_cols = [c for c in required_columns if c not in df_fl_ready.columns]
    if missing_cols:
        raise ValueError(f"Final dataset creation failed: missing columns {missing_cols}")

    df_final = df_fl_ready[required_columns].copy()

    # 2. Final Integrity Checks
    assert df_final.duplicated().sum() == 0, "Integrity Error: Found duplicate rows in final dataset!"
    assert df_final.duplicated(subset=["flight_id"]).sum() == 0, "Integrity Error: Found duplicate flight_id primary keys!"
    assert df_final["flight_id"].isnull().sum() == 0, "Integrity Error: Null flight_ids exist!"
    assert (df_final["flight_duration_minutes"] < 0).sum() == 0, "Integrity Error: Negative flight duration present!"
    assert df_final["source"].isnull().sum() == 0 and df_final["destination"].isnull().sum() == 0, "Integrity Error: Missing source/destination!"

    logger.info(f"Final Integrity Checks Passed: {len(df_final)} rows, {len(df_final.columns)} columns.")

    # 3. Construct Rejected / Audit Dataset from Raw Ingestion Comparison
    excel_file = pd.ExcelFile(RAW_PATH, engine="openpyxl")
    raw_fl = pd.read_excel(excel_file, sheet_name="flights")
    total_raw = len(raw_fl)

    # Identify rejected rows (15 full duplicates + 1 conflicting duplicate)
    rejected_records = []
    
    # Check full duplicates in raw
    full_dup_mask = raw_fl.duplicated(keep="first")
    for idx, row in raw_fl[full_dup_mask].iterrows():
        rejected_records.append({
            "flight_id": str(row["flight_id"]),
            "reason": "Exact Full Row Duplicate",
            "validation_status": "REJECTED_DEDUPLICATION"
        })

    # Check conflicting flight_id duplicates
    raw_no_full_dup = raw_fl[~full_dup_mask]
    id_dup_mask = raw_no_full_dup.duplicated(subset=["flight_id"], keep="first")
    for idx, row in raw_no_full_dup[id_dup_mask].iterrows():
        rejected_records.append({
            "flight_id": str(row["flight_id"]),
            "reason": "Conflicting Duplicate Flight ID Details",
            "validation_status": "REJECTED_PRIMARY_KEY_CONFLICT"
        })

    df_rejected = pd.DataFrame(rejected_records)
    total_rejected = len(df_rejected)
    logger.info(f"Audit Trail Generated: {total_rejected} rejected records documented.")

    # 4. Save Final CSV Files
    final_path = os.path.join(PROCESSED_DIR, "final_flights.csv")
    rejected_path = os.path.join(PROCESSED_DIR, "rejected_flights.csv")

    df_final.to_csv(final_path, index=False)
    df_rejected.to_csv(rejected_path, index=False)

    logger.info(f"Final dataset exported to: {final_path}")
    logger.info(f"Rejected dataset exported to: {rejected_path}")

    # Also update final transformed files for bookings, passengers, payments for Power BI completeness
    for df_name in ["transformed_bookings.csv", "transformed_passengers.csv", "transformed_payments.csv"]:
        src_p = os.path.join(PROCESSED_DIR, df_name)
        dst_p = os.path.join(PROCESSED_DIR, df_name.replace("transformed_", "final_"))
        if os.path.exists(src_p):
            df_temp = pd.read_csv(src_p)
            df_temp.to_csv(dst_p, index=False)
            logger.info(f"Exported clean final analytical table: {dst_p}")

    summary_stats = {
        "total_input_records": total_raw,
        "final_analytical_records": len(df_final),
        "rejected_records": total_rejected,
        "duplicate_records": total_rejected,
        "missing_critical_values": 0,
        "overnight_flights": int(df_final["overnight_flag"].astype(int).sum()),
        "valid_durations": (df_final["duration_status"] == "Valid").sum(),
        "suspicious_durations": (df_final["duration_status"] == "Suspicious").sum(),
        "final_validation_status": "READY FOR POWER BI"
    }

    return df_final, df_rejected, summary_stats


def main():
    df_final, df_rejected, summary = build_final_dataset()

    print("\n" + "=" * 60)
    print("           ASG AIRLINES FINAL DATASET SUMMARY")
    print("=" * 60)
    print(f"Total Input Records      : {summary['total_input_records']} (Raw Ingestion)")
    print(f"Final Analytical Records : {summary['final_analytical_records']}")
    print(f"Rejected Records         : {summary['rejected_records']}")
    print(f"Duplicate Records        : {summary['duplicate_records']}")
    print(f"Missing Critical Values  : {summary['missing_critical_values']}")
    print(f"Overnight Flights        : {summary['overnight_flights']}")
    print(f"Valid Durations          : {summary['valid_durations']}")
    print(f"Suspicious Durations     : {summary['suspicious_durations']}")
    print("=" * 60)
    print(f"FINAL DATASET STATUS: {summary['final_validation_status']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
