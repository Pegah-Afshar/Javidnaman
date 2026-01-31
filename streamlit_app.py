import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time
import numpy as np
import uuid

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="مدیریت جاویدنامان", 
    layout="wide", 
    page_icon="📋",
    initial_sidebar_state="collapsed"
)

# Groups
GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "اسم"]
GROUP_INCIDENT = ["تاریخ شمسی", "تاریخ میلادی", "استان", "شهر", "محله خیابان", "محل دقیق کشته شدن", "طریقه‌ی کشته شدن", "آرامگاه"]
GROUP_OTHER = ["اکانت در شبکه‌های اجتماعی", "بستگان", "توضیحات"]
NUMERIC_FIELDS = ["سن"]

# 🎨 CLEAN CSS
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    .stTextInput label, .stSelectbox label { direction: rtl; text-align: right; font-weight: bold; color: #444; }
    .custom-header {
        color: #1a73e8;
        font-size: 1.1rem;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 5px;
        border-bottom: 1px solid #eee;
    }
    div[data-testid="stHorizontalBlock"] button { border-radius: 8px; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. STATE MANAGEMENT (THE FIX)
# ==========================================
if 'form_id' not in st.session_state:
    st.session_state.form_id = str(uuid.uuid4())

if 'active_name' not in st.session_state:
    st.session_state.active_name = None

def reset_app():
    """Forces a complete reset of the form and search box"""
    st.session_state.active_name = None
    st.session_state.form_id = str(uuid.uuid4()) # Change ID to force empty boxes
    
    # Nuke the search box state
    if "search_box_main" in st.session_state:
        del st.session_state["search_box_main"]

# ==========================================
# 3. HELPER FUNCTIONS
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
# 4. BACKEND
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600) 
def get_data():
    client = get_connection()
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    raw_data = sheet.get_all_records(expected_headers=[])
    df = pd.DataFrame(raw_data)
    df = df.astype(str)
    return df

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
# 5. TOP TOOLBAR
# ==========================================
c_tools_1, c_tools_2, c_tools_3 = st.columns([1, 1, 2])

with c_tools_1:
    if st.button("🔄 رفرش", use_container_width=True):
        get_data.clear()
        st.rerun()

with c_tools_2:
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 بکاپ", csv, f"Backup_{time.strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

with c_tools_3:
    with st.expander("📤 ایمپورت اکسل"):
        uploaded_file = st.file_uploader("فایل اکسل", type=["xlsx", "xls"])
        if uploaded_file:
            try:
                up_df = pd.read_excel(uploaded_file, dtype=str).fillna("").astype(str)
                up_df.columns = [clean_str(c) for c in up_df.columns]
                
                c_idx = lambda cols, k: next((i for i, c in enumerate(cols) if k in c), 0)
                col_name = st.selectbox("ستون نام", up_df.columns, index=c_idx(up_df.columns, 'اسم'))
                col_city = st.selectbox("ستون شهر", up_df.columns, index=c_idx(up_df.columns, 'شهر'))
                col_prov = st.selectbox("ستون استان", up_df.columns, index=c_idx(up_df.columns, 'استان'))

                sheet_index = {}
                for idx, row in df.iterrows():
                    nm = clean_str(row.get('اسم', ''))
                    if nm:
                        fp = get_fingerprint(nm)
                        if fp not in sheet_index: sheet_index[fp] = []
                        sheet_index[fp].append({'idx': idx + 2, 'data': row})

                rows_to_add = []
                rows_to_update = []
                
                for i, row in up_df.iterrows():
                    u_name = clean_str(row[col_name])
                    if not u_name: continue
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
                        r_idx = match_found['idx']
                        merged = []
                        do_upd = False
                        for h in all_headers:
                            s_val = clean_str(match_found['data'].get(h, ""))
                            e_val = ""
                            if h == 'اسم': e_val = u_name
                            elif h in up_df.columns: e_val = format_age(row[h]) if h == 'سن' else clean_str(row[h])
                            if s_val == "" and e_val != "":
                                merged.append(e_val)
                                do_upd = True
                            else:
                                merged.append(s_val)
                        if do_upd: rows_to_update.append((r_idx, merged))
                    else:
                        new_r = []
                        for h in all_headers:
                            if h == 'اسم': new_r.append(u_name)
                            elif h in up_df.columns: new_r.append(format_age(row[h]) if h == 'سن' else clean_str(row[h]))
                            else: new_r.append("")
                        rows_to_add.append(new_r)

                if rows_to_add or rows_to_update:
                    st.info(f"➕ {len(rows_to_add)} | 🔄 {len(rows_to_update)}")
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
                    st.success("✅ هماهنگ")
            except Exception as e:
                st.error(f"خطا: {e}")

st.divider()

# ==========================================
# 6. MAIN INTERFACE
# ==========================================
def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# --- SCREEN 1: SEARCH ---
if st.session_state.active_name is None:
    # Use standard container
    with st.container():
        c_head1, c_head2 = st.columns([4, 1])
        with c_head1: st.subheader("🔍 جستجوی پرونده")
        with c_head2: st.caption(f"تعداد: {len(existing_names)}")
        
        # SEARCH BOX
        # We check if 'search_box_main' is in session state to handle resets
        selected_value = st_searchbox(
            search_names, 
            key="search_box_main", 
            placeholder="نام را تایپ کنید (اینتر بزنید)..."
        )
        
        if selected_value:
            st.session_state.active_name = selected_value
            st.rerun()

# --- SCREEN 2: FORM ---
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    # Header
    c_status, c_close = st.columns([5, 1])
    with c_status:
        if is_edit_mode: st.success(f"✏️ ویرایش: **{locked_name}**")
        else: st.warning(f"🆕 جدید: **{locked_name}**")
    with c_close:
        if st.button("❌", use_container_width=True):
            reset_app() # Force Clean Reset
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    def draw_section(title, headers, cols=3):
        valid = [h for h in headers if h in form_headers]
        if not valid: return
        
        st.markdown(f'<div class="custom-header">{title}</div>', unsafe_allow_html=True)
        cc = st.columns(cols)
        for i, h in enumerate(valid):
            with cc[i % cols]:
                val = current_data.get(h, "")
                if h == 'سن': val = format_age(val)
                
                # 🔥 THE FIX: Use form_id in the key to force fresh boxes
                unique_key = f"{h}_{st.session_state.form_id}"
                st.text_input(h, value=str(val), key=unique_key)

    with st.form("main_form"):
        draw_section("👤 اطلاعات فردی", GROUP_PERSONAL, 3)
        draw_section("📍 اطلاعات حادثه", GROUP_INCIDENT, 2)
        draw_section("🔗 سایر اطلاعات", GROUP_OTHER, 2)
        
        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        rem = [h for h in form_headers if h not in used]
        if rem: draw_section("📂 موارد دیگر", rem, 3)

        st.markdown("---")
        
        if st.form_submit_button("💾 ذخیره اطلاعات", type="primary"):
            try:
                sheet = get_connection().open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                row_data = []
                for h in all_headers:
                    # Retrieve using the UNIQUE key
                    unique_key = f"{h}_{st.session_state.form_id}"
                    val = st.session_state.get(unique_key, "")
                    
                    if h == 'اسم': row_data.append(locked_name)
                    elif h == 'سن': row_data.append(format_age(val))
                    else: row_data.append(val)
                
                if is_edit_mode:
                    cell = sheet.find(locked_name)
                    sheet.update(range_name=f"A{cell.row}", values=[row_data])
                else:
                    sheet.append_row(row_data)
                
                st.toast("اطلاعات ذخیره شد.", icon='✅')
                get_data.clear()
                time.sleep(1)
                
                # 🔥 FORCE RESET EVERYTHING
                reset_app()
                st.rerun()
            except Exception as e:
                st.error(f"خطا در ذخیره سازی: {e}")
