import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title=" جاویدنامان", layout="wide", page_icon="📋")

GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "اسم"]
GROUP_INCIDENT = ["تاریخ شمسی", "تاریخ میلادی", "استان", "شهر", "محله خیابان", "محل دقیق کشته شدن", "طریقه‌ی کشته شدن", "آرامگاه"]
GROUP_OTHER = ["اکانت در شبکه‌های اجتماعی", "بستگان", "توضیحات"]
NUMERIC_FIELDS = ["سن"]

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast, .stExpander, .stMetric, .stAlert { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; transition: 0.3s; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def clean_str(val):
    """Basic cleaner for display and saving (keeps spaces, but removes junk)"""
    if val is None: return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'nat', 'null', '0', '0.0']: return ""
    return s

def get_fingerprint(text):
    """
    SUPER CLEANER for MATCHING only.
    Removes ALL spaces, Half-spaces (ZWNJ), and normalizes Ye/Kaf.
    """
    if not text: return ""
    t = str(text).strip()
    # 1. Normalize Characters
    t = t.replace("ي", "ی").replace("ك", "ک")
    # 2. Remove ALL types of spaces (Regular, Half-space, Tab)
    t = t.replace(" ", "").replace("\u200c", "").replace("\t", "")
    return t

# ==========================================
# 3. BACKEND
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
    raw_data = sheet.get_all_records(expected_headers=[])
    df = pd.DataFrame(raw_data)
    df = df.astype(str)
    return df

# ==========================================
# 4. LOAD & PREPARE
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    # Clean Headers
    df.columns = [clean_str(c) for c in df.columns]
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [clean_str(x) for x in df['اسم'].tolist() if clean_str(x) != ""]
except Exception as e:
    st.error(f"❌ خطا: {e}")
    st.stop()

