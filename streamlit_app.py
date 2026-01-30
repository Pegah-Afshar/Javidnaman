import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Config
st.set_page_config(page_title="ثبت و ویرایش جاویدنامان", layout="wide")

# 2. RTL & Clean Styling
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #4CAF50; color: white; height: 3em; font-size: 1.2em; }
    input { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# 3. Database Connection
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("خطا در اتصال به دیتابیس")
    st.stop()

names_list = df['اسم'].dropna().unique().tolist()

# 4. Logic for "Edit" vs "New"
st.title("📋 سامانه ثبت اطلاعات")

# We use a session state to hold the name so it doesn't vanish
if "current_name" not in st.session_state:
    st.session_state.current_name = ""

# 5. THE COMBOBOX (Single Field)
# This creates the suggestion list
options_html = "".join([f'<option value="{n}">' for n in names_list])
st.markdown(f'<datalist id="names_datalist">{options_html}</datalist>', unsafe_allow_html=True)

# The Input Box
name_input = st.text_input("📍 نام و نام خانوادگی:", 
                          value=st.session_state.current_name,
                          placeholder="تایپ کنید... (نام‌های موجود پیشنهاد می‌شوند)",
                          key="name_input_field")

# Javascript to link the list to the box
st.markdown("""
    <script>
    var inputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].getAttribute('aria-label') == "📍 نام و نام خانوادگی:") {
            inputs[i].setAttribute('list', 'names_datalist');
        }
    }
    </script>
    """, unsafe_allow_html=True)

# 6. Check if person exists to load data
is_edit = name_input in names_list
if is_edit:
    st.info(f"🔄 در حال ویرایش اطلاعات موجود برای: {name_input}")
    user_data = df[df['اسم'] == name_input].iloc[0]
else:
    if name_input != "":
        st.success(f"✨ در حال ثبت فرد جدید: {name_input}")

# 7. THE FORM
with st.form("main_form", clear_on_submit=True):
    
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with c2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with c3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")
    
    v_birth_place = st.text_input("محل تولد", value=str(user_data.get("محل تولد", "")) if is_edit else "")

    st.divider()
    st.markdown("### 🔍 جزئیات واقعه")
    
    # Grid: Province - City - District/Street
    det_col1, det_col2, det_col3 = st.columns(3)
    with det_col1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with det_col2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with det_col3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")
    
    # Date row
    date_col1, date_col2 = st.columns(2)
    with date_col1: v_shamsi = st.text_input("تاریخ شمسی", value=str(user_data.get("تاریخ شمسی", "")) if is_edit else "")
    with date_col2: v_en = st.text_input("تاریخ میلادی", value=str(user_data.get("تاریخ میلادی", "")) if is_edit else "")
    
    v_loc = st.text_input("محل دقیق کشته شدن", value=str(user_data.get("محل دقیق کشته شدن", "")) if is_edit else "")
    v_method = st.text_input("طریقه‌ی کشته شدن", value=str(user_data.get("طریقه‌ی کشته شدن", "")) if is_edit else "")
    v_grave = st.text_input("آرامگاه", value=str(user_data.get("آرامگاه", "")) if is_edit else "")

    st.divider()
    st.markdown("### 🌐 اطلاعات تکمیلی")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value=str(user_data.get("اکانت در شبکه‌های اجتماعی", "")) if is_edit else "")
    v_rel = st.text_input("بستگان در شبکه‌های اجتماعی", value=str(user_data.get("بستگان در شبکه‌های اجتماعی", "")) if is_edit else "")
    v_notes = st.text_area("توضیحات", value=str(user_data.get("توضیحات", "")) if is_edit else "")

    submit = st.form_submit_button("💾 ذخیره نهایی اطلاعات")

    if submit:
        if not name_input:
            st.error("لطفا نام را وارد کنید")
        else:
            new_data = {
                "اسم": name_input, "استان": v_prov, "شهر": v_city, "محله/خیابان": v_dist, 
                "تاریخ شمسی": v_shamsi, "تاریخ میلادی": v_en, "محل دقیق کشته شدن": v_loc,
                "طریقه‌ی کشته شدن": v_method, "آرامگاه": v_grave, "سن": v_age, "جنسیت": v_gender, 
                "توضیحات": v_notes, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
                "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_rel
            }
            
            # Update local dataframe
            if is_edit:
                df.loc[df['اسم'] == name_input, list(new_data.keys())] = list(new_data.values())
            else:
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            
            # Push to Google Sheets
            conn.update(spreadsheet=spreadsheet_url, data=df)
            st.success("✅ اطلاعات با موفقیت در گوگل‌شیت ذخیره شد!")
            
            # Reset the name for next entry
            st.session_state.current_name = ""
            st.rerun()
