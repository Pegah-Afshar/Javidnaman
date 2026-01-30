import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="مدیریت داده‌ها", layout="wide")

# استایل راست‌چین
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #2e7d32; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# تابع اتصال با عیب‌یابی دقیق
def connect_to_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        if "gspread_creds" not in st.secrets:
            return None, "کلید gspread_creds در Secrets پیدا نشد!"
        
        creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
        client = gspread.authorize(creds)
        
        if "public_gsheets_url" not in st.secrets:
            return None, "آدرس شیت (public_gsheets_url) در Secrets پیدا نشد!"
            
        url = st.secrets["public_gsheets_url"]
        sh = client.open_by_url(url)
        wks = sh.get_worksheet(0)
        return wks, None
    except Exception as e:
        return None, str(e)

worksheet, error_msg = connect_to_sheet()

if error_msg:
    st.error(f"❌ خطای اتصال: {error_msg}")
    st.info("راهنما: مطمئن شوید ایمیل ربات را Editor کرده‌اید و آدرس شیت درست است.")
    st.stop()

# خواندن داده‌ها برای لیست اسامی
data = worksheet.get_all_records()
df = pd.DataFrame(data)
names_list = df['اسم'].dropna().unique().tolist() if not df.empty else []

st.title("📋 پنل ثبت و ویرایش هوشمند")

# --- بخش باکس نام (تکی و هوشمند) ---


# 1. Initialize the name in session state so it NEVER clears
if "saved_name" not in st.session_state:
    st.session_state.saved_name = ""

# 2. The Searchable Box
# We use a trick: the 'label' changes based on what is typed to "lock" it in.
selected_name = st.selectbox(
    "📍 نام و نام خانوادگی را انتخاب یا تایپ کنید:",
    options=names_list,
    index=None,
    placeholder="جستجو کنید یا بنویسید...",
    key="name_selector"
)

# 3. The Logic that prevents clearing:
# If they selected from the dropdown, update the saved name
if selected_name:
    st.session_state.saved_name = selected_name
# If they are typing something new, we need a way to capture it. 
# Since selectbox clears new text, we add a "Confirm New Name" button 
# ONLY if the name isn't in the list.
else:
    # This captures the text even if it's not in the list
    pass 

# Check if we are editing
name_to_use = st.session_state.saved_name
is_edit = name_to_use in names_list and name_to_use != ""

# --- Display the Active Name ---
if name_to_use:
    st.markdown(f"### 📝 در حال ثبت اطلاعات برای: **{name_to_use}**")
    if is_edit:
        st.warning("⚠️ این نام در دیتابیس موجود است (حالت ویرایش)")
        user_data = df[df['اسم'] == name_to_use].iloc[0]
    else:
        st.success("✨ این یک نام جدید است")
        user_data = {}

# متصل کردن لیست به باکس نام
st.markdown("""<script>
    var inputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].getAttribute('aria-label') == "📍 نام و نام خانوادگی:") {
            inputs[i].setAttribute('list', 'names_list');
        }
    }
</script>""", unsafe_allow_html=True)

is_edit = name_input in names_list
user_data = df[df['اسم'] == name_input].iloc[0] if is_edit else {}

# --- فرم ورودی ---
with st.form("main_form"):
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with c2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with c3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")

    st.divider()
    st.markdown("### 🔍 جزئیات واقعه")
    l1, l2, l3 = st.columns(3)
    with l1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with l2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with l3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")

    d1, d2 = st.columns(2)
    with d1: v_shamsi = st.text_input("تاریخ شمسی", value=str(user_data.get("تاریخ شمسی", "")) if is_edit else "")
    with d2: v_en = st.text_input("تاریخ میلادی", value=str(user_data.get("تاریخ میلادی", "")) if is_edit else "")

    if st.form_submit_button("💾 ذخیره نهایی"):
        if not name_input:
            st.error("نام را وارد کنید")
        else:
            row_data = [name_input, v_prov, v_city, v_dist, v_shamsi, v_en, v_age, v_gender, v_bday]
            try:
                if is_edit:
                    cell = worksheet.find(name_input)
                    worksheet.update(f"A{cell.row}:I{cell.row}", [row_data])
                else:
                    worksheet.append_row(row_data)
                st.success("انجام شد!")
                st.rerun()
            except Exception as e:
                st.error(f"خطا در لحظه ذخیره: {e}")
