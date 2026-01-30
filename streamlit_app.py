import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

# 2. RTL Styling for Farsi
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stSelectbox, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { display: block; margin-right: 0; margin-left: auto; background-color: #4CAF50; color: white; }
    div[data-testid="stExpander"] { text-align: right; direction: rtl; }
    .stMetric { text-align: right; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 پنل جامع ثبت و ویرایش اطلاعات")

# 3. Connect to Google Sheets
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("خطا در اتصال به گوگل‌شیت. لطفا تنظیمات Secrets را بررسی کنید.")
    st.stop()

# 4. Search & Dropdown Section
names_list = df['اسم'].dropna().unique().tolist()

c_top1, c_top2 = st.columns([3, 1])
with c_top1:
    search_query = st.selectbox(
        "🔍 جستجوی نام (تایپ کنید تا لیست فیلتر شود):", 
        ["+ افزودن مورد جدید"] + names_list
    )
with c_top2:
    st.metric("تعداد کل افراد", len(df))

# 5. The Main Form
with st.form("main_form"):
    if search_query == "+ افزودن مورد جدید":
        st.subheader("✨ ثبت ورودی جدید")
        v_name = st.text_input("اسم")
    else:
        st.subheader(f"🔄 ویرایش اطلاعات: {search_query}")
        # Get existing data for the selected name
        user_data = df[df['اسم'] == search_query].iloc[0]
        v_name = search_query
        st.info("در حال ویرایش اطلاعات موجود. تغییرات را اعمال و دکمه بروزرسانی را بزنید.")

    # --- Section 1: Personal Info ---
    st.markdown("### 👤 اطلاعات شخصی")
    col1, col2, col3 = st.columns(3)
    with col1: 
        v_bday = st.text_input("تاریخ تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ تولد", "")))
    with col2: 
        v_age = st.text_input("سن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("سن", "")))
    with col3: 
        v_gender = st.text_input("جنسیت", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("جنسیت", "")))
    
    col_birth1, col_birth2 = st.columns(2)
    with col_birth1:
        v_birth_place = st.text_input("محل تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محل تولد", "")))
    with col_birth2:
        v_city_base = st.text_input("شهر", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("شهر", "")))

    st.divider()

    # --- Section 2: Details of Incident ---
    st.markdown("### 🔍 جزئیات واقعه")
    col4, col5, col6 = st.columns(3)
    with col4: 
        v_province = st.text_input("استان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("استان", "")))
    with col5: 
        v_district = st.text_input("محله", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محله", "")))
    with col6: 
        v_street = st.text_input("خیابان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("خیابان", "")))
    
    col_incident1, col_incident2 = st.columns(2)
    with col_incident1:
        v_date = st.text_input("تاریخ", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ", "")))
    with col_incident2:
        v_exact_loc = st.text_input("محل دقیق کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محل دقیق کشته شدن", "")))
    
    v_method = st.text_input("طریقه‌ی کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("طریقه‌ی کشته شدن", "")))
    v_grave = st.text_input("آرامگاه", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("آرامگاه", "")))

    st.divider()

    # --- Section 3: Additional Info ---
    st.markdown("### 🌐 اطلاعات تکمیلی")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("اکانت در شبکه‌های اجتماعی", "")))
    v_relatives = st.text_input("بستگان در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("بستگان در شبکه‌های اجتماعی", "")))
    
    v_date_en = st.text_input("تاریخ میلادی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ میلادی", "")))
    v_notes = st.text_area("توضیحات", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("توضیحات", "")))

    # 6. Submit Button Logic
    submit_label = "💾 ذخیره اطلاعات جدید" if search_query == "+ افزودن مورد جدید" else "✅ بروزرسانی تغییرات"
    submit = st.form_submit_button(submit_label)

    if submit:
        # Construct dictionary
        updated_dict = {
            "اسم": v_name, "شهر": v_city_base, "محله": v_district, "خیابان": v_street, 
            "استان": v_province, "تاریخ": v_date, "تاریخ میلادی": v_date_en, 
            "سن": v_age, "جنسیت": v_gender, "توضیحات": v_notes, 
            "محل دقیق کشته شدن": v_exact_loc, "طریقه‌ی کشته شدن": v_method, 
            "آرامگاه": v_grave, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
            "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_relatives
        }
        
        # Validation Gatekeeper
        if not v_name or v_name.strip() == "" or v_name == "+ افزودن مورد جدید":
            st.error("⚠️ خطای نام: وارد کردن 'اسم' برای ثبت اطلاعات الزامی است.")
        else:
            if search_query == "+ افزودن مورد جدید":
                if v_name in names_list:
                    st.error("این اسم قبلاً در لیست موجود است. لطفاً آن را از لیست بالا انتخاب کرده و ویرایش کنید.")
                else:
                    new_row = pd.DataFrame([updated_dict])
                    df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(data=df)
                    st.success(f"اطلاعات '{v_name}' با موفقیت ثبت شد.")
                    st.balloons()
            else:
                # Update existing row
                df.loc[df['اسم'] == search_query, list(updated_dict.keys())] = list(updated_dict.values())
                conn.update(data=df)
                st.success("بروزرسانی با موفقیت انجام شد.")
