import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox

# 1. Setup & RTL Config
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea, .stSelectbox, .stMarkdown { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# 2. Connection with Cache (CRITICAL FOR MULTI-USER)
# cache_resource is for the connection object (connect once)
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

# cache_data with ttl=10 ensures users see new names added by others within 10 seconds
@st.cache_data(ttl=10)
def get_data():
    client = get_connection()
    # Replace with your actual Sheet Name inside the spreadsheet if not "Sheet1"
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Load data
df = get_data()
names_list = df['اسم'].dropna().unique().tolist()

# 3. Search Function
def search_names(search_term: str):
    if not search_term:
        return [] # Return empty if nothing typed to keep UI clean
    # Simple case-insensitive search
    return [n for n in names_list if search_term in n]

st.title("📋 سامانه مدیریت هوشمند")

# 4. Input Logic
col_search, col_reset = st.columns([4, 1])

with col_search:
    # This box suggests names. If clicked, it returns the full name.
    # If typed new, it returns the new string.
    name_input = st_searchbox(
        search_names,
        placeholder="نام را جستجو کنید یا نام جدید بنویسید...",
        key="name_search",
    )

# Logic to determine if we are Editing or Creating
is_edit_mode = False
current_data = {}

if name_input:
    if name_input in names_list:
        # EXISTING USER -> EDIT MODE
        is_edit_mode = True
        current_data = df[df['اسم'] == name_input].iloc[0].to_dict()
        st.success(f"✅ نام **{name_input}** پیدا شد. در حال ویرایش اطلاعات...")
    else:
        # NEW USER -> CREATE MODE
        is_edit_mode = False
        st.warning(f"🆕 نام **{name_input}** جدید است. لطفاً فرم را پر کنید.")

with col_reset:
    # A button to clear everything if the user sees the name and wants to stop
    st.write("") # Spacer
    st.write("") # Spacer
    if st.button("❌ پاک کردن"):
        st.rerun()

# 5. The Form
# We only show the form if a name has been entered/selected
if name_input:
    with st.form("main_form"):
        st.markdown("### 👤 اطلاعات فردی")
        
        # We use .get() to avoid errors if columns are missing
        c1, c2, c3 = st.columns(3)
        with c1: 
            v_bday = st.text_input("تاریخ تولد", value=str(current_data.get("تاریخ تولد", "")))
        with c2: 
            v_age = st.text_input("سن", value=str(current_data.get("سن", "")))
        with c3: 
            v_gender = st.text_input("جنسیت", value=str(current_data.get("جنسیت", "")))
        
        st.divider()
        
        l1, l2, l3 = st.columns(3)
        with l1: 
            v_prov = st.text_input("استان", value=str(current_data.get("استان", "")))
        with l2: 
            v_city = st.text_input("شهر", value=str(current_data.get("شهر", "")))
        with l3: 
            v_dist = st.text_input("محله/خیابان", value=str(current_data.get("محله/خیابان", "")))

        # Submit Logic
        submitted = st.form_submit_button("💾 ذخیره اطلاعات")
        
        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                # Prepare the row data
                # Ensure the order matches your Google Sheet headers exactly!
                row_data = [name_input, v_prov, v_city, v_dist, v_age, v_gender, v_bday]
                
                if is_edit_mode:
                    # Find the cell again right now to be safe (concurrency safety)
                    cell = sheet.find(name_input)
                    # Update that specific row
                    # Assuming columns A to G. Adjust range if you have more columns.
                    sheet.update(range_name=f"A{cell.row}:G{cell.row}", values=[row_data])
                    st.toast("اطلاعات با موفقیت بروزرسانی شد!", icon='🎉')
                else:
                    # Append new row
                    sheet.append_row(row_data)
                    st.toast("نام جدید با موفقیت ثبت شد!", icon='✨')
                
                # Clear cache so the new name appears immediately for everyone
                get_data.clear()
                
                # Wait 2 seconds then reload
                import time
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"خطا در ارتباط با گوگل شیت: {e}")
