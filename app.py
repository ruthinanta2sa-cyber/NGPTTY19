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

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def init_db():
    # เชื่อมต่อฐานข้อมูล
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    
    # 1. ตาราง User
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # --- Auto Fix: ตรวจสอบและเพิ่ม column 'role' หากไม่มี ---
    try:
        c.execute("SELECT role FROM users LIMIT 1")
    except sqlite3.OperationalError:
        # ถ้า Error แสดงว่าไม่มี column role ให้เพิ่มเข้าไป
        try:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # กันเหนียว กรณีมีการเข้าถึงพร้อมกัน
    # ----------------------------------------------------

    # 2. ตารางบุคคล
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
def generate_pdf(person_name, trans_data, start_date, end_date):
    pdf = FPDF()
    pdf.add_page()
    
    # Font Setup
    if os.path.exists('THSarabunNew.ttf'):
        pdf.add_font('THSarabunNew', '', 'THSarabunNew.ttf', uni=True)
        pdf.set_font("THSarabunNew", size=16)
    else:
        pdf.set_font("Arial", size=12)
    
    # Header
    pdf.cell(200, 10, txt=f"Payment Report", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Name: {person_name}", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Period: {start_date} to {end_date}", ln=1, align='C')
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(40, 10, txt="Date", border=1, align='C', fill=True)
    pdf.cell(40, 10, txt="Amount", border=1, align='C', fill=True)
    pdf.cell(110, 10, txt="Note", border=1, align='C', fill=True)
    pdf.ln()
    
    total = 0
    for index, row in trans_data.iterrows():
        date_show = str(row['date'].split()[0])
        pdf.cell(40, 10, txt=date_show, border=1, align='C')
        pdf.cell(40, 10, txt=f"{row['amount']:,.2f}", border=1, align='R')
        note_txt = str(row['note']) if row['note'] else "-"
        pdf.cell(110, 10, txt=note_txt, border=1, align='L')
        pdf.ln()
        total += row['amount']
        
    pdf.ln(5)
    pdf.cell(80, 10, txt="Grand Total", border=1, align='C')
    pdf.cell(110, 10, txt=f"{total:,.2f}", border=1, align='L')
    
    # --- ส่วนลายเซ็น ---
    pdf.ln(25) 
    line_y_position = pdf.get_y()

    # วาดเส้นปะ
    pdf.cell(100, 8, txt="", ln=0)
    pdf.cell(90, 8, txt="......................................................", ln=1, align='C')

    # วางรูปลายเซ็น (ถ้ามี)
    if os.path.exists('signature.png'):
        image_y = line_y_position - 15 
        pdf.image('signature.png', x=138, y=image_y, w=32)

    # ข้อความใต้ลายเซ็น
    pdf.cell(100, 8, txt="", ln=0)
    pdf.cell(90, 8, txt="( Authorized Signature )", ln=1, align='C')
    pdf.cell(100, 8, txt="", ln=0)
    pdf.cell(90, 8, txt="Chairman / Admin", ln=1, align='C')

    filename = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# --- 3. MAIN APP ---
