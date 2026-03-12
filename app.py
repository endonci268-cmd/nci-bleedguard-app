import streamlit as st
import numpy as np
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="NCI BleedGuard Dashboard", page_icon="🛡️", layout="wide")
bkk_tz = pytz.timezone('Asia/Bangkok')

# --- 2. การเชื่อมต่อ Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_history = conn.read(worksheet="Sheet1", ttl="0")
except Exception as e:
    st.error("⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้")
    df_history = pd.DataFrame()

# --- 3. ฟังก์ชันหาลำดับถัดไป (Auto-increment ID) ---
def get_next_id(df):
    if df.empty or "Case_ID" not in df.columns:
        return "Endonci-1"
    ids = df["Case_ID"].str.extract(r'Endonci-(\d+)').dropna().astype(int)
    if ids.empty:
        return "Endonci-1"
    next_num = ids.max().values[0] + 1
    return f"Endonci-{next_num}"

next_case_id = get_next_id(df_history)

# --- 4. ส่วนหัวของแอป ---
st.title("🛡️ NCI BleedGuard-AI: Smart Dashboard")
st.write(f"ศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ | ขณะนี้กำลังทำเคสลำดับที่: **{next_case_id}**")

# --- 5. ฟอร์มรับข้อมูล (Input Section) ---
with st.expander("➕ บันทึกเคสใหม่", expanded=True):
    with st.form("triage_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 ข้อมูลผู้ป่วย**")
            case_id = st.text_input("รหัสเคส (Case ID)", value=next_case_id, help="ระบบรันเลขให้อัตโนมัติ")
            age = st.number_input("อายุ (ปี)", min_value=1, value=38)
            sex = st.selectbox("เพศ", ["หญิง", "ชาย"])
            medication = st.selectbox("ยาละลายลิ่มเลือด", ["ไม่ใช่", "ใช่"])
        with col2:
            st.markdown("**🔍 ข้อมูลหัตถการ**")
            size = st.number_input("ขนาดติ่งเนื้อ (cm)", min_value=0.1, step=0.1)
            location = st.selectbox("ตำแหน่ง", ["ลำไส้ใหญ่ฝั่งซ้าย", "ลำไส้ใหญ่ฝั่งขวา"])
            procedure = st.selectbox("วิธีตัดติ่งเนื้อ", ["Biopsy Only", "Cold Snare", "Hot Polypectomy", "EMR"])
            clip = st.selectbox("มีการใช้ Clip?", ["ไม่ใช่", "ใช่"])
        with col3:
            st.markdown("**🏥 ประวัติเพิ่มเติม**")
            surgery = st.selectbox("ประวัติผ่าตัดช่องท้อง", ["ไม่ใช่", "ใช่"])
            radiation = st.selectbox("ประวัติฉายแสง", ["ไม่ใช่", "ใช่"])
            chemo = st.selectbox("ประวัติเคมีบำบัด", ["ไม่ใช่", "ใช่"])
            st.info(f"💡 ลำดับที่ใช้ไปแล้ว: {df_history['Case_ID'].tail(3).tolist() if not df_history.empty else 'ไม่มี'}")
        
        submit_button = st.form_submit_button("🚀 บันทึกและประเมินผล")

