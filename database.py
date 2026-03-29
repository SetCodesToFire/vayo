import os
import psycopg2
import pandas as pd
from datetime import date as date_cls
import hashlib

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


def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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
    CREATE TABLE IF NOT EXISTS drivers (
        driver_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        dl_number TEXT NOT NULL,
        aadhar_number TEXT NOT NULL,
        current_address TEXT NOT NULL,
        permanent_address TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        emergency_contact TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        date_of_joining DATE NOT NULL
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_leave_balances (
        driver_id TEXT PRIMARY KEY,
        total_leaves_taken INTEGER NOT NULL DEFAULT 0,
        carry_forward INTEGER NOT NULL DEFAULT 0,
        first_month_leaves INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS super_users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM super_users")
    super_count = cursor.fetchone()[0] or 0
    if super_count == 0:
        default_password = os.environ.get("VAYO_SUPER_USER_PASSWORD", "VayoSuperAdmin")
        cursor.execute(
            """
            INSERT INTO super_users (username, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
            """,
            ("admin", _hash_password(default_password)),
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


def authenticate_super_user(username, password):
    if not username or not password:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM super_users
        WHERE username = %s AND password_hash = %s
        """,
        (username.strip(), _hash_password(password)),
    )
    ok = cursor.fetchone() is not None
    conn.close()
    return ok


def _generate_driver_id(cursor):
    cursor.execute(
        """
        SELECT driver_id
        FROM drivers
        WHERE driver_id LIKE 'DRV%'
        ORDER BY driver_id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return "DRV001"

    latest = row[0]
    try:
        num = int(latest.replace("DRV", ""))
    except ValueError:
        num = 0
    return f"DRV{num + 1:03d}"


def onboard_driver(
    first_name,
    last_name,
    dl_number,
    aadhar_number,
    current_address,
    permanent_address,
    phone_number,
    emergency_contact,
    password,
):
    if not dl_number or not aadhar_number:
        return False, "DL Number and Aadhar Number are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    join_date = date_cls.today()
    first_month_leaves = 4 if join_date.day <= 15 else 2

    conn = get_connection()
    cursor = conn.cursor()
    try:
        driver_id = _generate_driver_id(cursor)
        cursor.execute(
            """
            INSERT INTO drivers (
                driver_id, first_name, last_name, dl_number, aadhar_number,
                current_address, permanent_address, phone_number,
                emergency_contact, password_hash, date_of_joining
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                driver_id, first_name, last_name, dl_number, aadhar_number,
                current_address, permanent_address, phone_number,
                emergency_contact, _hash_password(password), join_date
            )
        )
        cursor.execute(
            """
            INSERT INTO driver_leave_balances (driver_id, first_month_leaves)
            VALUES (%s, %s)
            ON CONFLICT (driver_id) DO NOTHING
            """,
            (driver_id, first_month_leaves)
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        conn.close()
        if "phone_number" in str(exc).lower():
            return False, "Phone number already exists. Use a unique phone number."
        return False, "Unable to onboard driver. Please try again."

    conn.close()
    masked_aadhar = ("*" * max(0, len(aadhar_number) - 4)) + aadhar_number[-4:]
    return True, {
        "driver_id": driver_id,
        "date_of_joining": join_date,
        "first_month_leaves": first_month_leaves,
        "masked_aadhar": masked_aadhar,
    }


def authenticate_driver(phone_number, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT driver_id
        FROM drivers
        WHERE phone_number = %s AND password_hash = %s
        """,
        (phone_number, _hash_password(password))
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_driver_profile(driver_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT driver_id, first_name, last_name, phone_number, date_of_joining
        FROM drivers
        WHERE driver_id = %s
        """,
        (driver_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "driver_id": row[0],
        "name": f"{row[1]} {row[2]}".strip(),
        "phone_number": row[3],
        "date_of_joining": row[4],
    }


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
        SELECT date_of_joining
        FROM drivers
        WHERE driver_id = %s
        """,
        (driver_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {
            "current_month_taken": 0,
            "current_month_remaining": 0,
            "carry_forward": 0,
            "total_available": 0,
            "projected_bonus": 0,
            "first_month_limit": 0,
            "date_of_joining": None,
        }

    join_date = row[0]
    first_month_limit = 4 if join_date.day <= 15 else 2

    if (year < join_date.year) or (year == join_date.year and month < join_date.month):
        conn.close()
        return {
            "current_month_taken": 0,
            "current_month_remaining": 0,
            "carry_forward": 0,
            "total_available": 0,
            "projected_bonus": 0,
            "first_month_limit": first_month_limit,
            "date_of_joining": join_date,
        }

    current_month_limit = first_month_limit if (year == join_date.year and month == join_date.month) else MONTHLY_LEAVE_LIMIT

    current_month_filter = "driver_id = %s AND year = %s AND month = %s AND leave_taken = 1"
    current_params = [driver_id, year, month]
    if year == join_date.year and month == join_date.month:
        current_month_filter += " AND date >= %s"
        current_params.append(join_date)

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM driver_leaves
        WHERE {current_month_filter}
        """,
        tuple(current_params)
    )
    current_month_taken = cursor.fetchone()[0] or 0

    carry_forward = 0
    yearly_entitlement = 0
    yearly_taken = 0

    for m in range(1, month):
        if year == join_date.year and m < join_date.month:
            continue
        month_limit = first_month_limit if (year == join_date.year and m == join_date.month) else MONTHLY_LEAVE_LIMIT
        yearly_entitlement += month_limit

        month_filter = "driver_id = %s AND year = %s AND month = %s AND leave_taken = 1"
        month_params = [driver_id, year, m]
        if year == join_date.year and m == join_date.month:
            month_filter += " AND date >= %s"
            month_params.append(join_date)

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM driver_leaves
            WHERE {month_filter}
            """,
            tuple(month_params)
        )
        month_taken = cursor.fetchone()[0] or 0
        yearly_taken += month_taken

    carry_forward = max(0, yearly_entitlement - yearly_taken)
    current_month_remaining = max(0, current_month_limit - current_month_taken)
    total_available = carry_forward + current_month_remaining
    projected_bonus = total_available * 500
    conn.close()

    return {
        "current_month_taken": current_month_taken,
        "current_month_remaining": current_month_remaining,
        "carry_forward": carry_forward,
        "total_available": total_available,
        "projected_bonus": projected_bonus,
        "first_month_limit": first_month_limit,
        "date_of_joining": join_date,
    }


def apply_driver_leave(driver_id, leave_date, reason):
    conn = get_connection()
    cursor = conn.cursor()
    if isinstance(leave_date, date_cls):
        leave_date_obj = leave_date
    else:
        leave_date_obj = pd.to_datetime(leave_date).date()

    cursor.execute("SELECT date_of_joining FROM drivers WHERE driver_id = %s", (driver_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Driver profile not found."
    join_date = row[0]

    if leave_date_obj < join_date:
        conn.close()
        return False, "Cannot apply leave before date of joining."

    leave_year = leave_date_obj.year
    leave_month = leave_date_obj.month
    summary = get_driver_leave_summary(driver_id, leave_year, leave_month)
    if summary["current_month_remaining"] <= 0:
        conn.close()
        return False, "Monthly leave limit exceeded for this month."
    if summary["total_available"] <= 0:
        conn.close()
        return False, "No leaves available to apply."

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
    cursor.execute(
        """
        INSERT INTO driver_leave_balances (driver_id, total_leaves_taken, carry_forward, first_month_leaves, updated_at)
        VALUES (%s, 1, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (driver_id)
        DO UPDATE SET
            total_leaves_taken = driver_leave_balances.total_leaves_taken + 1,
            carry_forward = %s,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            driver_id,
            summary["carry_forward"],
            summary["first_month_limit"],
            summary["carry_forward"],
        )
    )
    conn.commit()
    conn.close()
    return True, "Leave applied successfully."


def get_admin_leave_dashboard_data(year, month=None):
    conn = get_connection()

    driver_df = pd.read_sql(
        """
        SELECT driver_id, first_name, last_name, phone_number, date_of_joining
        FROM drivers
        ORDER BY driver_id
        """,
        conn,
    )

    leave_query = """
        SELECT driver_id, date, reason, month, year, leave_taken
        FROM driver_leaves
        WHERE year = %s
    """
    params = [year]
    if month:
        leave_query += " AND month = %s"
        params.append(month)
    leave_query += " ORDER BY date DESC"

    leave_df = pd.read_sql(leave_query, conn, params=tuple(params))
    conn.close()

    if driver_df.empty:
        return {
            "driver_count": 0,
            "leave_count": 0,
            "avg_leaves_per_driver": 0.0,
            "driver_summary": pd.DataFrame(),
            "leave_history": pd.DataFrame(),
        }

    if leave_df.empty:
        driver_summary = driver_df.copy()
        driver_summary["driver_name"] = (
            driver_summary["first_name"].fillna("") + " " + driver_summary["last_name"].fillna("")
        ).str.strip()
        driver_summary["leaves_taken"] = 0
        driver_summary["last_leave_date"] = pd.NaT
        driver_summary = driver_summary[
            ["driver_id", "driver_name", "phone_number", "date_of_joining", "leaves_taken", "last_leave_date"]
        ]
        return {
            "driver_count": int(len(driver_summary)),
            "leave_count": 0,
            "avg_leaves_per_driver": 0.0,
            "driver_summary": driver_summary,
            "leave_history": pd.DataFrame(),
        }

    leave_df["date"] = pd.to_datetime(leave_df["date"], errors="coerce")

    leave_counts = (
        leave_df.groupby("driver_id")
        .agg(leaves_taken=("leave_taken", "sum"), last_leave_date=("date", "max"))
        .reset_index()
    )

    driver_summary = driver_df.merge(leave_counts, on="driver_id", how="left")
    driver_summary["driver_name"] = (
        driver_summary["first_name"].fillna("") + " " + driver_summary["last_name"].fillna("")
    ).str.strip()
    driver_summary["leaves_taken"] = driver_summary["leaves_taken"].fillna(0).astype(int)
    driver_summary = driver_summary[
        ["driver_id", "driver_name", "phone_number", "date_of_joining", "leaves_taken", "last_leave_date"]
    ].sort_values(["leaves_taken", "driver_name"], ascending=[False, True])

    leave_history = leave_df.merge(
        driver_df[["driver_id", "first_name", "last_name"]],
        on="driver_id",
        how="left",
    )
    leave_history["driver_name"] = (
        leave_history["first_name"].fillna("") + " " + leave_history["last_name"].fillna("")
    ).str.strip()
    leave_history = leave_history[
        ["driver_id", "driver_name", "date", "reason", "month", "year"]
    ].sort_values("date", ascending=False)

    total_drivers = int(len(driver_summary))
    total_leaves = int(driver_summary["leaves_taken"].sum())
    avg_leaves = round(total_leaves / total_drivers, 2) if total_drivers else 0.0

    return {
        "driver_count": total_drivers,
        "leave_count": total_leaves,
        "avg_leaves_per_driver": avg_leaves,
        "driver_summary": driver_summary,
        "leave_history": leave_history,
    }
