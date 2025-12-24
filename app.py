import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime, time
import hashlib
# *** ต้องติดตั้งก่อน: pip install bahttext ***
from bahttext import bahttext

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
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    
    # 1. Users
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, 
                  sec_question TEXT, sec_answer TEXT)''')
    # Auto Fix for old DB
    try: c.execute("SELECT sec_question FROM users LIMIT 1")
    except: 
        c.execute("ALTER TABLE users ADD COLUMN sec_question TEXT")
        c.execute("ALTER TABLE users ADD COLUMN sec_answer TEXT")
    try: c.execute("SELECT role FROM users LIMIT 1")
    except: c.execute("ALTER TABLE users ADD COLUMN role TEXT")


    # 2. Personnel
    c.execute('''CREATE TABLE IF NOT EXISTS personnel
                 (id INTEGER PRIMARY KEY, owner_id INTEGER, name TEXT, phone TEXT, address TEXT)''')
                  
    # 3. Transactions
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, person_id INTEGER, amount REAL, 
                  date TEXT, slip_path TEXT, note TEXT, category TEXT, download_count INTEGER DEFAULT 0)''')
    # Auto Fix for old DB
    try: c.execute("SELECT category FROM transactions LIMIT 1")
    except: c.execute("ALTER TABLE transactions ADD COLUMN category TEXT")
    try: c.execute("SELECT download_count FROM transactions LIMIT 1")
    except: c.execute("ALTER TABLE transactions ADD COLUMN download_count INTEGER DEFAULT 0")

    conn.commit()
    return conn

conn = init_db()

