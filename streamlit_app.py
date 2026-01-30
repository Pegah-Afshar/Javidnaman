import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox

# 1. Setup
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

# RTL Fix
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea, .stSelectbox { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# 2. Connection
@st.cache_resource
def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)

sheet = get_sheet()
df = pd.DataFrame(sheet.get_all_records())
names_list = df['اسم'].dropna().unique().tolist()

# 3. Search function for the box
def search_names(search_term: str):
    if not search_term:
        return names_list
    return [n for n in names_list if search_term in n]

st.title("📋 سامانه مدیریت هوشمند")

# 4. THE PERFECT BOX
# This stays put, suggests names, and accepts new ones.
name_input = st_searchbox(
    search_names,
    placeholder="نام را جستجو کنید یا نام جدید بنویسید...",
    key="name_search",
)

# Mode Check
is_edit = name_input in names_list and name_input is not None
user_data = df[df['اسم'] == name_input].iloc[0] if is_edit else {}

if name_input:
    st.info(f"📍 هدف: {name_input}")

# 5. THE FORM
with st.form("main_form"):
    st.markdown("### 👤 اطلاعات")
    c1, c2, c3 = st.columns(3)
    with c1: v_bday = st.text_input("تاریخ تولد", value=str(user_data.get("تاریخ تولد", "")) if is_edit else "")
    with c2: v_age = st.text_input("سن", value=str(user_data.get("سن", "")) if is_edit else "")
    with c3: v_gender = st.text_input("جنسیت", value=str(user_data.get("جنسیت", "")) if is_edit else "")
    
    st.divider()
    l1, l2, l3 = st.columns(3)
    with l1: v_prov = st.text_input("استان", value=str(user_data.get("استان", "")) if is_edit else "")
    with l2: v_city = st.text_input("شهر", value=str(user_data.get("شهر", "")) if is_edit else "")
    with l3: v_dist = st.text_input("محله/خیابان", value=str(user_data.get("محله/خیابان", "")) if is_edit else "")

    if st.form_submit_button("💾 ذخیره"):
        row = [name_input, v_prov, v_city, v_dist, v_age, v_gender, v_bday]
        if is_edit:
            cell = sheet.find(name_input)
            sheet.update(f"A{cell.row}:G{cell.row}", [row])
        else:
            sheet.append_row(row)
        st.success("انجام شد")
        st.rerun()