def main():
    st.set_page_config(page_title="ระบบการเงิน", layout="wide")
    st.title("💰 ระบบจัดการข้อมูลและธุรกรรมออนไลน์")

    # Session State Init
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
        st.session_state["role"] = None
        st.session_state["username"] = None

    # Sidebar Menu
    if st.session_state["user_id"] is None:
        menu = ["เข้าสู่ระบบ (Login)", "สมัครสมาชิกใหม่ (Register)"]
        choice = st.sidebar.selectbox("เลือกรายการ", menu)
    else:
        menu_list = ["หน้าหลัก", "จัดการรายชื่อ", "บันทึกธุรกรรม", "ออกรายงาน"]
        if st.session_state["role"] == 'admin':
            menu_list.append("Admin Panel")
        menu_list.append("ออกจากระบบ (Logout)")
        choice = st.sidebar.selectbox(f"เมนู ({st.session_state['username']})", menu_list)

    # --- REGISTER ---
    if choice == "สมัครสมาชิกใหม่ (Register)":
        st.subheader("สร้างบัญชีผู้ใช้ใหม่")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("สมัครสมาชิก"):
            c = conn.cursor()
            role = 'admin' if new_user.lower() == 'admin' else 'user'
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", 
                          (new_user, make_hashes(new_password), role))
                conn.commit()
                st.success(f"สร้างบัญชีสำเร็จ! สถานะของคุณคือ: {role}")
                st.info("ไปที่เมนู 'เข้าสู่ระบบ' ได้เลย")
            except sqlite3.IntegrityError:
                st.error("ชื่อผู้ใช้นี้มีคนใช้แล้ว")

    # --- LOGIN ---
    elif choice == "เข้าสู่ระบบ (Login)":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type='password')
        if st.sidebar.button("Login"):
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username =?', (username,))
            data = c.fetchall()
            
            if data:
                if check_hashes(password, data[0][2]):
                    st.session_state["user_id"] = data[0][0]
                    st.session_state["username"] = data[0][1]
                    try:
                        st.session_state["role"] = data[0][3]
                    except IndexError:
                        st.session_state["role"] = "user"
                    st.rerun()
                else:
                    st.warning("รหัสผ่านไม่ถูกต้อง")
            else:
                st.warning("ไม่พบชื่อผู้ใช้นี้")

    # --- LOGOUT ---
    elif choice == "ออกจากระบบ (Logout)":
        st.session_state["user_id"] = None
        st.session_state["role"] = None
        st.session_state["username"] = None
        st.rerun()

    # --- SYSTEM FUNCTIONS (Logged In) ---
    elif st.session_state["user_id"] is not None:
        my_id = st.session_state["user_id"]
        
        # 1. จัดการรายชื่อ
        if choice == "จัดการรายชื่อ":
            st.header("📇 จัดการรายชื่อลูกค้า/ลูกหนี้")
            col1, col2 = st.columns([1, 2])
            with col1:
                with st.form("new_person"):
                    name = st.text_input("ชื่อ-สกุล")
                    phone = st.text_input("เบอร์โทร")
                    addr = st.text_area("ที่อยู่")
                    if st.form_submit_button("เพิ่มรายชื่อ"):
                        c = conn.cursor()
                        c.execute("INSERT INTO personnel (owner_id, name, phone, address) VALUES (?,?,?,?)", 
                                  (my_id, name, phone, addr))
                        conn.commit()
                        st.success("บันทึกแล้ว")
                        st.rerun()
            with col2:
                my_people = pd.read_sql(f"SELECT name, phone, address FROM personnel WHERE owner_id={my_id}", conn)
                st.dataframe(my_people, use_container_width=True)

        # 2. บันทึกธุรกรรม
        elif choice == "บันทึกธุรกรรม":
            st.header("💸 บันทึกการจ่ายเงิน")
            df_p = pd.read_sql(f"SELECT * FROM personnel WHERE owner_id={my_id}", conn)
            if not df_p.empty:
                col1, col2 = st.columns(2)
                with col1:
                    p_name = st.selectbox("เลือกรายชื่อ", df_p['name'])
                    p_id = df_p[df_p['name'] == p_name]['id'].values[0]
                    amt = st.number_input("ยอดเงิน (บาท)", step=100.0)
                    note = st.text_input("รายละเอียด/หมายเหตุ")
                    if st.button("ยืนยันการบันทึก"):
                        c = conn.cursor()
                        c.execute("INSERT INTO transactions (person_id, amount, date, slip_path, note) VALUES (?,?,?,?,?)",
                                  (int(p_id), amt, datetime.now().strftime("%Y-%m-%d %H:%M"), "", note))
                        conn.commit()
                        st.success("บันทึกข้อมูลเรียบร้อย!")
            else:
                st.info("กรุณาเพิ่มรายชื่อในเมนู 'จัดการรายชื่อ' ก่อน")

        # 3. ออกรายงาน (เลือกรายการได้)
        elif choice == "ออกรายงาน":
            st.header("📄 ออกรายงานสรุปยอด (PDF)")
            df_p = pd.read_sql(f"SELECT * FROM personnel WHERE owner_id={my_id}", conn)
            
            if not df_p.empty:
                col1, col2 = st.columns(2)
                with col1:
                    p_name = st.selectbox("เลือกบุคคล", df_p['name'])
                    start_d = st.date_input("ตั้งแต่วันที่")
                    end_d = st.date_input("ถึงวันที่")
                
                p_id = df_p[df_p['name'] == p_name]['id'].values[0]
                query = f"SELECT * FROM transactions WHERE person_id={p_id}"
                df_t = pd.read_sql(query, conn)
                
                if not df_t.empty:
                    df_t['date_obj'] = pd.to_datetime(df_t['date'])
                    mask = (df_t['date_obj'].dt.date >= start_d) & (df_t['date_obj'].dt.date <= end_d)
                    df_filtered = df_t.loc[mask].copy() 
                    
                    if not df_filtered.empty:
                        st.divider()
                        st.subheader("✅ เลือกรายการที่จะพิมพ์")
                        df_filtered.insert(0, "เลือก", True) 

                        # ตรงนี้ที่เคยมีปัญหา Syntax Error ผมจัดรูปแบบใหม่ให้แล้วครับ
                        edited_df = st.data_editor(
                            df_filtered,
                            column_config={
                                "เลือก": st.column_config.CheckboxColumn("พิมพ์?", default=True),
                                "date": st.column_config.TextColumn("วันที่"),
                                "amount": st.column_config.NumberColumn("ยอดเงิน", format="%.2f"),
                                "note": st.column_config.TextColumn("หมายเหตุ"),
                                "id": None, "person_id": None, "slip_path": None, "date_obj": None
                            },
                            disabled=["date", "amount", "note"],
                            hide_index=True,
                            use_container_width=True
                        )

                        selected_items = edited_df[edited_df["เลือก"] == True]
                        total_print = selected_items['amount'].sum()
                        st.info(f"รายการที่เลือก: {len(selected_items)} | รวมยอดเงิน: {total_print:,.2f} บาท")
                        
                        if st.button("ดาวน์โหลด PDF"):
                            if len(selected_items) > 0:
                                f_name = generate_pdf(p_name, selected_items, str(start_d), str(end_d))
                                with open(f_name, "rb") as f:
                                    st.download_button("Download PDF", f, file_name=f_name)
                            else:
                                st.warning("กรุณาเลือกอย่างน้อย 1 รายการ")
                    else:
                        st.warning("ไม่พบข้อมูลในช่วงวันที่นี้")
                else:
                    st.warning("ไม่พบประวัติธุรกรรม")

        # 4. Admin Panel
        elif choice == "Admin Panel":
            if st.session_state["role"] == 'admin':
