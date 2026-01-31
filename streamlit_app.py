import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# ==========================================
# 1. CONFIGURATION & LAYOUT SETUP
# ==========================================
# ⚠️ IMPORTANT: Update these lists to match your Google Sheet Headers EXACTLY.
# If a column in your sheet is not listed here, it will appear at the bottom automatically.

GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "نام "]
GROUP_INCIDENT = ["تاریخ شهادت شمسی", "تاریخ شهادت میلادی", "استان", "شهر", "خیابان", "مکان دقیق", "نحوه شهادت", "مزار"]
GROUP_OTHER    = ["اینستاگرام توییتر", "بستگان", "توضیحات تکمیلی"]

# Numeric check (unchanged)
NUMERIC_FIELDS = ["سن", "سال تولد"]

st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide", page_icon="📋")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton button:hover { background-color: #1557b0; }
    .st-emotion-cache-16idsys p { display: none; } 
    [data-testid="stForm"] { border: 1px solid #ddd; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    
    /* Section Headers */
    .section-header { color: #1a73e8; font-size: 1.2em; font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. BACKEND CONNECTIONS
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
# 3. LOGIC & STATE
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    all_headers = df.columns.tolist()
    # "form_headers" contains all editable columns (everything except Name)
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]
except Exception as e:
    st.error("❌ خطا در دریافت اطلاعات. لطفا نام ستون‌ها در گوگل شیت را بررسی کنید.")
    st.stop()

def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

st.title("📋 سامانه مدیریت هوشمند")

# ==========================================
# SCREEN 1: SEARCH
# ==========================================
if st.session_state.active_name is None:
    st.info("👇 نام را جستجو کنید یا نام جدید بنویسید و **اینتر بزنید**")
    
    selected_value = st_searchbox(
        search_names, key="search_box_main", placeholder="نام را تایپ کنید..."
    )

    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()

# ==========================================
# SCREEN 2: ENTRY FORM (NEW LAYOUT)
# ==========================================
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    # Header
    c_info, c_btn = st.columns([6, 1])
    with c_info:
        if is_edit_mode:
            st.success(f"✏️ ویرایش: **{locked_name}**")
        else:
            st.warning(f"🆕 ثبت جدید: **{locked_name}**")
    
    with c_btn:
        if st.button("❌ انصراف"):
            for header in form_headers:
                if f"input_{header}" in st.session_state: del st.session_state[f"input_{header}"]
            if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
            st.session_state.active_name = None
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    # --- HELPER TO DRAW INPUTS ---
    def draw_inputs(headers_list, container, data_dict, inputs_dict):
        # Filter: only draw headers that actually exist in the Google Sheet
        valid_headers = [h for h in headers_list if h in form_headers]
        if not valid_headers: return
        
        cols = container.columns(3)
        for i, header in enumerate(valid_headers):
            with cols[i % 3]:
                val = data_dict.get(header, "")
                inputs_dict[header] = st.text_input(header, value=str(val), key=f"input_{header}")
                # Mark as drawn so we don't draw it again
                drawn_headers.add(header)

    # --- THE FORM ---
    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 پرونده: {locked_name}")
        
        user_inputs = {}
        drawn_headers = set() # To keep track of what we have shown

        # SECTION 1: PERSONAL INFO
        st.markdown('<div class="section-header">👤 اطلاعات فردی</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_PERSONAL, st, current_data, user_inputs)

        # SECTION 2: INCIDENT INFO
        st.markdown('<div class="section-header">📍 اطلاعات حادثه</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_INCIDENT, st, current_data, user_inputs)

        # SECTION 3: OTHER INFO
        st.markdown('<div class="section-header">🔗 سایر موارد</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_OTHER, st, current_data, user_inputs)

        # SECTION 4: UNCATEGORIZED (Safety Net)
        # Any column in Google Sheet not listed above will appear here
        remaining_headers = [h for h in form_headers if h not in drawn_headers]
        if remaining_headers:
            st.markdown("---")
            st.caption("سایر ستون‌های موجود در فایل:")
            draw_inputs(remaining_headers, st, current_data, user_inputs)

        st.markdown("---")
        
        c_sub, c_nul = st.columns([2, 5])
        with c_sub:
            submitted = st.form_submit_button("💾 ثبت نهایی")

        if submitted:
            # Validation
            validation_errors = []
            for field in NUMERIC_FIELDS:
                if field in user_inputs and user_inputs[field].strip():
                    if not user_inputs[field].strip().isdigit():
                        validation_errors.append(f"⛔ فیلد **{field}** باید عدد باشد.")
            
            if validation_errors:
                for err in validation_errors: st.error(err)
            else:
                try:
                    # Check Changes
                    changes_detected = True
                    if is_edit_mode:
                        changes_detected = False
                        for header in form_headers:
                            # We check all headers (user_inputs has everything, even if drawn in different sections)
                            if str(current_data.get(header, "")).strip() != user_inputs.get(header, "").strip():
                                changes_detected = True
                                break
                    
                    if not changes_detected:
                        st.info("ℹ️ تغییری داده نشد.")
                        time.sleep(1.5)
                        if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
                        st.session_state.active_name = None
                        st.rerun()
                    else:
                        # Save
                        with st.status("📡 در حال ذخیره...", expanded=True) as status:
                            client = get_connection()
                            sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                            
                            final_row = []
                            for header in all_headers:
                                if header == 'اسم':
                                    final_row.append(locked_name)
                                else:
                                    final_row.append(str(user_inputs.get(header, "")))
                            
                            if is_edit_mode:
                                cell = sheet.find(locked_name)
                                sheet.update(range_name=f"A{cell.row}", values=[final_row])
                            else:
                                sheet.append_row(final_row)
                            
                            get_data.clear() 
                            status.update(label="✅ انجام شد!", state="complete", expanded=False)
                        
                        st.toast("ذخیره شد", icon='🎉')
                        time.sleep(1)
                        
                        # Cleanup
                        for header in form_headers:
                            if f"input_{header}" in st.session_state: del st.session_state[f"input_{header}"]
                        if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
                        
                        st.session_state.active_name = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ خطا: {e}")
