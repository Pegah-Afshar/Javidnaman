import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# 1. Setup & RTL
st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide")
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, input, textarea, .stSelectbox, .stMarkdown { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; height: 3em; }
    /* Hide the search box label if needed */
    .st-emotion-cache-16idsys p { display: none; } 
</style>""", unsafe_allow_html=True)

# 2. Connection
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

# 3. Session State Management (The Fix)
if 'selected_name' not in st.session_state:
    st.session_state.selected_name = None

# Function to handle search logic
df = get_data()
all_headers = df.columns.tolist()
existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]

def search_names(search_term: str):
    if not search_term:
        return existing_names
    matches = [n for n in existing_names if search_term in n]
    # Always allow the new name to be selectable
    if search_term not in matches:
        matches.insert(0, search_term)
    return matches

#st.title("📋 سامانه مدیریت هوشمند")

# ==========================================
# PART A: SEARCH MODE (Only show if no name selected)
# ==========================================
if st.session_state.selected_name is None:
    st.info("👇 نام را جستجو کنید یا نام جدید بنویسید و **اینتر بزنید**")
    
    # The Search Box
    selected_value = st_searchbox(
        search_names,
        key="search_input",
        placeholder="جستجوی نام..."
    )

    # LOCK LOGIC: If user picked something, save to session and RERUN immediately
    if selected_value:
        st.session_state.selected_name = selected_value
        st.rerun()

# ==========================================
# PART B: FORM MODE (Show this when name is locked)
# ==========================================
else:
    # Get the locked name
    locked_name = st.session_state.selected_name
    
    # Check if Edit or New
    is_edit_mode = locked_name in existing_names
    
    # Fetch data if editing
    current_data = {}
    if is_edit_mode:
        current_data = df[df['اسم'] == locked_name].iloc[0].to_dict()

    # HEADER SECTION
    c1, c2 = st.columns([5, 1])
    with c1:
        if is_edit_mode:
            st.success(f"📝 در حال ویرایش: **{locked_name}**")
        else:
            st.warning(f"🆕 ثبت اطلاعات جدید برای: **{locked_name}**")
    with c2:
        # Button to Cancel/Change User
        if st.button("❌ بازگشت"):
            st.session_state.selected_name = None
            st.rerun()

    # THE FORM (Now it will never disappear!)
    with st.form("entry_form"):
        st.markdown("---")
        
        # Dynamic Columns
        valid_headers = [h for h in all_headers if h != 'اسم']
        cols = st.columns(3)
        user_inputs = {}

        for i, header in enumerate(valid_headers):
            with cols[i % 3]:
                val = current_data.get(header, "")
                user_inputs[header] = st.text_input(header, value=str(val))

        st.markdown("---")
        submitted = st.form_submit_button("💾 ذخیره نهایی")

        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                final_row = []
                for header in all_headers:
                    if header == 'اسم':
                        final_row.append(locked_name)
                    else:
                        final_row.append(user_inputs.get(header, ""))
                
                if is_edit_mode:
                    cell = sheet.find(locked_name)
                    sheet.update(range_name=f"A{cell.row}", values=[final_row])
                    st.toast("اطلاعات بروزرسانی شد", icon='🎉')
                else:
                    sheet.append_row(final_row)
                    st.toast("رکورد جدید ثبت شد", icon='✨')
                
                # Clear session and reload
                st.session_state.selected_name = None
                get_data.clear()
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"خطا: {e}")
