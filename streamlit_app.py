import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

# 2. RTL & Persian Styling
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stSelectbox, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #4CAF50; color: white; height: 3em; }
    input { direction: rtl; text-align: right; }
    div[data-baseweb="select"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# 3. Connection to Google Sheets
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("خطا در اتصال به گوگل‌شیت. لطفا تنظیمات Secrets را چک کنید.")
    st.stop()

# 4. Data Prep
if df is not None:
    names_list = df['اسم'].dropna().unique().tolist()
else:
    names_list = []

st.title("📋 سامانه مدیریت اطلاعات")

# 5. THE COMBOBOX LOGIC
# This is the single box you asked for.
selected_name = st.selectbox(
    "📍 نام و نام خانوادگی را انتخاب یا تایپ کنید:",
    options=names_list,
    index=None,
    placeholder="شروع به تایپ کنید...",
    help="اگر نام در لیست نیست، آن را کامل تایپ کرده و Enter بزنید.",
    no_options_label="نام جدید (برای تایید Enter بزنید)"
)

# Determine if we are Editing or Creating
is_edit = selected_name in names_list and selected_name is not None
user_data = df[df['اسم'] == selected_name].iloc[0] if is_edit else {}

if selected_name:
    if is_edit:
        st.info(f"🔄 در حال ویرایش: {selected_name}")
    else:
        st.success(f"✨ نام جدید شناسایی شد: {selected_name}")

# 6. THE FORM
with st.form("main_form", clear_on_submit=True):
    
    # Section 1: Personal
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with c2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with c3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")
    
    v_birth_place = st.text_input("محل تولد", value=str(user_data.get("محل تولد", "")) if is_edit else "")

    st.divider()
    
    # Section 2: Incident Details (The specific layout you requested)
    st.markdown("### 🔍 جزئیات واقعه")
    
    # Row: Province - City - District/Street
    det_col1, det_col2, det_col3 = st.columns(3)
    with det_col1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with det_col2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with det_col3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")
    
    # Row: Shamsi Date - English Date
    date_col1, date_col2 = st.columns(2)
    with date_col1: v_shamsi = st.text_input("تاریخ شمسی", value=str(user_data.get("تاریخ شمسی", "")) if is_edit else "")
    with date_col2: v_en = st.text_input("تاریخ میلادی", value=str(user_data.get("تاریخ میلادی", "")) if is_edit else "")
    
    v_loc = st.text_input("محل دقیق کشته شدن", value=str(user_data.get("محل دقیق کشته شدن", "")) if is_edit else "")
    v_method = st.text_input("طریقه‌ی کشته شدن", value=str(user_data.get("طریقه‌ی کشته شدن", "")) if is_edit else "")
    v_grave = st.text_input("آرامگاه", value=str(user_data.get("آرامگاه", "")) if is_edit else "")

    st.divider()
    
    # Section 3: Additional
    st.markdown("### 🌐 اطلاعات تکمیلی")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value=str(user_data.get("اکانت در شبکه‌های اجتماعی", "")) if is_edit else "")
    v_rel = st.text_input("بستگان در شبکه‌های اجتماعی", value=str(user_data.get("بستگان در شبکه‌های اجتماعی", "")) if is_edit else "")
    v_notes = st.text_area("توضیحات", value=str(user_data.get("توضیحات", "")) if is_edit else "")

    # Submit Button
    submit = st.form_submit_button("💾 ذخیره نهایی اطلاعات")

    if submit:
        if not selected_name:
            st.error("⚠️ ابتدا نام را وارد کنید.")
        else:
            new_entry = {
                "اسم": selected_name, "استان": v_prov, "شهر": v_city, "محله/خیابان": v_dist, 
                "تاریخ شمسی": v_shamsi, "تاریخ میلادی": v_en, "محل دقیق کشته شدن": v_loc,
                "طریقه‌ی کشته شدن": v_method, "آرامگاه": v_grave, "سن": v_age, "جنسیت": v_gender, 
                "توضیحات": v_notes, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
                "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_rel
            }
            
            try:
                # Refresh data to avoid overwriting others
                fresh_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                
                if is_edit:
                    fresh_df.loc[fresh_df['اسم'] == selected_name, list(new_entry.keys())] = list(new_entry.values())
                else:
                    new_row = pd.DataFrame([new_entry])
                    fresh_df = pd.concat([fresh_df, new_row], ignore_index=True)
                
                conn.update(spreadsheet=spreadsheet_url, data=fresh_df)
                st.success("✅ با موفقیت ذخیره شد!")
                st.rerun()
            except Exception as e:
                st.error(f"خطا در ذخیره: {e}")
