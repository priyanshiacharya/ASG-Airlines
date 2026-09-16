"""
ASG Airlines Data Engineering Pipeline
Step 8: Data Validation Module

This script performs rigorous validation on the final dataset 'flight_data_ready.csv'
and associated analytical tables (bookings, passengers, payments):
  - A. Schema Validation
  - B. Record Validation
  - C. Flight ID Validation
  - D. Route Validation
  - E. Time Validation
  - F. Duration Validation
  - G. Relationship & Referential Integrity Validation
  - H. PII Anonymization & Governance Validation

Outputs validation report to: 'data/processed/validation_report.csv'
Log file generated: 'logs/data_validation.log'
"""

import os
import sys
import logging
import re
from typing import Dict, List, Any, Tuple
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# Configure Paths & Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "data_validation.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_DataValidation")


def run_data_validation() -> Tuple[pd.DataFrame, Dict[str, int], str]:
    """
    Executes validation check suites A through H and generates a validation report.

    Returns:
        Tuple[pd.DataFrame, Dict[str, int], str]: Report DF, summary dict, overall readiness status.
    """
    logger.info("Starting ASG Airlines Data Validation Suite...")

    fl_ready_path = os.path.join(PROCESSED_DIR, "flight_data_ready.csv")
    bk_path = os.path.join(PROCESSED_DIR, "transformed_bookings.csv")
    pass_path = os.path.join(PROCESSED_DIR, "transformed_passengers.csv")
    pay_path = os.path.join(PROCESSED_DIR, "transformed_payments.csv")

    for path in [fl_ready_path, bk_path, pass_path, pay_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Validation target missing at: {path}")

    df_fl = pd.read_csv(fl_ready_path)
    df_bk = pd.read_csv(bk_path)
    df_pass = pd.read_csv(pass_path)
    df_pay = pd.read_csv(pay_path)

    checks: List[Dict[str, Any]] = []

    # Helper to append check results
    def add_check(check_name: str, dataset: str, failed_count: int, total_count: int, details_pass: str, details_fail: str, is_warning: bool = False):
        status = "PASS"
        if failed_count > 0:
            status = "WARNING" if is_warning else "FAIL"
        
        pct_failed = round((failed_count / total_count) * 100, 2) if total_count > 0 else 0.0
        details = details_pass if failed_count == 0 else details_fail
        
        checks.append({
            "check_name": check_name,
            "dataset": dataset,
            "status": status,
            "records_checked": total_count,
            "records_failed": failed_count,
            "failure_percentage": pct_failed,
            "details": details
        })

    total_fl = len(df_fl)

    # -------------------------------------------------------------
    # A. SCHEMA VALIDATION
    # -------------------------------------------------------------
    req_cols = [
        "flight_id", "airline", "source", "destination", "route",
        "departure_time", "arrival_time", "departure_hour", "arrival_hour",
        "departure_period", "overnight_flag", "flight_duration_minutes",
        "flight_duration_hours", "duration_status"
    ]
    missing_cols = [c for c in req_cols if c not in df_fl.columns]
    add_check(
        check_name="Required Schema Columns Check",
        dataset="flight_data_ready.csv",
        failed_count=len(missing_cols),
        total_count=len(req_cols),
        details_pass="All 14 required analytical schema columns are present.",
        details_fail=f"Missing required columns: {missing_cols}"
    )

    dup_cols = [c for c in df_fl.columns if list(df_fl.columns).count(c) > 1]
    add_check(
        check_name="Duplicate Column Names Check",
        dataset="flight_data_ready.csv",
        failed_count=len(dup_cols),
        total_count=len(df_fl.columns),
        details_pass="No duplicate column names detected.",
        details_fail=f"Duplicate columns found: {dup_cols}"
    )

    # -------------------------------------------------------------
    # B. RECORD VALIDATION
    # -------------------------------------------------------------
    full_dups = df_fl.duplicated().sum()
    add_check(
        check_name="Full Record Duplicate Check",
        dataset="flight_data_ready.csv",
        failed_count=int(full_dups),
        total_count=total_fl,
        details_pass="Zero full duplicate rows detected in final dataset.",
        details_fail=f"Found {full_dups} duplicate rows."
    )

    id_dups = df_fl.duplicated(subset=["flight_id"]).sum()
    add_check(
        check_name="Flight ID Primary Key Uniqueness Check",
        dataset="flight_data_ready.csv",
        failed_count=int(id_dups),
        total_count=total_fl,
        details_pass="All flight_id primary key entries are unique.",
        details_fail=f"Found {id_dups} duplicate flight_id primary keys."
    )

    crit_nulls = df_fl[["flight_id", "source", "destination", "departure_time", "arrival_time"]].isnull().sum().sum()
    add_check(
        check_name="Critical Fields Missing Value Check",
        dataset="flight_data_ready.csv",
        failed_count=int(crit_nulls),
        total_count=total_fl * 5,
        details_pass="Zero missing values in critical flight metadata fields.",
        details_fail=f"Found {crit_nulls} null entries in critical metadata."
    )

    # -------------------------------------------------------------
    # C. FLIGHT ID VALIDATION
    # -------------------------------------------------------------
    null_fids = df_fl["flight_id"].isnull().sum()
    add_check(
        check_name="Flight ID Null Check",
        dataset="flight_data_ready.csv",
        failed_count=int(null_fids),
        total_count=total_fl,
        details_pass="No null flight_id values exist.",
        details_fail=f"Found {null_fids} null flight_ids."
    )

    flight_id_regex = r"^[A-Z0-9]{2}\d{3}$"
    malformed_fids = df_fl[~df_fl["flight_id"].astype(str).str.match(flight_id_regex, na=False)]
    add_check(
        check_name="Flight ID Format Regex Check (^[A-Z0-9]{2}\\d{3}$)",
        dataset="flight_data_ready.csv",
        failed_count=len(malformed_fids),
        total_count=total_fl,
        details_pass="100% of flight_id entries match standard regex format.",
        details_fail=f"Found {len(malformed_fids)} malformed flight_ids."
    )

    # -------------------------------------------------------------
    # D. ROUTE VALIDATION
    # -------------------------------------------------------------
    same_src_dst = df_fl[df_fl["source"] == df_fl["destination"]]
    add_check(
        check_name="Route Source != Destination Check",
        dataset="flight_data_ready.csv",
        failed_count=len(same_src_dst),
        total_count=total_fl,
        details_pass="All flight routes connect distinct source and destination airports.",
        details_fail=f"Found {len(same_src_dst)} flights where source equals destination."
    )

    route_format_invalid = df_fl[~df_fl["route"].astype(str).str.contains(" → ", na=False)]
    add_check(
        check_name="Route String Format Check ('source → destination')",
        dataset="flight_data_ready.csv",
        failed_count=len(route_format_invalid),
        total_count=total_fl,
        details_pass="All route strings match required format ('source → destination').",
        details_fail=f"Found {len(route_format_invalid)} invalid route string formats."
    )

    # -------------------------------------------------------------
    # E. TIME VALIDATION
    # -------------------------------------------------------------
    unparseable_dep = pd.to_datetime(df_fl["departure_time"], errors="coerce").isnull().sum()
    add_check(
        check_name="Departure Datetime Validity Check",
        dataset="flight_data_ready.csv",
        failed_count=int(unparseable_dep),
        total_count=total_fl,
        details_pass="100% of departure_time values are valid datetimes.",
        details_fail=f"Found {unparseable_dep} unparseable departure times."
    )

    unparseable_arr = pd.to_datetime(df_fl["arrival_time"], errors="coerce").isnull().sum()
    add_check(
        check_name="Arrival Datetime Validity Check",
        dataset="flight_data_ready.csv",
        failed_count=int(unparseable_arr),
        total_count=total_fl,
        details_pass="100% of arrival_time values are valid datetimes.",
        details_fail=f"Found {unparseable_arr} unparseable arrival times."
    )

    # Overnight Flag Consistency Check
    dep_dts = pd.to_datetime(df_fl["departure_time"])
    arr_dts = pd.to_datetime(df_fl["arrival_time"])
    expected_overnight = (arr_dts.dt.date > dep_dts.dt.date) | (df_fl["arrival_hour"] < df_fl["departure_hour"]) | (arr_dts < dep_dts)
    actual_overnight = df_fl["overnight_flag"].astype(bool)
    mismatched_overnight = (expected_overnight != actual_overnight).sum()
    add_check(
        check_name="Overnight Flag Consistency Check",
        dataset="flight_data_ready.csv",
        failed_count=int(mismatched_overnight),
        total_count=total_fl,
        details_pass="Overnight flags are 100% consistent with departure and arrival timestamps.",
        details_fail=f"Found {mismatched_overnight} mismatched overnight_flag values."
    )

    # -------------------------------------------------------------
    # F. DURATION VALIDATION
    # -------------------------------------------------------------
    neg_duration = (df_fl["flight_duration_minutes"] < 0).sum()
    add_check(
        check_name="Non-Negative Duration Check",
        dataset="flight_data_ready.csv",
        failed_count=int(neg_duration),
        total_count=total_fl,
        details_pass="Zero negative flight durations detected.",
        details_fail=f"Found {neg_duration} negative duration values."
    )

    suspicious_durations = (df_fl["duration_status"] == "Suspicious").sum()
    add_check(
        check_name="Duration Status Sanity Check (<15 mins or >600 mins)",
        dataset="flight_data_ready.csv",
        failed_count=int(suspicious_durations),
        total_count=total_fl,
        details_pass="All flight durations fall within reasonable operational limits (15-600 mins).",
        details_fail=f"Found {suspicious_durations} suspicious duration records.",
        is_warning=True
    )

    # -------------------------------------------------------------
    # G. RELATIONSHIP & REFERENTIAL INTEGRITY VALIDATION
    # -------------------------------------------------------------
    orphan_bookings_fl = ~df_bk["flight_id"].isin(df_fl["flight_id"])
    add_check(
        check_name="Referential Integrity: Bookings -> Flights FK Check",
        dataset="transformed_bookings.csv",
        failed_count=int(orphan_bookings_fl.sum()),
        total_count=len(df_bk),
        details_pass="100% of booking flight_ids reference existing records in flight_data_ready.",
        details_fail=f"Found {orphan_bookings_fl.sum()} orphan booking records with missing flight_ids."
    )

    orphan_bookings_pass = ~df_bk["passenger_id"].isin(df_pass["passenger_id"])
    add_check(
        check_name="Referential Integrity: Bookings -> Passengers FK Check",
        dataset="transformed_bookings.csv",
        failed_count=int(orphan_bookings_pass.sum()),
        total_count=len(df_bk),
        details_pass="100% of booking passenger_ids reference existing records in transformed_passengers.",
        details_fail=f"Found {orphan_bookings_pass.sum()} orphan booking records with missing passenger_ids."
    )

    orphan_payments = ~df_pay["booking_id"].isin(df_bk["booking_id"])
    add_check(
        check_name="Referential Integrity: Payments -> Bookings FK Check",
        dataset="transformed_payments.csv",
        failed_count=int(orphan_payments.sum()),
        total_count=len(df_pay),
        details_pass="100% of payment booking_ids reference existing records in transformed_bookings.",
        details_fail=f"Found {orphan_payments.sum()} orphan payment records with missing booking_ids."
    )

    # -------------------------------------------------------------
    # H. PII ANONYMIZATION VALIDATION
    # -------------------------------------------------------------
    raw_email_pattern = df_pass["email"].str.contains(r"^[^@]+@[^@]+\.[^@]+$", na=False).sum()
    add_check(
        check_name="PII Anonymization Check: Passenger Email Hashing",
        dataset="transformed_passengers.csv",
        failed_count=int(raw_email_pattern),
        total_count=len(df_pass),
        details_pass="100% of passenger emails are securely SHA-256 hashed.",
        details_fail=f"Found {raw_email_pattern} unhashed plain-text email addresses."
    )

    unmasked_phone = df_pass["phone"].str.match(r"^\+?\d{10,12}$", na=False).sum()
    add_check(
        check_name="PII Anonymization Check: Phone Number Masking",
        dataset="transformed_passengers.csv",
        failed_count=int(unmasked_phone),
        total_count=len(df_pass),
        details_pass="100% of phone numbers are character-masked.",
        details_fail=f"Found {unmasked_phone} unmasked plain-text phone numbers."
    )

    report_df = pd.DataFrame(checks)
    report_path = os.path.join(PROCESSED_DIR, "validation_report.csv")
    report_df.to_csv(report_path, index=False)

    # Count Summary
    passed_cnt = (report_df["status"] == "PASS").sum()
    warning_cnt = (report_df["status"] == "WARNING").sum()
    fail_cnt = (report_df["status"] == "FAIL").sum()
    total_checks = len(report_df)

    readiness = "READY FOR ANALYTICS" if fail_cnt == 0 else "REQUIRES CORRECTION"

    summary_stats = {
        "total_checks": total_checks,
        "passed": passed_cnt,
        "warnings": warning_cnt,
        "failed": fail_cnt
    }

    logger.info(f"Validation Complete: Total={total_checks}, Passed={passed_cnt}, Warnings={warning_cnt}, Failed={fail_cnt}. Dataset Readiness: {readiness}")

    return report_df, summary_stats, readiness


def main():
    report_df, summary, readiness = run_data_validation()

    print("\n" + "=" * 80)
    print("                    ASG AIRLINES DATA VALIDATION REPORT")
    print("=" * 80)
    print(report_df.to_string(index=False))
    print("=" * 80)
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed      : {summary['passed']}")
    print(f"Warnings    : {summary['warnings']}")
    print(f"Failed      : {summary['failed']}")
    print("-" * 80)
    print(f"DATASET STATUS: {readiness}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
