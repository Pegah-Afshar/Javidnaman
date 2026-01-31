import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# 1. Setup & RTL Config
#st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")

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
    # Ensure we get all values, even empty strings to preserve structure
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records())

# Load data and get Headers dynamically
df = get_data()
all_headers = df.columns.tolist() # This grabs ["اسم", "سن", "شهر" ...] from your sheet

# Clean up name list
existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]

# 3. Search Function (Keeps your new names visible)
def search_names(search_term: str):
    if not search_term:
        return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches:
        matches.insert(0, search_term) # Add new name to top of list
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# 4. Input Logic
col_search, col_reset = st.columns([4, 1])

with col_search:
    name_input = st_searchbox(
        search_names,
        placeholder="نام را جستجو کنید یا نام جدید بنویسید...",
        key="name_search",
    )

with col_reset:
    st.write("")
    st.write("")
    if st.button("❌ پاک کردن"):
        st.rerun()

# 5. Logic: Check if Edit or New
is_edit_mode = False
current_data = {}

if name_input:
    # IMPORTANT: User must select the name from dropdown for this to trigger
    if name_input in existing_names:
        is_edit_mode = True
        # Get the row matching the name
        current_data = df[df['اسم'] == name_input].iloc[0].to_dict()
        st.success(f"✅ ویرایش اطلاعات: {name_input}")
    else:
        st.info(f"🆕 ثبت فرد جدید: {name_input}")

# 6. DYNAMIC FORM GENERATION
# This part automatically creates boxes for whatever columns are in your Google Sheet
if name_input:
    with st.form("main_form"):
        st.markdown("### 📝 ورود اطلاعات")
        
        # We create a dictionary to store the user's inputs
        user_inputs = {}
        
        # Create 3 visual columns for layout
        cols = st.columns(3)
        
        # Loop through every header in your Google Sheet
        # valid_headers skips 'اسم' because we already have that from the searchbox
        valid_headers = [h for h in all_headers if h != 'اسم']
        
        for i, header in enumerate(valid_headers):
            # Pick a column (0, 1, or 2)
            with cols[i % 3]:
                # If editing, grab the existing value. If new, use empty string.
                val = current_data.get(header, "")
                # Create the input box
                user_inputs[header] = st.text_input(header, value=str(val))

        st.divider()
        submitted = st.form_submit_button("💾 ذخیره و ثبت")
        
        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                # Build the row to save in the EXACT order of your Google Sheet columns
                final_row = []
                for header in all_headers:
                    if header == 'اسم':
                        final_row.append(name_input)
                    else:
                        final_row.append(user_inputs.get(header, ""))
                
                if is_edit_mode:
                    cell = sheet.find(name_input)
                    # Convert row number to range (e.g., A5:G5)
                    # We calculate the end column letter based on length of headers
                    sheet.update(range_name=f"A{cell.row}", values=[final_row])
                    st.toast("✅ اطلاعات بروزرسانی شد", icon='🎉')
                else:
                    sheet.append_row(final_row)
                    st.toast("✅ فرد جدید اضافه شد", icon='✨')
                
                # Refresh data
                get_data.clear()
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"خطا: {e}")
