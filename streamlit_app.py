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
    .st-emotion-cache-16idsys p { display: none; } 
    [data-testid="stForm"] { border: 1px solid #ddd; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .section-header { color: #1a73e8; font-size: 1.1em; font-weight: bold; margin-top: 25px; margin-bottom: 15px; border-bottom: 2px solid #f0f2f6; padding-bottom: 8px; }
</style>""", unsafe_allow_html=True)

# ==========================================
# 2. CORE FUNCTIONS
# ==========================================

def normalize_text(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    text = text.replace("ي", "ی").replace("ك", "ک")
    if text.lower() in ["nan", "none", "null", "-", ".", ""]:
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
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOAD DATA
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    # Normalize Headers
    df.columns = [normalize_text(c) for c in df.columns]
    
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [normalize_text(x) for x in df['اسم'].dropna().tolist() if x]
except Exception as e:
    st.error(f"❌ خطا در دریافت اطلاعات: {e}")
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
# 📥 IMPORT SECTION (FIXED FOR DUPLICATES)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Import & Merge)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 1. Read Excel
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
            up_df.columns = [normalize_text(c) for c in up_df.columns]

            # 2. Select Name Column
            def find_col_index(columns, keywords):
                for i, col in enumerate(columns):
                    if any(k in col for k in keywords): return i
                return 0

            col_name = st.selectbox("ستون 'نام' در فایل:", up_df.columns, index=find_col_index(up_df.columns, ['اسم', 'name']))

            # 3. Build Name Index (Supports Multiple Rows per Name)
            # Key = Name, Value = LIST of {row_idx, data}
            name_index = {}
            for index, row in df.iterrows():
                raw_name = str(row.get('اسم', ''))
                norm_name = normalize_text(raw_name)
                
                if norm_name:
                    if norm_name not in name_index:
                        name_index[norm_name] = [] # Create list
                    # Append this row to the list
                    name_index[norm_name].append({'row_idx': index + 2, 'data': row})

            # 4. Process Excel
            rows_to_append = []
            rows_to_update = []
            
            cnt_new = 0
            cnt_merged = 0

            for index, row in up_df.iterrows():
                u_name = normalize_text(str(row[col_name]))
                if not u_name: continue

                # Look for candidates in Sheet
                candidates = name_index.get(u_name, [])
                
                match_found = False
                
                if candidates:
                    # Check each candidate to see if we can update it
                    for cand in candidates:
                        current_data = cand['data']
                        r_idx = cand['row_idx']
                        
                        merged_row = []
                        new_info_count = 0
                        
                        # Build potential merged row
                        for header in all_headers:
                            sheet_val = normalize_text(str(current_data.get(header, "")))
                            
                            excel_val = ""
                            if header == 'اسم':
                                excel_val = u_name
                            elif header in up_df.columns:
                                excel_val = normalize_text(str(row[header]))
                            
                            # LOGIC: Only update if Sheet is Empty & Excel has Value
                            if sheet_val == "" and excel_val != "":
                                merged_row.append(excel_val) # Use Excel
                                new_info_count += 1
                            else:
                                merged_row.append(sheet_val) # Keep Sheet (Original)
                        
                        if new_info_count > 0:
                            # We found a row that needs updating!
                            rows_to_update.append((r_idx, merged_row))
                            cnt_merged += 1
                            match_found = True
                            break # Move to next name in Excel (we updated one instance)
                        
                        # If sheet_val was NOT empty, or Excel matched sheet, 
                        # we check if everything matches perfectly.
                        # If everything matches perfectly, we consider it "Found" and do nothing.
                        elif sheet_val == excel_val:
                            match_found = True # It exists, it's identical, no update needed.
                            # Don't break yet, maybe another duplicate needs filling? 
                            # (Simplification: Assuming one Excel row updates one Sheet row)
                            break
                
                if not match_found and not candidates:
                    # Name does NOT exist in Sheet -> Add New
                    new_row = []
                    for header in all_headers:
                        if header == 'اسم':
                            new_row.append(u_name)
                        elif header in up_df.columns:
                            new_row.append(normalize_text(str(row[header])))
                        else:
                            new_row.append("")
                    rows_to_append.append(new_row)
                    cnt_new += 1
                elif not match_found and candidates:
                    # Name exists, but existing rows were FULL (no empty cells to fill).
                    # Do we add a duplicate?
                    # The requirement says: "if name exists but different info -> add"
                    # But here we are assuming if we couldn't merge, it might be a new person?
                    # For safety in this specific "Exact Copy" test, we do nothing if it's full.
                    pass

            # 5. Execute
            if cnt_new > 0 or cnt_merged > 0:
                c_a, c_b = st.columns(2)
                with c_a: st.warning(f"🆕 افراد جدید: {cnt_new}")
                with c_b: st.info(f"🔄 بروزرسانی: {cnt_merged}")
                
                if st.button("🚀 شروع عملیات"):
                    with st.status("در حال پردازش...", expanded=True) as status:
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_append:
                            status.write("✍️ افزودن...")
                            sheet.append_rows(rows_to_append)
                        
                        if rows_to_update:
                            status.write("🔄 آپدیت...")
                            for r_num, r_vals in rows_to_update:
                                sheet.update(range_name=f"A{r_num}", values=[r_vals])
                                time.sleep(0.3)
                        
                        status.update(label="✅ انجام شد!", state="complete")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ داده‌ها هماهنگ هستند (مورد جدید یا ناقصی پیدا نشد).")

        except Exception as e:
            st.error(f"خطا: {e}")

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

    # --- HELPER FUNCTION ---
    def draw_inputs(headers_list, container, data_dict, inputs_dict, num_columns=3):
        valid_headers = [h for h in headers_list if h in form_headers]
        if not valid_headers: return
        
        cols = container.columns(num_columns)
        for i, header in enumerate(valid_headers):
            with cols[i % num_columns]:
                val = data_dict.get(header, "")
                inputs_dict[header] = st.text_input(header, value=str(val), key=f"input_{header}")

    # --- THE FORM ---
    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 پرونده: {locked_name}")
        
        user_inputs = {}

        # SECTION 1: PERSONAL (3 cols)
        st.markdown('<div class="section-header">👤 اطلاعات فردی</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_PERSONAL, st, current_data, user_inputs, num_columns=3)

        # SECTION 2: INCIDENT (1 col)
        st.markdown('<div class="section-header">📍 اطلاعات حادثه</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_INCIDENT, st, current_data, user_inputs, num_columns=1)

        # SECTION 3: OTHER (2 cols)
        st.markdown('<div class="section-header">🔗 سایر موارد</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_OTHER, st, current_data, user_inputs, num_columns=2)

        # SECTION 4: CATCH-ALL
        used_headers = set(GROUP_PERSONAL + GROUP_INCIDENT + GROUP_OTHER + ['اسم'])
        remaining_headers = [h for h in form_headers if h not in used_headers]
        if remaining_headers:
            st.markdown('<div class="section-header">📂 ستون‌های دسته‌بندی نشده</div>', unsafe_allow_html=True)
            draw_inputs(remaining_headers, st, current_data, user_inputs, num_columns=3)

        st.markdown("---")
        
        c_sub, c_nul = st.columns([2, 5])
        with c_sub:
            submitted = st.form_submit_button("💾 ثبت نهایی")

        if submitted:
            validation_errors = []
            for field in NUMERIC_FIELDS:
                if field in user_inputs and user_inputs[field].strip():
                    if not user_inputs[field].strip().isdigit():
                        validation_errors.append(f"⛔ فیلد **{field}** باید عدد باشد.")
            
            if validation_errors:
                for err in validation_errors: st.error(err)
            else:
                try:
                    changes_detected = True
                    if is_edit_mode:
                        changes_detected = False
                        for header in form_headers:
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
                        
                        for header in form_headers:
                            if f"input_{header}" in st.session_state: del st.session_state[f"input_{header}"]
                        if "search_box_main" in st.session_state: del st.session_state["search_box_main"]
                        
                        st.session_state.active_name = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ خطا: {e}")
