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
    # Get all records as string to avoid type issues
    return pd.DataFrame(sheet.get_all_records(expected_headers=[]))

# ==========================================
# 3. LOGIC & STATE
# ==========================================
if 'active_name' not in st.session_state:
    st.session_state.active_name = None

try:
    df = get_data()
    # Clean up column names (remove hidden spaces)
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
    st.title("📋 سامانه مدیریت هوشمند")
with c_count:
    st.metric(label="تعداد کل", value=len(existing_names))

# ==========================================
# 📥 INTELLIGENT IMPORT (SMART FILL)
# ==========================================
with st.expander("📥 افزودن و تکمیل گروهی (Smart Merge)"):
    uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بکشید", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # 1. Read & Force Text Type
            # dtype=str ensures '25' (age) is read as text "25", not number 25.0
            up_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
            up_df.columns = up_df.columns.astype(str).str.strip()

            # --- DIAGNOSTIC REPORT ---
            # Map Lowercase -> Real Excel Header
            excel_col_map = {c.lower().strip(): c for c in up_df.columns}
            
            matched_cols = []
            missing_cols = []
            for h in all_headers:
                if h.lower().strip() in excel_col_map:
                    matched_cols.append(h)
                else:
                    missing_cols.append(h)
            
            st.markdown("##### 📊 گزارش وضعیت ستون‌ها:")
            c_ok, c_bad = st.columns(2)
            with c_ok:
                if matched_cols:
                    st.success(f"✅ {len(matched_cols)} ستون شناسایی شد (آماده کپی)")
            with c_bad:
                if missing_cols:
                    st.error(f"❌ {len(missing_cols)} ستون در اکسل پیدا نشد (کپی نمی‌شوند)")
                    st.caption(f"مثال: {', '.join(missing_cols[:3])}...")
            st.markdown("---")

            # 2. Key Columns
            def find_col_index(columns, keywords):
                for i, col in enumerate(columns):
                    if any(k in col for k in keywords): return i
                return 0

            st.info("لطفاً ستون‌های کلیدی را تأیید کنید:")
            c1, c2, c3 = st.columns(3)
            with c1:
                col_name = st.selectbox("ستون 'نام':", up_df.columns, index=find_col_index(up_df.columns, ['اسم', 'name']))
            with c2:
                col_city = st.selectbox("ستون 'شهر':", up_df.columns, index=find_col_index(up_df.columns, ['شهر', 'city']))
            with c3:
                col_prov = st.selectbox("ستون 'استان':", up_df.columns, index=find_col_index(up_df.columns, ['استان', 'prov']))

            # Helper: Is cell TRULY empty?
            def is_empty(val):
                if not val: return True
                s = str(val).strip().lower()
                return s == "" or s == "nan" or s == "none" or s == "-"

            # 3. Build Name Index
            name_index = {}
            for index, row in df.iterrows():
                f_name = str(row.get('اسم', '')).strip()
                if f_name not in name_index: name_index[f_name] = []
                name_index[f_name].append({'row_idx': index + 2, 'data': row})

            # 4. Process Excel Rows
            rows_to_append = []
            rows_to_update = []

            for index, row in up_df.iterrows():
                u_name = str(row[col_name]).strip()
                u_city = str(row[col_city]).strip()
                u_prov = str(row[col_prov]).strip()
                
                if is_empty(u_name): continue

                candidate_list = name_index.get(u_name, [])
                
                # We need to find the BEST candidate to update
                # Priority: A compatible match that HAS EMPTY CELLS we can fill
                best_match = None
                best_new_info_count = -1
                
                # Check compatibility
                compatible_candidates = []
                for candidate in candidate_list:
                    sheet_city = str(candidate['data'].get('شهر', '')).strip()
                    sheet_prov = str(candidate['data'].get('استان', '')).strip()
                    
                    # Logic: Compatible if Sheet location is Empty OR Matches Excel
                    city_ok = is_empty(sheet_city) or (sheet_city.lower() == u_city.lower())
                    prov_ok = is_empty(sheet_prov) or (sheet_prov.lower() == u_prov.lower())
                    
                    if city_ok and prov_ok:
                        compatible_candidates.append(candidate)

                if compatible_candidates:
                    # We found existing people! Now let's see if we should update one.
                    for cand in compatible_candidates:
                        current_sheet_data = cand['data']
                        
                        # Calculate how much new info this update would provide
                        new_info_count = 0
                        temp_merged_row = [] # Just for checking
                        
                        for header in all_headers:
                            current_val = str(current_sheet_data.get(header, "")).strip()
                            
                            # Get Excel Value
                            excel_val = ""
                            if header == 'اسم': excel_val = u_name
                            elif header == 'شهر': excel_val = u_city
                            elif header == 'استان': excel_val = u_prov
                            elif header.lower().strip() in excel_col_map:
                                real_col = excel_col_map[header.lower().strip()]
                                excel_val = str(row[real_col]).strip()
                            
                            # LOGIC: If Sheet Empty AND Excel Not Empty -> It's useful!
                            if is_empty(current_val) and not is_empty(excel_val):
                                new_info_count += 1
                        
                        # We pick the candidate that benefits the MOST from this update
                        if new_info_count > best_new_info_count:
                            best_new_info_count = new_info_count
                            best_match = cand

                    # If we found a useful update (count > 0), queue it
                    if best_match and best_new_info_count > 0:
                        row_number = best_match['row_idx']
                        current_sheet_data = best_match['data']
                        final_merged_row = []
                        
                        for header in all_headers:
                            current_val = str(current_sheet_data.get(header, "")).strip()
                            
                            excel_val = ""
                            if header == 'اسم': excel_val = u_name
                            elif header == 'شهر': excel_val = u_city
                            elif header == 'استان': excel_val = u_prov
                            elif header.lower().strip() in excel_col_map:
                                real_col = excel_col_map[header.lower().strip()]
                                excel_val = str(row[real_col]).strip()
                            
                            if is_empty(current_val) and not is_empty(excel_val):
                                final_merged_row.append(excel_val)
                            else:
                                final_merged_row.append(current_val)
                        
                        rows_to_update.append((row_number, final_merged_row))
                    
                    # Note: If best_new_info_count == 0, it means the sheet already has all info
                    # So we do NOTHING (Don't duplicate, Don't overwrite)

                else:
                    # No compatible match found -> NEW PERSON
                    new_row = []
                    for header in all_headers:
                        excel_val = ""
                        if header == 'اسم': excel_val = u_name
                        elif header == 'شهر': excel_val = u_city
                        elif header == 'استان': excel_val = u_prov
                        elif header.lower().strip() in excel_col_map:
                            real_col = excel_col_map[header.lower().strip()]
                            excel_val = str(row[real_col]).strip()
                        new_row.append(excel_val)
                    rows_to_append.append(new_row)

            # 5. Execute
            if rows_to_append or rows_to_update:
                c_new, c_upd = st.columns(2)
                with c_new:
                    st.warning(f"🆕 افراد جدید: {len(rows_to_append)}")
                with c_upd:
                    st.info(f"🔄 بروزرسانی و تکمیل: {len(rows_to_update)}")
                
                if st.button("🚀 اجرای عملیات"):
                    with st.status("در حال پردازش...", expanded=True) as status:
                        client = get_connection()
                        sheet = client.open_by_url(st.secrets["public_gsheets_url"]).get_worksheet(0)
                        
                        if rows_to_append:
                            status.write("✍️ افزودن ردیف‌های جدید...")
                            sheet.append_rows(rows_to_append)
                        
                        if rows_to_update:
                            status.write("🔄 تکمیل اطلاعات ناقص...")
                            if len(rows_to_update) > 50: st.caption("لطفاً صبر کنید...")
                            for r_num, r_data in rows_to_update:
                                sheet.update(range_name=f"A{r_num}", values=[r_data])
                                time.sleep(0.4) 
                        
                        status.update(label="✅ تمام شد!", state="complete")
                        get_data.clear()
                        time.sleep(2)
                        st.rerun()
            else:
                st.success("✅ هیچ تغییر جدیدی لازم نیست (داده‌ها کامل هستند).")

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
