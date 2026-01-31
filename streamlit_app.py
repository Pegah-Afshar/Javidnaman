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

st.set_page_config(page_title=" جاویدنامان", layout="wide", page_icon="📋")

st.markdown("""<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif; }
    label, input, textarea, .stSelectbox, .stMarkdown, .stToast, .stExpander, .stMetric { direction: rtl !important; text-align: right !important; }
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
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOGIC & STATE
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    df.columns = df.columns.astype(str).str.strip() 
    
    all_headers = df.columns.tolist()
    form_headers = [h for h in all_headers if h and h != 'اسم']
    existing_names = [x for x in df['اسم'].dropna().unique().tolist() if x]
except Exception as e:
    st.error("❌ خطا در دریافت اطلاعات. لطفا اینترنت را بررسی کنید.")
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
    st.title("📋 ")
with c_count:
    st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 ADVANCED IMPORT (MERGE & ADD)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Add & Merge)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            up_df = pd.read_excel(uploaded_file).fillna("")
            up_df.columns = up_df.columns.astype(str).str.strip()
            up_df = up_df.astype(str)

            def find_col_index(columns, keywords):
                for i, col in enumerate(columns):
                    if any(k in col for k in keywords):
                        return i
                return 0

            st.info("لطفاً ستون‌های کلیدی را مشخص کنید تا افراد تکراری شناسایی شوند:")
            c1, c2, c3 = st.columns(3)
            with c1:
                col_name = st.selectbox("ستون 'نام':", up_df.columns, index=find_col_index(up_df.columns, ['اسم', 'name']))
            with c2:
                col_city = st.selectbox("ستون 'شهر':", up_df.columns, index=find_col_index(up_df.columns, ['شهر', 'city']))
            with c3:
                col_prov = st.selectbox("ستون 'استان':", up_df.columns, index=find_col_index(up_df.columns, ['استان', 'prov']))

            # --- STEP 1: INDEX EXISTING DATA ---
            # We map (Name, City, Prov) -> to its Row Number and Data
            # This helps us find "Who to Update"
            existing_map = {}
            for index, row in df.iterrows():
                f_name = str(row.get('اسم', '')).strip()
                f_city = str(row.get('شهر', '')).strip()
                f_prov = str(row.get('استان', '')).strip()
                # Store row index (index + 2 because sheet starts at row 2) and the data
                existing_map[(f_name, f_city, f_prov)] = {'row_idx': index + 2, 'data': row}

            # --- STEP 2: ANALYZE EXCEL FILE ---
            rows_to_append = [] # New people
            rows_to_update = [] # Existing people with new info

            for index, row in up_df.iterrows():
                u_name = str(row[col_name]).strip()
                u_city = str(row[col_city]).strip()
                u_prov = str(row[col_prov]).strip()
                
                if not u_name or u_name.lower() == 'nan': continue
                
                key = (u_name, u_city, u_prov)

                # --- SCENARIO A: NEW PERSON ---
                if key not in existing_map:
                    new_row = []
                    for header in all_headers:
                        if header == 'اسم': new_row.append(u_name)
                        elif header == 'شهر': new_row.append(u_city)
                        elif header == 'استان': new_row.append(u_prov)
                        else:
                            val = str(row[header]).strip() if header in up_df.columns else ""
                            new_row.append(val)
                    rows_to_append.append(new_row)
                
                # --- SCENARIO B: SAME PERSON (CHECK FOR MISSING INFO) ---
                else:
                    existing_record = existing_map[key]
                    current_sheet_data = existing_record['data']
                    row_number = existing_record['row_idx']
                    
                    # We build a "Merged Row"
                    merged_row = []
                    has_new_info = False
                    
                    for header in all_headers:
                        current_val = str(current_sheet_data.get(header, "")).strip()
                        
                        # Find value in Excel
                        excel_val = ""
                        if header == 'اسم': excel_val = u_name
                        elif header == 'شهر': excel_val = u_city
                        elif header == 'استان': excel_val = u_prov
                        elif header in up_df.columns: excel_val = str(row[header]).strip()
                        
                        # LOGIC: If Sheet is Empty AND Excel has data -> Update it!
                        if current_val == "" and excel_val != "":
                            merged_row.append(excel_val)
                            has_new_info = True
                        else:
                            # Otherwise keep the Sheet data (Sheet has priority if matched)
                            merged_row.append(current_val)
                    
                    if has_new_info:
                        rows_to_update.append((row_number, merged_row))

            # --- STEP 3: EXECUTE ---
            if rows_to_append or rows_to_update:
                c_new, c_upd = st.columns(2)
                with c_new:
                    st.warning(f"🆕 افراد جدید برای افزودن: {len(rows_to_append)}")
                with c_upd:
                    st.info(f"🔄 افراد موجود با اطلاعات جدید (تکمیل نواقص): {len(rows_to_update)}")
                
                if st.button("🚀 شروع عملیات (افزودن و بروزرسانی)"):
                    with st.status("در حال پردازش...", expanded=True) as status:
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        # 1. Add New Rows (Fast Batch)
                        if rows_to_append:
                            status.write("✍️ افزودن افراد جدید...")
                            sheet.append_rows(rows_to_append)
                        
                        # 2. Update Existing Rows (One by One - Safest for updates)
                        if rows_to_update:
                            status.write("🔄 تکمیل اطلاعات ناقص افراد موجود...")
                            # To avoid API limits on massive files, we verify size
                            if len(rows_to_update) > 50:
                                st.warning("تعداد بروزرسانی‌ها زیاد است، ممکن است کمی طول بکشد...")
                            
                            for r_num, r_data in rows_to_update:
                                # Update the whole row A{n}:Z{n}
                                sheet.update(range_name=f"A{r_num}", values=[r_data])
                                time.sleep(0.5) # Slight pause to be kind to API
                        
                        status.update(label="✅ انجام شد!", state="complete")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ هیچ داده جدیدی یافت نشد. تمام اطلاعات کامل و به‌روز است.")

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
