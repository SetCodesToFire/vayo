import psycopg2
import pandas as pd

# -------------------------------
# DB CONFIG (Replace with Supabase credentials)
# -------------------------------
DB_CONFIG = {
    "host": "db.lypebrexlzjzyetkkkfp.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "Vayocab123@",
    "port": "5432"
}


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
