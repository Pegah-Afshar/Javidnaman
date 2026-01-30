import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# 1. Setup & RTL Config
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea, .stSelectbox, .stMarkdown { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# 2. Connection with Cache
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=10)
def get_data():
    client = get_connection()
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records())

# Load data
df = get_data()
# We clean the list to ensure no empty values
existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]

# 3. FIXED SEARCH FUNCTION
def search_names(search_term: str):
    # If the user hasn't typed anything, return the full list
    if not search_term:
        return existing_names

    # 1. Find matches in the existing database
    matches = [n for n in existing_names if search_term in n]
    
    # 2. CRITICAL FIX: If the exact search term is NOT in the matches, 
    # add it as the first option. This allows "Create New".
    if search_term not in matches:
        matches.insert(0, search_term)
        
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# 4. Input Logic
col_search, col_reset = st.columns([4, 1])

with col_search:
    # Key Update: We use the modified search_names function
    name_input = st_searchbox(
        search_names,
        placeholder="نام را جستجو کنید یا نام جدید بنویسید...",
        key="name_search",
        # clear_on_submit=False  # Ensure this stays False
    )

with col_reset:
    st.write("")
    st.write("")
    if st.button("❌ پاک کردن"):
        st.rerun()

# Logic to determine Mode (Edit vs New)
# We check if the input is inside the ORIGINAL list from the database
is_edit_mode = False
current_data = {}

if name_input:
    if name_input in existing_names:
        # EXISTING USER
        is_edit_mode = True
        current_data = df[df['اسم'] == name_input].iloc[0].to_dict()
        st.success(f"✅ نام **{name_input}** پیدا شد. (ویرایش)")
    else:
        # NEW USER
        is_edit_mode = False
        st.info(f"🆕 نام **{name_input}** جدید است. (ثبت جدید)")

# 5. The Form
if name_input:
    with st.form("main_form"):
        st.markdown("### 👤 اطلاعات فردی")
        
        c1, c2, c3 = st.columns(3)
        with c1: v_bday = st.text_input("تاریخ تولد", value=str(current_data.get("تاریخ تولد", "")))
        with c2: v_age = st.text_input("سن", value=str(current_data.get("سن", "")))
        with c3: v_gender = st.text_input("جنسیت", value=str(current_data.get("جنسیت", "")))
        
        st.divider()
        
        l1, l2, l3 = st.columns(3)
        with l1: v_prov = st.text_input("استان", value=str(current_data.get("استان", "")))
        with l2: v_city = st.text_input("شهر", value=str(current_data.get("شهر", "")))
        with l3: v_dist = st.text_input("محله/خیابان", value=str(current_data.get("محله/خیابان", "")))

        submitted = st.form_submit_button("💾 ذخیره اطلاعات")
        
        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                row_data = [name_input, v_prov, v_city, v_dist, v_age, v_gender, v_bday]
                
                if is_edit_mode:
                    cell = sheet.find(name_input)
                    sheet.update(range_name=f"A{cell.row}:G{cell.row}", values=[row_data])
                    st.toast("ویرایش شد!", icon='🎉')
                else:
                    sheet.append_row(row_data)
                    st.toast("ذخیره شد!", icon='✨')
                
                get_data.clear()
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
