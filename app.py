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

# --- 2. การเชื่อมต่อ Google Sheets (ระบุชื่อไฟล์และชีทชัดเจน) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1RRXOhnjmnRG_6ynHkrd2iXmQYVTqN96CjmCXnuZNA9w/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # อ่านข้อมูลจาก Sheet1 ของไฟล์ BleedGuard_NCI_Final
    df_history = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl="0")
except Exception as e:
    st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
    df_history = pd.DataFrame()

# --- 3. ฟังก์ชันหาลำดับถัดไป (Auto-increment ID) ---
def get_next_id(df):
    prefix = "Endonci-"
    if df.empty or "Case_ID" not in df.columns:
        return f"{prefix}1"
    # ดึงเฉพาะตัวเลขหลัง Endonci- ออกมาหาค่าสูงสุด
    ids = df["Case_ID"].str.extract(r'Endonci-(\d+)').dropna().astype(int)
    if ids.empty:
        return f"{prefix}1"
    next_num = ids.max().values[0] + 1
    return f"{prefix}{next_num}"

next_case_id = get_next_id(df_history)

# --- 4. ส่วนหัวของแอป ---
st.markdown("<h1 style='text-align: center;'>🛡️ NCI BleedGuard-AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ระบบบันทึกและวิเคราะห์ความเสี่ยงเลือดออกหลังส่องกล้องลำไส้ใหญ่<br>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</p>", unsafe_allow_html=True)
st.divider()

# --- 5. ฟอร์มรับข้อมูล (Input Section) ---
with st.expander(f"➕ บันทึกเคสใหม่ (ลำดับถัดไป: {next_case_id})", expanded=True):
    with st.form("triage_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 ข้อมูลผู้ป่วย**")
            case_id = st.text_input("รหัสเคส (Case ID)", value=next_case_id)
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
        
        submit_button = st.form_submit_button("🚀 บันทึกและประเมินผล AI")

# --- 6. การประมวลผลและแสดงผล ---
if submit_button:
    # ตรวจสอบ ID ซ้ำ
    if not df_history.empty and case_id in df_history["Case_ID"].values:
        st.error(f"❌ รหัส {case_id} มีในระบบแล้ว กรุณาตรวจสอบลำดับอีกครั้ง")
    else:
        # AI Calculation (ใช้สูตรเดิมแต่ตัด BX ออกตามสั่ง)
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
        bx_v = 0 # ตัด Biopsy ออก

        z = intercept + (3.2052 * emr_v) + (1.7408 * size) + (1.0052 * med_v) + \
            (0.6243 * rad_v) + (0.5988 * loc_v) + (0.4511 * cold_v) + \
            (0.3931 * hot_v) + (0.2509 * sur_v) + (0.2030 * che_v) + \
            (0.0051 * age) + (-0.2321 * sex_v) + (-0.4070 * bx_v)
        
        score = 1 / (1 + np.exp(-z))
        
        # กำหนดระดับความเสี่ยง
        if score >= 0.40: risk, advice, color = "RED", "📞 โทรติดตาม 24, 48, 72 ชม. (High Risk)", "#FF4B4B"
        elif score >= 0.11: risk, advice, color = "YELLOW", "📞 โทรติดตาม 24, 48 ชม. (Moderate Risk)", "#FFA500"
        else: risk, advice, color = "GREEN", "✅ ให้คู่มือสังเกตอาการ (Low Risk)", "#28A745"

        # ผลลัพธ์และปุ่ม Add Line (แสดงทุกระดับ)
        st.markdown(f"""
            <div style='background-color:{color}; padding:25px; border-radius:15px; text-align:center; color:white;'>
                <h2 style='margin:0;'>ผลประเมิน: {risk} (Score: {score:.4f})</h2>
                <p style='font-size:18px; margin-top:10px;'>{advice}</p>
            </div>
            <div style='text-align:center; margin-top:15px;'>
                <a href='https://line.me' target='_blank' style='background-color:#06C755; color:white; padding:12px 25px; text-decoration:none; border-radius:8px; font-weight:bold;'>📲 แอดไลน์เพื่อรับคำแนะนำและติดตามอาการ</a>
            </div>
        """, unsafe_allow_html=True)

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
            st.toast(f"✅ บันทึกเคส {case_id} สำเร็จ!")
            st.rerun()
        except:
            st.error("บันทึกไม่สำเร็จ กรุณาเช็กสิทธิ์ Editor ใน Google Sheets")

# --- 7. Dashboard สรุปผล ---
st.divider()
st.header("📊 Dashboard สถิติศูนย์ส่องกล้อง")

if not df_history.empty:
    df_history['Timestamp'] = pd.to_datetime(df_history['Timestamp'])
    df_history['Date'] = df_history['Timestamp'].dt.date
    today = datetime.now(bkk_tz).date()
    
    # --- ส่วนที่ 1: ยอดรวมวันนี้ (Real-time) ---
    st.subheader(f"📅 สรุปยอดวันนี้ ({today.strftime('%d/%m/%Y')})")
    df_today = df_history[df_history['Date'] == today]
    
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("เคสวันนี้ทั้งหมด", len(df_today))
    t2.metric("🔴 เสี่ยงสูง", len(df_today[df_today['Risk_Level'] == 'RED']))
    t3.metric("🟡 เสี่ยงปานกลาง", len(df_today[df_today['Risk_Level'] == 'YELLOW']))
    t4.metric("🟢 เสี่ยงต่ำ", len(df_today[df_today['Risk_Level'] == 'GREEN']))
    
    # --- ส่วนที่ 2: ค้นหาสถิติรายเดือน ---
    st.markdown("---")
    df_history['MonthYear'] = df_history['Timestamp'].dt.strftime('%m/%Y')
    months = sorted(df_history['MonthYear'].unique(), reverse=True)
    
    col_sel, col_space = st.columns([1, 2])
    with col_sel:
        selected_month = st.selectbox("🔍 เลือกเดือนที่ต้องการดูสถิติ", options=months)
    
    df_month = df_history[df_history['MonthYear'] == selected_month]
    
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"**สัดส่วนสีความเสี่ยงเดือน {selected_month}**")
        fig_pie = px.pie(df_month, names='Risk_Level', color='Risk_Level', 
                         color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'},
                         hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with m2:
        st.markdown(f"**จำนวนเคสแยกรายสี (รวม {len(df_month)} เคส)**")
        # กราฟแท่งแสดงตัวเลขชัดๆ
        count_data = df_month['Risk_Level'].value_counts().reindex(['RED', 'YELLOW', 'GREEN'], fill_value=0).reset_index()
        count_data.columns = ['Level', 'Count']
        fig_bar = px.bar(count_data, x='Level', y='Count', color='Level',
                         color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'},
                         text='Count')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 ประวัติการบันทึกล่าสุด")
    st.dataframe(df_history.tail(10)[['Timestamp', 'Case_ID', 'Risk_Level', 'Advice']].sort_values(by='Timestamp', ascending=False), use_container_width=True)
else:
    st.info("ยังไม่มีข้อมูลเพื่อแสดง Dashboard")