# --- 2. ฟังก์ชัน PDF (ฉบับแก้ไขตามบรีฟล่าสุด) ---
def generate_receipt_pdf(trans_id, person_name, date_str, amount, category, note, is_original=True):
    pdf = FPDF()
    pdf.add_page()
    
    # Font Setup
    if os.path.exists('THSarabunNew.ttf'):
        pdf.add_font('THSarabunNew', '', 'THSarabunNew.ttf', uni=True)
        pdf.add_font('THSarabunNew', 'B', 'THSarabunNew Bold.ttf', uni=True)
        font_normal = 'THSarabunNew'
    else:
        font_normal = 'Arial'
        
    # --- HEADER ---
    pdf.set_font(font_normal, 'B', 20)
    pdf.cell(0, 10, txt="ใบเสร็จรับเงิน / RECEIPT", ln=1, align='C')
    
    # --- WATERMARK ---
    pdf.set_font(font_normal, 'B', 14)
    status_text = "ต้นฉบับ / ORIGINAL" if is_original else "สำเนา / COPY"
    pdf.set_xy(150, 10)
    pdf.set_text_color(255, 0, 0) if not is_original else pdf.set_text_color(0, 100, 0)
    pdf.cell(50, 10, txt=f"[{status_text}]", border=1, align='C')
    pdf.set_text_color(0, 0, 0) # Reset color

    pdf.ln(20)
    
    # --- INFO BLOCK (แก้ไขแสดงวันที่/เวลาตามจริง) ---
    pdf.set_font(font_normal, '', 14)
    # ใช้ส่วนวันที่มาทำเลขที่ใบเสร็จ
    rec_date_obj = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
    receipt_no = f"RCP-{rec_date_obj.strftime('%Y%m')}-{trans_id:04d}"
    
    pdf.cell(130, 8, txt=f"ได้รับเงินจาก: {person_name}", ln=0)
    pdf.cell(60, 8, txt=f"เลขที่: {receipt_no}", ln=1, align='R')
    
    # แสดงวันเวลาที่ผู้ใช้กรอกมาจริงๆ (date_str เต็มๆ)
    pdf.cell(130, 8, txt=f"วันที่ชำระ (Date/Time): {date_str}", ln=0)
    pdf.cell(60, 8, txt=f"สถานะ: ชำระเงินเรียบร้อย", ln=1, align='R')
    pdf.ln(10)
    
    # --- TABLE (แก้ไขการจัดวางและขนาดคอลัมน์) ---
    # กำหนดความกว้างคอลัมน์ใหม่ให้พอดี: No(15) + Desc(115) + Amount(50) = 180
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_normal, 'B', 14)
    pdf.cell(15, 10, txt="#", border=1, align='C', fill=True)
    pdf.cell(115, 10, txt="รายการ (Description)", border=1, align='C', fill=True)
    pdf.cell(50, 10, txt="จำนวนเงิน (Amount)", border=1, align='C', fill=True) # จัดกลางให้ตรงหัวข้อ
    pdf.ln()
    
    pdf.set_font(font_normal, '', 14)
    # Row 1 Data
    pdf.cell(15, 10, txt="1", border=1, align='C')
    pdf.cell(115, 10, txt=f"{category} - {note}", border=1, align='L')
    pdf.cell(50, 10, txt=f"{amount:,.2f}", border=1, align='R') # ตัวเลขชิดขวา
    pdf.ln()
    
    # Grand Total Row
    pdf.set_font(font_normal, 'B', 14)
    pdf.cell(130, 10, txt="รวมทั้งสิ้น (Grand Total)", border=1, align='R') # 15+115 = 130
    pdf.cell(50, 10, txt=f"{amount:,.2f}", border=1, align='R', fill=True)
    pdf.ln()

    # --- THAI BAHT TEXT ROW (เพิ่มใหม่) ---
    thai_text = bahttext(amount) # แปลงตัวเลขเป็นตัวอักษรไทย
    pdf.set_font(font_normal, '', 14)
    # ใช้ cell กว้างเต็ม 180 เพื่อแสดงตัวอักษร
    pdf.cell(180, 10, txt=f"( ตัวอักษร: {thai_text} )", border='T', align='C', fill=True)
    
    # --- SIGNATURE SECTION (แก้ไขตำแหน่งและการซ้อนทับ) ---
    pdf.ln(25) # เว้นระยะห่าง

    # 1. วาดเส้นปะก่อน เพื่อหาตำแหน่ง Y อ้างอิง
    pdf.cell(120, 8, txt="", ln=0) # ดันไปขวา
    line_start_y = pdf.get_y() # เก็บตำแหน่ง Y ของบรรทัดนี้
    pdf.cell(70, 8, txt="......................................................", ln=1, align='C')

    # 2. วางรูปภาพโดยอิงจากตำแหน่งเส้นปะ (ดึงขึ้นไปด้านบนเล็กน้อย)
    if os.path.exists('signature.png'):
        # ใช้ line_start_y แล้วลบออก (เช่น -12) เพื่อให้รูปอยู่เหนือ/ทับเส้นปะ
        pdf.image('signature.png', x=135, y=line_start_y - 12, w=40)
        
    # 3. ใส่ข้อความใต้เส้นปะ (แก้ไขคำตามที่ขอ)
    pdf.cell(120, 8, txt="", ln=0)
    pdf.cell(70, 8, txt="( ผู้มีอำนาจลงนาม )", ln=1, align='C') # แก้ไขคำตรงนี้
    pdf.cell(120, 8, txt="", ln=0)
    pdf.cell(70, 8, txt="นิติบุคคลอาคารชุด/หมู่บ้าน", ln=1, align='C')

    filename = f"receipt_{receipt_no}.pdf"
    pdf.output(filename)
    return filename

