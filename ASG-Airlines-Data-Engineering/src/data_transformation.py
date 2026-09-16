"""
ASG Airlines Data Engineering Pipeline
Step 6: Data Transformation Module

This script loads cleaned datasets from 'data/processed/' and performs analytical field 
engineering:
  - Route creation (source → destination)
  - Hour extraction (departure_hour, arrival_hour)
  - Time period categorization (Night, Morning, Afternoon, Evening)
  - Overnight flight flagging (arrival date > departure date)
  - Date component extraction for bookings (year, month, day, dayofweek)
  - Age group categorization for passengers (Child, Youth, Adult, Senior)

Outputs analytics-ready datasets to 'data/processed/':
  - transformed_flights.csv
  - transformed_bookings.csv
  - transformed_passengers.csv
  - transformed_payments.csv

Log file generated: 'logs/data_transformation.log'
"""

import os
import sys
import logging
from typing import Dict, Tuple
import pandas as pd


# Setup Paths & Logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "data_transformation.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ASG_Airlines_DataTransformation")


def get_departure_period(hour: int) -> str:
    """
    Categorizes departure hour into time periods:
      - Night:     00:00 - 05:59 (Hours 0-5)
      - Morning:   06:00 - 11:59 (Hours 6-11)
      - Afternoon: 12:00 - 17:59 (Hours 12-17)
      - Evening:   18:00 - 23:59 (Hours 18-23)
    """
    if 0 <= hour < 6:
        return "Night"
    elif 6 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 18:
        return "Afternoon"
    else:
        return "Evening"


def get_age_group(age: int) -> str:
    """Categorizes passenger age into analytical age groups."""
    if age < 12:
        return "Child"
    elif 12 <= age <= 24:
        return "Youth"
    elif 25 <= age <= 59:
        return "Adult"
    else:
        return "Senior"


