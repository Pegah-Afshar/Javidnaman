import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time
import uuid
df = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
# ==========================================
# 1. SETUP
# ==========================================
st.set_page_config(page_title=" جاویدنامان", layout="wide", page_icon="📋", initial_sidebar_state="collapsed")

# Groups
GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "اسم"]
GROUP_INCIDENT = ["تاریخ شمسی", "تاریخ میلادی", "استان", "شهر", "محله خیابان", "محل دقیق کشته شدن", "طریقه‌ی کشته شدن", "آرامگاه"]
GROUP_OTHER = ["اکانت در شبکه‌های اجتماعی", "بستگان", "توضیحات"]
NUMERIC_FIELDS = ["سن"]

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    .stTextInput label, .stSelectbox label { direction: rtl; text-align: right; font-weight: bold; color: #444; }
    .custom-header { color: #1a73e8; font-size: 1.1rem; font-weight: bold; margin-top: 15px; border-bottom: 1px solid #eee; }
    div[data-testid="stHorizontalBlock"] button { border-radius: 8px; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. STATE & HELPER FUNCTIONS
# ==========================================
if 'form_id' not in st.session_state:
    st.session_state.form_id = str(uuid.uuid4())
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

def reset_app():
    """Forces clear of all inputs"""
    st.session_state.active_name = None
    st.session_state.form_id = str(uuid.uuid4())
    if "search_box_main" in st.session_state: del st.session_state["search_box_main"]

def clean_str(val):
    if val is None: return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'null', '0', '0.0']: return ""
    return s

def format_age(val):
    s = clean_str(val)
    if not s: return ""
    try: return str(int(float(s)))
    except: return s

def get_fingerprint(text):
    if not text: return ""
    t = str(text).strip().replace("ي", "ی").replace("ك", "ک")
    t = t.replace(" ", "").replace("\u200c", "").replace("\t", "")
    return t

# ==========================================
# 3. CONNECTION & DATA
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gspread_creds"], scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600) 
def get_data():
    client = get_connection()
    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
    df = pd.DataFrame(sheet.get_all_records(expected_headers=[]))
    return df.astype(str)

try:
    df = get_data()
    # Normalize headers immediately
    df.columns = [clean_str(c) for c in df.columns]
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [clean_str(x) for x in df['اسم'].tolist() if clean_str(x)]
except Exception as e:
    st.error(f"❌ خطا در لود اولیه: {e}")
    st.stop()

# ==========================================
# 4. TOP TOOLBAR
# ==========================================
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    if st.button("🔄 رفرش"):
        get_data.clear()
        st.rerun()
with c2:
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 بکاپ", csv, "backup.csv", "text/csv")

# ==========================================
# 5. THE IMPORT SECTION (TRANSPARENT)
# ==========================================
with c3:
    with st.expander("📤 ایمپورت اکسل (Excel)"):
        uploaded_file = st.file_uploader("فایل را انتخاب کنید", type=["xlsx", "xls"])
        
        if uploaded_file:
            # 1. READ & SHOW PREVIEW
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("").astype(str)
            up_df.columns = [clean_str(c) for c in up_df.columns]
            
            st.caption("پیش‌نمایش فایل شما (۵ خط اول):")
            st.dataframe(up_df.head())

            # 2. MAP COLUMNS
            # Helper to find index
            def get_idx(options, key):
                for i, opt in enumerate(options):
                    if key in opt: return i
                return 0

            c_a, c_b, c_c = st.columns(3)
            col_name = c_a.selectbox("ستون نام", up_df.columns, index=get_idx(up_df.columns, 'اسم'))
            col_city = c_b.selectbox("ستون شهر", up_df.columns, index=get_idx(up_df.columns, 'شهر'))
            col_prov = c_c.selectbox("ستون استان", up_df.columns, index=get_idx(up_df.columns, 'استان'))

            # 3. PROCESS LOGIC
            if st.button("🔍 بررسی فایل"):
                # Build Index
                sheet_index = {}
                for idx, row in df.iterrows():
                    nm = clean_str(row.get('اسم', ''))
                    if nm:
                        fp = get_fingerprint(nm)
                        if fp not in sheet_index: sheet_index[fp] = []
                        sheet_index[fp].append({'idx': idx + 2, 'data': row})

                to_add = []
                to_update = []
                logs = []

                for i, row in up_df.iterrows():
                    u_name = clean_str(row[col_name])
                    if not u_name: continue
                    
                    u_key = get_fingerprint(u_name)
                    candidates = sheet_index.get(u_key, [])
                    
                    match_found = None
                    u_city = clean_str(row[col_city])
                    u_prov = clean_str(row[col_prov])

                    # Match Logic: Empty is Wildcard
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
                        # Prepare Merge
                        r_idx = match_found['idx']
                        merged = []
                        has_change = False
                        
                        for h in all_headers:
                            s_val = clean_str(match_found['data'].get(h, ""))
                            
                            e_val = ""
                            if h == 'اسم': e_val = u_name
                            elif h in up_df.columns:
                                e_val = format_age(row[h]) if h == 'سن' else clean_str(row[h])
                            
                            # Only update if Sheet is empty and Excel has data
                            if s_val == "" and e_val != "":
                                merged.append(e_val)
                                has_change = True
                            else:
                                merged.append(s_val)
                        
                        if has_change:
                            to_update.append((r_idx, merged))
                            logs.append(f"🔄 آپدیت: {u_name}")
                    else:
                        # Prepare Add
                        new_r = []
                        for h in all_headers:
                            if h == 'اسم': new_r.append(u_name)
                            elif h in up_df.columns:
                                new_r.append(format_age(row[h]) if h == 'سن' else clean_str(row[h]))
                            else: new_r.append("")
                        to_add.append(new_r)
                        logs.append(f"➕ جدید: {u_name}")

                # 4. SAVE TO SESSION STATE (So button click works)
                st.session_state['import_add'] = to_add
                st.session_state['import_upd'] = to_update
                st.session_state['import_logs'] = logs
                st.success(f"تحلیل انجام شد: {len(to_add)} مورد جدید، {len(to_update)} مورد آپدیت.")

            # 5. EXECUTE BUTTON
            if 'import_add' in st.session_state and (st.session_state['import_add'] or st.session_state['import_upd']):
                st.write("---")
                st.caption("لیست تغییرات:")
                st.text("\n".join(st.session_state['import_logs'][:10]) + ("..." if len(st.session_state['import_logs']) > 10 else ""))
                
                if st.button("🚀 تایید و ذخیره نهایی"):
                    try:
                        sheet = get_connection().open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        # Fix Grid Limit Error by checking length
                        current_row_count = len(df) + 2 # Header + buffer
                        
                        if st.session_state['import_add']:
                            sheet.append_rows(st.session_state['import_add'])
                        
                        if st.session_state['import_upd']:
                            batch = []
                            for r, v in st.session_state['import_upd']:
                                # Safety: Don't update rows that don't exist
                                if r < current_row_count + 100: 
                                    batch.append({'range': f"A{r}", 'values': [v]})
                            
                            if batch:
                                sheet.batch_update(batch)
                        
                        st.success("انجام شد! لطفاً رفرش کنید.")
                        # Clear state
                        del st.session_state['import_add']
                        del st.session_state['import_upd']
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطا: {e}")

st.divider()

# ==========================================
# 6. MAIN APP
# ==========================================
def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

if st.session_state.active_name is None:
    c_h1, c_h2 = st.columns([4, 1])
    with c_h1: st.subheader("🔍 ")
    with c_h2: st.caption(f"تعداد: {len(existing_names)}")
    
    sel = st_searchbox(search_names, key="search_box_main", placeholder="نام...")
    if sel:
        st.session_state.active_name = sel
        st.rerun()
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
    c_stat, c_cls = st.columns([5, 1])
    with c_stat:
        if is_edit_mode: st.success(f"✏️ **{locked_name}**")
        else: st.warning(f"🆕 **{locked_name}**")
    with c_cls:
        if st.button("❌"):
            reset_app()
            st.rerun()

    current_data = df[df['اسم'] == locked_name].iloc[0].to_dict() if is_edit_mode else {}

    def draw(title, headers, cols=3):
        valid = [h for h in headers if h in form_headers]
        if not valid: return
        st.markdown(f'<div class="custom-header">{title}</div>', unsafe_allow_html=True)
        cc = st.columns(cols)
        for i, h in enumerate(valid):
            with cc[i%cols]:
                val = current_data.get(h, "")
                if h == 'سن': val = format_age(val)
                # Form ID in Key = Fresh Box
                st.text_input(h, value=str(val), key=f"{h}_{st.session_state.form_id}")

    with st.form("main"):
        draw("👤 فردی", GROUP_PERSONAL, 3)
        draw("📍 حادثه", GROUP_INCIDENT, 2)
        draw("🔗 سایر", GROUP_OTHER, 2)
        
        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        rem = [h for h in form_headers if h not in used]
        if rem: draw("📂 دیگر", rem, 3)

        st.markdown("---")
        if st.form_submit_button("💾 ذخیره", type="primary"):
            try:
                sheet = get_connection().open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                row = []
                for h in all_headers:
                    val = st.session_state.get(f"{h}_{st.session_state.form_id}", "")
                    if h == 'اسم': row.append(locked_name)
                    elif h == 'سن': row.append(format_age(val))
                    else: row.append(val)
                
                if is_edit_mode:
                    cell = sheet.find(locked_name)
                    sheet.update(range_name=f"A{cell.row}", values=[row])
                else:
                    sheet.append_row(row)
                
                st.toast("ذخیره شد", icon='✅')
                get_data.clear()
                reset_app()
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"خطا: {e}")
