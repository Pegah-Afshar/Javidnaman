import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# 1. Setup
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea, .stSelectbox, .stMarkdown { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# 2. Connection & Data
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=10)
def get_data():
    client = get_connection()
    # Ensure this index (0) matches your sheet tab
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records())

df = get_data()
# Get unique names, ensure they are strings
names_list = df['اسم'].dropna().astype(str).unique().tolist()

# 3. FIXED SEARCH FUNCTION
# This is the magic part. If the name is new, we add it to the list dynamically.
def search_names(search_term: str):
    # 1. Find matches in existing DB
    matches = [n for n in names_list if search_term in n]
    
    # 2. If the user typed something that isn't in the list, 
    # add it as the first option so they can "Select" their new name.
    if search_term and search_term not in matches:
        matches.insert(0, search_term)
        
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# 4. INPUT LOGIC
col_search, col_reset = st.columns([5, 1])

with col_search:
    # We use a key for session state to help it remember
    name_input = st_searchbox(
        search_names,
        placeholder="نام را جستجو کنید یا نام جدید بنویسید (و اینتر بزنید)...",
        key="name_search_box",
        clear_on_submit=False, # Important: Don't clear when they hit enter
    )

with col_reset:
    st.write("")
    st.write("")
    if st.button("❌ پاک کردن"):
        st.rerun()

# Determine Edit vs New
is_edit_mode = False
current_data = {}

if name_input:
    # Check if the name actually exists in our original database
    if name_input in names_list:
        is_edit_mode = True
        current_data = df[df['اسم'] == name_input].iloc[0].to_dict()
        st.info(f"✏️ در حال ویرایش: **{name_input}**")
    else:
        is_edit_mode = False
        st.success(f"➕ ثبت نام جدید: **{name_input}**")

# 5. THE FORM
# Only show form if a name is selected/typed
if name_input:
    with st.form("main_form"):
        st.markdown("### 👤 اطلاعات")
        
        # Use .get() to handle missing columns gracefully
        c1, c2, c3 = st.columns(3)
        with c1: v_bday = st.text_input("تاریخ تولد", value=str(current_data.get("تاریخ تولد", "")))
        with c2: v_age = st.text_input("سن", value=str(current_data.get("سن", "")))
        with c3: v_gender = st.text_input("جنسیت", value=str(current_data.get("جنسیت", "")))
        
        st.divider()
        l1, l2, l3 = st.columns(3)
        with l1: v_prov = st.text_input("استان", value=str(current_data.get("استان", "")))
        with l2: v_city = st.text_input("شهر", value=str(current_data.get("شهر", "")))
        with l3: v_dist = st.text_input("محله/خیابان", value=str(current_data.get("محله/خیابان", "")))

        submitted = st.form_submit_button("💾 ذخیره")

        if submitted:
            try:
                # Re-connect inside the button for safety
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                row_data = [name_input, v_prov, v_city, v_dist, v_age, v_gender, v_bday]
                
                if is_edit_mode:
                    # Find the row again to ensure we don't overwrite wrong line
                    cell = sheet.find(name_input)
                    sheet.update(range_name=f"A{cell.row}:G{cell.row}", values=[row_data])
                    st.toast(f"اطلاعات {name_input} بروز شد!", icon='✅')
                else:
                    # Append new row
                    sheet.append_row(row_data)
                    st.toast(f"نام {name_input} اضافه شد!", icon='✨')
                
                # Clear cache and wait a moment
                get_data.clear()
                time.sleep(2) 
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")