def transform_flights(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Transforms flights dataset:
    - Route creation (source → destination)
    - Datetime conversion & hour extraction
    - Departure period categorization
    - Overnight flight flagging
    """
    initial_rows = len(df)
    logger.info(f"Transforming 'flights': input record count = {initial_rows}")

    df_trans = df.copy()

    # 1. Datetime conversion
    dep_dt = pd.to_datetime(df_trans["departure_time"])
    arr_dt = pd.to_datetime(df_trans["arrival_time"])

    # 2. Route creation
    df_trans["route"] = df_trans["source"].astype(str) + " → " + df_trans["destination"].astype(str)

    # 3. Hour extractions
    df_trans["departure_hour"] = dep_dt.dt.hour
    df_trans["arrival_hour"] = arr_dt.dt.hour

    # 4. Departure period categorization
    df_trans["departure_period"] = df_trans["departure_hour"].apply(get_departure_period)

    # 5. Overnight flight flag (arrival date > departure date or arrival hour < departure hour)
    is_next_day_date = (arr_dt.dt.date > dep_dt.dt.date)
    is_next_day_hour = (df_trans["arrival_hour"] < df_trans["departure_hour"])
    df_trans["overnight_flag"] = (is_next_day_date | is_next_day_hour).astype(int)

    overnight_cnt = df_trans["overnight_flag"].sum()
    logger.info(f"'flights': created route, departure_hour, arrival_hour, departure_period. Flagged {overnight_cnt} overnight flights.")

    # Reorder columns logically
    col_order = [
        "flight_id", "airline", "source", "destination", "route",
        "departure_time", "arrival_time", "departure_hour", "arrival_hour",
        "departure_period", "overnight_flag", "duration"
    ]
    df_trans = df_trans[[c for c in col_order if c in df_trans.columns]]

    cols_created = "route, departure_hour, arrival_hour, departure_period, overnight_flag"
    return df_trans, {"input_rows": initial_rows, "output_rows": len(df_trans), "cols_created": cols_created}


def transform_bookings(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Transforms bookings dataset:
    - Date component extractions (booking_year, booking_month, booking_day, booking_dayofweek)
    """
    initial_rows = len(df)
    logger.info(f"Transforming 'bookings': input record count = {initial_rows}")

    df_trans = df.copy()
    bdate = pd.to_datetime(df_trans["booking_date"])

    df_trans["booking_year"] = bdate.dt.year
    df_trans["booking_month"] = bdate.dt.month
    df_trans["booking_day"] = bdate.dt.day
    df_trans["booking_dayofweek"] = bdate.dt.day_name()

    cols_created = "booking_year, booking_month, booking_day, booking_dayofweek"
    logger.info(f"'bookings': extracted date components ({cols_created}).")

    return df_trans, {"input_rows": initial_rows, "output_rows": len(df_trans), "cols_created": cols_created}


def transform_passengers(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Transforms passengers dataset:
    - Categorizes age into age_group (Child, Youth, Adult, Senior)
    """
    initial_rows = len(df)
    logger.info(f"Transforming 'passengers': input record count = {initial_rows}")

    df_trans = df.copy()
    df_trans["age_group"] = df_trans["age"].astype(int).apply(get_age_group)

    cols_created = "age_group"
    logger.info(f"'passengers': created categorical field 'age_group'.")

    return df_trans, {"input_rows": initial_rows, "output_rows": len(df_trans), "cols_created": cols_created}


def transform_payments(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Transforms payments dataset:
    - Enforces numeric schema & data type consistency.
    """
    initial_rows = len(df)
    logger.info(f"Transforming 'payments': input record count = {initial_rows}")

    df_trans = df.copy()
    df_trans["amount"] = df_trans["amount"].astype(float).round(2)
    df_trans["payment_id"] = df_trans["payment_id"].astype(str)
    df_trans["booking_id"] = df_trans["booking_id"].astype(str)
    df_trans["payment_method"] = df_trans["payment_method"].astype(str)

    cols_created = "Data type standardization"
    logger.info("'payments': standardized data types.")

    return df_trans, {"input_rows": initial_rows, "output_rows": len(df_trans), "cols_created": cols_created}


def run_data_transformation_pipeline() -> None:
    """Orchestrates data transformation pipeline across all cleaned datasets."""
    logger.info("Starting ASG Airlines Data Transformation Pipeline...")

    fl_path = os.path.join(PROCESSED_DIR, "cleaned_flights.csv")
    bk_path = os.path.join(PROCESSED_DIR, "cleaned_bookings.csv")
    pass_path = os.path.join(PROCESSED_DIR, "cleaned_passengers.csv")
    pay_path = os.path.join(PROCESSED_DIR, "cleaned_payments.csv")

    for p in [fl_path, bk_path, pass_path, pay_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Cleaned dataset missing at: {p}")

    df_fl = pd.read_csv(fl_path)
    df_bk = pd.read_csv(bk_path)
    df_pass = pd.read_csv(pass_path)
    df_pay = pd.read_csv(pay_path)

    # Transformations
    trans_fl, fl_meta = transform_flights(df_fl)
    trans_bk, bk_meta = transform_bookings(df_bk)
    trans_pass, pass_meta = transform_passengers(df_pass)
    trans_pay, pay_meta = transform_payments(df_pay)

    # Save transformed datasets
    trans_fl.to_csv(os.path.join(PROCESSED_DIR, "transformed_flights.csv"), index=False)
    trans_bk.to_csv(os.path.join(PROCESSED_DIR, "transformed_bookings.csv"), index=False)
    trans_pass.to_csv(os.path.join(PROCESSED_DIR, "transformed_passengers.csv"), index=False)
    trans_pay.to_csv(os.path.join(PROCESSED_DIR, "transformed_payments.csv"), index=False)

    summary_list = [
        {"Dataset": "transformed_flights.csv", **fl_meta},
        {"Dataset": "transformed_bookings.csv", **bk_meta},
        {"Dataset": "transformed_passengers.csv", **pass_meta},
        {"Dataset": "transformed_payments.csv", **pay_meta}
    ]

    summary_df = pd.DataFrame(summary_list)

    print("\n" + "=" * 90)
    print("                    ASG AIRLINES DATA TRANSFORMATION SUMMARY")
    print("=" * 90)
    print(summary_df.to_string(index=False))
    print("=" * 90)
    print(f"Transformed datasets exported successfully to: {PROCESSED_DIR}\n")

    logger.info("Data Transformation Pipeline finished cleanly.")


if __name__ == "__main__":
    run_data_transformation_pipeline()
