import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="ثبت اطلاعات", layout="wide")

# --- RTL Styling ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stSelectbox, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { display: block; margin-right: 0; margin-left: auto; }
    div[data-testid="stExpander"] { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 پنل جامع ثبت و ویرایش")

# Connect
spreadsheet_url = st.secrets["public_gsheets_url"]
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(spreadsheet=spreadsheet_url, ttl=0)

# Search Selection
names_list = df['اسم'].dropna().unique().tolist()
search_query = st.selectbox("🔍 انتخاب فرد جهت ویرایش یا افزودن جدید:", ["+ افزودن مورد جدید"] + names_list)

with st.form("main_form"):
    if search_query == "+ افزودن مورد جدید":
        st.subheader("✨ ثبت ورودی جدید")
        v_name = st.text_input("اسم")
    else:
        st.subheader(f"🔄 ویرایش اطلاعات: {search_query}")
        user_data = df[df['اسم'] == search_query].iloc[0]
        v_name = search_query

    # --- Section 1: Personal Info ---
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: 
        v_bday = st.text_input("تاریخ تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["تاریخ تولد"]))
    with c2: 
        v_age = st.text_input("سن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["سن"]))
    with c3: 
        v_gender = st.text_input("جنسیت", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["جنسیت"]))
    
    c1b, c2b = st.columns(2)
    with c1b:
        v_birth_place = st.text_input("محل تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["محل تولد"]))
    with c2b:
        v_city_base = st.text_input("شهر (محل سکونت/تولد)", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["شهر"]))

    st.divider()

    # --- Section 2: Details of Incident ---
    st.markdown("### 🔍 جزئیات واقعه")
    c4, c5, c6 = st.columns(3)
    with c4: 
        v_province = st.text_input("استان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["استان"]))
    with c5: 
        v_district = st.text_input("محله", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["محله"]))
    with c6: 
        v_street = st.text_input("خیابان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["خیابان"]))
    
    c7, c8 = st.columns(2)
    with c7:
        v_date = st.text_input("تاریخ", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["تاریخ"]))
    with c8:
        v_exact_loc = st.text_input("محل دقیق کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["محل دقیق کشته شدن"]))
    
    v_method = st.text_input("طریقه‌ی کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["طریقه‌ی کشته شدن"]))
    v_grave = st.text_input("آرامگاه", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["آرامگاه"]))

    st.divider()

    # --- Section 3: Additional Info ---
    st.markdown("### 🌐 اطلاعات تکمیلی")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["اکانت در شبکه‌های اجتماعی"]))
    v_relatives = st.text_input("بستگان در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["بستگان در شبکه‌های اجتماعی"]))
    
    # Catch-all for columns not specifically placed (like تاریخ میلادی)
    v_date_en = st.text_input("تاریخ میلادی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["تاریخ میلادی"]))
    v_notes = st.text_area("توضیحات", value="" if search_query=="+ افزودن مورد جدید" else str(user_data["توضیحات"]))

    # Submit button
    submit_label = "💾 ذخیره اطلاعات جدید" if search_query == "+ افزودن مورد جدید" else "✅ بروزرسانی تغییرات"
    submit = st.form_submit_button(submit_label)

    if submit:
        # Construct the data dictionary to match Google Sheet headers exactly
        updated_dict = {
            "اسم": v_name, "شهر": v_city_base, "محله": v_district, "خیابان": v_street, 
            "استان": v_province, "تاریخ": v_date, "تاریخ میلادی": v_date_en, 
            "سن": v_age, "جنسیت": v_gender, "توضیحات": v_notes, 
            "محل دقیق کشته شدن": v_exact_loc, "طریقه‌ی کشته شدن": v_method, 
            "آرامگاه": v_grave, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
            "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_relatives
        }
        
        if search_query == "+ افزودن مورد جدید":
            if v_name == "":
                st.error("لطفاً 'اسم' را وارد کنید.")
            else:
                new_row = pd.DataFrame([updated_dict])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success("اطلاعات با موفقیت ثبت شد.")
                st.balloons()
        else:
            df.loc[df['اسم'] == search_query, list(updated_dict.keys())] = list(updated_dict.values())
            conn.update(data=df)
            st.success("بروزرسانی با موفقیت انجام شد.")

if submit:
        # Construct the data dictionary
        updated_dict = {
            "اسم": v_name, "شهر": v_city_base, "محله": v_district, "خیابان": v_street, 
            "استان": v_province, "تاریخ": v_date, "تاریخ میلادی": v_date_en, 
            "سن": v_age, "جنسیت": v_gender, "توضیحات": v_notes, 
            "محل دقیق کشته شدن": v_exact_loc, "طریقه‌ی کشته شدن": v_method, 
            "آرامگاه": v_grave, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
            "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_relatives
        }
        
        # --- THE GATEKEEPER CHECK ---
        if not v_name or v_name.strip() == "" or v_name == "+ افزودن مورد جدید":
            st.error("⚠️ خطای نام: وارد کردن 'اسم' برای ثبت اطلاعات الزامی است.")
        else:
            if search_query == "+ افزودن مورد جدید":
                # Check if name already exists to prevent duplicates
                if v_name in names_list:
                    st.error("این اسم قبلاً در لیست موجود است. لطفاً از منوی بالا آن را ویرایش کنید.")
                else:
                    new_row = pd.DataFrame([updated_dict])
                    df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(data=df)
                    st.success(f"اطلاعات مربوط به '{v_name}' با موفقیت ثبت شد.")
                    st.balloons()
            else:
                # Update existing
                df.loc[df['اسم'] == search_query, list(updated_dict.keys())] = list(updated_dict.values())
                conn.update(data=df)
                st.success("بروزرسانی با موفقیت انجام شد.")
