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
    # Get all records as strings
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOGIC & STATE
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    # ⚠️ FORCE CLEAN HEADERS: Remove all spaces from column names
    df.columns = df.columns.astype(str).str.strip()
    
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]
except Exception as e:
    st.error(f"❌ خطا در دریافت اطلاعات: {e}")
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
# 📥 FORCE MERGE (EXACT COLUMN MATCH)
# ==========================================
with st.expander("📥 افزودن و تکمیل (Import & Merge)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 1. Read Excel & FORCE CLEAN HEADERS
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
            # Strip whitespace from column names (e.g., "Age " -> "Age")
            up_df.columns = up_df.columns.astype(str).str.strip()
            
            # 2. Diagnostic: Check if columns match
            sheet_cols = set(all_headers)
            excel_cols = set(up_df.columns)
            common_cols = sheet_cols.intersection(excel_cols)
            
            # Show the user what we found
            st.markdown("##### 🔍 گزارش ستون‌ها")
            if len(common_cols) < 3:
                st.error("⚠️ هشدار: تعداد ستون‌های مشترک بسیار کم است. لطفاً نام ستون‌ها را چک کنید.")
                st.write("ستون‌های شیت شما:", list(sheet_cols))
                st.write("ستون‌های اکسل شما:", list(excel_cols))
            else:
                st.success(f"✅ {len(common_cols)} ستون دقیقاً هم‌نام پیدا شد (آماده کپی).")

            # 3. Select Name Column
            def find_col_index(columns, keywords):
                for i, col in enumerate(columns):
                    if any(k in col for k in keywords): return i
                return 0

            col_name = st.selectbox("ستون 'نام' در فایل:", up_df.columns, index=find_col_index(up_df.columns, ['اسم', 'name']))

            # Helper: Is cell TRULY empty?
            def is_empty(val):
                if not val: return True
                s = str(val).strip()
                return s == "" or s.lower() == "nan" or s == "-"

            # 4. Build Index (Strip spaces from names!)
            name_index = {}
            for index, row in df.iterrows():
                # Clean name from sheet
                f_name = str(row.get('اسم', '')).strip()
                if f_name:
                    name_index[f_name] = {'row_idx': index + 2, 'data': row}

            # 5. Process
            rows_to_append = []
            rows_to_update = []
            
            cnt_new = 0
            cnt_update = 0

            for index, row in up_df.iterrows():
                # Clean name from excel
                u_name = str(row[col_name]).strip()
                if is_empty(u_name): continue

                # CHECK MATCH
                if u_name in name_index:
                    # FOUND! PREPARE MERGE
                    target = name_index[u_name]
                    current_data = target['data']
                    r_idx = target['row_idx']
                    merged_row = []
                    has_new = False
                    
                    for header in all_headers:
                        curr_val = str(current_data.get(header, "")).strip()
                        
                        # Get new value from Excel (if column exists)
                        new_val = ""
                        if header == 'اسم': 
                            new_val = u_name
                        elif header in up_df.columns:
                            new_val = str(row[header]).strip()
                        
                        # LOGIC: If Sheet Empty AND Excel Not Empty -> FILL IT
                        if is_empty(curr_val) and not is_empty(new_val):
                            merged_row.append(new_val)
                            has_new = True
                        else:
                            merged_row.append(curr_val)
                    
                    if has_new:
                        rows_to_update.append((r_idx, merged_row))
                        cnt_update += 1
                else:
                    # NOT FOUND -> ADD NEW
                    new_row = []
                    for header in all_headers:
                        if header == 'اسم': 
                            new_row.append(u_name)
                        elif header in up_df.columns:
                            new_row.append(str(row[header]).strip())
                        else:
                            new_row.append("")
                    rows_to_append.append(new_row)
                    cnt_new += 1

            # 6. Execute
            if cnt_new > 0 or cnt_update > 0:
                c_a, c_b = st.columns(2)
                with c_a: st.warning(f"🆕 افراد جدید: {cnt_new}")
                with c_b: st.info(f"🔄 بروزرسانی (پر کردن خالی‌ها): {cnt_update}")
                
                if st.button("🚀 اجرای عملیات"):
                    with st.status("در حال انجام...", expanded=True) as status:
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_append:
                            status.write("✍️ افزودن جدید...")
                            sheet.append_rows(rows_to_append)
                        
                        if rows_to_update:
                            status.write("🔄 آپدیت موجود...")
                            # Batch update limits safety check
                            for r_num, r_vals in rows_to_update:
                                sheet.update(range_name=f"A{r_num}", values=[r_vals])
                                time.sleep(0.3)
                        
                        status.update(label="✅ تمام شد!", state="complete")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ هیچ داده جدیدی برای اضافه کردن یا تکمیل کردن یافت نشد (نام‌ها تکراری هستند و اطلاعات شیت پر است).")

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
                drawn_headers.add(header)

    # --- THE FORM ---
    with st.form("entry_form", border=True):
        st.markdown(f"### 📄 پرونده: {locked_name}")
        
        user_inputs = {}
        drawn_headers = set() 

        # SECTION 1: PERSONAL (3 cols)
        st.markdown('<div class="section-header">👤 اطلاعات فردی</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_PERSONAL, st, current_data, user_inputs, num_columns=3)

        # SECTION 2: INCIDENT (1 col - Vertical)
        st.markdown('<div class="section-header">📍 اطلاعات حادثه</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_INCIDENT, st, current_data, user_inputs, num_columns=1)

        # SECTION 3: OTHER (2 cols)
        st.markdown('<div class="section-header">🔗 سایر موارد</div>', unsafe_allow_html=True)
        draw_inputs(GROUP_OTHER, st, current_data, user_inputs, num_columns=2)

        # SECTION 4: CATCH-ALL (3 cols)
        remaining_headers = [h for h in form_headers if h not in drawn_headers]
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
