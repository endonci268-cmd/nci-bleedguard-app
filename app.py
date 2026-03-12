import streamlit as st
import numpy as np
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import plotly.express as px

# ---------------------------
# 1 ตั้งค่าหน้าแอป
# ---------------------------

st.set_page_config(
    page_title="NCI BleedGuard Dashboard",
    page_icon="🛡️",
    layout="wide"
)

bkk_tz = pytz.timezone("Asia/Bangkok")

# ---------------------------
# 2 เชื่อม Google Sheet
# ---------------------------

SHEET_URL = "https://docs.google.com/spreadsheets/d/1RRXOhnjmnRG_6ynHkrd2iXmQYVTqN96CjmCXnuZNA9w/edit"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_history = conn.read(
        spreadsheet=SHEET_URL,
        worksheet="Sheet1",
        ttl=0
    )
except Exception as e:
    st.error(f"เชื่อม Google Sheets ไม่ได้: {e}")
    df_history = pd.DataFrame()

# ---------------------------
# 3 สร้าง Case ID อัตโนมัติ
# ---------------------------

def get_next_id(df):

    prefix = "Endonci-"

    if df.empty or "Case_ID" not in df.columns:
        return f"{prefix}1"

    ids = df["Case_ID"].str.extract(r'Endonci-(\d+)').dropna()

    if ids.empty:
        return f"{prefix}1"

    next_num = ids.astype(int).max()[0] + 1

    return f"{prefix}{next_num}"


next_case_id = get_next_id(df_history)

# ---------------------------
# 4 Header
# ---------------------------

st.markdown(
"""
<h2 style='text-align:center'>
🛡️ NCI BleedGuard-AI
</h2>
<p style='text-align:center;color:gray'>
ระบบประเมินความเสี่ยงเลือดออกหลังตัดติ่งเนื้อ
<br>
ศูนย์ส่องกล้องทางเดินอาหาร
</p>
""",
unsafe_allow_html=True
)

st.divider()

# ---------------------------
# 5 Input Form
# ---------------------------

with st.expander(f"➕ บันทึกเคสใหม่ (ลำดับ {next_case_id})", expanded=True):

    with st.form("triage_form", clear_on_submit=True):

        col1, col2, col3 = st.columns(3)

        with col1:

            st.markdown("### 👤 ข้อมูลผู้ป่วย")

            case_id = st.text_input("Case ID", value=next_case_id)

            age = st.number_input("Age", min_value=1, value=40)

            sex = st.selectbox("Sex", ["หญิง", "ชาย"])

            medication = st.selectbox(
                "Anticoagulant",
                ["ไม่ใช่", "ใช่"]
            )

        with col2:

            st.markdown("### 🔬 หัตถการ")

            size = st.number_input("Polyp size (cm)", min_value=0.1)

            location = st.selectbox(
                "Location",
                ["ลำไส้ใหญ่ฝั่งซ้าย", "ลำไส้ใหญ่ฝั่งขวา"]
            )

            procedure = st.selectbox(
                "Procedure",
                [
                    "Biopsy Only",
                    "Cold Snare",
                    "Hot Polypectomy",
                    "EMR"
                ]
            )

            clip = st.selectbox(
                "Clip used",
                ["ไม่ใช่", "ใช่"]
            )

        with col3:

            st.markdown("### 🏥 ประวัติ")

            surgery = st.selectbox(
                "Abdominal surgery",
                ["ไม่ใช่", "ใช่"]
            )

            radiation = st.selectbox(
                "Radiation",
                ["ไม่ใช่", "ใช่"]
            )

            chemo = st.selectbox(
                "Chemotherapy",
                ["ไม่ใช่", "ใช่"]
            )

        submit_button = st.form_submit_button("🚀 ประเมิน AI")

# ---------------------------
# 6 AI MODEL
# ---------------------------

