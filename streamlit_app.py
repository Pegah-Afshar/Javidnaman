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
    /* Hide the search box label */
    .st-emotion-cache-16idsys p { display: none; } 
</style>""", unsafe_allow_html=True)

# 2. Connection
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=5) 
def get_data():
    client = get_connection()
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records())

# 3. Session State Init
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

# Load Data
df = get_data()
all_headers = df.columns.tolist()
# Get headers for the form (everything except 'اسم')
form_headers = [h for h in all_headers if h and h != 'اسم']
existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]

# Search Function
def search_names(search_term: str):
    if not search_term:
        return existing_names
    matches = [n for n in existing_names if search_term in n]
    # IMPORTANT: Ensure the typed name is always the first option
    if search_term not in matches:
        matches.insert(0, search_term)
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# ==========================================
# LOGIC SPLIT
# ==========================================

# SCREEN 1: SEARCH (Only shows if NO name is currently selected)
if st.session_state.active_name is None:
    st.info("👇 نام را جستجو کنید یا نام جدید بنویسید و **روی آن کلیک کنید**")
    
    selected_value = st_searchbox(
        search_names,
        key="search_box_main",
        placeholder="نام مورد نظر را تایپ کنید..."
    )

    # If user picks a name (New or Old), Lock it and Rerun
    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()

# SCREEN 2: FORM (Only shows if a name IS selected)
else:
    # 1. Get the locked name
    locked_name = st.session_state.active_name
    
    # 2. Check if it's Edit or New
    is_edit_mode = locked_name in existing_names
    
    # 3. Header & Back Button
    c_info, c_btn = st.columns([5, 1])
    with c_info:
        if is_edit_mode:
            st.success(f"✏️ ویرایش اطلاعات: **{locked_name}**")
        else:
            st.warning(f"🆕 ثبت فرد جدید: **{locked_name}**")
    
    with c_btn:
        # This button clears the state and goes back to Screen 1
        if st.button("❌ تغییر نام"):
            st.session_state.active_name = None
            st.rerun()

    # 4. Prepare Data for Inputs
    # If editing, get row data. If new, get empty dict.
    if is_edit_mode:
        current_data = df[df['اسم'] == locked_name].iloc[0].to_dict()
    else:
        current_data = {}

    # 5. The Form
    with st.form("entry_form"):
        st.markdown("---")
        
        cols = st.columns(3)
        user_inputs = {}

        # Dynamically create boxes
        for i, header in enumerate(form_headers):
            with cols[i % 3]:
                # We fetch the existing value (or empty string)
                val = current_data.get(header, "")
                # We use a unique key for every input to prevent conflicts
                user_inputs[header] = st.text_input(header, value=str(val), key=f"input_{header}")

        st.markdown("---")
        submitted = st.form_submit_button("💾 ذخیره نهایی")

        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                # Build Row in exact order
                final_row = []
                for header in all_headers:
                    if header == 'اسم':
                        final_row.append(locked_name)
                    else:
                        final_row.append(user_inputs.get(header, ""))
                
                if is_edit_mode:
                    cell = sheet.find(locked_name)
                    sheet.update(range_name=f"A{cell.row}", values=[final_row])
                    st.toast("✅ بروزرسانی انجام شد", icon='🎉')
                else:
                    sheet.append_row(final_row)
                    st.toast("✅ نام جدید اضافه شد", icon='✨')
                
                # Success Logic: Clear name and go back to search
                st.session_state.active_name = None
                get_data.clear() # Clear cache
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"خطا: {e}")