# --- 6. การประมวลผล ---
if submit_button:
    # ตรวจสอบ ID ซ้ำ
    if not df_history.empty and case_id in df_history["Case_ID"].values:
        st.error(f"❌ รหัส {case_id} ถูกใช้ไปแล้ว กรุณาใช้รหัสอื่น")
    else:
        # AI Calculation
        intercept = -3.26419367
        emr_v = 1 if procedure == "EMR" else 0
        med_v = 1 if medication == "ใช่" else 0
        rad_v = 1 if radiation == "ใช่" else 0
        loc_v = 1 if location == "ลำไส้ใหญ่ฝั่งขวา" else 0
        cold_v = 1 if procedure == "Cold Snare" else 0
        hot_v = 1 if procedure == "Hot Polypectomy" else 0
        sur_v = 1 if surgery == "ใช่" else 0
        che_v = 1 if chemo == "ใช่" else 0
        sex_v = 1 if sex == "ชาย" else 0
        bx_v = 0 # กำหนดเป็น 0 เนื่องจากตัด BX ออก

        z = intercept + (3.2052 * emr_v) + (1.7408 * size) + (1.0052 * med_v) + \
            (0.6243 * rad_v) + (0.5988 * loc_v) + (0.4511 * cold_v) + \
            (0.3931 * hot_v) + (0.2509 * sur_v) + (0.2030 * che_v) + \
            (0.0051 * age) + (-0.2321 * sex_v) + (-0.4070 * bx_v)
        
        score = 1 / (1 + np.exp(-z))
        
        if score >= 0.40: risk, advice, color = "RED", "📞 โทรติดตาม 24, 48, 72 ชม.", "#FF4B4B"
        elif score >= 0.11: risk, advice, color = "YELLOW", "📞 โทรติดตาม 24, 48 ชม.", "#FFA500"
        else: risk, advice, color = "GREEN", "✅ ให้คู่มือสังเกตอาการ", "#28A745"

        # แสดงผลและปุ่ม Add Line
        st.markdown(f"<div style='background-color:{color}; padding:20px; border-radius:10px; text-align:center;'> <h2 style='color:white;'>ผลประเมิน: {risk}</h2> <p style='color:white; font-size:20px;'>{advice}</p> </div>", unsafe_allow_html=True)
        st.markdown("""<div style='text-align:center; margin-top:20px;'><a href='https://line.me' target='_blank' style='background-color:#06C755; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;'>📲 คลิกเพื่อ Add Line ศูนย์ส่องกล้อง</a></div>""", unsafe_allow_html=True)

        # บันทึกข้อมูล
        new_entry = pd.DataFrame([{
            "Timestamp": datetime.now(bkk_tz).strftime("%Y-%m-%d %H:%M:%S"),
            "Case_ID": case_id, "Age": age, "Sex": sex, "Size": size,
            "loc_right": loc_v, "Medication": medication, "Surgery": surgery,
            "Radiation": radiation, "Chemo": chemo, "BX": "N/A",
            "Cold_Poly": cold_v, "Hot_Poly": hot_v, "EMR": emr_v,
            "Clip": clip, "Risk_Level": risk, "Advice": advice
        }])
        
        try:
            df_updated = pd.concat([df_history, new_entry], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_updated)
            st.toast("✅ บันทึกข้อมูลเรียบร้อย")
            st.rerun()
        except:
            st.error("บันทึกไม่สำเร็จ")

# --- 7. Dashboard ---
st.divider()
st.header("📊 Dashboard วิเคราะห์ข้อมูล")

if not df_history.empty:
    df_history['Timestamp'] = pd.to_datetime(df_history['Timestamp'])
    today = datetime.now(bkk_tz).date()
    
    # --- ส่วนที่ 1: สถิติของวันนี้ ---
    st.subheader(f"📅 ยอดผู้ป่วยวันนี้ ({today.strftime('%d/%m/%Y')})")
    df_today = df_history[df_history['Timestamp'].dt.date == today]
    
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("วันนี้ทั้งหมด", len(df_today))
    t2.metric("🔴 แดง", len(df_today[df_today['Risk_Level'] == 'RED']))
    t3.metric("🟡 เหลือง", len(df_today[df_today['Risk_Level'] == 'YELLOW']))
    t4.metric("🟢 เขียว", len(df_today[df_today['Risk_Level'] == 'GREEN']))
    
    # --- ส่วนที่ 2: ตัวกรองรายเดือน ---
    st.markdown("---")
    df_history['MonthYear'] = df_history['Timestamp'].dt.strftime('%m/%Y')
    selected_month = st.selectbox("🔍 เลือกเดือนที่ต้องการดูสถิติ", options=sorted(df_history['MonthYear'].unique(), reverse=True))
    
    df_month = df_history[df_history['MonthYear'] == selected_month]
    
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"**สัดส่วนความเสี่ยงเดือน {selected_month}**")
        fig_pie = px.pie(df_month, names='Risk_Level', color='Risk_Level', 
                         color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with m2:
        st.markdown(f"**จำนวนเคสแยกรายสี (รวม {len(df_month)} เคส)**")
        fig_bar = px.bar(df_month['Risk_Level'].value_counts().reset_index(), x='index', y='Risk_Level',
                         color='index', color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'})
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 ประวัติ 10 รายล่าสุด")
    st.dataframe(df_history.tail(10), use_container_width=True)