if submit_button:

    if not df_history.empty and case_id in df_history["Case_ID"].values:

        st.error("Case ID ซ้ำ")

    else:

        emr_v = 1 if procedure == "EMR" else 0
        med_v = 1 if medication == "ใช่" else 0
        rad_v = 1 if radiation == "ใช่" else 0
        loc_v = 1 if location == "ลำไส้ใหญ่ฝั่งขวา" else 0
        cold_v = 1 if procedure == "Cold Snare" else 0
        hot_v = 1 if procedure == "Hot Polypectomy" else 0
        sur_v = 1 if surgery == "ใช่" else 0
        che_v = 1 if chemo == "ใช่" else 0
        sex_v = 1 if sex == "ชาย" else 0
        bx_v = 0

        intercept = -3.26419367

        z = (
            intercept
            + (3.2052 * emr_v)
            + (1.7408 * size)
            + (1.0052 * med_v)
            + (0.6243 * rad_v)
            + (0.5988 * loc_v)
            + (0.4511 * cold_v)
            + (0.3931 * hot_v)
            + (0.2509 * sur_v)
            + (0.2030 * che_v)
            + (0.0051 * age)
            + (-0.2321 * sex_v)
            + (-0.4070 * bx_v)
        )

        score = 1 / (1 + np.exp(-z))

        prob = score * 100

        if score >= 0.40:

            risk = "RED"
            color = "#FF4B4B"
            advice = "โทรติดตาม 24 48 72 ชม"

        elif score >= 0.11:

            risk = "YELLOW"
            color = "#FFA500"
            advice = "โทรติดตาม 24 48 ชม"

        else:

            risk = "GREEN"
            color = "#28A745"
            advice = "ให้คู่มือสังเกตอาการ"

        st.markdown(
        f"""
        <div style='background:{color};
        padding:25px;
        border-radius:10px;
        text-align:center;
        color:white'>

        <h2>{risk}</h2>

        <h3>Bleeding risk {prob:.2f}%</h3>

        <p>{advice}</p>

        </div>
        """,
        unsafe_allow_html=True
        )

        new_entry = pd.DataFrame([{

        "Timestamp": datetime.now(bkk_tz).strftime("%Y-%m-%d %H:%M:%S"),
        "Case_ID": case_id,
        "Age": age,
        "Sex": sex,
        "Size": size,
        "loc_right": loc_v,
        "Medication": medication,
        "Surgery": surgery,
        "Radiation": radiation,
        "Chemo": chemo,
        "BX": "N/A",
        "Cold_Poly": cold_v,
        "Hot_Poly": hot_v,
        "EMR": emr_v,
        "Clip": clip,
        "Risk_Level": risk,
        "Actual_Bleeding": "",
        "Advice": advice

        }])

        try:

            df_updated = pd.concat(
                [df_history, new_entry],
                ignore_index=True
            )

            conn.update(
                worksheet="Sheet1",
                data=df_updated
            )

            st.success("บันทึกสำเร็จ")

            st.rerun()

        except:

            st.error("บันทึกไม่สำเร็จ")

# ---------------------------
# 7 Dashboard
# ---------------------------

st.divider()

st.header("📊 Dashboard")

if not df_history.empty:

    df_history["Timestamp"] = pd.to_datetime(
        df_history["Timestamp"]
    )

    today = datetime.now(bkk_tz).date()

    df_today = df_history[
        df_history["Timestamp"].dt.date == today
    ]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("วันนี้", len(df_today))

    c2.metric(
        "RED",
        len(df_today[df_today["Risk_Level"] == "RED"])
    )

    c3.metric(
        "YELLOW",
        len(df_today[df_today["Risk_Level"] == "YELLOW"])
    )

    c4.metric(
        "GREEN",
        len(df_today[df_today["Risk_Level"] == "GREEN"])
    )

    df_history["MonthYear"] = df_history[
        "Timestamp"
    ].dt.strftime("%m/%Y")

    month = st.selectbox(
        "เลือกเดือน",
        sorted(
            df_history["MonthYear"].unique(),
            reverse=True
        )
    )

    df_month = df_history[
        df_history["MonthYear"] == month
    ]

    fig = px.pie(
        df_month,
        names="Risk_Level"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_history
        .sort_values("Timestamp", ascending=False)
        .head(10),
        use_container_width=True
    )

else:

    st.info("ยังไม่มีข้อมูล")
