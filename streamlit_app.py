import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
# ✅ CHANGE: No fields are forced anymore. You can save empty records.
REQUIRED_FIELDS = [] 

# We keep this just to ensure 'Age' is a number IF typed. 
# If left empty, it will be ignored (which is what you want).
NUMERIC_FIELDS = ["سن", "سال تولد"]

st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide", page_icon="📋")

# CSS Styles
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton button:hover { background-color: #1557b0; }
    .st-emotion-cache-16idsys p { display: none; } 
    [data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. BACKEND CONNECTION
# ==========================================
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
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def validate_inputs(inputs):
    """Checks data validity. Allows empty fields now."""
    errors = []
    
    # We removed the loop for REQUIRED_FIELDS so nothing is mandatory.
            
    # Check Numeric Fields ONLY IF value is provided
    for field in NUMERIC_FIELDS:
        # We check "if inputs[field].strip()" -> This means "If the user actually typed something"
        if field in inputs and inputs[field].strip():
            if not inputs[field].strip().isdigit():
                errors.append(f"⛔ فیلد **{field}** باید فقط عدد باشد (در صورت وارد کردن).")
    
    return errors

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

# Load Data
try:
    df = get_data()
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]
except Exception as e:
    st.error("خطا در بارگذاری داده‌ها.")
    st.stop()

def search_names(search_term: str):
    if not search_term:
        return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches:
        matches.insert(0, search_term)
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# ------------------------------------------
# SCREEN 1: SEARCH MODE
# ------------------------------------------
if st.session_state.active_name is None:
    st.info("👇 نام را جستجو کنید یا نام جدید بنویسید")
    
    selected_value = st_searchbox(
        search_names,
        key="search_box_main",
        placeholder="نام شخص را اینجا بنویسید..."
    )

    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()

# ------------------------------------------
# SCREEN 2: ENTRY FORM MODE
# ------------------------------------------
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    # Top Bar
    c_info, c_btn = st.columns([6, 1])
    with c_info:
        if is_edit_mode:
            st.success(f"✏️ در حال ویرایش پرونده: **{locked_name}**")
        else:
            st.warning(f"🆕 ایجاد پرونده جدید: **{locked_name}**")
    
    with c_btn:
        if st.button("❌ انصراف"):
            # Cleanup
            for header in form_headers:
                key = f"input_{header}"
                if key in st.session_state: del st.session_state[key]
            if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
            
            st.session_state.active_name = None
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 اطلاعات پرونده: {locked_name}")
        st.markdown("---")
        
        cols = st.columns(3) 
        user_inputs = {}

        for i, header in enumerate(form_headers):
            with cols[i % 3]:
                val = current_data.get(header, "")
                # No "*" asterisk anymore since nothing is required
                user_inputs[header] = st.text_input(header, value=str(val), key=f"input_{header}")

        st.markdown("---")
        
        c_submit, c_space = st.columns([2, 5])
        with c_submit:
            submitted = st.form_submit_button("💾 ثبت و ذخیره نهایی")

        if submitted:
            # 1. Validation (Now very lenient)
            validation_errors = validate_inputs(user_inputs)
            
            if validation_errors:
                for err in validation_errors:
                    st.error(err)
            else:
                try:
                    # Check for changes
                    changes_detected = True
                    if is_edit_mode:
                        changes_detected = False
                        for header in form_headers:
                            if str(current_data.get(header, "")).strip() != user_inputs.get(header, "").strip():
                                changes_detected = True
                                break
                    
                    if not changes_detected:
                        st.info("ℹ️ تغییری اعمال نشده است.")
                        time.sleep(1.5)
                        if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
                        st.session_state.active_name = None
                        st.rerun()
                    else:
                        with st.status("📡 در حال ارسال به سرور...", expanded=True) as status:
                            client = get_connection()
                            sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                            
                            final_row = []
                            for header in all_headers:
                                if header == 'اسم':
                                    final_row.append(locked_name)
                                else:
                                    final_row.append(str(user_inputs.get(header, "")))
                            
                            status.write("✍️ ثبت در پایگاه داده...")
                            
                            if is_edit_mode:
                                cell = sheet.find(locked_name)
                                sheet.update(range_name=f"A{cell.row}", values=[final_row])
                            else:
                                sheet.append_row(final_row)
                            
                            get_data.clear() 
                            status.update(label="✅ عملیات موفقیت‌آمیز بود!", state="complete", expanded=False)
                        
                        st.toast("پرونده ذخیره شد", icon='🎉')
                        
                        time.sleep(1)
                        
                        for header in form_headers:
                            if f"input_{header}" in st.session_state: del st.session_state[f"input_{header}"]
                        if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
                        
                        st.session_state.active_name = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ خطای سیستمی: {e}")
