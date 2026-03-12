import streamlit as st
import numpy as np
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="NCI BleedGuard Dashboard", page_icon="🛡️", layout="wide")

# --- 2. การเชื่อมต่อ Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้ กรุณาเช็ก Secrets ใน Streamlit Cloud")

# --- 3. ส่วนหัวของแอป ---
st.title("🛡️ NCI BleedGuard-AI: Smart Dashboard")
st.write("ระบบบันทึกและวิเคราะห์ความเสี่ยงเลือดออก ศูนย์ส่องกล้อง สถาบันมะเร็งแห่งชาติ")

# --- 4. ฟอร์มรับข้อมูล (Input Section) ---
with st.expander("➕ เพิ่มข้อมูลผู้ป่วยรายใหม่ ( HN / ประเมินความเสี่ยง )", expanded=True):
    with st.form("triage_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**👤 ข้อมูลผู้ป่วย**")
            case_id = st.text_input("HN (Case ID)")
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
            bx = st.selectbox("ทำ Biopsy ร่วมด้วย?", ["ไม่ใช่", "ใช่"])
        
        submit_button = st.form_submit_button("🚀 บันทึกและประเมินผล")

# --- 5. การประมวลผลโมเดล ---
if submit_button:
    # ค่า Intercept และ Coefficients จากผลวิเคราะห์ Logistic Regression
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
    bx_v = 1 if bx == "ใช่" else 0

    # คำนวณค่า z ตามสมการ Logistic Regression
    z = intercept + (3.2052 * emr_v) + (1.7408 * size) + (1.0052 * med_v) + \
        (0.6243 * rad_v) + (0.5988 * loc_v) + (0.4511 * cold_v) + \
        (0.3931 * hot_v) + (0.2509 * sur_v) + (0.2030 * che_v) + \
        (0.0051 * age) + (-0.2321 * sex_v) + (-0.4070 * bx_v)
    
    score = 1 / (1 + np.exp(-z))
    
    # กำหนดระดับความเสี่ยง (Triage)
    if score >= 0.40:
        risk, advice = "RED", "📞 โทรติดตาม 24, 48, 72 ชม. และเน้นย้ำสัญญาณเลือดออก"
    elif score >= 0.11:
        risk, advice = "YELLOW", "📞 โทรติดตาม 24, 48 ชม."
    else:
        risk, advice = "GREEN", "✅ ให้คู่มือสังเกตอาการ / Add LINE ศูนย์ส่องกล้อง"

    # แสดงผลลัพธ์บนหน้าจอ
    st.subheader(f"ผลประเมิน HN: {case_id}")
    if risk == "RED": 
        st.error(f"ระดับความเสี่ยง: {risk} (Score: {score:.4f})")
    elif risk == "YELLOW": 
        st.warning(f"ระดับความเสี่ยง: {risk} (Score: {score:.4f})")
    else: 
        st.success(f"ระดับความเสี่ยง: {risk} (Score: {score:.4f})")
    st.info(f"📋 คำแนะนำพยาบาล: {advice}")

    # บันทึกข้อมูลลง Google Sheets (Timezone กรุงเทพ)
    bkk_tz = pytz.timezone('Asia/Bangkok')
    new_entry = pd.DataFrame([{
        "Timestamp": datetime.now(bkk_tz).strftime("%Y-%m-%d %H:%M:%S"),
        "Case_ID": case_id, "Age": age, "Sex": sex, "Size": size,
        "loc_right": loc_v, "Medication": medication, "Surgery": surgery,
        "Radiation": radiation, "Chemo": chemo, "BX": bx,
        "Cold_Poly": cold_v, "Hot_Poly": hot_v, "EMR": emr_v,
        "Clip": clip, "Risk_Level": risk, "Advice": advice
    }])
    
    try:
        # อ่านข้อมูลเดิมและเขียนทับพร้อมข้อมูลใหม่
        df_existing = conn.read(worksheet="Sheet1")
        df_updated = pd.concat([df_existing, new_entry], ignore_index=True)
        conn.update(worksheet="Sheet1", data=df_updated)
        st.toast("✅ บันทึกข้อมูลลงฐานข้อมูลเรียบร้อยแล้ว")
    except Exception as e:
        st.error(f"⚠️ บันทึกข้อมูลไม่สำเร็จ: {e}")

# --- 6. ส่วน Dashboard (Data Visualization) ---
st.divider()
st.header("📊 สรุปสถิติความเสี่ยงรวม")

try:
    # ดึงข้อมูลมาสร้างกราฟ
    df_history = conn.read(worksheet="Sheet1")
    if not df_history.empty:
        # แสดงตัวเลขสรุป (Metrics)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เคสทั้งหมด", len(df_history))
        m2.metric("เสี่ยงสูง (RED)", len(df_history[df_history['Risk_Level'] == 'RED']))
        m3.metric("ปานกลาง (YELLOW)", len(df_history[df_history['Risk_Level'] == 'YELLOW']))
        m4.metric("ต่ำ (GREEN)", len(df_history[df_history['Risk_Level'] == 'GREEN']))

        # แสดงกราฟสัดส่วน
        g1, g2 = st.columns(2)
        with g1:
            fig1 = px.pie(df_history, names='Risk_Level', title="สัดส่วนความเสี่ยงผู้ป่วยภาพรวม",
                          color='Risk_Level', color_discrete_map={'RED':'#FF4B4B', 'YELLOW':'#FFA500', 'GREEN':'#28A745'})
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = px.histogram(df_history, x='Risk_Level', color='Sex', barmode='group', title="ความเสี่ยงแยกตามเพศ")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 รายการข้อมูล 10 รายล่าสุด")
        st.dataframe(df_history.tail(10), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ เพื่อใช้สร้าง Dashboard")
except:
    st.write("ระบบกำลังเตรียมข้อมูลสำหรับ Dashboard...")