# --- 3. MAIN APP ---
def main():
    st.set_page_config(page_title="Smart Juristic Pro", layout="wide", page_icon="🏢")

    # Init Session
    if "user_id" not in st.session_state:
        st.session_state.update({"user_id": None, "role": None, "username": None})
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = 0
    if "reset_username" not in st.session_state:
        st.session_state.reset_username = ""

    # --- LOGIN / REGISTER TABS ---
    if st.session_state["user_id"] is None:
        st.title("🏢 ระบบจัดการหมู่บ้าน/คอนโดมิเนียม")
        tab1, tab2, tab3 = st.tabs(["🔐 เข้าสู่ระบบ", "📝 สมัครสมาชิก", "❓ ลืมรหัสผ่าน"])

        with tab1: # LOGIN
            with st.container(border=True):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.button("เข้าสู่ระบบ", type="primary", use_container_width=True):
                    c = conn.cursor()
                    c.execute('SELECT * FROM users WHERE username=?', (u,))
                    d = c.fetchone()
                    if d and check_hashes(p, d[2]):
                        st.session_state.update({"user_id": d[0], "username": d[1], "role": d[3] if len(d)>3 else 'user'})
                        st.rerun()
                    else: st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        with tab2: # REGISTER
            st.info("สมัครสมาชิกใหม่ กรุณาตั้งคำถามกันลืมเพื่อใช้กู้คืนรหัสผ่าน")
            with st.form("reg"):
                new_u = st.text_input("ตั้งชื่อผู้ใช้ (Username)")
                new_p = st.text_input("ตั้งรหัสผ่าน (Password)", type="password")
                st.divider()
                st.write("**ตั้งค่าความปลอดภัย (ใช้เมื่อลืมรหัสผ่าน)**")
                q_list = ["สัตว์เลี้ยงตัวแรกชื่ออะไร?", "โรงเรียนประถมชื่ออะไร?", "จังหวัดที่คุณเกิด?", "ชื่อเล่นคุณแม่?"]
                sec_q = st.selectbox("เลือกคำถาม", q_list)
                sec_a = st.text_input("คำตอบ (จำให้แม่น!)", type="password")
                if st.form_submit_button("ยืนยันการสมัคร"):
                    if new_u and new_p and sec_a:
                        role = 'admin' if new_u.lower() == 'admin' else 'user'
                        try:
                            c = conn.cursor()
                            c.execute("INSERT INTO users (username, password, role, sec_question, sec_answer) VALUES (?,?,?,?,?)", 
                                      (new_u, make_hashes(new_p), role, sec_q, make_hashes(sec_a)))
                            conn.commit()
                            st.success(f"สมัครสำเร็จ! กรุณาเข้าสู่ระบบ")
                        except: st.error("ชื่อผู้ใช้นี้ถูกใช้ไปแล้ว")
                    else: st.error("กรุณากรอกข้อมูลให้ครบทุกช่อง")

        with tab3: # FORGOT PASSWORD
            st.warning("ระบบกู้คืนรหัสผ่านด้วยตนเอง")
            if st.session_state.reset_step == 0:
                with st.form("reset_0"):
                    f_user = st.text_input("ระบุ Username ของท่าน")
                    if st.form_submit_button("ตรวจสอบ"):
                        c = conn.cursor()
                        c.execute("SELECT sec_question, sec_answer FROM users WHERE username=?", (f_user,))
                        user_data = c.fetchone()
                        if user_data:
                            st.session_state.reset_username = f_user
                            st.session_state.reset_q = user_data[0]
                            st.session_state.reset_real_a = user_data[1]
                            st.session_state.reset_step = 1
                            st.rerun()
                        else: st.error("ไม่พบชื่อผู้ใช้นี้")
            elif st.session_state.reset_step == 1:
                st.info(f"ผู้ใช้: **{st.session_state.reset_username}**")
                with st.form("reset_1"):
                    st.write(f"คำถามความปลอดภัย: **{st.session_state.reset_q}**")
                    ans_input = st.text_input("กรุณาระบุคำตอบ", type="password")
                    if st.form_submit_button("ยืนยันคำตอบ"):
                        if check_hashes(ans_input, st.session_state.reset_real_a):
                            st.success("ถูกต้อง! กรุณาตั้งรหัสผ่านใหม่")
                            st.session_state.reset_step = 2
                            st.rerun()
                        else: st.error("คำตอบไม่ถูกต้อง")
                    if st.form_submit_button("ยกเลิก"):
                        st.session_state.reset_step = 0
                        st.rerun()
            elif st.session_state.reset_step == 2:
                with st.form("reset_2"):
                    new_pass_1 = st.text_input("รหัสผ่านใหม่", type="password")
                    new_pass_2 = st.text_input("ยืนยันรหัสผ่านใหม่", type="password")
                    if st.form_submit_button("เปลี่ยนรหัสผ่าน"):
                        if new_pass_1 == new_pass_2 and new_pass_1 != "":
                            c = conn.cursor()
                            c.execute("UPDATE users SET password=? WHERE username=?", 
                                      (make_hashes(new_pass_1), st.session_state.reset_username))
                            conn.commit()
                            st.success("เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบใหม่")
                            st.session_state.reset_step = 0
                            st.session_state.reset_username = ""
                        else: st.error("รหัสผ่านไม่ตรงกัน หรือ เป็นค่าว่าง")

    # --- LOGGED IN ZONES ---
    else:
        # Sidebar
        role_txt = "👑 Admin" if st.session_state["role"] == 'admin' else "👤 ลูกบ้าน"
        st.sidebar.success(f"{st.session_state['username']} ({role_txt})")
        menu_list = ["หน้าหลัก", "ข้อมูลส่วนตัว", "ชำระเงิน/แจ้งโอน", "ประวัติ/ดาวน์โหลดใบเสร็จ"]
        if st.session_state["role"] == 'admin':
            st.sidebar.divider()
            menu_list.extend(["Admin: แดชบอร์ด", "Admin: ข้อมูลลูกบ้าน", "Admin: จัดการสิทธิ์"])
        st.sidebar.divider()
        if st.sidebar.button("ออกจากระบบ", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        choice = st.sidebar.radio("เลือกเมนู", menu_list)
        my_id = st.session_state["user_id"]

        if choice == "หน้าหลัก":
            st.title("🏡 หน้าหลัก")
            st.info(f"ยินดีต้อนรับคุณ **{st.session_state['username']}** สู่ระบบจัดการหมู่บ้าน")

        elif choice == "ข้อมูลส่วนตัว":
            st.header("📇 ข้อมูลส่วนตัว (Profile)")
            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            with st.form("profile"):
                n = st.text_input("ชื่อ-สกุล (เจ้าของ)", value=prof[2] if prof else "")
                ph = st.text_input("เบอร์โทร", value=prof[3] if prof else "")
                ad = st.text_area("ที่อยู่ / เลขห้อง", value=prof[4] if prof else "")
                if st.form_submit_button("บันทึกข้อมูล"):
                    if prof: c.execute("UPDATE personnel SET name=?, phone=?, address=? WHERE owner_id=?", (n,ph,ad,my_id))
                    else: c.execute("INSERT INTO personnel (owner_id,name,phone,address) VALUES (?,?,?,?)", (my_id,n,ph,ad))
                    conn.commit()
                    st.toast("บันทึกเรียบร้อย", icon="✅")
                    st.rerun()

        # --- แก้ไขส่วนชำระเงิน ให้เลือกวัน/เวลาได้เอง ---
        elif choice == "ชำระเงิน/แจ้งโอน":
            st.header("💸 แจ้งชำระเงิน")
            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            if prof:
                st.info(f"ทำรายการในนาม: {prof[2]}")
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        main_cat = st.selectbox("เลือกประเภทรายการ", 
                                              ["ค่าส่วนกลาง (Common Fee)", "ค่าน้ำประปา", "ค่าบัตรจอดรถ/คีย์การ์ด", "ค่าปรับ", "อื่นๆ (ระบุเอง)"])
                        final_note, final_cat = "", main_cat
                        if main_cat == "ค่าส่วนกลาง (Common Fee)":
                            m = st.selectbox("เดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
                            y = st.selectbox("ปี (พ.ศ.)", [str(x) for x in range(2567, 2575)])
                            final_note = f"ค่าส่วนกลาง เดือน {m} {y}"
                        elif main_cat == "อื่นๆ (ระบุเอง)":
                            custom_input = st.text_input("ระบุรายละเอียด")
                            if custom_input: final_note, final_cat = custom_input, "ค่าใช้จ่ายอื่นๆ"
                            else: final_note = "ไม่ระบุรายละเอียด"
                        else:
                            note_add = st.text_input("รายละเอียดเพิ่มเติม")
                            final_note = f"{main_cat} {note_add}"
                        
                        st.divider()
                        st.write("**ระบุวันที่และเวลาที่โอนจริง (ตามสลิป)**")
                        # --- เพิ่ม Date/Time Picker ---
                        col_d, col_t = st.columns(2)
                        with col_d:
                            pay_date = st.date_input("วันที่โอน", datetime.now())
                        with col_t:
                            # ใช้ time(hour, minute) เพื่อกำหนดเวลาเริ่มต้น หรือใช้ datetime.now().time()
                            pay_time = st.time_input("เวลาที่โอน", datetime.now().time())
                        
                        # รวมวันที่และเวลาเป็น string สำหรับเก็บใน DB
                        pay_datetime_str = f"{pay_date.strftime('%Y-%m-%d')} {pay_time.strftime('%H:%M')}"
                        # -----------------------------

                    with col2:
                        amount = st.number_input("ยอดเงิน (บาท)", min_value=0.0, step=100.0)
                        st.write("📷 **หลักฐานการโอน (Mandatory)**")
                        if amount > 0:
                            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=PROMPTPAY_ID_HERE:{amount}", caption="สแกนจ่าย")
                        file = st.file_uploader("อัปโหลดสลิป", type=['jpg','png','jpeg'])

                    if st.button("ยืนยันแจ้งโอน", type="primary", use_container_width=True):
                        if amount > 0 and file:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            fpath = f"slips/{ts}_{file.name}"
                            with open(fpath, "wb") as f: f.write(file.getbuffer())
                            
                            # บันทึกโดยใช้ pay_datetime_str ที่ผู้ใช้เลือก
                            c.execute("INSERT INTO transactions (person_id,amount,date,slip_path,note,category) VALUES (?,?,?,?,?,?)",
                                      (prof[0], amount, pay_datetime_str, fpath, final_note, final_cat))
                            conn.commit()
                            st.balloons()
                            st.success("บันทึกสำเร็จ!")
                        else: st.error("ข้อมูลไม่ครบ")
            else: st.warning("กรุณากรอกข้อมูลส่วนตัวก่อน")

        # --- แก้ไขส่วนดาวน์โหลดใบเสร็จ (เปลี่ยนปุ่มโหลด) ---
        elif choice == "ประวัติ/ดาวน์โหลดใบเสร็จ":
            st.header("📜 ประวัติและใบเสร็จ")
            # Callback function สำหรับอัปเดตยอดโหลด
            def update_dl_count(tid):
                conn_cb = sqlite3.connect('data.db', check_same_thread=False)
                c_cb = conn_cb.cursor()
                c_cb.execute("UPDATE transactions SET download_count = download_count + 1 WHERE id=?", (tid,))
                conn_cb.commit()
                conn_cb.close()

            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            if prof:
                c.execute(f"SELECT * FROM transactions WHERE person_id={prof[0]} ORDER BY date DESC")
                rows = c.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=['id', 'pid', 'amount', 'date', 'path', 'note', 'cat', 'dl_count'])
                    st.dataframe(df[['date', 'cat', 'note', 'amount']], use_container_width=True)
                    st.divider()
                    st.subheader("📥 ดาวน์โหลด (รายรายการ)")
                    for row in rows:
                        tid, _, amt, dt, path, note, cat, dl_count = row
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.write(f"**{dt}** | {cat}")
                                st.caption(note)
                            with c2:
                                st.write(f"**{amt:,.2f} บาท**")
                                st.caption(f"{'✨ ต้นฉบับ' if dl_count==0 else f'⚠️ สำเนา (โหลด {dl_count} ครั้ง)'}")
                            with c3:
                                # สร้าง PDF เตรียมไว้เลย
                                is_orig = True if dl_count == 0 else False
                                pdf_filename = generate_receipt_pdf(tid, prof[2], dt, amt, cat, note, is_orig)
                                with open(pdf_filename, "rb") as f:
                                    pdf_bytes = f.read()
                                # ใช้ download_button โดยตรง พร้อม callback
                                st.download_button(
                                    label="📄 ดาวน์โหลดใบเสร็จ",
                                    data=pdf_bytes,
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    key=f"dl_btn_{tid}",
                                    on_click=update_dl_count,
                                    args=(tid,)
                                )
                else: st.info("ไม่พบประวัติ")
            else: st.warning("กรุณากรอกข้อมูลส่วนตัวก่อน")

        # --- ADMIN ZONES ---
        elif "Admin" in choice and st.session_state["role"] == 'admin':
            if "แดชบอร์ด" in choice:
                st.header("📊 Admin Dashboard")
                df = pd.read_sql("SELECT * FROM transactions", conn)
                if not df.empty:
                    st.metric("Total Income", f"{df['amount'].sum():,.2f}")
                    st.dataframe(df)
            elif "ข้อมูลลูกบ้าน" in choice:
                st.header("👥 User Data")
                st.dataframe(pd.read_sql("SELECT * FROM personnel", conn))
            elif "จัดการสิทธิ์" in choice:
                st.header("🔑 Manage Roles")
                users = pd.read_sql("SELECT username, role FROM users", conn)
                target = st.selectbox("เลือก User", users['username'])
                new_r = st.radio("สถานะ", ["user", "admin"])
                if st.button("บันทึก"):
                    conn.execute("UPDATE users SET role=? WHERE username=?", (new_r, target))
                    conn.commit()
                    st.success("Saved!")

if __name__ == '__main__':
    main()
