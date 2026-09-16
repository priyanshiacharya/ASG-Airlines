"""
ASG Airlines Data Engineering Pipeline
Step 7: Flight Duration & Overnight Flight Handling Module

This script processes 'data/processed/transformed_flights.csv' to:
  - Compute precise flight duration in minutes ('flight_duration_minutes')
  - Compute flight duration in hours ('flight_duration_hours')
  - Implement overnight flight handling (arrival < departure -> arrival day 2)
  - Set boolean 'overnight_flag' (True / False)
  - Perform duration validation categorizing records into 'duration_status'
    (Valid, Missing, Suspicious, Invalid)

Outputs final dataset to: 'data/processed/flight_data_ready.csv'
Log file generated: 'logs/flight_duration.log'
"""

import os
import sys
import logging
from typing import Dict, Tuple, Any
import pandas as pd
import numpy as np


# Configure Paths & Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "flight_duration.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_FlightDuration")


def calculate_flight_duration(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Calculates flight duration in minutes and hours, handles overnight flight arithmetic,
    sets overnight_flag, and validates durations into duration_status.

    Validation Rules:
      - 'Missing': departure_time or arrival_time is null.
      - 'Invalid': negative duration (diff < 0).
      - 'Suspicious': zero duration (diff == 0) or extreme durations (< 15 mins or > 600 mins / 10 hrs).
      - 'Valid': all normal durations (15 <= diff <= 600 mins).
    """
    total_flights = len(df)
    logger.info(f"Processing flight duration calculation for {total_flights} records...")

    df_res = df.copy()

    # Convert to datetime objects
    df_res["dep_dt"] = pd.to_datetime(df_res["departure_time"], errors="coerce")
    df_res["arr_dt"] = pd.to_datetime(df_res["arrival_time"], errors="coerce")

    duration_minutes = []
    duration_hours = []
    overnight_flags = []
    duration_statuses = []

    overnight_count = 0
    valid_count = 0
    missing_count = 0
    suspicious_count = 0
    invalid_count = 0

    for idx, row in df_res.iterrows():
        dep = row["dep_dt"]
        arr = row["arr_dt"]

        if pd.isna(dep) or pd.isna(arr):
            duration_minutes.append(np.nan)
            duration_hours.append(np.nan)
            overnight_flags.append(False)
            duration_statuses.append("Missing")
            missing_count += 1
            continue

        is_overnight = False

        # Overnight flight handling: arrival time earlier than departure time
        if arr < dep:
            arr = arr + pd.Timedelta(days=1)
            is_overnight = True
        elif arr.date() > dep.date():
            is_overnight = True

        diff_sec = (arr - dep).total_seconds()
        diff_min = round(diff_sec / 60.0, 2)
        diff_hrs = round(diff_min / 60.0, 2)

        duration_minutes.append(diff_min)
        duration_hours.append(diff_hrs)
        overnight_flags.append(is_overnight)

        if is_overnight:
            overnight_count += 1

        # Validation Rule Assignment
        if diff_min < 0:
            duration_statuses.append("Invalid")
            invalid_count += 1
        elif diff_min == 0 or diff_min < 15 or diff_min > 600:
            duration_statuses.append("Suspicious")
            suspicious_count += 1
        else:
            duration_statuses.append("Valid")
            valid_count += 1

    df_res["flight_duration_minutes"] = duration_minutes
    df_res["flight_duration_hours"] = duration_hours
    df_res["overnight_flag"] = overnight_flags
    df_res["duration_status"] = duration_statuses

    # Drop temporary datetime work columns
    df_res.drop(columns=["dep_dt", "arr_dt"], inplace=True)

    summary_stats = {
        "total_flights": total_flights,
        "overnight_flights": overnight_count,
        "valid_durations": valid_count,
        "missing_durations": missing_count,
        "suspicious_durations": suspicious_count,
        "invalid_durations": invalid_count
    }

    logger.info(f"Duration Calculation Summary: Total={total_flights}, Overnight={overnight_count}, Valid={valid_count}, Missing={missing_count}, Suspicious={suspicious_count}, Invalid={invalid_count}")
    return df_res, summary_stats


def run_flight_duration_pipeline() -> pd.DataFrame:
    """Main execution workflow."""
    logger.info("Starting ASG Airlines Flight Duration Pipeline...")

    input_path = os.path.join(PROCESSED_DIR, "transformed_flights.csv")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Transformed flights file missing at: {input_path}")

    df_transformed = pd.read_csv(input_path)
    df_ready, summary = calculate_flight_duration(df_transformed)

    output_path = os.path.join(PROCESSED_DIR, "flight_data_ready.csv")
    df_ready.to_csv(output_path, index=False)
    logger.info(f"Final flight dataset saved to: {output_path}")

    print("\n" + "=" * 60)
    print("           ASG AIRLINES FLIGHT DURATION SUMMARY")
    print("=" * 60)
    print(f"Total Flights        : {summary['total_flights']}")
    print(f"Overnight Flights    : {summary['overnight_flights']}")
    print(f"Valid Durations      : {summary['valid_durations']}")
    print(f"Missing Durations    : {summary['missing_durations']}")
    print(f"Suspicious Durations : {summary['suspicious_durations']}")
    print(f"Invalid Durations    : {summary['invalid_durations']}")
    print("=" * 60)
    print(f"Dataset successfully exported to: {output_path}\n")

    logger.info("Flight Duration Pipeline completed cleanly.")
    return df_ready


if __name__ == "__main__":
    run_flight_duration_pipeline()
