import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# تنظیمات صفحه
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

# استایل راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #2e7d32; color: white; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# اتصال امن با gspread
@st.cache_resource
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # استفاده از اطلاعاتی که در Secrets گذاشتید
    creds_info = st.secrets["gspread_creds"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

try:
    client = get_gsheet_client()
    sheet_url = st.secrets["public_gsheets_url"]
    sh = client.open_by_url(sheet_url)
    worksheet = sh.get_worksheet(0) # کاربرگ اول
    
    # خواندن داده‌ها برای لیست پیشنهادی
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    names_list = df['اسم'].dropna().unique().tolist() if not df.empty else []
except Exception as e:
    st.error(f"❌ خطا در اتصال: {e}")
    st.info("نکته: مطمئن شوید ایمیل ربات را در شیت Editor کرده‌اید.")
    st.stop()

st.title("📋 سامانه ثبت و ویرایش")

# --- بخش اصلی: باکس نام هوشمند ---
# ایجاد لیست پیشنهادات مخفی
options_html = "".join([f'<option value="{n}">' for n in names_list])
st.markdown(f'<datalist id="names_list">{options_html}</datalist>', unsafe_allow_html=True)

# باکس متن اصلی (پاک نمی‌شود)
name_input = st.text_input("📍 نام و نام خانوادگی:", placeholder="نام را وارد کنید یا از لیست انتخاب کنید...", key="name_box")

# جاوااسکریپت برای اتصال لیست به باکس
st.markdown("""
    <script>
    var inputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].getAttribute('aria-label') == "📍 نام و نام خانوادگی:") {
            inputs[i].setAttribute('list', 'names_list');
        }
    }
    </script>
    """, unsafe_allow_html=True)

# تشخیص حالت ویرایش یا جدید
is_edit = name_input in names_list
user_data = df[df['اسم'] == name_input].iloc[0] if is_edit else {}

# --- فرم ورودی اطلاعات ---
with st.form("main_form", clear_on_submit=True):
    st.markdown("### 👤 اطلاعات شخصی")
    col1, col2, col3 = st.columns(3)
    with col1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with col2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with col3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")

    st.divider()
    st.markdown("### 🔍 جزئیات واقعه")
    
    # چیدمان: استان - شهر - محله/خیابان
    l1, l2, l3 = st.columns(3)
    with l1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with l2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with l3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")
    
    d1, d2 = st.columns(2)
    with d1: v_shamsi = st.text_input("تاریخ شمسی", value=str(user_data.get("تاریخ شمسی", "")) if is_edit else "")
    with d2: v_en = st.text_input("تاریخ میلادی", value=str(user_data.get("تاریخ میلادی", "")) if is_edit else "")

    v_notes = st.text_area("توضیحات", value=str(user_data.get("توضیحات", "")) if is_edit else "")

    if st.form_submit_button("💾 ذخیره نهایی"):
        if not name_input:
            st.error("⚠️ نام الزامی است.")
        else:
            # آماده‌سازی ردیف برای ذخیره (مطابق با ستون‌های شیت شما)
            row_dict = {
                "اسم": name_input, "استان": v_prov, "شهر": v_city, "محله/خیابان": v_dist,
                "تاریخ شمسی": v_shamsi, "تاریخ میلادی": v_en, "سن": v_age, "جنسیت": v_gender,
                "تاریخ تولد": v_bday, "توضیحات": v_notes
            }
            
            try:
                if is_edit:
                    # پیدا کردن ردیف و آپدیت
                    cell = worksheet.find(name_input)
                    # فرض بر این است که ستون‌ها به ترتیب row_dict هستند
                    worksheet.update(f"A{cell.row}", [list(row_dict.values())])
                    st.success("✅ اطلاعات ویرایش شد.")
                else:
                    # افزودن ردیف جدید
                    worksheet.append_row(list(row_dict.values()))
                    st.success("✅ فرد جدید ثبت شد.")
                st.rerun()
            except Exception as ex:
                st.error(f"خطا در ذخیره: {ex}")
