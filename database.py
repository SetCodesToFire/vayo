import sqlite3
import pandas as pd

DB_NAME = "vayo.db"

# -------------------------------
# INIT DB
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver TEXT,
        date TEXT,
        fare REAL,
        subscription REAL,
        cash REAL,
        tip REAL,
        net_payout REAL,
        driver_gross REAL,
        cng REAL
    )
    """)

    conn.commit()
    conn.close()


# -------------------------------
# INSERT SINGLE ROW
# -------------------------------
def insert_payout(row, date, cng):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO payouts 
    (driver, date, fare, subscription, cash, tip, net_payout, driver_gross, cng)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row['Driver'],
        str(date),
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
# BULK SAVE
# -------------------------------
def save_to_db(df, date, cng):

    for _, row in df.iterrows():
        insert_payout(row, date, cng)


# -------------------------------
# GET DATA
# -------------------------------
def get_dataframe():
    conn = sqlite3.connect(DB_NAME)

    try:
        df = pd.read_sql("SELECT * FROM payouts", conn)
    except:
        df = pd.DataFrame()

    conn.close()
    return df