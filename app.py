import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime
import hashlib

# --- 1. CONFIG & DATABASE SETUP ---
if not os.path.exists('slips'):
    os.makedirs('slips')

# ฟังก์ชันเข้ารหัส Password (เพื่อความปลอดภัยเบื้องต้น)
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def init_db():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    
    # 1. ตาราง User (เพิ่มใหม่)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    
    # 2. ตารางบุคคล (เพิ่ม owner_id เพื่อระบุเจ้าของข้อมูล)
    c.execute('''CREATE TABLE IF NOT EXISTS personnel
                 (id INTEGER PRIMARY KEY, owner_id INTEGER, name TEXT, phone TEXT, address TEXT)''')
                 
    # 3. ตารางธุรกรรม
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, person_id INTEGER, amount REAL, 
                  date TEXT, slip_path TEXT, note TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 2. ฟังก์ชัน PDF ---
def generate_pdf(person_name, trans_data):
    pdf = FPDF()
    pdf.add_page()
    
    # ใช้ฟอนต์ไทย (ถ้ามี)
    if os.path.exists('THSarabunNew.ttf'):
        pdf.add_font('THSarabunNew', '', 'THSarabunNew.ttf', uni=True)
        pdf.set_font("THSarabunNew", size=16)
    else:
        pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Payment Report: {person_name}", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 10, txt="Date", border=1, align='C', fill=True)
    pdf.cell(40, 10, txt="Amount", border=1, align='C', fill=True)
    pdf.cell(110, 10, txt="Note", border=1, align='C', fill=True)
    pdf.ln()
    
    total = 0
    for index, row in trans_data.iterrows():
        pdf.cell(40, 10, txt=str(row['date'].split()[0]), border=1, align='C')
        pdf.cell(40, 10, txt=f"{row['amount']:,.2f}", border=1, align='R')
        note_txt = str(row['note']) if row['note'] else "-"
        pdf.cell(110, 10, txt=note_txt, border=1, align='L')
        pdf.ln()
        total += row['amount']
        
    pdf.ln(5)
    pdf.cell(80, 10, txt="Total", border=1, align='C')
    pdf.cell(110, 10, txt=f"{total:,.2f}", border=1, align='L')
        
    filename = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# --- 3. MAIN APP ---
def main():
    st.title("💰 ระบบจัดการข้อมูลและธุรกรรมออนไลน์")

    # เมนูเลือก: Login หรือ Register
    menu = ["เข้าสู่ระบบ (Login)", "สมัครสมาชิกใหม่ (Register)"]
    choice = st.sidebar.selectbox("เลือกรายการ", menu)

    if choice == "สมัครสมาชิกใหม่ (Register)":
        st.subheader("สร้างบัญชีผู้ใช้ใหม่")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("สมัครสมาชิก"):
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?,?)", 
                          (new_user, make_hashes(new_password)))
                conn.commit()
                st.success("สร้างบัญชีสำเร็จ! กรุณาไปที่เมนู 'เข้าสู่ระบบ'")
            except sqlite3.IntegrityError:
                st.error("ชื่อผู้ใช้นี้มีคนใช้แล้ว")

    elif choice == "เข้าสู่ระบบ (Login)":
        
        # เช็ค Session
        if "user_id" not in st.session_state:
            st.session_state["user_id"] = None
            
        if st.session_state["user_id"] is None:
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type='password')
            if st.sidebar.button("Login"):
                c = conn.cursor()
                # ค้นหา User
                c.execute('SELECT * FROM users WHERE username =?', (username,))
                data = c.fetchall()
                
                if data:
                    # เช็ค Password
                    if check_hashes(password, data[0][2]):
                        st.session_state["user_id"] = data[0][0] # เก็บ ID คนที่ล็อคอิน
                        st.session_state["username"] = username
                        st.rerun()
                    else:
                        st.warning("รหัสผ่านไม่ถูกต้อง")
                else:
                    st.warning("ไม่พบชื่อผู้ใช้นี้")
        
        # --- ส่วนทำงานหลัก (เมื่อ Login ผ่านแล้ว) ---
        else:
            st.sidebar.success(f"ยินดีต้อนรับ: {st.session_state['username']}")
            if st.sidebar.button("Logout"):
                st.session_state["user_id"] = None
                st.rerun()

            # *** ดึงข้อมูลเฉพาะของ User คนนี้เท่านั้น ***
            my_id = st.session_state["user_id"]
            
            task = st.selectbox("เมนูทำงาน", ["จัดการรายชื่อ", "บันทึกธุรกรรม", "ออกรายงาน"])
            
            if task == "จัดการรายชื่อ":
                with st.form("new_person"):
                    name = st.text_input("ชื่อ-สกุล")
                    phone = st.text_input("เบอร์โทร")
                    addr = st.text_area("ที่อยู่")
                    if st.form_submit_button("บันทึก"):
                        c = conn.cursor()
                        # บันทึกโดยผูกกับ owner_id
                        c.execute("INSERT INTO personnel (owner_id, name, phone, address) VALUES (?,?,?,?)", 
                                  (my_id, name, phone, addr))
                        conn.commit()
                        st.success("บันทึกแล้ว")
                        st.rerun()
                
                # แสดงเฉพาะรายชื่อของฉัน
                my_people = pd.read_sql(f"SELECT name, phone, address FROM personnel WHERE owner_id={my_id}", conn)
                st.dataframe(my_people, use_container_width=True)

            elif task == "บันทึกธุรกรรม":
                # ดึงรายชื่อเฉพาะของฉัน
                df_p = pd.read_sql(f"SELECT * FROM personnel WHERE owner_id={my_id}", conn)
                if not df_p.empty:
                    p_name = st.selectbox("เลือกรายชื่อ", df_p['name'])
                    p_id = df_p[df_p['name'] == p_name]['id'].values[0]
                    
                    amt = st.number_input("ยอดเงิน", step=100.0)
                    note = st.text_input("รายละเอียด")
                    if st.button("บันทึก"):
                        c = conn.cursor()
                        c.execute("INSERT INTO transactions (person_id, amount, date, slip_path, note) VALUES (?,?,?,?,?)",
                                  (int(p_id), amt, datetime.now().strftime("%Y-%m-%d %H:%M"), "", note))
                        conn.commit()
                        st.success("บันทึกแล้ว")
                else:
                    st.info("ยังไม่มีรายชื่อ")

            elif task == "ออกรายงาน":
                df_p = pd.read_sql(f"SELECT * FROM personnel WHERE owner_id={my_id}", conn)
                if not df_p.empty:
                    p_name = st.selectbox("เลือกรายชื่อทำรายงาน", df_p['name'])
                    p_id = df_p[df_p['name'] == p_name]['id'].values[0]
                    
                    df_t = pd.read_sql(f"SELECT * FROM transactions WHERE person_id={p_id}", conn)
                    st.dataframe(df_t[['date','amount','note']], use_container_width=True)
                    
                    if st.button("โหลด PDF"):
                        f_name = generate_pdf(p_name, df_t)
                        with open(f_name, "rb") as f:
                            st.download_button("Download", f, file_name=f_name)

if __name__ == '__main__':
    main()