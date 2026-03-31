import pandas as pd
import os
import re
from datetime import datetime

from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

from database import init_db

# -------------------------------
# STYLES
# -------------------------------
styles = getSampleStyleSheet()

title_style = ParagraphStyle('title', parent=styles['Normal'], fontSize=16, textColor=colors.white, leading=18)
subtle_style = ParagraphStyle('subtle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#AAAAAA"))
driver_style = ParagraphStyle('driver', parent=styles['Normal'], fontSize=11, textColor=colors.black)
label_style = ParagraphStyle('label', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#777777"))
value_style = ParagraphStyle('value', parent=styles['Normal'], fontSize=11, alignment=2, textColor=colors.white)
bold_value = ParagraphStyle('bold_value', parent=styles['Normal'], fontSize=11, alignment=2, textColor=colors.white)
footer_style = ParagraphStyle('footer', parent=styles['Normal'], fontSize=9, alignment=1, textColor=colors.HexColor("#777777"))

# -------------------------------
# HELPERS
# -------------------------------
def safe(val):
    try:
        return round(float(val), 2)
    except:
        return 0.0

def clean_money(col):
    return (
        col.astype(str)
        .str.replace(',', '')
        .str.replace('₹', '')
        .str.strip()
        .astype(float)
    )

# -------------------------------
# PDF CREATION
# -------------------------------
def create_driver_pdf(row, output_folder):

    name = str(row['Driver']).upper()
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    file_path = os.path.join(output_folder, f"{safe_name}_{timestamp}.pdf")

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    today = datetime.now().strftime("%d %b %Y")

    logo_path = os.path.join(os.getcwd(), "logo.png")
    logo = Image(logo_path, width=40, height=40)

    # HEADER
    header = Table([
        [
            logo,
            Paragraph("<b>VAYO CAB SERVICE</b><br/><font size=9 color='#AAAAAA'>Payout Statement</font>", title_style),
            Paragraph(f"{today}", subtle_style)
        ]
    ], colWidths=[60, 290, 150])

    header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0A0A0A")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))

    elements.append(header)
    elements.append(Spacer(1, 25))

    elements.append(Paragraph(f"<b>Fleet Partner:</b> {name}", driver_style))
    elements.append(Spacer(1, 15))

    # SECTION 1
    data1 = [
        ["Gross Trip Revenue", f"Rs {safe(row.get('Fare'))}"],
        ["Driver Subscription", f"- Rs {safe(row.get('Subscription'))}"],
        ["Net Platform Earnings", f"Rs {safe(row.get('Net_Platform_Earnings'))}"],
        ["Partner Share (30%)", f"Rs {safe(row.get('Driver_Share_30'))}"],
    ]

    table1 = Table(
        [[Paragraph(l, label_style), Paragraph(v, value_style)] for l,v in data1],
        colWidths=[320,180]
    )

    table1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#111111")),
        ('LINEBELOW', (0,0), (-1,-2), 0.2, colors.HexColor("#333333")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))

    elements.append(table1)
    elements.append(Spacer(1, 20))

    # SECTION 2
    cash = safe(row.get('Cash_Collected'))

    data2 = [
        ["Partner Gross Earnings", f"Rs {safe(row.get('Driver_Gross'))}"],
        ["Cash Collected", f"Rs {abs(cash)}"],
        ["Tip", f"Rs {safe(row.get('Tip'))}"],
        ["Net Payout", f"Rs {safe(row.get('Net_Payout'))}"],
    ]

    table2 = Table(
        [[Paragraph(l, label_style),
          Paragraph(v, bold_value if l=="Net Payout" else value_style)]
         for l,v in data2],
        colWidths=[320,180]
    )

    table2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#111111")),
        ('LINEABOVE', (0,-1), (-1,-1), 0.5, colors.HexColor("#555555")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))

    elements.append(table2)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph(
        "System generated statement • Vayo Cab Service",
        footer_style
    ))

    doc.build(elements)

    return file_path

