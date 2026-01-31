import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time
import numpy as np

# ==========================================
# 1. MOBILE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="مدیریت جاویدنامان", 
    layout="wide", 
    page_icon="📋",
    initial_sidebar_state="collapsed" # Keeps sidebar closed on mobile to save space
)

# Groups
GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "اسم"]
GROUP_INCIDENT = ["تاریخ شمسی", "تاریخ میلادی", "استان", "شهر", "محله خیابان", "محل دقیق کشته شدن", "طریقه‌ی کشته شدن", "آرامگاه"]
GROUP_OTHER = ["اکانت در شبکه‌های اجتماعی", "بستگان", "توضیحات"]
NUMERIC_FIELDS = ["سن"]

# 🎨 MOBILE CSS OPTIMIZATION
st.markdown("""<style>
    /* Global Font & Direction */
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    
    /* Input Labels Alignment */
    .stTextInput label, .stSelectbox label { direction: rtl; text-align: right; font-size: 0.9rem; }
    
    /* Reduce Padding on Mobile */
    .block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; }
    
    /* Make buttons full width on mobile */
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    
    /* Hide the 'Deploy' button and header decoration */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    /* Custom Card Style for Form Groups */
    .form-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #eee;
    }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def clean_str(val):
    if val is None: return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'nat', 'null', '0', '0.0']: return ""
    return s

def format_age(val):
    s = clean_str(val)
    if not s: return ""
    try:
        return str(int(float(s)))
    except:
        return s

def get_fingerprint(text):
    if not text: return ""
    t = str(text).strip()
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = t.replace(" ", "").replace("\u200c", "").replace("\t", "")
    return t

# ==========================================
# 3. BACKEND (OPTIMIZED SPEED)
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

# ⚡ INCREASED CACHE TO 10 MINUTES (600s) FOR SPEED
@st.cache_data(ttl=600) 
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
    df.columns = [clean_str(c) for c in df.columns]
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [clean_str(x) for x in df['اسم'].tolist() if clean_str(x) != ""]
except Exception as e:
    st.error(f"❌ خطا: {e}")
    st.stop()

# ==========================================
# 🛡️ SIDEBAR: ADVANCED TOOLS (Backup & Import)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ ابزار مدیریت")
    
    # 1. REFRESH BUTTON (Since we increased cache time)
    if st.button("🔄 بروزرسانی لیست (Refresh)"):
        get_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # 2. BACKUP
    st.markdown("#### 💾 پشتیبان‌گیری")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 دانلود فایل CSV",
        data=csv,
        file_name=f"Backup_{time.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # 3. IMPORT (Moved to Sidebar to clean Main Screen)
    with st.expander("📥 ایمپورت اکسل (Advanced)"):
        uploaded_file = st.file_uploader("فایل اکسل", type=["xlsx", "xls"])
        debug_mode = st.checkbox("دیباگ", value=False)
        
        if uploaded_file:
            try:
                up_df = pd.read_excel(uploaded_file, dtype=str)
                up_df = up_df.fillna("").astype(str)
                up_df.columns = [clean_str(c) for c in up_df.columns]

                # Map Columns (Simplified for sidebar width)
                c_idx = lambda cols, k: next((i for i, c in enumerate(cols) if k in c), 0)
                col_name = st.selectbox("ستون نام", up_df.columns, index=c_idx(up_df.columns, 'اسم'))
                col_city = st.selectbox("ستون شهر", up_df.columns, index=c_idx(up_df.columns, 'شهر'))
                col_prov = st.selectbox("ستون استان", up_df.columns, index=c_idx(up_df.columns, 'استان'))

                # Build Index
                sheet_index = {}
                for idx, row in df.iterrows():
                    nm = clean_str(row.get('اسم', ''))
                    if nm:
                        fp = get_fingerprint(nm)
                        if fp not in sheet_index: sheet_index[fp] = []
                        sheet_index[fp].append({'idx': idx + 2, 'data': row})

                rows_to_add = []
                rows_to_update = []
                
                # Logic Loop
                for i, row in up_df.iterrows():
                    u_name = clean_str(row[col_name])
                    if not u_name: continue
                    
                    # Logic same as before (Fingerprint + Empty Check)
                    u_key = get_fingerprint(u_name)
                    candidates = sheet_index.get(u_key, [])
                    match_found = None
                    
                    u_city = clean_str(row[col_city])
                    u_prov = clean_str(row[col_prov])

                    for cand in candidates:
                        s_data = cand['data']
                        s_city = clean_str(s_data.get('شهر', ''))
                        s_prov = clean_str(s_data.get('استان', ''))
                        city_ok = (get_fingerprint(s_city) == "") or (get_fingerprint(s_city) == get_fingerprint(u_city)) or (u_city == "")
                        prov_ok = (get_fingerprint(s_prov) == "") or (get_fingerprint(s_prov) == get_fingerprint(u_prov)) or (u_prov == "")
                        if city_ok and prov_ok:
                            match_found = cand
                            break
                    
                    if match_found:
                        # Merge
                        r_idx = match_found['idx']
                        merged = []
                        do_upd = False
                        for h in all_headers:
                            s_val = clean_str(match_found['data'].get(h, ""))
                            e_val = ""
                            if h == 'اسم': e_val = u_name
                            elif h in up_df.columns: 
                                e_val = format_age(row[h]) if h == 'سن' else clean_str(row[h])
                            
                            if s_val == "" and e_val != "":
                                merged.append(e_val)
                                do_upd = True
                            else:
                                merged.append(s_val)
                        if do_upd: rows_to_update.append((r_idx, merged))
                    else:
                        # Add
                        new_r = []
                        for h in all_headers:
                            if h == 'اسم': new_r.append(u_name)
                            elif h in up_df.columns:
                                new_r.append(format_age(row[h]) if h == 'سن' else clean_str(row[h]))
                            else: new_r.append("")
                        rows_to_add.append(new_r)

                if rows_to_add or rows_to_update:
                    st.info(f"➕ جدید: {len(rows_to_add)} | 🔄 آپدیت: {len(rows_to_update)}")
                    if st.button("🚀 اجرا"):
                        sheet = get_connection().open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        if rows_to_add: sheet.append_rows(rows_to_add)
                        if rows_to_update:
                            batch = [{'range': f"A{r}", 'values': [v]} for r, v in rows_to_update]
                            sheet.batch_update(batch)
                        st.success("انجام شد")
                        get_data.clear()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.success("✅ داده‌ها یکسان هستند")

            except Exception as e:
                st.error(f"خطا: {e}")

# ==========================================
# MAIN UI (CLEAN FOR MOBILE)
# ==========================================
def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# HEADER
c1, c2 = st.columns([4, 2])
with c1: st.title("📋 سامانه هوشمند")
with c2: st.metric("کل", len(existing_names))

# SEARCH
if st.session_state.active_name is None:
    st.info("👇 جستجو کنید:")
    selected_value = st_searchbox(search_names, key="search_box_main", placeholder="نام...")
    if selected_value:
        st.session_state.active_name = selected_value
        st.rerun()

# FORM
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    # Top Bar
    c_status, c_close = st.columns([3, 1])
    with c_status:
        if is_edit_mode: st.success(f"✏️ ویرایش: **{locked_name}**")
        else: st.warning(f"🆕 جدید: **{locked_name}**")
    with c_close:
        if st.button("❌ بستن"):
            st.session_state.active_name = None
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    # Helper to draw inputs nicely
    def draw_section(title, headers, cols=3):
        valid = [h for h in headers if h in form_headers]
        if not valid: return
        
        # UI Card effect
        st.markdown(f'<div class="form-card"><b>{title}</b></div>', unsafe_allow_html=True)
        
        cc = st.columns(cols)
        for i, h in enumerate(valid):
            with cc[i % cols]:
                val = current_data.get(h, "")
                if h == 'سن': val = format_age(val)
                st.text_input(h, value=str(val), key=f"input_{h}", label_visibility="visible")

    with st.form("main_form"):
        # We use fewer columns on mobile logic by relying on st.columns wrapping
        # But 'st.columns(3)' usually works OK on mobile (stacks to 1)
        
        draw_section("👤 فردی", GROUP_PERSONAL, 2) # 2 cols looks better on mobile than 3
        draw_section("📍 حادثه", GROUP_INCIDENT, 1) # Vertical is safer for long text
        draw_section("🔗 سایر", GROUP_OTHER, 1)
        
        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        rem = [h for h in form_headers if h not in used]
        if rem: draw_section("📂 دیگر", rem, 2)

        st.markdown("---")
        if st.form_submit_button("💾 ذخیره اطلاعات", type="primary"):
            try:
                sheet = get_connection().open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                row_data = []
                for h in all_headers:
                    val = st.session_state.get(f"input_{h}", "")
                    if h == 'اسم': row_data.append(locked_name)
                    elif h == 'سن': row_data.append(format_age(val))
                    else: row_data.append(val)
                
                if is_edit_mode:
                    cell = sheet.find(locked_name)
                    sheet.update(range_name=f"A{cell.row}", values=[row_data])
                else:
                    sheet.append_row(row_data)
                
                st.toast("ذخیره شد!", icon='✅')
                get_data.clear()
                time.sleep(1)
                st.session_state.active_name = None
                st.rerun()
            except Exception as e:
                st.error(f"خطا: {e}")
