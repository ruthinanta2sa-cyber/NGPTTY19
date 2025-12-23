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
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    
    # 1. Users
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    try: c.execute("SELECT role FROM users LIMIT 1")
    except: c.execute("ALTER TABLE users ADD COLUMN role TEXT")

    # 2. Personnel
    c.execute('''CREATE TABLE IF NOT EXISTS personnel
                 (id INTEGER PRIMARY KEY, owner_id INTEGER, name TEXT, phone TEXT, address TEXT)''')
                  
    # 3. Transactions (เพิ่ม column download_count)
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY, person_id INTEGER, amount REAL, 
                  date TEXT, slip_path TEXT, note TEXT, category TEXT, download_count INTEGER DEFAULT 0)''')
    
    # Auto Fix: เพิ่ม column ใหม่ๆ
    try: c.execute("SELECT category FROM transactions LIMIT 1")
    except: c.execute("ALTER TABLE transactions ADD COLUMN category TEXT")
    
    try: c.execute("SELECT download_count FROM transactions LIMIT 1")
    except: 
        c.execute("ALTER TABLE transactions ADD COLUMN download_count INTEGER DEFAULT 0")
        conn.commit()

    conn.commit()
    return conn

conn = init_db()

# --- 2. ฟังก์ชัน PDF (ฉบับเทพ: รองรับ ต้นฉบับ/สำเนา) ---
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
        
    # --- LOGO & HEADER ---
    pdf.set_font(font_normal, 'B', 20)
    pdf.cell(0, 10, txt="ใบเสร็จรับเงิน / RECEIPT", ln=1, align='C')
    
    # --- WATERMARK (ต้นฉบับ / สำเนา) ---
    pdf.set_font(font_normal, 'B', 14)
    # มุมขวาบน
    status_text = "ต้นฉบับ / ORIGINAL" if is_original else "สำเนา / COPY"
    pdf.set_xy(150, 10)
    pdf.set_text_color(255, 0, 0) if not is_original else pdf.set_text_color(0, 100, 0) # สีแดงถ้าสำเนา, เขียวถ้าต้นฉบับ
    pdf.cell(50, 10, txt=f"[{status_text}]", border=1, align='C')
    pdf.set_text_color(0, 0, 0) # Reset สีดำ

    pdf.ln(20)
    
    # --- INFO BLOCK ---
    pdf.set_font(font_normal, '', 14)
    # Generate Receipt No (RCP-YYYYMM-ID)
    rec_date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
    receipt_no = f"RCP-{rec_date.strftime('%Y%m')}-{trans_id:04d}"
    
    pdf.cell(130, 8, txt=f"ได้รับเงินจาก: {person_name}", ln=0)
    pdf.cell(60, 8, txt=f"เลขที่: {receipt_no}", ln=1, align='R')
    
    pdf.cell(130, 8, txt=f"วันที่ชำระ: {date_str}", ln=0)
    pdf.cell(60, 8, txt=f"สถานะ: ชำระเงินเรียบร้อย", ln=1, align='R')
    pdf.ln(10)
    
    # --- TABLE ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_normal, 'B', 14)
    pdf.cell(10, 10, txt="#", border=1, align='C', fill=True)
    pdf.cell(130, 10, txt="รายการ (Description)", border=1, align='C', fill=True)
    pdf.cell(50, 10, txt="จำนวนเงิน (Amount)", border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font(font_normal, '', 14)
    # Row 1
    pdf.cell(10, 10, txt="1", border=1, align='C')
    pdf.cell(130, 10, txt=f"{category} - {note}", border=1, align='L')
    pdf.cell(50, 10, txt=f"{amount:,.2f}", border=1, align='R')
    pdf.ln()
    
    # Total
    pdf.set_font(font_normal, 'B', 14)
    pdf.cell(140, 10, txt="รวมทั้งสิ้น (Grand Total)", border=1, align='R')
    pdf.cell(50, 10, txt=f"{amount:,.2f}", border=1, align='R', fill=True)
    
    # --- SIGNATURE ---
    pdf.ln(30)
    if os.path.exists('signature.png'):
        pdf.image('signature.png', x=140, y=pdf.get_y()-10, w=30)
        
    pdf.cell(120, 8, txt="", ln=0)
    pdf.cell(70, 8, txt="......................................................", ln=1, align='C')
    pdf.cell(120, 8, txt="", ln=0)
    pdf.cell(70, 8, txt="( ผู้รับเงิน / Collector )", ln=1, align='C')
    pdf.cell(120, 8, txt="", ln=0)
    pdf.cell(70, 8, txt="นิติบุคคลอาคารชุด/หมู่บ้าน", ln=1, align='C')

    filename = f"receipt_{receipt_no}.pdf"
    pdf.output(filename)
    return filename

# --- 3. HELPER: PromptPay QR (Text only concept for simplicity) ---
def generate_promptpay_info(amount):
    # ในการใช้งานจริงต้องใช้ library 'promptpay' แต่เพื่อลด dependency 
    # เราจะแสดงเป็น Text หรือ Link แทนในเวอร์ชั่นนี้
    return f"https://promptpay.io/0812345678/{amount}" # เปลี่ยนเบอร์ตรงนี้

# --- 4. MAIN APP ---
def main():
    st.set_page_config(page_title="Smart Juristic", layout="wide", page_icon="🏢")
    st.title("🏢 ระบบจัดการหมู่บ้าน/คอนโดมิเนียม (Pro)")

    # Init Session
    if "user_id" not in st.session_state:
        st.session_state.update({"user_id": None, "role": None, "username": None})

    # --- SIDEBAR ---
    if st.session_state["user_id"] is None:
        menu = ["เข้าสู่ระบบ", "สมัครสมาชิก"]
        choice = st.sidebar.selectbox("ยินดีต้อนรับ", menu)
    else:
        role_txt = "👑 Admin" if st.session_state["role"] == 'admin' else "👤 ลูกบ้าน"
        st.sidebar.success(f"{st.session_state['username']} ({role_txt})")
        
        menu_list = ["หน้าหลัก", "ข้อมูลส่วนตัว", "ชำระเงิน/แจ้งโอน", "ประวัติ/ดาวน์โหลดใบเสร็จ"]
        if st.session_state["role"] == 'admin':
            st.sidebar.divider()
            menu_list.extend(["Admin: แดชบอร์ด", "Admin: ข้อมูลลูกบ้าน", "Admin: จัดการสิทธิ์"])
            
        menu_list.append("ออกจากระบบ")
        choice = st.sidebar.selectbox("เมนู", menu_list)

    # --- AUTHENTICATION ZONE ---
    if choice == "สมัครสมาชิก":
        st.subheader("📝 สมัครสมาชิก")
        with st.form("reg"):
            u = st.text_input("Username").strip()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("สมัคร"):
                if u and p:
                    role = 'admin' if u.lower() == 'admin' else 'user'
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", 
                                  (u, make_hashes(p), role))
                        conn.commit()
                        st.success(f"สมัครสำเร็จ! ({role})")
                    except: st.error("ชื่อซ้ำ")
                else: st.error("กรอกให้ครบ")

    elif choice == "เข้าสู่ระบบ":
        st.subheader("🔐 Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("เข้าสู่ระบบ", type="primary"):
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username=?', (u,))
            d = c.fetchone()
            if d and check_hashes(p, d[2]):
                st.session_state.update({"user_id": d[0], "username": d[1], "role": d[3] if len(d)>3 else 'user'})
                st.rerun()
            else: st.error("รหัสผิด")

    elif choice == "ออกจากระบบ":
        st.session_state.clear()
        st.rerun()

    # --- USER ZONES ---
    elif st.session_state["user_id"]:
        my_id = st.session_state["user_id"]
        
        # 1. PROFILE
        if choice == "ข้อมูลส่วนตัว":
            st.header("📇 ข้อมูลส่วนตัว (Profile)")
            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            
            with st.form("profile"):
                n = st.text_input("ชื่อ-สกุล (เจ้าของ)", value=prof[2] if prof else "")
                ph = st.text_input("เบอร์โทร", value=prof[3] if prof else "")
                ad = st.text_area("ที่อยู่ / เลขห้อง", value=prof[4] if prof else "")
                if st.form_submit_button("บันทึกข้อมูล"):
                    if prof:
                        c.execute("UPDATE personnel SET name=?, phone=?, address=? WHERE owner_id=?", (n,ph,ad,my_id))
                    else:
                        c.execute("INSERT INTO personnel (owner_id,name,phone,address) VALUES (?,?,?,?)", (my_id,n,ph,ad))
                    conn.commit()
                    st.toast("บันทึกเรียบร้อย", icon="✅")
                    st.rerun()

        # 2. PAYMENT (Smart Dropdown + Manual Input)
        elif choice == "ชำระเงิน/แจ้งโอน":
            st.header("💸 แจ้งชำระเงิน")
            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            
            if prof:
                st.info(f"ทำรายการในนาม: {prof[2]}")
                
                # --- Payment Form ---
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        # Dropdown หลัก
                        main_cat = st.selectbox("เลือกประเภทรายการ", 
                                              ["ค่าส่วนกลาง (Common Fee)", 
                                               "ค่าน้ำประปา (Water Bill)", 
                                               "ค่าบัตรจอดรถ/คีย์การ์ด", 
                                               "ค่าปรับ (Fine)",
                                               "อื่นๆ (ระบุเอง)"])
                        
                        # Logic การแสดงผลตามตัวเลือก
                        final_note = ""
                        final_cat = main_cat
                        
                        if main_cat == "ค่าส่วนกลาง (Common Fee)":
                            m = st.selectbox("เดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
                            y = st.selectbox("ปี (พ.ศ.)", [str(x) for x in range(2567, 2575)])
                            final_note = f"ค่าส่วนกลาง เดือน {m} {y}"
                            
                        elif main_cat == "อื่นๆ (ระบุเอง)":
                            # ถ้าเลือกอื่นๆ ให้พิมพ์เอง
                            custom_input = st.text_input("ระบุรายละเอียดค่าใช้จ่าย", placeholder="เช่น ค่าซ่อมท่อ, ค่ามัดจำ...")
                            if custom_input:
                                final_note = custom_input
                                final_cat = "ค่าใช้จ่ายอื่นๆ"
                            else:
                                final_note = "ไม่ระบุรายละเอียด"
                        else:
                            # กรณีอื่นๆ ให้เติมรายละเอียดเล็กน้อยได้
                            note_add = st.text_input("รายละเอียดเพิ่มเติม (ถ้ามี)", placeholder="เช่น รอบบิล...")
                            final_note = f"{main_cat} {note_add}"

                        amount = st.number_input("ยอดเงิน (บาท)", min_value=0.0, step=100.0)

                    with col2:
                        st.write("📷 **หลักฐานการโอน (Mandatory)**")
                        # QR Code จำลอง
                        if amount > 0:
                            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=PROMPTPAY_ID_HERE:{amount}", caption="สแกนจ่ายได้เลย")
                        
                        file = st.file_uploader("อัปโหลดสลิป", type=['jpg','png','jpeg'])

                    if st.button("ยืนยันแจ้งโอน", type="primary", use_container_width=True):
                        if amount > 0 and file:
                            # Save
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            fpath = f"slips/{ts}_{file.name}"
                            with open(fpath, "wb") as f: f.write(file.getbuffer())
                            
                            c.execute("INSERT INTO transactions (person_id,amount,date,slip_path,note,category) VALUES (?,?,?,?,?,?)",
                                      (prof[0], amount, datetime.now().strftime("%Y-%m-%d %H:%M"), fpath, final_note, final_cat))
                            conn.commit()
                            st.balloons()
                            st.success("บันทึกข้อมูลเรียบร้อย! ไปที่เมนู 'ประวัติ' เพื่อดาวน์โหลดใบเสร็จ")
                        else:
                            st.error("กรุณาระบุยอดเงินและแนบสลิป")
            else:
                st.warning("กรุณากรอกข้อมูลส่วนตัวก่อน")

        # 3. HISTORY & RECEIPT (God-tier Original/Copy Logic)
        elif choice == "ประวัติ/ดาวน์โหลดใบเสร็จ":
            st.header("📜 ประวัติและใบเสร็จรับเงิน")
            c = conn.cursor()
            c.execute("SELECT * FROM personnel WHERE owner_id=?", (my_id,))
            prof = c.fetchone()
            
            if prof:
                c.execute(f"SELECT * FROM transactions WHERE person_id={prof[0]} ORDER BY date DESC")
                rows = c.fetchall()
                
                if rows:
                    # แปลงเป็น DataFrame เพื่อโชว์ตารางรวมก่อน
                    df = pd.DataFrame(rows, columns=['id', 'pid', 'amount', 'date', 'path', 'note', 'cat', 'dl_count'])
                    st.dataframe(df[['date', 'cat', 'note', 'amount']], use_container_width=True)
                    
                    st.divider()
                    st.subheader("📥 ดาวน์โหลดใบเสร็จ (รายรายการ)")
                    
                    # Loop แสดงแต่ละรายการพร้อมปุ่มโหลด
                    for row in rows:
                        tid, _, amt, dt, path, note, cat, dl_count = row
                        
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.write(f"**{dt}** | {cat}")
                                st.caption(note)
                            with c2:
                                st.write(f"**{amt:,.2f} บาท**")
                                if dl_count == 0:
                                    st.markdown(":new: *ยังไม่เคยโหลด*")
                                else:
                                    st.markdown(f":repeat: *โหลดแล้ว {dl_count} ครั้ง*")
                            with c3:
                                # Logic ปุ่มดาวน์โหลด
                                if st.button(f"📄 ดาวน์โหลดใบเสร็จ", key=f"btn_{tid}"):
                                    # 1. เช็คสถานะ Original/Copy
                                    is_orig = True if dl_count == 0 else False
                                    
                                    # 2. สร้าง PDF
                                    pdf_file = generate_receipt_pdf(tid, prof[2], dt, amt, cat, note, is_orig)
                                    
                                    # 3. อัปเดต DB ว่าโหลดแล้ว (Counter + 1)
                                    c.execute("UPDATE transactions SET download_count = download_count + 1 WHERE id=?", (tid,))
                                    conn.commit()
                                    
                                    # 4. ส่งไฟล์ให้โหลด
                                    with open(pdf_file, "rb") as f:
                                        st.download_button(
                                            label="คลิกเพื่อบันทึกไฟล์ (PDF)",
                                            data=f,
                                            file_name=pdf_file,
                                            mime="application/pdf",
                                            key=f"dl_{tid}"
                                        )
                                    st.rerun() # Refresh เพื่ออัปเดตสถานะ Copy ทันที
                else:
                    st.info("ไม่พบประวัติ")

        # --- ADMIN ZONES (ย่อให้สั้นลง แต่ครบฟังก์ชัน) ---
        elif "Admin" in choice and st.session_state["role"] == 'admin':
            if "แดชบอร์ด" in choice:
                st.header("📊 Admin Dashboard")
                df = pd.read_sql("SELECT * FROM transactions", conn)
                if not df.empty:
                    st.metric("ยอดรวมทั้งหมด", f"{df['amount'].sum():,.2f}")
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
