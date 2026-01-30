import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

# 2. RTL Styling
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stSelectbox, .stTextInput, .stTextArea { direction: rtl !important; text-align: right !important; }
    .stButton button { display: block; margin-right: 0; margin-left: auto; background-color: #4CAF50; color: white; }
    div[data-baseweb="select"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 پنل جامع ثبت و ویرایش اطلاعات")

# 3. Connection
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error("Connection Error")
    st.stop()

# 4. Preparation
names_list = df['اسم'].dropna().unique().tolist()

# Top Navigation
search_query = st.selectbox(
    "🔍 جستجوی کلی (انتخاب برای ویرایش):", 
    ["+ افزودن مورد جدید"] + names_list
)

# 5. The Main Form
with st.form("main_form"):
    if search_query == "+ افزودن مورد جدید":
        st.subheader("✨ ثبت ورودی جدید")
        
        # We use a selectbox that handles "New" entries. 
        # If you type a name not in the list, Streamlit 1.30+ allows labels.
        v_name = st.selectbox(
            "اسم (تایپ کنید - اگر جدید است Enter بزنید):",
            options=names_list,
            index=None,
            placeholder="نام را وارد کنید...",
            # This is the magic part: it shows suggestions as you type
        )
        
        # If the name is brand new and not in the list, use a text box that ONLY 
        # appears if the dropdown is empty.
        if v_name is None:
            v_final_name = st.text_input("تایید نام جدید (اگر در لیست بالا نبود اینجا بنویسید):")
        else:
            v_final_name = v_name
            
    else:
        st.subheader(f"🔄 ویرایش: {search_query}")
        user_data = df[df['اسم'] == search_query].iloc[0]
        v_final_name = search_query

    # --- Personal Info ---
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ تولد", "")))
    with c2: v_age = st.text_input("سن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("سن", "")))
    with c3: v_gender = st.text_input("جنسیت", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("جنسیت", "")))
    
    # --- Details ---
    st.markdown("### 🔍 جزئیات واقعه")
    c4, c5, c6 = st.columns(3)
    with c4: v_city = st.text_input("شهر", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("شهر", "")))
    with c5: v_district = st.text_input("محله", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محله", "")))
    with c6: v_street = st.text_input("خیابان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("خیابان", "")))
    
    v_province = st.text_input("استان", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("استان", "")))
    v_date = st.text_input("تاریخ", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ", "")))
    v_exact_loc = st.text_input("محل دقیق کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محل دقیق کشته شدن", "")))
    v_method = st.text_input("طریقه‌ی کشته شدن", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("طریقه‌ی کشته شدن", "")))
    v_grave = st.text_input("آرامگاه", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("آرامگاه", "")))
    v_birth_place = st.text_input("محل تولد", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("محل تولد", "")))

    # --- Additional ---
    st.markdown("### 🌐 اطلاعات تکمیلی")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("اکانت در شبکه‌های اجتماعی", "")))
    v_relatives = st.text_input("بستگان در شبکه‌های اجتماعی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("بستگان در شبکه‌های اجتماعی", "")))
    v_date_en = st.text_input("تاریخ میلادی", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("تاریخ میلادی", "")))
    v_notes = st.text_area("توضیحات", value="" if search_query=="+ افزودن مورد جدید" else str(user_data.get("توضیحات", "")))

    submit = st.form_submit_button("💾 ذخیره نهایی")

    if submit:
        if not v_final_name:
            st.error("⚠️ نام الزامی است.")
        else:
            data = {
                "اسم": v_final_name, "شهر": v_city, "محله": v_district, "خیابان": v_street, 
                "استان": v_province, "تاریخ": v_date, "تاریخ میلادی": v_date_en, 
                "سن": v_age, "جنسیت": v_gender, "توضیحات": v_notes, 
                "محل دقیق کشته شدن": v_exact_loc, "طریقه‌ی کشته شدن": v_method, 
                "آرامگاه": v_grave, "محل تولد": v_birth_place, "تاریخ تولد": v_bday, 
                "اکانت در شبکه‌های اجتماعی": v_social, "بستگان در شبکه‌های اجتماعی": v_relatives
            }
            if search_query == "+ افزودن مورد جدید":
                new_df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
                conn.update(data=new_df)
                st.success("ثبت شد.")
            else:
                df.loc[df['اسم'] == search_query, list(data.keys())] = list(data.values())
                conn.update(data=df)
                st.success("بروزرسانی شد.")
            st.rerun()
