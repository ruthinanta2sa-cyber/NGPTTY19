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

# สร้างไฟล์ signature.png จำลองไว้เพื่อไม่ให้ error (ในการใช้งานจริง คุณควรเอาไฟล์รูปของคุณมาวางทับ)
if not os.path.exists('signature.png'):
    # (ส่วนนี้แค่สร้างไฟล์เปล่าๆ หรือคุณจะลบออกแล้วหาไฟล์รูปมาใส่เองก็ได้)
    pass 

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def init_db():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    
    # 1. ตาราง User (เพิ่ม column role)
    # role: 'admin' (Chairman), 'user' (General)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
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
    
    # Font Setup (ต้องมีไฟล์ font หรือใช้ Arial)
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
        # แปลงวันที่ให้สวยงาม
        date_show = str(row['date'].split()[0])
        pdf.cell(40, 10, txt=date_show, border=1, align='C')
        pdf.cell(40, 10, txt=f"{row['amount']:,.2f}", border=1, align='R')
        
        # จัดการ Note
        note_txt = str(row['note']) if row['note'] else "-"
        # (กรณีภาษาไทยใน FPDF อาจต้องตัดคำระวังตกขอบ แต่ในตัวอย่างนี้แสดงแบบง่าย)
        pdf.cell(110, 10, txt=note_txt, border=1, align='L')
        pdf.ln()
        total += row['amount']
        
    pdf.ln(5)
    pdf.cell(80, 10, txt="Grand Total", border=1, align='C')
    pdf.cell(110, 10, txt=f"{total:,.2f}", border=1, align='L')
    
    # --- ส่วนลายเซ็น (Chairman Signature) ---
    # 1. เว้นระยะห่างจากตารางลงมา
    pdf.ln(25) 

    # เก็บตำแหน่ง Y เริ่มต้นของบรรทัดเส้นปะ
    line_y_position = pdf.get_y()

    # 2. วาดเส้นปะ (ใช้ cell ความสูง 8 เพื่อความกระชับ)
    pdf.cell(100, 8, txt="", ln=0) # ดันไปทางขวา
    pdf.cell(90, 8, txt="......................................................", ln=1, align='C')

    # 3. วางรูปลายเซ็น (ถ้ามีไฟล์)
    if os.path.exists('signature.png'):
        # คำนวณตำแหน่ง Y ของรูปภาพ
        # line_y_position คือระดับเดียวกับเส้นปะ
        # ลบค่าออก (-) เพื่อขยับรูปขึ้นไปด้านบน
        # **ลองปรับค่า -15 นี้ดูครับ** ถ้าอยากให้สูงขึ้นให้ลบเยอะขึ้น (เช่น -20) ถ้าต่ำลงให้ลบน้อยลง (เช่น -10)
        image_y = line_y_position - 15 
        
        # x=138 คือตำแหน่งแนวนอน (กึ่งกลางเส้นปะ), w=32 คือความกว้างรูป
        pdf.image('signature.png', x=138, y=image_y, w=32)

    # 4. เขียนข้อความบรรทัดถัดไป (Cursor จะอยู่ใต้เส้นปะโดยอัตโนมัติจากขั้นตอนที่ 2)
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
        # เมนูสำหรับคนล็อกอินแล้ว
        menu_list = ["หน้าหลัก", "จัดการรายชื่อ", "บันทึกธุรกรรม", "ออกรายงาน"]
        
        # **เพิ่มเมนูเฉพาะ Admin**
        if st.session_state["role"] == 'admin':
            menu_list.append("Admin Panel (จัดการสิทธิ์)")
            
        menu_list.append("ออกจากระบบ (Logout)")
        choice = st.sidebar.selectbox(f"เมนู (User: {st.session_state['username']})", menu_list)

    # --- REGISTER ---
    if choice == "สมัครสมาชิกใหม่ (Register)":
        st.subheader("สร้างบัญชีผู้ใช้ใหม่")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("สมัครสมาชิก"):
            c = conn.cursor()
            # **Logic กำหนด Role:** ถ้าชื่อ 'admin' ให้เป็น admin ทันที (เพื่อ setup ครั้งแรก) นอกนั้นเป็น user
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
                    st.session_state["role"] = data[0][3] # เก็บ Role เข้า Session
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

        # 3. ออกรายงาน (แก้ไขใหม่: เลือกรายการได้)
        elif choice == "ออกรายงาน":
            st.header("📄 ออกรายงานสรุปยอด (PDF)")
            df_p = pd.read_sql(f"SELECT * FROM personnel WHERE owner_id={my_id}", conn)
            
            if not df_p.empty:
                col1, col2 = st.columns(2)
                with col1:
                    p_name = st.selectbox("เลือกบุคคลที่ต้องการออกรายงาน", df_p['name'])
                    # ยังคงให้เลือกช่วงวันที่เพื่อกรองข้อมูลเบื้องต้นก่อน
                    start_d = st.date_input("ตั้งแต่วันที่")
                    end_d = st.date_input("ถึงวันที่")
                
                p_id = df_p[df_p['name'] == p_name]['id'].values[0]
                
                # Query ข้อมูล
                query = f"SELECT * FROM transactions WHERE person_id={p_id}"
                df_t = pd.read_sql(query, conn)
                
                if not df_t.empty:
                    # แปลงวันที่เพื่อใช้กรอง
                    df_t['date_obj'] = pd.to_datetime(df_t['date'])
                    
                    # 1. กรองตามวันที่ก่อน (Filter Date)
                    mask = (df_t['date_obj'].dt.date >= start_d) & (df_t['date_obj'].dt.date <= end_d)
                    df_filtered = df_t.loc[mask].copy() 
                    
                    if not df_filtered.empty:
                        st.divider()
                        st.subheader("✅ เลือกรายการที่ต้องการพิมพ์")
                        
                        # 2. เพิ่มคอลัมน์ 'เลือก' เข้าไปในตาราง (ค่าเริ่มต้น True = เลือกทั้งหมด)
                        df_filtered.insert(0, "เลือก", True)

                        # 3. แสดงตารางแบบแก้ไขได้ (Data Editor)
                        # เราจะซ่อนคอลัมน์ที่ไม่จำเป็น (เช่น id, slip_path) และโชว์แค่ที่ต้องใช้
                        edited_df = st.data_editor(
                            df_filtered,
                            column_config={
                                "เลือก": st.column_config.CheckboxColumn(
                                    "พิมพ์?",
                                    help="ติ๊กถูกเพื่อนำรายการนี้ไปออกรายงาน PDF",
                                    default=True,
                                ),
                                "date": st.column_config.TextColumn("วันที่"),
                                "amount": st.column_config.NumberColumn("ยอดเงิน", format="%.2f บาท"),
                                "note": st.column_config.TextColumn("รายการ/หมายเหตุ"),
                                # ซ่อนคอลัมน์ระบบที่ไม่ต้องการแสดง
                                "id": None,
                                "person_id": None,
                                "slip_path": None,
                                "date_obj": None,
                            },
                            disabled=["date", "amount", "note"], # ห้ามแก้เนื้อหา แก้ได้แค่ Checkbox
                            hide_index=True,
                            use_container_width=True
                        )

                        # 4. กรองเอาเฉพาะแถวที่ผู้ใช้ติ๊กถูก (Check = True)
                        selected_items = edited_df[edited_df["เลือก"] == True]

                        # แสดงสรุปยอดที่จะพิมพ์
                        total_print = selected_items['amount'].sum()
                        st.info(f"รายการที่เลือก: {len(selected_items)} รายการ | รวมยอดเงิน: {total_print:,.2f} บาท")
                        
                        if st.button("ดาวน์โหลด PDF (ตามรายการที่เลือก)"):
                            if len(selected_items) > 0:
                                # ส่งเฉพาะ selected_items ไปสร้าง PDF
                                # ฟังก์ชัน generate_pdf จะคำนวณยอดรวมใหม่จากรายการที่ส่งไปให้อัตโนมัติ
                                f_name = generate_pdf(p_name, selected_items, str(start_d), str(end_d))
                                with open(f_name, "rb") as f:
                                    st.download_button("Download PDF", f, file_name=f_name)
                            else:
                                st.warning("กรุณาเลือกรายการอย่างน้อย 1 รายการ")
                    else:
                        st.warning("ไม่พบข้อมูลในช่วงวันที่ที่เลือก")
                else:
                    st.warning("ไม่พบประวัติธุรกรรมของบุคคลนี้")

        # 4. Admin Panel (เฉพาะ Admin เท่านั้น)
        elif choice == "Admin Panel (จัดการสิทธิ์)":
            if st.session_state["role"] == 'admin':
                st.header("🔑 ส่วนจัดการของผู้ดูแลระบบ (Chairman)")
                st.write("จัดการสิทธิ์ผู้ใช้งานทั้งหมด")
                
                # โชว์รายชื่อ User ทั้งหมด
                users_df = pd.read_sql("SELECT id, username, role FROM users", conn)
                st.dataframe(users_df, use_container_width=True)
                
                st.divider()
                st.subheader("แก้ไขสิทธิ์ผู้ใช้งาน")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    user_to_edit = st.selectbox("เลือก User", users_df['username'])
                with col_b:
                    new_role = st.selectbox("เลือกสิทธิ์ใหม่", ["user", "admin"])
                with col_c:
                    st.write("") # จัดระยะ
                    st.write("")
                    if st.button("อัปเดตสิทธิ์"):
                        if user_to_edit == st.session_state['username']:
                            st.warning("ไม่สามารถเปลี่ยนสิทธิ์ตัวเองได้ในหน้านี้")
                        else:
                            c = conn.cursor()
                            c.execute("UPDATE users SET role=? WHERE username=?", (new_role, user_to_edit))
                            conn.commit()
                            st.success(f"เปลี่ยนสิทธิ์ {user_to_edit} เป็น {new_role} เรียบร้อย")
                            st.rerun()
            else:
                st.error("คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        
        elif choice == "หน้าหลัก":
            st.info("ยินดีต้อนรับสู่ระบบ เลือกเมนูทางด้านซ้ายเพื่อเริ่มทำงาน")

if __name__ == '__main__':
    main()


