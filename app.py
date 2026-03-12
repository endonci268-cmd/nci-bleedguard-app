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
# ระบุ URL ที่คุณพยาบาลส่งมาให้โดยตรงในโค้ดเพื่อความแม่นยำ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1RRXOhnjmnRG_6ynHkrd2iXmQYVTqN96CjmCXnuZNA9w/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # ดึงข้อมูลล่าสุด (ttl=0 เพื่อให้เลข Case ID อัปเดตทันที)
    df_history = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl="0")
except Exception as e:
    st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
    df_history = pd.DataFrame()

# --- 3. ระบบ Auto-increment Case ID (Endonci-X) ---
def get_next_id(df):
    prefix = "Endonci-"
    if df.empty or "Case_ID" not in df.columns:
        return f"{prefix}1"
    # ค้นหาตัวเลขลำดับสูงสุดในระบบ
    ids = df["Case_ID"].str.extract(r'Endonci-(\d+)').dropna().astype(int)
    if ids.empty:
        return f"{prefix}1"
    next_num = ids.max().values[0] + 1
    return f"{prefix}{next_num}"

next_case_id = get_next_id(df_history)

# --- 4. ส่วนหัวของแอป ---
st.markdown("<h2 style='text-align: center;'>🛡️ NCI BleedGuard-AI: Smart Dashboard</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>ระบบบันทึกและวิเคราะห์ความเสี่ยงเลือดออกหลังส่องกล้องลำไส้ใหญ่<br>ศูนย์ส่องกล้องทางเดินอาหาร สถาบันมะเร็งแห่งชาติ</p>", unsafe_allow_html=True)
st.divider()

# --- 5. ฟอร์มรับข้อมูล (Input Section) ---
with st.expander(f"➕ บันทึกเคสใหม่ (กำลังทำลำดับที่: {next_case_id})", expanded=True):
    with st.form("triage_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 ข้อมูลผู้ป่วย**")
            # ล็อครหัส Endonci- ให้พยาบาลรู้ลำดับปัจจุบัน
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
            st.info(f"💡 ลำดับล่าสุดในระบบ: {df_history['Case_ID'].iloc[-1] if not df_history.empty else 'ยังไม่มีข้อมูล'}")
        
        submit_button = st.form_submit_button("🚀 บันทึกและประเมินผล AI")

# --- 6. การประมวลผลโมเดล AI ---
if submit_button:
    # ตรวจสอบเพื่อไม่ให้บันทึก ID ซ้ำ
    if not df_history.empty and case_id in df_history["Case_ID"].values:
        st.error(f"❌ รหัส {case_id} ถูกบันทึกไปแล้ว! ระบบกำลังอัปเดตลำดับถัดไปให้ใหม่ครับ")
        st.rerun()
    else:
        # AI Calculation Logic
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
        bx_v = 0 # ตัด Biopsy ออกตามสั่ง

        z = intercept + (3.2052 * emr_v) + (1.7408 * size) + (1.0052 * med_v) + \
            (0.6243 * rad_v) + (0.5988 * loc_v) + (0.4511 * cold_v) + \
            (0.3931 * hot_v) + (0.2509 * sur_v) + (0.2030 * che_v) + \
            (0.0051 * age) + (-0.2321 * sex_v) + (-0.4070 * bx_v)
        
        score = 1 / (1 + np.exp(-z))
        
        # กำหนดระดับความเสี่ยง
        if score >= 0.40:
            risk, advice, color = "RED", "📞 โทรติดตาม 24, 48, 72 ชม. และเน้นย้ำสัญญาณเลือดออก", "#FF4B4B"
        elif score >= 0.11:
            risk, advice, color = "YELLOW", "📞 โทรติดตาม 24, 48 ชม.", "#FFA500"
        else:
            risk, advice, color = "GREEN", "✅ ให้คู่มือสังเกตอาการ / แนะนำการปฏิบัติตัว", "#28A745"

        # แสดงผลลัพธ์พร้อมปุ่ม Add Line (ทุกระดับ)
        st.markdown(f"""
            <div style='background-color:{color}; padding:25px; border-radius:15px; text-align:center; color:white;'>
                <h2 style='margin:0;'>ผลประเมิน: {risk} (Score: {score:.4f})</h2>
                <p style='font-size:18px; margin-top:10px;'>{advice}</p>
            </div>
            <div style='text-align:center; margin-top:15px;'>
                <p><b>📲 กรุณาแจ้งให้ผู้ป่วย Add Line ศูนย์ส่องกล้อง</b></p>
                <a href='https://line.me' target='_blank' style='background-color:#06C755; color:white; padding:12px 25px; text-decoration:none; border-radius:8px; font-weight:bold;'>➕ เพิ่มเพื่อนทาง LINE</a>
            </div>
        """, unsafe_allow_html=True)

        # เตรียมข้อมูลบันทึก
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
            st.toast(f"✅ บันทึกเคส {case_id} เรียบร้อยแล้ว!")
            st.rerun()
        except:
            st.error("บันทึกข้อมูลไม่สำเร็จ กรุณาตรวจสอบสิทธิ์การแชร์ Google Sheets (ต้องเป็น Editor)")

# --- 7. Dashboard สรุปผล ---
st.divider()
st.header("📊 Dashboard วิเคราะห์ข้อมูล")

if not df_history.empty:
    df_history['Timestamp'] = pd.to_datetime(df_history['Timestamp'])
    today = datetime.now(bkk_tz).date()
    
    # --- ส่วนที่ 1: สถิติของวันนี้ (Daily Breakdown) ---
    st.subheader(f"📅 ยอดผู้ป่วยวันนี้ ({today.strftime('%d/%m/%Y')})")
    df_today = df_history[df_history['Timestamp'].dt.date == today]
    
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("วันนี้ทั้งหมด", f"{len(df_today)} เคส")
    t2.metric("🔴 เสี่ยงสูง", len(df_today[df_today['Risk_Level'] == 'RED']))
    t3.metric("🟡 ปานกลาง", len(df_today[df_today['Risk_Level'] == 'YELLOW']))
    t4.metric("🟢 เสี่ยงต่ำ", len(df_today[df_today['Risk_Level'] == 'GREEN']))
    
    # --- ส่วนที่ 2: ค้นหาสถิติรายเดือน (Monthly Stats) ---
    st.markdown("---")
    df_history['MonthYear'] = df_history['Timestamp'].dt.strftime('%m/%Y')
    selected_month = st.selectbox("🔍 เลือกเดือนเพื่อดูสถิติย้อนหลัง", options=sorted(df_history['MonthYear'].unique(), reverse=True))
    
    df_month = df_history[df_history['MonthYear'] == selected_month]
    
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.markdown(f"**สัดส่วนความเสี่ยงเดือน {selected_month}**")
        fig_pie = px.pie(df_month, names='Risk_Level', color='Risk_Level', 
                         color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'},
                         hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    with m_col2:
        st.markdown(f"**จำนวนเคสแยกตามระดับ (รวม {len(df_month)} เคส)**")
        # กราฟแท่งแสดงตัวเลขชัดเจน
        fig_bar = px.bar(df_month['Risk_Level'].value_counts().reset_index(), x='index', y='Risk_Level',
                         color='index', color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'},
                         text_auto=True, labels={'index': 'ระดับความเสี่ยง', 'Risk_Level': 'จำนวนเคส'})
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 ประวัติการบันทึก 10 รายล่าสุด")
    st.dataframe(df_history.tail(10).sort_values(by='Timestamp', ascending=False), use_container_width=True)
else:
    st.info("ยังไม่มีข้อมูลเพื่อแสดง Dashboard")
