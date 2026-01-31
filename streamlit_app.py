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

# 2. Connection
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=5) # Short cache for multi-user updates
def get_data():
    client = get_connection()
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records())

# 3. Initialize Session State
# This acts as our "Temporary Memory" while you are typing
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

# 4. Search Function
df = get_data()
all_headers = df.columns.tolist()
# Filter out empty headers and 'اسم'
form_headers = [h for h in all_headers if h and h != 'اسم']
existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]

def search_names(search_term: str):
    if not search_term:
        return existing_names
    matches = [n for n in existing_names if search_term in n]
    # CRITICAL: Always offer the search term itself as an option (for new names)
    if search_term not in matches:
        matches.insert(0, search_term)
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# ==========================================
# SEARCH SECTION
# ==========================================
st.info("👇 نام را انتخاب کنید (یا نام جدید بنویسید و روی آن کلیک کنید)")

# We use a callback logic here. 
# If the search box output differs from our 'active_name', we know the user switched people.
selected_search = st_searchbox(
    search_names,
    key="sb_search",
    placeholder="جستجو یا ثبت نام جدید..."
)

# 5. STATE MANAGER (The Magic Fix)
# This block runs every time something changes.
# It checks: "Did the user pick a NEW person in the search box?"
if selected_search and selected_search != st.session_state.active_name:
    
    # 1. Update the Active Name
    st.session_state.active_name = selected_search
    
    # 2. Fetch Data from DB (if exists)
    if selected_search in existing_names:
        user_row = df[df['اسم'] == selected_search].iloc[0].to_dict()
        is_new = False
    else:
        user_row = {}
        is_new = True
        
    # 3. Load Data into Form Keys
    # We manually set the value of every input box in session_state
    for header in form_headers:
        key_name = f"field_{header}"
        st.session_state[key_name] = str(user_row.get(header, ""))
    
    # 4. Rerun to refresh the form with new data
    st.rerun()

# If user clears the box, we clear the form
if not selected_search and st.session_state.active_name:
    st.session_state.active_name = None
    st.rerun()

# ==========================================
# FORM SECTION
# ==========================================
# Only show form if we have an active name locked in memory
if st.session_state.active_name:
    
    # Determine Mode for UI
    is_edit = st.session_state.active_name in existing_names
    
    if is_edit:
        st.success(f"✏️ در حال ویرایش: **{st.session_state.active_name}**")
    else:
        st.warning(f"🆕 در حال ثبت نام جدید: **{st.session_state.active_name}**")

    with st.form("entry_form"):
        # Dynamic Columns
        cols = st.columns(3)
        
        # We generate input boxes that are TIED to session_state keys
        for i, header in enumerate(form_headers):
            key_name = f"field_{header}"
            
            # Ensure key exists (safety check)
            if key_name not in st.session_state:
                st.session_state[key_name] = ""
                
            with cols[i % 3]:
                # Notice: We do NOT use 'value='. We use 'key='.
                # Streamlit automatically fills the box from st.session_state[key_name]
                st.text_input(header, key=key_name)

        st.markdown("---")
        submitted = st.form_submit_button("💾 ذخیره تغییرات")

        if submitted:
            try:
                client = get_connection()
                sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                
                # Collect data from Session State
                final_row = []
                for header in all_headers:
                    if header == 'اسم':
                        final_row.append(st.session_state.active_name)
                    else:
                        # Grab the value the user just typed into the box
                        final_row.append(st.session_state.get(f"field_{header}", ""))
                
                if is_edit:
                    cell = sheet.find(st.session_state.active_name)
                    sheet.update(range_name=f"A{cell.row}", values=[final_row])
                    st.toast("✅ بروزرسانی موفقیت‌آمیز بود", icon='🎉')
                else:
                    sheet.append_row(final_row)
                    st.toast("✅ ثبت نام جدید انجام شد", icon='✨')
                
                # Clear cache to see update immediately
                get_data.clear()
                
                # Optional: Clear form after save? 
                # Uncomment next 2 lines if you want to reset after save
                # st.session_state.active_name = None
                # st.rerun() 
                
            except Exception as e:
                st.error(f"خطا در ذخیره‌سازی: {e}")

elif selected_search:
    # Fallback if state lag happens (rare)
    st.spinner("در حال بارگذاری...")
