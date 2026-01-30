import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Config
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

# 2. RTL Styling
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stSelectbox, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #4CAF50; color: white; height: 3em; font-weight: bold; }
    input { direction: rtl; text-align: right; }
    div[data-baseweb="select"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# 3. Connection
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("❌ خطا در اتصال به گوگل‌شیت. لطفا فایل Secrets را چک کنید.")
    st.stop()

# 4. Prepare Names
names_list = df['اسم'].dropna().unique().tolist() if df is not None else []

st.title("📋 سامانه مدیریت اطلاعات")

# 5. THE SINGLE BOX (Combobox Logic)
# We use st.selectbox. If you type a name not in the list, 
# Streamlit 1.30+ handles it gracefully.
selected_name = st.selectbox(
    "📍 نام و نام خانوادگی را وارد یا انتخاب کنید:",
    options=names_list,
    index=None,
    placeholder="شروع به تایپ کنید...",
)

# Detect if we are Editing or Creating
is_edit = selected_name in names_list and selected_name is not None
user_data = df[df['اسم'] == selected_name].iloc[0] if is_edit else {}

if selected_name:
    if is_edit:
        st.info(f"🔄 در حال ویرایش: {selected_name}")
    else:
        st.success(f"✨ در حال ثبت نام جدید: {selected_name}")

# 6. THE FORM
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
    
    # Row: Dates
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

    submit = st.form_submit_button("💾 ذخیره نهایی")

    if submit:
        if not selected_name:
            st.error("⚠️ نام وارد نشده است!")
        else:
            updated_row = {
                "اسم": selected_name, "استان": v_prov, "شهر": v_city, "محله/خیابان": v_dist, 
                "تاریخ شمسی": v_shamsi, "تاریخ میلادی": v_en, "محل دقیق کشته شدن": v_loc,
                "طریقه‌ی کشته شدن": v_method, "آرامگاه": v_grave, "سن": v_age, "جنسیت": v_gender, 
                "توضیحات": v_notes, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
                "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_rel
            }
            
            try:
                # Refresh data
                fresh_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                
                if is_edit:
                    fresh_df.loc[fresh_df['اسم'] == selected_name, list(updated_row.keys())] = list(updated_row.values())
                else:
                    new_df = pd.DataFrame([updated_row])
                    fresh_df = pd.concat([fresh_df, new_df], ignore_index=True)
                
                conn.update(spreadsheet=spreadsheet_url, data=fresh_df)
                st.success("✅ ذخیره شد!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطا: {e}")
