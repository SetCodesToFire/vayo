import psycopg2
import pandas as pd
from datetime import date as date_cls

# -------------------------------
# DB CONFIG (Replace with Supabase credentials)
# -------------------------------
DB_CONFIG = {
    "host": "aws-1-ap-northeast-1.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.lypebrexlzjzyetkkkfp",
    "password": "Vayocab123@",
    "port": "5432"
}

MONTHLY_LEAVE_LIMIT = 4
DEFAULT_DRIVER_CREDENTIALS = [
    ("DRV001", "Laxman", "passLaxMan"),
    ("DRV002", "Devender", "passDeVen"),
    ("DRV003", "Suraj", "passSuRaj"),
]


# -------------------------------
# CONNECTION HELPER
# -------------------------------
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# -------------------------------
# INIT DB
# -------------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payouts (
        id SERIAL PRIMARY KEY,
        driver TEXT,
        date DATE,
        fare FLOAT,
        subscription FLOAT,
        cash FLOAT,
        tip FLOAT,
        net_payout FLOAT,
        driver_gross FLOAT,
        cng FLOAT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_credentials (
        driver_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_leaves (
        id SERIAL PRIMARY KEY,
        driver_id TEXT NOT NULL,
        date DATE NOT NULL,
        leave_taken INTEGER NOT NULL DEFAULT 1,
        reason TEXT,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(driver_id, date)
    )
    """)

    cursor.executemany(
        """
        INSERT INTO driver_credentials (driver_id, username, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (driver_id) DO NOTHING
        """,
        DEFAULT_DRIVER_CREDENTIALS
    )

    conn.commit()
    conn.close()


# -------------------------------
# INSERT SINGLE ROW
# -------------------------------
def insert_payout(row, date, cng):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payouts 
    (driver, date, fare, subscription, cash, tip, net_payout, driver_gross, cng)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row['Driver'],
        date,
        float(row['Fare']),
        float(row['Subscription']),
        float(row['Cash_Collected']),
        float(row['Tip']),
        float(row['Net_Payout']),
        float(row['Driver_Gross']),
        float(cng)
    ))

    conn.commit()
    conn.close()


# -------------------------------
# BULK SAVE (Optimized)
# -------------------------------
def save_to_db(df, date, cng):
    conn = get_connection()
    cursor = conn.cursor()

    data = [
        (
            row['Driver'],
            date,
            float(row['Fare']),
            float(row['Subscription']),
            float(row['Cash_Collected']),
            float(row['Tip']),
            float(row['Net_Payout']),
            float(row['Driver_Gross']),
            float(cng)
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany("""
    INSERT INTO payouts 
    (driver, date, fare, subscription, cash, tip, net_payout, driver_gross, cng)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, data)

    conn.commit()
    conn.close()


# -------------------------------
# GET DATA
# -------------------------------
def get_dataframe():
    conn = get_connection()

    try:
        df = pd.read_sql("SELECT * FROM payouts", conn)
    except:
        df = pd.DataFrame()

    conn.close()
    return df


def authenticate_driver(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT driver_id
        FROM driver_credentials
        WHERE username = %s AND password = %s
        """,
        (username, password)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_driver_leave_history(driver_id):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT date, leave_taken, reason, month, year
        FROM driver_leaves
        WHERE driver_id = %s
        ORDER BY date DESC
        """,
        conn,
        params=(driver_id,)
    )
    conn.close()
    return df


def get_driver_leave_summary(driver_id, year, month):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM driver_leaves
        WHERE driver_id = %s AND year = %s AND month = %s AND leave_taken = 1
        """,
        (driver_id, year, month)
    )
    current_month_taken = cursor.fetchone()[0] or 0

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM driver_leaves
        WHERE driver_id = %s AND year = %s AND month < %s AND leave_taken = 1
        """,
        (driver_id, year, month)
    )
    previous_months_taken = cursor.fetchone()[0] or 0
    conn.close()

    months_completed = max(0, month - 1)
    earned_until_last_month = months_completed * MONTHLY_LEAVE_LIMIT
    carry_forward = max(0, earned_until_last_month - previous_months_taken)
    current_month_remaining = max(0, MONTHLY_LEAVE_LIMIT - current_month_taken)
    total_available = carry_forward + current_month_remaining
    projected_bonus = total_available * 500

    return {
        "current_month_taken": current_month_taken,
        "current_month_remaining": current_month_remaining,
        "carry_forward": carry_forward,
        "total_available": total_available,
        "projected_bonus": projected_bonus,
    }


def apply_driver_leave(driver_id, leave_date, reason):
    if isinstance(leave_date, date_cls):
        leave_date_obj = leave_date
    else:
        leave_date_obj = pd.to_datetime(leave_date).date()

    leave_year = leave_date_obj.year
    leave_month = leave_date_obj.month
    summary = get_driver_leave_summary(driver_id, leave_year, leave_month)

    if summary["current_month_remaining"] <= 0:
        return False, "Monthly leave limit exceeded for this month."
    if summary["total_available"] <= 0:
        return False, "No leaves available to apply."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM driver_leaves
        WHERE driver_id = %s AND date = %s
        """,
        (driver_id, leave_date_obj)
    )
    exists = cursor.fetchone()
    if exists:
        conn.close()
        return False, "Leave already applied for this date."

    cursor.execute(
        """
        INSERT INTO driver_leaves (driver_id, date, leave_taken, reason, month, year)
        VALUES (%s, %s, 1, %s, %s, %s)
        """,
        (driver_id, leave_date_obj, reason.strip(), leave_month, leave_year)
    )
    conn.commit()
    conn.close()
    return True, "Leave applied successfully."
