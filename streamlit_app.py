import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
REQUIRED_FIELDS = [] 
NUMERIC_FIELDS = ["سن", "سال تولد"]

st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide", page_icon="📋")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton button:hover { background-color: #1557b0; }
    [data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    /* Highlight the similarity warning */
    .similar-names-box { background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; margin-bottom: 10px; color: #856404; }
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

def validate_inputs(inputs):
    errors = []
    for field in NUMERIC_FIELDS:
        if field in inputs and inputs[field].strip():
            if not inputs[field].strip().isdigit():
                errors.append(f"⛔ فیلد **{field}** باید فقط عدد باشد.")
    return errors

# ==========================================
# 3. MAIN APP LOGIC
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]
except Exception as e:
    st.error("خطا در بارگذاری داده‌ها.")
    st.stop()

st.title("📋 سامانه مدیریت هوشمند")

# ------------------------------------------
# SCREEN 1: SPEED ENTRY (TEXT INPUT)
# ------------------------------------------
if st.session_state.active_name is None:
    st.info("👇 نام را بنویسید و **اینتر (Enter)** بزنید. (نیازی به کلیک نیست)")
    
    # Replaced SearchBox with standard TextInput for speed
    name_input = st.text_input("نام شخص:", key="name_entry_box", placeholder="مثال: علی رضایی")

    if name_input:
        # Immediately Lock and Rerun when Enter is pressed
        st.session_state.active_name = name_input
        st.rerun()

# ------------------------------------------
# SCREEN 2: FORM MODE
# ------------------------------------------
else:
    locked_name = st.session_state.active_name
    
    # 1. Check if Exact Match Exists
    is_edit_mode = locked_name in existing_names
    
    # 2. Check for SIMILAR names (Partial Match)
    # This helps prevents duplicates like "Ali" vs "Ali Reza"
    similar_names = [n for n in existing_names if locked_name in n and locked_name != n]

    # Top Bar
    c_info, c_btn = st.columns([6, 1])
    with c_info:
        if is_edit_mode:
            st.success(f"✏️ در حال ویرایش پرونده: **{locked_name}**")
        else:
            st.warning(f"🆕 ایجاد پرونده جدید: **{locked_name}**")
    
    with c_btn:
        if st.button("❌ برگشت"):
            # Cleanup
            for header in form_headers:
                if f"input_{header}" in st.session_state: del st.session_state[f"input_{header}"]
            st.session_state.active_name = None
            st.rerun()

    # ⚠️ SIMILARITY WARNING SYSTEM
    # If we are creating a new person, but similar names exist, warn the user!
    if not is_edit_mode and similar_names:
        with st.expander(f"⚠️ توجه: {len(similar_names)} نام مشابه پیدا شد! (کلیک برای مشاهده)", expanded=True):
            st.markdown(f"آیا منظور شما یکی از افراد زیر بود؟")
            st.write(", ".join([f"**{n}**" for n in similar_names]))
            st.markdown("---")
            st.caption("اگر نام مورد نظر شما در لیست بالا نیست، فرم زیر را پر کنید.")

    # Load Data (if Edit) or Empty (if New)
    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    # The Form
    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 اطلاعات پرونده: {locked_name}")
        st.markdown("---")
        
        cols = st.columns(3) 
        user_inputs = {}

        for i, header in enumerate(form_headers):
            with cols[i % 3]:
                val = current_data.get(header, "")
                user_inputs[header] = st.text_input(header, value=str(val), key=f"input_{header}")

        st.markdown("---")
        
        c_submit, c_space = st.columns([2, 5])
        with c_submit:
            # We use on_click callback to handle the save logic cleanly
            submitted = st.form_submit_button("💾 ثبت و ذخیره نهایی")

        if submitted:
            validation_errors = validate_inputs(user_inputs)
            
            if validation_errors:
                for err in validation_errors:
                    st.error(err)
            else:
                try:
                    changes_detected = True
                    if is_edit_mode:
                        changes_detected = False
                        for header in form_headers:
                            if str(
