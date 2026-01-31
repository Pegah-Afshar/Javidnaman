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
    .stButton button:hover { background-color: #1557b0; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def clean_str(val):
    """Basic cleaner for display and saving."""
    if val is None: return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'nat', 'null', '0', '0.0']: return ""
    return s

def format_age(val):
    """
    Forces Age to be an Integer string (e.g. '25.0' -> '25').
    """
    s = clean_str(val)
    if not s: return ""
    try:
        # Try converting to float first (handles 25.0), then int
        return str(int(float(s)))
    except:
        # If it's text (e.g. "Unknown"), return as is
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
    # Get all records
    raw_data = sheet.get_all_records(expected_headers=[])
    df = pd.DataFrame(raw_data)
    # Force everything to string
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

# ==========================================
# 🛡️ SIDEBAR: BACKUP
# ==========================================
with st.sidebar:
    st.header("💾 پشتیبان‌گیری")
    st.info("قبل از تغییرات گروهی، دانلود کنید.")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 دانلود فایل CSV (بکاپ)",
        data=csv,
        file_name=f"Backup_Javidnaman_{time.strftime('%Y-%m-%d_%H-%M')}.csv",
        mime="text/csv",
    )

# ==========================================
# MAIN SEARCH LOGIC
# ==========================================
def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# ==========================================
# APP UI
# ==========================================
c_title, c_count = st.columns([5, 1])
with c_title: st.title("📋 ")
with c_count: st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 IMPORT (Turbo + Smart Match + Integer Age)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Smart Import)"):
    uploaded_file = st.file_uploader("فایل اکسل", type=["xlsx", "xls"])
    debug_mode = st.checkbox("🐞 نمایش جزئیات", value=False)
    
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

            # 3. BUILD FINGERPRINT INDEX
            sheet_index = {}
            for idx, row in df.iterrows():
                nm = clean_str(row.get('اسم', ''))
                if nm:
                    fp = get_fingerprint(nm)
                    if fp not in sheet_index: sheet_index[fp] = []
                    sheet_index[fp].append({'idx': idx + 2, 'data': row})

            # 4. PROCESS LOOP
            rows_to_add = []
            rows_to_update = []
            log_messages = []

            for i, row in up_df.iterrows():
                u_name = clean_str(row[col_name])
                if not u_name: continue

                u_key = get_fingerprint(u_name)
                candidates = sheet_index.get(u_key, [])
                match_found = None

                # Normalize Location
                u_city = clean_str(row[col_city])
                u_prov = clean_str(row[col_prov])

                # MATCHING LOGIC
                for cand in candidates:
                    s_data = cand['data']
                    s_city = clean_str(s_data.get('شهر', ''))
                    s_prov = clean_str(s_data.get('استان', ''))
                    
                    # Ignore spaces in city/prov too
                    city_ok = (get_fingerprint(s_city) == "") or (get_fingerprint(s_city) == get_fingerprint(u_city)) or (u_city == "")
                    prov_ok = (get_fingerprint(s_prov) == "") or (get_fingerprint(s_prov) == get_fingerprint(u_prov)) or (u_prov == "")

                    if city_ok and prov_ok:
                        match_found = cand
                        break
                
                if match_found:
                    # MERGE
                    r_idx = match_found['idx']
                    s_data = match_found['data']
                    merged = []
                    do_update = False
                    
                    for h in all_headers:
                        s_val = clean_str(s_data.get(h, ""))
                        e_val = ""
                        
                        if h == 'اسم': 
                            e_val = u_name
                        elif h in up_df.columns: 
                            raw_val = row[h]
                            # 🔢 AGE FIX: Convert to Integer format if column is 'سن'
                            if h == 'سن':
                                e_val = format_age(raw_val)
                            else:
                                e_val = clean_str(raw_val)

                        # Logic: Sheet Empty & Excel Has Data -> FILL
                        if s_val == "" and e_val != "":
                            merged.append(e_val)
                            do_update = True
                        else:
                            merged.append(s_val)
                    
                    if do_update:
                        rows_to_update.append((r_idx, merged))
                        if debug_mode and len(log_messages) < 10:
                            log_messages.append(f"🔄 تکمیل: {u_name}")

                else:
                    # ADD NEW
                    new_row = []
                    for h in all_headers:
                        if h == 'اسم':
                            new_row.append(u_name)
                        elif h in up_df.columns:
                            raw_val = row[h]
                            # 🔢 AGE FIX
                            if h == 'سن':
                                new_row.append(format_age(raw_val))
                            else:
                                new_row.append(clean_str(raw_val))
                        else:
                            new_row.append("")
                    rows_to_add.append(new_row)
                    if debug_mode and len(log_messages) < 10:
                        log_messages.append(f"➕ جدید: {u_name}")

            # 5. EXECUTE (TURBO MODE)
            if debug_mode:
                st.info("Log:")
                for m in log_messages: st.text(m)

            if rows_to_add or rows_to_update:
                c_a, c_b = st.columns(2)
                c_a.warning(f"🆕 افراد جدید: {len(rows_to_add)}")
                c_b.info(f"🔄 تکمیل اطلاعات: {len(rows_to_update)}")
                
                if st.button("🚀 ذخیره نهایی (Turbo)"):
                    with st.status("در حال پردازش سریع...", expanded=True):
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        # 1. Batch Add
                        if rows_to_add:
                            sheet.append_rows(rows_to_add)
                        
                        # 2. Batch Update (API Efficient)
                        if rows_to_update:
                            batch_reqs = []
                            for r_num, r_vals in rows_to_update:
                                batch_reqs.append({
                                    'range': f"A{r_num}",
                                    'values': [r_vals]
                                })
                            sheet.batch_update(batch_reqs)
                        
                        st.success("✅ انجام شد!")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ داده‌ها یکسان هستند.")

        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# SEARCH
# ==========================================
if st.session_state.active_name is None:
    st.info("👇 نام را جستجو کنید...")
    selected_value = st_searchbox(search_names, key="search_box_main")
    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()
else:
    # EDIT FORM
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
                val = current_data.get(h, "")
                # AGE FIX on Load
                if h == 'سن': val = format_age(val)
                st.text_input(h, value=str(val), key=f"input_{h}")

    with st.form("main_form"):
        st.markdown("### اطلاعات")
        draw(GROUP_PERSONAL, 3)
        draw(GROUP_INCIDENT, 1) # Vertical
        draw(GROUP_OTHER, 2)
        
        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        rem = [h for h in form_headers if h not in used]
        if rem: draw(rem, 3)

        if st.form_submit_button("💾 ذخیره"):
            client = get_connection()
            sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
            
            row_data = []
            for h in all_headers:
                val = st.session_state.get(f"input_{h}", "")
                if h == 'اسم': row_data.append(locked_name)
                elif h == 'سن': row_data.append(format_age(val)) # Format on manual save too
                else: row_data.append(val)
            
            if is_edit_mode:
                cell = sheet.find(locked_name)
                sheet.update(range_name=f"A{cell.row}", values=[row_data])
            else:
                sheet.append_row(row_data)
            
            st.toast("ذخیره شد")
            get_data.clear()
            st.session_state.active_name = None
            time.sleep(1)
            st.rerun()