def search_names(search_term: str):
    if not search_term: return existing_names
    # Simple search for the dropdown (keeps spaces for readability)
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# ==========================================
# APP UI
# ==========================================
c_title, c_count = st.columns([5, 1])
with c_title: st.title("📋 سامانه مدیریت هوشمند")
with c_count: st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 IMPORT (WITH FINGERPRINT MATCHING)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Smart Farsi Matching)"):
    uploaded_file = st.file_uploader("فایل اکسل", type=["xlsx", "xls"])
    debug_mode = st.checkbox("🐞 نمایش جزئیات دیباگ", value=False)
    
    if uploaded_file:
        try:
            # 1. READ EXCEL
            up_df = pd.read_excel(uploaded_file, dtype=str)
            up_df = up_df.fillna("").astype(str)
            up_df.columns = [clean_str(c) for c in up_df.columns]

            # 2. MAP COLUMNS
            def find_col(cols, key):
                for c in cols:
                    if key in c or (key == 'name' and 'اسم' in c): return c
                return cols[0]
            
            c1, c2, c3 = st.columns(3)
            col_name = c1.selectbox("ستون 'نام':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'اسم')))
            col_city = c2.selectbox("ستون 'شهر':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'شهر')))
            col_prov = c3.selectbox("ستون 'استان':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'استان')))

            # 3. BUILD INDEX USING FINGERPRINTS
            # Key = Crushed Name (no spaces), Value = List of {idx, data}
            sheet_index = {}
            for idx, row in df.iterrows():
                nm = clean_str(row.get('اسم', ''))
                if nm:
                    # ✨ MAGIC HERE: Create Fingerprint Key
                    fingerprint = get_fingerprint(nm)
                    if fingerprint not in sheet_index: sheet_index[fingerprint] = []
                    sheet_index[fingerprint].append({'idx': idx + 2, 'data': row})

            # 4. RUN COMPARISON
            rows_to_add = []
            rows_to_update = []
            log_messages = []

            for i, row in up_df.iterrows():
                u_name = clean_str(row[col_name])
                if not u_name: continue

                # ✨ MAGIC HERE: Search using Fingerprint
                u_key = get_fingerprint(u_name)
                
                candidates = sheet_index.get(u_key, [])
                match_found = None

                # Normalize Excel Location for comparison
                u_city = clean_str(row[col_city])
                u_prov = clean_str(row[col_prov])

                # Find Compatible Match
                for cand in candidates:
                    s_data = cand['data']
                    s_city = clean_str(s_data.get('شهر', ''))
                    s_prov = clean_str(s_data.get('استان', ''))
                    
                    # We also fingerprint cities/provs to ignore spaces there too!
                    city_ok = (get_fingerprint(s_city) == "") or (get_fingerprint(s_city) == get_fingerprint(u_city)) or (u_city == "")
                    prov_ok = (get_fingerprint(s_prov) == "") or (get_fingerprint(s_prov) == get_fingerprint(u_prov)) or (u_prov == "")

                    if city_ok and prov_ok:
                        match_found = cand
                        break
                
                if match_found:
                    # CHECK FOR MERGE
                    r_idx = match_found['idx']
                    s_data = match_found['data']
                    merged = []
                    do_update = False
                    debug_info = []

                    for h in all_headers:
                        s_val = clean_str(s_data.get(h, ""))
                        
                        e_val = ""
                        if h == 'اسم': e_val = u_name # Use the Excel name formatting if needed, or keep original? Usually keep original is safer, but user might want fixes.
                        elif h in up_df.columns: e_val = clean_str(row[h])

                        # UPDATE ONLY IF SHEET EMPTY & EXCEL HAS DATA
                        if s_val == "" and e_val != "":
                            merged.append(e_val)
                            do_update = True
                            if debug_mode and len(log_messages) < 10:
                                debug_info.append(f"{h}: {e_val}")
                        else:
                            merged.append(s_val)
                    
                    if do_update:
                        rows_to_update.append((r_idx, merged))
                        if debug_mode and len(log_messages) < 10:
                            log_messages.append(f"🔄 (تطبیق فضا) '{u_name}': {', '.join(debug_info)}")

                else:
                    # ADD NEW
                    new_row = []
                    for h in all_headers:
                        if h == 'اسم': new_row.append(u_name)
                        elif h in up_df.columns: new_row.append(clean_str(row[h]))
                        else: new_row.append("")
                    rows_to_add.append(new_row)
                    if debug_mode and len(log_messages) < 10:
                        log_messages.append(f"➕ جدید: '{u_name}'")

            # 5. EXECUTE
            if debug_mode:
                st.info("🐞 گزارش دیباگ:")
                for msg in log_messages: st.text(msg)

            if rows_to_add or rows_to_update:
                c_a, c_b = st.columns(2)
                c_a.warning(f"🆕 افراد جدید: {len(rows_to_add)}")
                c_b.info(f"🔄 تکمیل اطلاعات: {len(rows_to_update)}")
                
                if st.button("🚀 ذخیره نهایی"):
                    with st.status("در حال کار...", expanded=True):
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_add:
                            sheet.append_rows(rows_to_add)
                        if rows_to_update:
                            for r, vals in rows_to_update:
                                sheet.update(range_name=f"A{r}", values=[vals])
                                time.sleep(0.3)
                        
                        st.success("تمام شد!")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ داده‌ها یکسان هستند.")

        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# SEARCH & FORM
# ==========================================
if st.session_state.active_name is None:
    st.info("👇 نام را جستجو کنید...")
    selected_value = st_searchbox(search_names, key="search_box_main")
    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    col1, col2 = st.columns([6,1])
    with col1:
        if is_edit_mode: st.success(f"✏️ ویرایش: {locked_name}")
        else: st.warning(f"🆕 جدید: {locked_name}")
    with col2:
        if st.button("❌ بستن"):
            st.session_state.active_name = None
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    def draw(headers, cols=3):
        valid = [h for h in headers if h in form_headers]
        if not valid: return
        cc = st.columns(cols)
        for i, h in enumerate(valid):
            with cc[i%cols]:
                st.text_input(h, value=str(current_data.get(h, "")), key=f"input_{h}")

    with st.form("main_form"):
        st.markdown("### اطلاعات")
        draw(GROUP_PERSONAL, 3)
        draw(GROUP_INCIDENT, 1)
        draw(GROUP_OTHER, 2)
        
        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        rem = [h for h in form_headers if h not in used]
        if rem: draw(rem, 3)

        if st.form_submit_button("💾 ذخیره"):
            client = get_connection()
            sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
            
            row_data = []
            for h in all_headers:
                if h == 'اسم': row_data.append(locked_name)
                else: row_data.append(st.session_state.get(f"input_{h}", ""))
            
            if is_edit_mode:
                cell = sheet.find(locked_name)
                sheet.update(range_name=f"A{cell.row}", values=[row_data])
            else:
                sheet.append_row(row_data)
            
            st.toast("انجام شد")
            get_data.clear()
            st.session_state.active_name = None
            time.sleep(1)
            st.rerun()
