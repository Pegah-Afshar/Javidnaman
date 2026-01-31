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
# 2. CORE FUNCTIONS
# ==========================================

def normalize_text(text):
    """Standardizes text to ensure accurate matching"""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).strip()
    text = text.replace("ي", "ی").replace("ك", "ک")
    if text.lower() in ["nan", "none", "null", "-", ""]:
        return ""
    return text

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
    # Get all records as strings
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOAD DATA
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    df.columns = [normalize_text(c) for c in df.columns]
    
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [normalize_text(x) for x in df['اسم'].tolist() if normalize_text(x)]
except Exception as e:
    st.error(f"❌ خطا: {e}")
    st.stop()

def search_names(search_term: str):
    if not search_term: return existing_names
    matches = [n for n in existing_names if search_term in n]
    if search_term not in matches: matches.insert(0, search_term)
    return matches

# ==========================================
# APP HEADER
# ==========================================
c_title, c_count = st.columns([5, 1])
with c_title:
    st.title("📋 سامانه مدیریت هوشمند")
with c_count:
    st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 SMART MERGE (FIXED LOGIC)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Smart Merge)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 1. Read Excel
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
            up_df.columns = [normalize_text(c) for c in up_df.columns]

            # 2. Select Columns
            def find_col(cols, key):
                for c in cols:
                    if key in c or (key == 'name' and 'اسم' in c): return c
                return cols[0]
            
            c1, c2, c3 = st.columns(3)
            col_name = c1.selectbox("ستون 'نام':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'اسم')))
            col_city = c2.selectbox("ستون 'شهر':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'شهر')))
            col_prov = c3.selectbox("ستون 'استان':", up_df.columns, index=up_df.columns.get_loc(find_col(up_df.columns, 'استان')))

            # 3. Build Index of Existing Data
            name_index = {}
            for idx, row in df.iterrows():
                nm = normalize_text(row.get('اسم', ''))
                if nm:
                    if nm not in name_index: name_index[nm] = []
                    name_index[nm].append({'idx': idx + 2, 'data': row})

            # 4. Processing Loop
            rows_to_add = []
            rows_to_update = []
            
            cnt_new = 0
            cnt_merged = 0

            for i, row in up_df.iterrows():
                # Get Excel Data (Normalized)
                u_name = normalize_text(row[col_name])
                u_city = normalize_text(row[col_city])
                u_prov = normalize_text(row[col_prov])
                
                if not u_name: continue

                # Look for candidates in Sheet
                candidates = name_index.get(u_name, [])
                
                matched_candidate = None
                
                # --- MATCHING LOGIC ---
                for cand in candidates:
                    sheet_data = cand['data']
                    sheet_city = normalize_text(sheet_data.get('شهر', ''))
                    sheet_prov = normalize_text(sheet_data.get('استان', ''))
                    
                    # RELAXED CHECK:
                    # They match if:
                    # 1. Cities are identical OR one of them is empty
                    # 2. AND Provinces are identical OR one of them is empty
                    
                    city_compatible = (sheet_city == u_city) or (sheet_city == "") or (u_city == "")
                    prov_compatible = (sheet_prov == u_prov) or (sheet_prov == "") or (u_prov == "")
                    
                    if city_compatible and prov_compatible:
                        matched_candidate = cand
                        break 

                if matched_candidate:
                    # === MERGE ===
                    r_idx = matched_candidate['idx']
                    current_data = matched_candidate['data']
                    merged_row = []
                    has_updates = False
                    
                    for header in all_headers:
                        sheet_val = normalize_text(current_data.get(header, ""))
                        
                        excel_val = ""
                        if header == 'اسم': excel_val = u_name
                        elif header in up_df.columns: excel_val = normalize_text(row[header])
                        
                        # UPDATE ONLY IF: Sheet is Empty AND Excel has Value
                        if sheet_val == "" and excel_val != "":
                            merged_row.append(excel_val)
                            has_updates = True
                        else:
                            merged_row.append(sheet_val)
                    
                    if has_updates:
                        rows_to_update.append((r_idx, merged_row))
                        cnt_merged += 1
                
                else:
                    # === ADD NEW ===
                    # (Only if Name is new, OR Name exists but Location CONTRADICTS)
                    new_row = []
                    for header in all_headers:
                        if header == 'اسم':
                            new_row.append(u_name)
                        elif header in up_df.columns:
                            new_row.append(normalize_text(row[header]))
                        else:
                            new_row.append("")
                    rows_to_add.append(new_row)
                    cnt_new += 1

            # 5. Execute
            if cnt_new > 0 or cnt_merged > 0:
                c_a, c_b = st.columns(2)
                c_a.warning(f"🆕 افراد جدید: {cnt_new}")
                c_b.info(f"🔄 تکمیل اطلاعات (ادغام): {cnt_merged}")
                
                if st.button("🚀 ذخیره تغییرات"):
                    with st.status("در حال پردازش...", expanded=True):
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_add:
                            sheet.append_rows(rows_to_add)
                        
                        if rows_to_update:
                            # Safely update row by row
                            for r_num, r_vals in rows_to_update:
                                sheet.update(range_name=f"A{r_num}", values=[r_vals])
                                time.sleep(0.3)
                        
                        st.success("عملیات با موفقیت انجام شد!")
                        get_data.clear()
                        time.sleep(1)
                        st.rerun()
            else:
                st.success("✅ داده‌ها کاملاً هماهنگ هستند.")

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

        used = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        remaining = [h for h in form_headers if h not in used]
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
                    
                    st.toast("ذخیره شد!", icon='🎉')
                    get_data.clear()
                    time.sleep(1)
                    st.session_state.active_name = None
                    st.rerun()
                except Exception as e:
                    st.error(f"خطا: {e}")
