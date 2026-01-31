import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_searchbox import st_searchbox
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================

GROUP_PERSONAL = ["سن", "تاریخ تولد", "محل تولد", "جنسیت", "اسم"]

GROUP_INCIDENT = [
    "تاریخ شمسی", 
    "تاریخ میلادی", 
    "استان", 
    "شهر", 
    "محله خیابان", 
    "محل دقیق کشته شدن", 
    "طریقه‌ی کشته شدن",           
    "آرامگاه"
]

GROUP_OTHER = ["اکانت در شبکه‌های اجتماعی", "بستگان", "توضیحات"]

NUMERIC_FIELDS = ["سن"]

st.set_page_config(page_title="مدیریت جاویدنامان", layout="wide", page_icon="📋")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast, .stExpander, .stMetric, .stAlert { direction: rtl !important; text-align: right !important; }
    .stButton button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton button:hover { background-color: #1557b0; }
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
    # Ensure all data is read as string to prevent type mismatches
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOAD DATA
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    # Simple cleanup: just remove extra spaces from column names
    df.columns = df.columns.astype(str).str.strip()
    
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [str(x).strip() for x in df['اسم'].dropna().tolist() if str(x).strip()]
except Exception as e:
    st.error(f"❌ خطا: {e}")
    st.stop()

def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# ==========================================
# HEADER
# ==========================================
c_title, c_count = st.columns([5, 1])
with c_title:
    st.title("📋 سامانه مدیریت هوشمند")
with c_count:
    st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 SIMPLE & DIRECT IMPORT
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (نسخه ساده)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 1. Read Excel (Force everything to String)
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
            up_df.columns = up_df.columns.astype(str).str.strip()

            # 2. Identify Name Column
            def find_col(cols):
                for c in cols:
                    if 'اسم' in c or 'name' in c.lower(): return c
                return cols[0]
            
            col_name = st.selectbox("ستون نام:", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns)))

            # 3. Index Existing Data
            # Key = Name, Value = List of {Index, Data}
            name_index = {}
            for idx, row in df.iterrows():
                nm = str(row.get('اسم', '')).strip()
                if nm:
                    if nm not in name_index: name_index[nm] = []
                    name_index[nm].append({'idx': idx + 2, 'data': row})

            # 4. Process Logic
            rows_to_add = []
            rows_to_update = []
            
            cnt_add = 0
            cnt_update = 0

            for i, row in up_df.iterrows():
                u_name = str(row[col_name]).strip()
                if not u_name or u_name.lower() == 'nan': continue

                # Is name in Sheet?
                candidates = name_index.get(u_name, [])
                
                matched_candidate = None
                
                if candidates:
                    # Try to find a COMPATIBLE match to merge with
                    for cand in candidates:
                        sheet_row = cand['data']
                        is_compatible = True
                        
                        # Check compatibility for ALL columns
                        for col in all_headers:
                            if col == 'اسم': continue
                            
                            sheet_val = str(sheet_row.get(col, "")).strip()
                            excel_val = str(row.get(col, "")).strip() if col in up_df.columns else ""
                            
                            # Conflict Rule: If Sheet has value X, and Excel has value Y, and X != Y -> Conflict!
                            # We only merge if Sheet is Empty OR Sheet matches Excel
                            if sheet_val != "" and excel_val != "" and sheet_val != excel_val:
                                is_compatible = False
                                break
                        
                        if is_compatible:
                            matched_candidate = cand
                            break
                
                # --- DECISION ---
                if matched_candidate:
                    # MERGE
                    r_idx = matched_candidate['idx']
                    current_data = matched_candidate['data']
                    merged_row = []
                    changes_found = False
                    
                    for col in all_headers:
                        sheet_val = str(current_data.get(col, "")).strip()
                        excel_val = str(row.get(col, "")).strip() if col in up_df.columns else ""
                        
                        # Update only if Sheet is empty and Excel has info
                        if col == 'اسم':
                            merged_row.append(u_name)
                        elif sheet_val == "" and excel_val != "":
                            merged_row.append(excel_val)
                            changes_found = True
                        else:
                            merged_row.append(sheet_val)
                    
                    if changes_found:
                        rows_to_update.append((r_idx, merged_row))
                        cnt_update += 1
                
                else:
                    # NO MATCH (or Conflict found) -> ADD NEW
                    new_row = []
                    for col in all_headers:
                        if col == 'اسم':
                            new_row.append(u_name)
                        elif col in up_df.columns:
                            new_row.append(str(row[col]).strip())
                        else:
                            new_row.append("")
                    rows_to_add.append(new_row)
                    cnt_add += 1

            # 5. Execute
            if cnt_add > 0 or cnt_update > 0:
                c1, c2 = st.columns(2)
                c1.warning(f"🆕 افزودن: {cnt_add}")
                c2.info(f"🔄 تکمیل: {cnt_update}")
                
                if st.button("🚀 اجرا"):
                    with st.status("در حال انجام...", expanded=True):
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_add:
                            sheet.append_rows(rows_to_add)
                        
                        if rows_to_update:
                            for r_num, r_vals in rows_to_update:
                                sheet.update(range_name=f"A{r_num}", values=[r_vals])
                                time.sleep(0.3)
                        
                        st.success("انجام شد!")
                        get_data.clear()
                        time.sleep(1)
                        st.rerun()
            else:
                st.success("✅ داده‌ها یکسان هستند (تغییری لازم نیست).")
                
        except Exception as e:
            st.error(f"Error: {e}")

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
# SCREEN 2: ENTRY FORM
# ==========================================
else:
    locked_name = st.session_state.active_name
    is_edit_mode = locked_name in existing_names
    
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

    def draw_inputs(headers_list, container, data_dict, inputs_dict, num_columns=3):
        valid_headers = [h for h in headers_list if h in form_headers]
        if not valid_headers: return
        cols = container.columns(num_columns)
        for i, header in enumerate(valid_headers):
            with cols[i % num_columns]:
                val = data_dict.get(header, "")
                inputs_dict[header] = st.text_input(header, value=str(val), key=f"input_{header}")

    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 پرونده: {locked_name}")
        user_inputs = {}
        st.markdown('<div class="section-header">👤 اطلاعات فردی</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_PERSONAL, st, current_data, user_inputs, num_columns=3)
        st.markdown('<div class="section-header">📍 اطلاعات حادثه</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_INCIDENT, st, current_data, user_inputs, num_columns=1)
        st.markdown('<div class="section-header">🔗 سایر موارد</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_OTHER, st, current_data, user_inputs, num_columns=2)
        
        remaining = [h for h in form_headers if h not in GROUP_PERSONAL+GROUP_INCIDENT+GROUP_OTHER]
        if remaining:
            st.markdown('<div class="section-header">📂 سایر</div>', unsafe_allow_html=True)
            draw_inputs(remaining, st, current_data, user_inputs, num_columns=3)

        st.markdown("---")
        c_sub, c_nul = st.columns([2, 5])
        with c_sub:
            if st.form_submit_button("💾 ثبت نهایی"):
                try:
                    client = get_connection()
                    sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                    row_data = [locked_name if h=='اسم' else user_inputs.get(h, "") for h in all_headers]
                    
                    if is_edit_mode:
                        cell = sheet.find(locked_name)
                        sheet.update(range_name=f"A{cell.row}", values=[row_data])
                    else:
                        sheet.append_row(row_data)
                    
                    st.toast("ذخیره شد!")
                    get_data.clear()
                    time.sleep(1)
                    st.session_state.active_name = None
                    st.rerun()
                except Exception as e:
                    st.error(f"خطا: {e}")
