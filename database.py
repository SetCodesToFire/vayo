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

    # Extended payout fields (safe to add even if table already exists)
    cursor.execute("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS driver_id TEXT")
    cursor.execute("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS vehicle_id TEXT")
    cursor.execute("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS payment_status TEXT DEFAULT 'Pending'")
    cursor.execute("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS trips_count INTEGER DEFAULT 0")
    cursor.execute("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS cash_adjustment FLOAT DEFAULT 0")

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

    cursor.execute("ALTER TABLE drivers ADD COLUMN IF NOT EXISTS monthly_income_target FLOAT")

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

    cursor.execute(
        "ALTER TABLE driver_leaves ADD COLUMN IF NOT EXISTS leave_status TEXT NOT NULL DEFAULT 'Pending'"
    )
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_leave_balances (
        driver_id TEXT PRIMARY KEY,
        total_leaves_taken INTEGER NOT NULL DEFAULT 0,
        carry_forward INTEGER NOT NULL DEFAULT 0,
        first_month_leaves INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # -------------------------------
    # Fleet / Vehicle data model
    # -------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id TEXT PRIMARY KEY,
        vehicle_number TEXT UNIQUE NOT NULL,
        date_of_purchase DATE NOT NULL,
        permit_expiry DATE,
        insurance_expiry DATE,
        service_due_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_vehicle_assignments (
        id SERIAL PRIMARY KEY,
        driver_id TEXT NOT NULL,
        vehicle_id TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,
        UNIQUE(driver_id, start_date)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_daily_cng (
        id SERIAL PRIMARY KEY,
        vehicle_id TEXT NOT NULL,
        date DATE NOT NULL,
        cng_amount FLOAT NOT NULL DEFAULT 0,
        UNIQUE(vehicle_id, date)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_monthly_targets (
        driver_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        target_amount FLOAT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (driver_id, year, month)
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
def insert_payout(row, date, cng=None, payment_status="Pending"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payouts 
    (driver, driver_id, vehicle_id, date, fare, subscription, cash, tip, net_payout, driver_gross, cng, trips_count, cash_adjustment, payment_status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row.get('Driver'),
        row.get('driver_id'),
        row.get('vehicle_id'),
        date,
        float(row.get('Fare', 0)),
        float(row.get('Subscription', 0)),
        float(row.get('Cash_Collected', 0)),
        float(row.get('Tip', 0)),
        float(row.get('Net_Payout', 0)),
        float(row.get('Driver_Gross', 0)),
        float(row.get('cng', cng or 0)),
        int(row.get('trips_count', 0) or 0),
        float(row.get('cash_adjustment', 0) or 0),
        row.get('payment_status', payment_status),
    ))

    conn.commit()
    conn.close()


# -------------------------------
# BULK SAVE (Optimized)
# -------------------------------
def save_to_db(df, date, cng=None, payment_status="Pending"):
    conn = get_connection()
    cursor = conn.cursor()

    data = [
        (
            row['Driver'],
            row.get('driver_id', None) if hasattr(row, "get") else None,
            row.get('vehicle_id', None) if hasattr(row, "get") else None,
            date,
            float(row['Fare']),
            float(row['Subscription']),
            float(row['Cash_Collected']),
            float(row['Tip']),
            float(row['Net_Payout']),
            float(row['Driver_Gross']),
            float(row['cng']) if 'cng' in row else float(cng or 0),
            int(row['trips_count']) if 'trips_count' in row else 0,
            float(row['cash_adjustment']) if 'cash_adjustment' in row else 0,
            row['payment_status'] if 'payment_status' in row else payment_status,
        )
        for _, row in df.iterrows()
    ]

    cursor.executemany("""
    INSERT INTO payouts 
    (driver, driver_id, vehicle_id, date, fare, subscription, cash, tip, net_payout, driver_gross, cng, trips_count, cash_adjustment, payment_status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    monthly_income_target=None,
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
        target_val = float(monthly_income_target) if monthly_income_target is not None else 30000.0
        cursor.execute(
            """
            INSERT INTO drivers (
                driver_id, first_name, last_name, dl_number, aadhar_number,
                current_address, permanent_address, phone_number,
                emergency_contact, password_hash, date_of_joining, monthly_income_target
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                driver_id, first_name, last_name, dl_number, aadhar_number,
                current_address, permanent_address, phone_number,
                emergency_contact, _hash_password(password), join_date, target_val
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

    masked_aadhar = ("*" * max(0, len(aadhar_number) - 4)) + aadhar_number[-4:]

    # Store target for current month (driver can update later)
    cursor.execute(
        """
        INSERT INTO driver_monthly_targets (driver_id, year, month, target_amount)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (driver_id, year, month)
        DO UPDATE SET target_amount = EXCLUDED.target_amount, updated_at = CURRENT_TIMESTAMP
        """,
        (driver_id, join_date.year, join_date.month, target_val),
    )
    conn.commit()
    conn.close()

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
        SELECT date, leave_taken, reason, month, year,
               COALESCE(leave_status, 'Pending') AS leave_status
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
        INSERT INTO driver_leaves (driver_id, date, leave_taken, reason, month, year, leave_status)
        VALUES (%s, %s, 1, %s, %s, %s, 'Pending')
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


def get_pending_leaves_df(year, month=None):
    conn = get_connection()
    query = """
        SELECT
            l.id,
            l.driver_id,
            (d.first_name || ' ' || d.last_name) AS driver_name,
            d.phone_number,
            l.date,
            l.reason,
            l.month,
            l.year,
            COALESCE(l.leave_status, 'Pending') AS leave_status
        FROM driver_leaves l
        JOIN drivers d ON d.driver_id = l.driver_id
        WHERE l.leave_taken = 1
          AND l.year = %s
          AND (l.leave_status IS NULL OR l.leave_status = 'Pending')
    """
    params = [int(year)]
    if month:
        query += " AND l.month = %s"
        params.append(int(month))
    query += " ORDER BY l.date ASC"

    df = pd.read_sql(query, conn, params=tuple(params))
    conn.close()
    return df


def set_leave_status(leave_id, status):
    status_norm = str(status).strip().capitalize()
    if status_norm not in ["Approved", "Rejected", "Pending"]:
        return False, "Invalid status."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE driver_leaves
        SET leave_status = %s
        WHERE id = %s
        """,
        (status_norm, int(leave_id)),
    )
    conn.commit()
    updated = cursor.rowcount
    conn.close()
    if updated and updated > 0:
        return True, f"Leave marked as {status_norm}."
    return False, "Leave not found or not updated."


# -------------------------------
# Admin fleet / vehicle helpers
# -------------------------------
def _normalize_driver_full_name(name: str) -> str:
    if not name:
        return ""
    # Normalize spaces/case to improve matching against first_name + last_name
    parts = str(name).strip().split()
    return " ".join(parts).upper()


def resolve_driver_id_by_full_name(driver_full_name: str):
    """
    Map Uber CSV driver full name to onboarded driver_id.
    Expected driver_full_name format from processor: "<first name> <surname>".
    """
    normalized = _normalize_driver_full_name(driver_full_name)
    if not normalized:
        return None

    tokens = normalized.split()
    if not tokens:
        return None

    uber_last = tokens[-1]
    uber_first_part = " ".join(tokens[:-1]).strip()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT driver_id, first_name, last_name
        FROM drivers
        """
    )
    candidates = cursor.fetchall()
    conn.close()

    best = None
    best_score = -1
    tie = False

    for driver_id, first_name, last_name in candidates:
        d_first = (first_name or "").strip().upper()
        d_last = (last_name or "").strip().upper()
        d_full = (d_first + " " + d_last).strip()

        score = 0
        if d_full == normalized:
            score = 100
        else:
            if d_last and d_last == uber_last:
                score += 60
            if uber_first_part and d_first:
                if d_first in uber_first_part or uber_first_part in d_first:
                    score += 25
            # token overlap with first+last strings
            if d_first or d_last:
                hay = (d_first + " " + d_last).replace("  ", " ").strip()
                overlap = sum(1 for t in tokens if t in hay)
                score += min(20, overlap * 5)
            # substring hints
            if d_first and d_first in normalized:
                score += 5
            if d_last and d_last in normalized:
                score += 5

        if score > best_score:
            best_score = score
            best = driver_id
            tie = False
        elif score == best_score and score > 0:
            tie = True

    # Avoid incorrect matches when ambiguous
    if tie or best_score < 40:
        return None
    return best


def _generate_vehicle_id(cursor):
    cursor.execute(
        """
        SELECT vehicle_id
        FROM vehicles
        WHERE vehicle_id LIKE 'VEH%'
        ORDER BY vehicle_id DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return "VEH001"
    latest = row[0]
    try:
        num = int(latest.replace("VEH", ""))
    except ValueError:
        num = 0
    return f"VEH{num + 1:03d}"


def onboard_vehicle(
    vehicle_number,
    date_of_purchase,
    permit_expiry=None,
    insurance_expiry=None,
    service_due_date=None,
):
    if not vehicle_number:
        return False, "Vehicle number is required."
    if date_of_purchase is None:
        return False, "Date of purchase is required."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        vehicle_id = _generate_vehicle_id(cursor)
        cursor.execute(
            """
            INSERT INTO vehicles (vehicle_id, vehicle_number, date_of_purchase, permit_expiry, insurance_expiry, service_due_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                vehicle_id,
                str(vehicle_number).strip().upper(),
                date_of_purchase,
                permit_expiry,
                insurance_expiry,
                service_due_date,
            ),
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        # Unique violation / other SQL errors
        msg = str(exc)
        conn.close()
        if "vehicle_number" in msg.lower() or "unique" in msg.lower():
            return False, "Vehicle number already exists."
        return False, "Unable to onboard vehicle. Please try again."
    conn.close()
    return True, {"vehicle_id": vehicle_id}


def get_vehicles_df():
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT vehicle_id, vehicle_number, date_of_purchase, permit_expiry, insurance_expiry, service_due_date
        FROM vehicles
        ORDER BY vehicle_id
        """,
        conn,
    )
    conn.close()
    return df


def assign_driver_to_vehicle(driver_id, vehicle_id, start_date):
    if not driver_id or not vehicle_id or start_date is None:
        return False, "driver_id, vehicle_id, and start_date are required."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Close currently-active assignment for the driver (if any)
        cursor.execute(
            """
            UPDATE driver_vehicle_assignments
            SET end_date = %s
            WHERE driver_id = %s AND end_date IS NULL AND start_date <= %s
            """,
            (start_date, driver_id, start_date),
        )
        cursor.execute(
            """
            INSERT INTO driver_vehicle_assignments (driver_id, vehicle_id, start_date, end_date)
            VALUES (%s, %s, %s, NULL)
            """,
            (driver_id, vehicle_id, start_date),
        )
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        msg = str(exc)
        conn.close()
        if "unique" in msg.lower():
            return False, "Assignment for this start date already exists."
        return False, "Unable to attach driver to vehicle. Please try again."
    conn.close()
    return True, "Driver attached to vehicle successfully."


def get_active_vehicle_for_driver(driver_id, on_date):
    if not driver_id or on_date is None:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vehicle_id
        FROM driver_vehicle_assignments
        WHERE driver_id = %s
          AND start_date <= %s
          AND (end_date IS NULL OR end_date >= %s)
        ORDER BY start_date DESC
        LIMIT 1
        """,
        (driver_id, on_date, on_date),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def upsert_vehicle_cng(vehicle_id, cng_date, cng_amount):
    if not vehicle_id or cng_date is None:
        return False, "vehicle_id and date are required."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO vehicle_daily_cng (vehicle_id, date, cng_amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (vehicle_id, date)
            DO UPDATE SET cng_amount = EXCLUDED.cng_amount
            """,
            (vehicle_id, cng_date, float(cng_amount)),
        )
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        conn.close()
        return False, "Unable to save vehicle CNG."
    conn.close()
    return True, "Vehicle CNG saved."


def get_vehicle_cng_for_date_df(cng_date):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT vehicle_id, cng_amount
        FROM vehicle_daily_cng
        WHERE date = %s
        """,
        conn,
        params=(cng_date,),
    )
    conn.close()
    return df


def set_monthly_target(driver_id, year, month, target_amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO driver_monthly_targets (driver_id, year, month, target_amount)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (driver_id, year, month)
        DO UPDATE SET target_amount = EXCLUDED.target_amount, updated_at = CURRENT_TIMESTAMP
        """,
        (driver_id, int(year), int(month), float(target_amount)),
    )
    conn.commit()
    conn.close()


def get_monthly_target(driver_id, year, month):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT target_amount
        FROM driver_monthly_targets
        WHERE driver_id = %s AND year = %s AND month = %s
        """,
        (driver_id, int(year), int(month)),
    )
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0


def get_drivers_df():
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT driver_id, first_name, last_name, phone_number, date_of_joining
        FROM drivers
        ORDER BY driver_id
        """,
        conn,
    )
    conn.close()
    df["driver_name"] = (df["first_name"].fillna("") + " " + df["last_name"].fillna("")).str.strip()
    return df[["driver_id", "driver_name", "phone_number", "date_of_joining"]]


def get_active_assignments_df(on_date):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT
            a.driver_id,
            d.first_name,
            d.last_name,
            a.vehicle_id,
            v.vehicle_number
        FROM driver_vehicle_assignments a
        JOIN drivers d ON d.driver_id = a.driver_id
        JOIN vehicles v ON v.vehicle_id = a.vehicle_id
        WHERE a.start_date <= %s
          AND (a.end_date IS NULL OR a.end_date >= %s)
        ORDER BY a.driver_id
        """,
        conn,
        params=(on_date, on_date),
    )
    conn.close()
    if not df.empty:
        df["driver_name"] = (df["first_name"].fillna("") + " " + df["last_name"].fillna("")).str.strip()
        df = df.rename(columns={"vehicle_number": "vehicle"})
        df = df[["driver_id", "driver_name", "vehicle_id", "vehicle"]]
    return df


def get_driver_payouts_df(driver_id, start_date=None, end_date=None):
    conn = get_connection()
    query = """
        SELECT
            date,
            fare,
            subscription,
            cash,
            tip,
            net_payout,
            driver_gross,
            cng,
            trips_count,
            COALESCE(payment_status, 'Pending') AS payment_status
        FROM payouts
        WHERE driver_id = %s
    """
    params = [driver_id]
    if start_date is not None:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date is not None:
        query += " AND date <= %s"
        params.append(end_date)
    query += " ORDER BY date ASC"
    df = pd.read_sql(query, conn, params=tuple(params))
    conn.close()
    return df


def get_driver_monthly_leave_count(driver_id, year, month):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM driver_leaves
        WHERE driver_id = %s AND year = %s AND month = %s AND leave_taken = 1
        """,
        (driver_id, int(year), int(month)),
    )
    count = cursor.fetchone()[0] or 0
    conn.close()
    return int(count)


def get_driver_pending_payouts_df(driver_id):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT
            date,
            fare,
            subscription,
            cash,
            tip,
            net_payout,
            driver_gross,
            cng,
            trips_count,
            COALESCE(payment_status, 'Pending') AS payment_status
        FROM payouts
        WHERE driver_id = %s
          AND COALESCE(payment_status, 'Pending') != 'Paid'
        ORDER BY date DESC
        """,
        conn,
        params=(driver_id,),
    )
    conn.close()
    return df


def get_pending_payouts_for_date_df(payout_date):
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT
            p.date,
            p.driver_id,
            COALESCE(d.first_name || ' ' || d.last_name, p.driver) AS driver_name,
            p.vehicle_id,
            p.net_payout,
            COALESCE(p.payment_status, 'Pending') AS payment_status,
            p.trips_count
        FROM payouts p
        LEFT JOIN drivers d ON d.driver_id = p.driver_id
        WHERE p.date = %s
          AND COALESCE(p.payment_status, 'Pending') != 'Paid'
        ORDER BY driver_name
        """,
        conn,
        params=(payout_date,),
    )
    conn.close()
    return df


def mark_payouts_paid_for_date(payout_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE payouts
        SET payment_status = 'Paid'
        WHERE date = %s AND COALESCE(payment_status, 'Pending') != 'Paid'
        """,
        (payout_date,),
    )
    conn.commit()
    conn.close()


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