# -------------------------------
# MAIN PROCESS FUNCTION
# -------------------------------
def process_file(input_data, total_cng=0):

    init_db()

    # HANDLE INPUT
    if isinstance(input_data, pd.DataFrame):
        df = input_data.copy()
    else:
        if input_data.name.endswith(".csv"):
            df = pd.read_csv(input_data)
        else:
            df = pd.read_excel(input_data)

    df.columns = df.columns.str.strip()

    # DRIVER NAME
    df['Driver'] = df['Driver first name'] + " " + df['Driver surname']

    # COLUMN MAPPING
    cash_col = 'Paid to you : Trip balance : Payouts : Cash collected'
    subscription_col = 'Paid to you:Trip balance:Expenses:Driver subscription charge'
    tip_col = 'Paid to you:Your earnings:Tip'
    platform_fee_col = 'Paid to you:Your earnings:Other fees:Platform fee'

    fare_columns = [col for col in df.columns if 'Your earnings:Fare' in col]

    # CLEAN DATA
    for col in fare_columns + [cash_col, subscription_col, tip_col, platform_fee_col]:
        if col in df.columns:
            df[col] = clean_money(df[col])
        else:
            df[col] = 0

    # CALCULATIONS
    df['Platform_Fee'] = df[platform_fee_col].abs()
    df['Fare'] = df[fare_columns].sum(axis=1) - df['Platform_Fee']
    df['Cash_Collected'] = df[cash_col]
    df['Subscription'] = df[subscription_col].abs()
    df['Tip'] = df[tip_col]

    # GROUP
    grouped = df.groupby('Driver').agg(
        Fare=('Fare', 'sum'),
        Cash_Collected=('Cash_Collected', 'sum'),
        Subscription=('Subscription', 'sum'),
        Tip=('Tip', 'sum'),
        trips_count=('Fare', 'size')
    ).reset_index()

    # BUSINESS LOGIC
    grouped['Net_Platform_Earnings'] = grouped['Fare'] - grouped['Subscription']
    grouped['Driver_Share_30'] = grouped['Net_Platform_Earnings'] * 0.3
    grouped['Driver_Gross'] = grouped['Driver_Share_30']

    grouped['Net_Payout'] = (
        grouped['Driver_Gross']
        + grouped['Cash_Collected']
        + grouped['Tip']
    )

    grouped = grouped.sort_values(by='Net_Payout', ascending=False)

    # CNG SPLIT
    num_drivers = len(grouped)
    cng_per_driver = total_cng / num_drivers if num_drivers else 0

    # OUTPUT FOLDER
    today_folder = datetime.now().strftime("%Y-%m-%d")
    output_folder = os.path.join("outputs", today_folder)
    os.makedirs(output_folder, exist_ok=True)

    # GENERATE PDFS
    results = {}
    for _, row in grouped.iterrows():
        pdf_path = create_driver_pdf(row, output_folder)
        results[row['Driver']] = pdf_path

    return results, grouped, cng_per_driver


def calculate_driver_payouts(input_data):
    """
    Calculate per-driver payout totals (no PDFs, no DB writes).
    Returns a dataframe compatible with save_to_db().
    """
    # HANDLE INPUT
    if isinstance(input_data, pd.DataFrame):
        df = input_data.copy()
    else:
        if input_data.name.endswith(".csv"):
            df = pd.read_csv(input_data)
        else:
            df = pd.read_excel(input_data)

    df.columns = df.columns.str.strip()

    # DRIVER NAME
    df['Driver'] = df['Driver first name'] + " " + df['Driver surname']

    # COLUMN MAPPING
    cash_col = 'Paid to you : Trip balance : Payouts : Cash collected'
    subscription_col = 'Paid to you:Trip balance:Expenses:Driver subscription charge'
    tip_col = 'Paid to you:Your earnings:Tip'
    platform_fee_col = 'Paid to you:Your earnings:Other fees:Platform fee'

    fare_columns = [col for col in df.columns if 'Your earnings:Fare' in col]

    # CLEAN DATA
    for col in fare_columns + [cash_col, subscription_col, tip_col, platform_fee_col]:
        if col in df.columns:
            df[col] = clean_money(df[col])
        else:
            df[col] = 0

    # CALCULATIONS
    df['Platform_Fee'] = df[platform_fee_col].abs()
    df['Fare'] = df[fare_columns].sum(axis=1) - df['Platform_Fee']
    df['Cash_Collected'] = df[cash_col]
    df['Subscription'] = df[subscription_col].abs()
    df['Tip'] = df[tip_col]

    # GROUP
    grouped = df.groupby('Driver').agg(
        Fare=('Fare', 'sum'),
        Cash_Collected=('Cash_Collected', 'sum'),
        Subscription=('Subscription', 'sum'),
        Tip=('Tip', 'sum'),
        trips_count=('Fare', 'size')
    ).reset_index()

    # BUSINESS LOGIC
    grouped['Net_Platform_Earnings'] = grouped['Fare'] - grouped['Subscription']
    grouped['Driver_Share_30'] = grouped['Net_Platform_Earnings'] * 0.3
    grouped['Driver_Gross'] = grouped['Driver_Share_30']
    grouped['Net_Payout'] = (
        grouped['Driver_Gross']
        + grouped['Cash_Collected']
        + grouped['Tip']
    )

    grouped = grouped.sort_values(by='Net_Payout', ascending=False)
    return grouped


def generate_driver_pdfs(grouped_df, output_folder):
    """
    Generate PDFs for each driver using the adjusted grouped dataframe.
    grouped_df must contain: Driver, Cash_Collected, Net_Payout, Subscription, Fare, etc.
    """
    results = {}
    for _, row in grouped_df.iterrows():
        pdf_path = create_driver_pdf(row, output_folder)
        results[row['Driver']] = pdf_path
    return results
