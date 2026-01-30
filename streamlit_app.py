import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ۱. تنظیمات صفحه
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

# ۲. استایل‌دهی راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    label, .stTextInput, .stTextArea, .stSelectbox { direction: rtl !important; text-align: right !important; }
    .stButton button { display: block; margin-right: 0; margin-left: auto; background-color: #4CAF50; color: white; }
    input { direction: rtl; text-align: right; }
    div[data-baseweb="select"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("📋 پنل جامع ثبت و ویرایش اطلاعات")

# اتصال به گوگل‌شیت
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error(f"خطا در اتصال: {e}")
    st.stop()

if "اسم" not in df.columns:
    st.error("ستون 'اسم' در صفحه‌گسترده یافت نشد.")
    st.stop()

names_list = df["اسم"].dropna().astype(str).unique().tolist()

# مقداردهی اولیه session state
if "name_value" not in st.session_state:
    st.session_state.name_value = ""
if "editing_name" not in st.session_state:
    st.session_state.editing_name = None
if "prefill" not in st.session_state:
    st.session_state.prefill = None

# ─── بخش نام: تایپ کنید، لیست مشابه نشان داده می‌شود ───
st.markdown("### نام (الزامی)")
# همگام‌سازی با انتخاب از لیست (وقتی از دراپ‌داون انتخاب می‌شود)
if "name_input" not in st.session_state:
    st.session_state.name_input = st.session_state.name_value
name_input = st.text_input(
    "اسم را وارد کنید یا از لیست انتخاب کنید",
    value=st.session_state.get("name_input", st.session_state.name_value),
    placeholder="شروع به تایپ کنید...",
    key="name_input",
)
st.session_state.name_value = name_input.strip() if name_input else ""

# لیست اسامی مشابه با آنچه تایپ شده
query = st.session_state.name_value
if query:
    matches = [n for n in names_list if query.lower() in n.lower()]
else:
    matches = []

# انتخاب از لیست موجود: اگر انتخاب شد → حالت ویرایش
picker_label = "— اگر این شخص در لیست است، اینجا انتخاب کنید (ویرایش) —"
picker_options = [picker_label] + matches
idx = 0
if st.session_state.editing_name and st.session_state.editing_name in picker_options:
    idx = picker_options.index(st.session_state.editing_name)

selected_existing = st.selectbox(
    "اسامی موجود (با تایپ شما فیلتر می‌شوند)",
    options=picker_options,
    index=idx if idx < len(picker_options) else 0,
    key="existing_picker",
)

# اگر کاربر یک نام موجود را انتخاب کرد → بارگذاری داده و رفتن به حالت ویرایش
if selected_existing and selected_existing != picker_label:
    if selected_existing != st.session_state.editing_name or st.session_state.prefill is None:
        row = df[df["اسم"].astype(str) == selected_existing]
        if not row.empty:
            st.session_state.editing_name = selected_existing
            st.session_state.name_value = selected_existing
            st.session_state.name_input = selected_existing
            st.session_state.prefill = row.iloc[0].to_dict()
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()
else:
    # انتخاب «جدید» → پاک کردن حالت ویرایش
    if st.session_state.editing_name is not None:
        st.session_state.editing_name = None
        st.session_state.prefill = None

prefill = st.session_state.prefill
editing_name = st.session_state.editing_name

def get_val(key, default=""):
    if prefill is None:
        return default
    v = prefill.get(key, default)
    return "" if pd.isna(v) else str(v)

# ─── فرم بقیهٔ اطلاعات (همه اختیاری به‌جز نام که بالا ست) ───
st.divider()
if editing_name:
    st.info(f"در حال ویرایش: **{editing_name}** — در صورت نیاز فیلدها را تغییر دهید.")

with st.form("main_form"):
    st.markdown("### 👤 اطلاعات شخصی (اختیاری)")
    col1, col2, col3 = st.columns(3)
    with col1:
        v_bday = st.text_input("تاریخ تولد", value=get_val("تاریخ تولد"))
    with col2:
        v_age = st.text_input("سن", value=get_val("سن"))
    with col3:
        v_gender = st.text_input("جنسیت", value=get_val("جنسیت"))
    v_birth_place = st.text_input("محل تولد", value=get_val("محل تولد"))

    st.divider()
    st.markdown("### 🔍 جزئیات واقعه (اختیاری)")
    det_col1, det_col2, det_col3 = st.columns(3)
    with det_col1:
        v_province = st.text_input("استان", value=get_val("استان"))
    with det_col2:
        v_city = st.text_input("شهر", value=get_val("شهر"))
    with det_col3:
        v_district_street = st.text_input("محله/خیابان", value=get_val("محله/خیابان"))
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        v_date_shamsi = st.text_input("تاریخ شمسی", value=get_val("تاریخ شمسی"))
    with date_col2:
        v_date_en = st.text_input("تاریخ میلادی", value=get_val("تاریخ میلادی"))
    v_exact_loc = st.text_input("محل دقیق کشته شدن", value=get_val("محل دقیق کشته شدن"))
    v_method = st.text_input("طریقه‌ی کشته شدن", value=get_val("طریقه‌ی کشته شدن"))
    v_grave = st.text_input("آرامگاه", value=get_val("آرامگاه"))

    st.divider()
    st.markdown("### اطلاعات تکمیلی (اختیاری)")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value=get_val("اکانت در شبکه‌های اجتماعی"))
    v_relatives = st.text_input("بستگان در شبکه‌های اجتماعی", value=get_val("بستگان در شبکه‌های اجتماعی"))
    v_notes = st.text_area("توضیحات", value=get_val("توضیحات"))

    submit = st.form_submit_button("💾 ذخیره نهایی")

    if submit:
        # نام نهایی از باکس بالا (الزامی)
        final_name = st.session_state.name_value
        if not final_name:
            st.error("⚠️ وارد کردن نام الزامی است.")
        else:
            data_to_save = {
                "اسم": final_name,
                "استان": v_province,
                "شهر": v_city,
                "محله/خیابان": v_district_street,
                "تاریخ شمسی": v_date_shamsi,
                "تاریخ میلادی": v_date_en,
                "محل دقیق کشته شدن": v_exact_loc,
                "طریقه‌ی کشته شدن": v_method,
                "آرامگاه": v_grave,
                "سن": v_age,
                "جنسیت": v_gender,
                "توضیحات": v_notes,
                "محل تولد": v_birth_place,
                "تاریخ تولد": v_bday,
                "اکانت در شبکه‌های اجتماعی": v_social,
                "بستگان در شبکه‌های اجتماعی": v_relatives,
            }
            try:
                if editing_name:
                    # به‌روزرسانی ردیف موجود
                    current_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                    mask = current_df["اسم"].astype(str) == editing_name
                    if mask.any():
                        for key, val in data_to_save.items():
                            if key in current_df.columns:
                                current_df.loc[mask, key] = val
                        conn.update(spreadsheet=spreadsheet_url, data=current_df)
                        st.success("اطلاعات با موفقیت به‌روزرسانی شد.")
                    else:
                        st.error("ردیف برای ویرایش یافت نشد.")
                else:
                    # افزودن ردیف جدید
                    current_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                    new_df = pd.concat(
                        [current_df, pd.DataFrame([data_to_save])],
                        ignore_index=True,
                    )
                    conn.update(spreadsheet=spreadsheet_url, data=new_df)
                    st.success("اطلاعات با موفقیت ذخیره شد.")
                # پاک کردن حالت ویرایش و نام برای ورودی بعدی
                st.session_state.editing_name = None
                st.session_state.prefill = None
                st.session_state.name_value = ""
                st.session_state.name_input = ""
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()
            except Exception as e:
                err_msg = str(e)
                if "cannot be written" in err_msg.lower() or "unsupported" in err_msg.lower():
                    st.error(
                        "ذخیره فقط با اتصال سرویس‌اکانت (Service Account) ممکن است. "
                        "شیت عمومی فقط خواندنی است."
                    )
                else:
                    st.error(f"خطا در ذخیره‌سازی: {e}")

# دکمه «شروع ورود جدید» برای پاک کردن نام و حالت ویرایش
st.divider()
if st.button("🆕 شروع ورود جدید (پاک کردن نام و حالت ویرایش)"):
    st.session_state.name_value = ""
    st.session_state.name_input = ""
    st.session_state.editing_name = None
    st.session_state.prefill = None
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()
