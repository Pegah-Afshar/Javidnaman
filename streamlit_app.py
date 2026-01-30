import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Setup & RTL
st.set_page_config(page_title="مدیریت داده‌ها", layout="wide")
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #2e7d32; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# 2. Stable Connection via gspread
def get_data():
    # Ensure your Secrets has "gspread_creds" and "spreadsheet_url"
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    data = sheet.get_all_records()
    return sheet, pd.DataFrame(data)

try:
    sheet_obj, df = get_data()
    names_list = df['اسم'].dropna().unique().tolist()
except Exception as e:
    st.error(f"خطا در اتصال: {e}")
    st.stop()

# 3. THE SINGLE NAME BOX (Combobox Behavior)
st.title("📋 پنل ثبت و ویرایش")

# HTML for Suggestions
options_html = "".join([f'<option value="{n}">' for n in names_list])
st.markdown(f'<datalist id="names_list">{options_html}</datalist>', unsafe_allow_html=True)

# THE BOX: One box that stays when you click away
name_input = st.text_input("📍 نام و نام خانوادگی:", placeholder="تایپ کنید...", key="name_box")

# JavaScript to link Suggestions
st.markdown("""<script>
    var inputs = window.parent.document.querySelectorAll('input[type="text"]');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].getAttribute('aria-label') == "📍 نام و نام خانوادگی:") {
            inputs[i].setAttribute('list', 'names_list');
        }
    }
</script>""", unsafe_allow_html=True)

# Mode Detection
is_edit = name_input in names_list
user_data = df[df['اسم'] == name_input].iloc[0] if is_edit else {}

# 4. THE FORM
with st.form("main_form", clear_on_submit=True):
    st.markdown("### 👤 اطلاعات شخصی")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with c2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with c3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")
    
    st.divider()
    st.markdown("### 🔍 جزئیات واقعه")
    
    # Layout: Province - City - District/Street
    l1, l2, l3 = st.columns(3)
    with l1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with l2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with l3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")
    
    # Dates
    d1, d2 = st.columns(2)
    with d1: v_shamsi = st.text_input("تاریخ شمسی", value=str(user_data.get("تاریخ شمسی", "")) if is_edit else "")
    with d2: v_en = st.text_input("تاریخ میلادی", value=str(user_data.get("تاریخ میلادی", "")) if is_edit else "")

    if st.form_submit_button("💾 ذخیره نهایی"):
        new_row = [name_input, v_prov, v_city, v_dist, v_shamsi, v_en, v_age, v_gender, v_bday] # Add other fields as per your sheet columns
        if is_edit:
            cell = sheet_obj.find(name_input)
            sheet_obj.update(range_name=f"A{cell.row}:I{cell.row}", values=[new_row])
        else:
            sheet_obj.append_row(new_row)
        st.success("ذخیره شد!")
        st.rerun()
