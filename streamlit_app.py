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

# ۳. اتصال به گوگل‌شیت
try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error(f"خطا در اتصال: {e}")
    st.stop()

# اطمینان از وجود ستون 'اسم'
if "اسم" not in df.columns:
    st.error("ستون 'اسم' در صفحه‌گسترده یافت نشد.")
    st.stop()

names_list = df["اسم"].dropna().unique().tolist()

# منوی جستجوی اصلی برای حالت ویرایش
search_query = st.selectbox(
    "🔍 جستجو برای ویرایش (برای مورد جدید روی گزینه اول بمانید):",
    ["+ افزودن مورد جدید"] + names_list,
)

# ۵. فرم اصلی
with st.form("main_form"):
    if search_query == "+ افزودن مورد جدید":
        st.subheader("✨ ثبت ورودی جدید")

        suggested_name = st.selectbox(
            "جستجوی نام‌های موجود (اگر نام جدید است این را خالی بگذارید):",
            options=names_list,
            index=None,
            placeholder="تایپ کنید تا اسامی مشابه را ببینید...",
        )

        v_name = st.text_input(
            "اسم نهایی برای ثبت:",
            value=suggested_name if suggested_name else "",
            placeholder="نام جدید را اینجا بنویسید...",
        )

        if suggested_name:
            st.warning(
                f"توجه: نام '{suggested_name}' قبلاً ثبت شده است. اگر هدف ثبت فرد جدیدی است، نام را تغییر دهید."
            )
        user_data = None  # در حالت افزودن، user_data تعریف نشده بود در شاخه else
    else:
        st.subheader(f"🔄 ویرایش اطلاعات: {search_query}")
        matches = df[df["اسم"] == search_query]
        if matches.empty:
            st.error("این نام در داده‌ها یافت نشد. لطفاً صفحه را رفرش کنید.")
            st.stop()
        user_data = matches.iloc[0]
        v_name = search_query

    is_new = search_query == "+ افزودن مورد جدید"

    def get_val(key, default=""):
        if is_new or user_data is None:
            return default
        return str(user_data.get(key, default))

    # --- بخش ۱: اطلاعات شخصی ---
    st.markdown("### 👤 اطلاعات شخصی")
    col1, col2, col3 = st.columns(3)
    with col1:
        v_bday = st.text_input("تاریخ تولد", value=get_val("تاریخ تولد"))
    with col2:
        v_age = st.text_input("سن", value=get_val("سن"))
    with col3:
        v_gender = st.text_input("جنسیت", value=get_val("جنسیت"))

    v_birth_place = st.text_input("محل تولد", value=get_val("محل تولد"))

    st.divider()

    # --- بخش ۲: جزئیات واقعه ---
    st.markdown("### 🔍 جزئیات واقعه")

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

    # --- بخش ۳: اطلاعات تکمیلی ---
    v_social = st.text_input(
        "اکانت در شبکه‌های اجتماعی", value=get_val("اکانت در شبکه‌های اجتماعی")
    )
    v_relatives = st.text_input(
        "بستگان در شبکه‌های اجتماعی", value=get_val("بستگان در شبکه‌های اجتماعی")
    )
    v_notes = st.text_area("توضیحات", value=get_val("توضیحات"))

    submit = st.form_submit_button("💾 ذخیره نهایی")

    if submit:
        if not v_name or v_name.strip() == "":
            st.error("⚠️ وارد کردن نام الزامی است.")
        else:
            data_to_save = {
                "اسم": v_name,
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
                if is_new:
                    current_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                    new_df = pd.concat(
                        [current_df, pd.DataFrame([data_to_save])], ignore_index=True
                    )
                    conn.update(spreadsheet=spreadsheet_url, data=new_df)
                else:
                    # به‌روزرسانی در حافظه و سپس یک‌بار نوشتن کل دیتافریم
                    mask = df["اسم"] == search_query
                    for key, val in data_to_save.items():
                        if key in df.columns:
                            df.loc[mask, key] = val
                    conn.update(spreadsheet=spreadsheet_url, data=df)

                st.success("اطلاعات با موفقیت ذخیره شد!")
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()
            except Exception as e:
                err_msg = str(e)
                if "cannot be written" in err_msg.lower() or "unsupported" in err_msg.lower():
                    st.error(
                        "ذخیره‌سازی فقط با اتصال سرویس‌اکانت (Service Account) ممکن است. "
                        "شیت عمومی فقط خواندنی است. در secrets از نوع service_account استفاده کنید."
                    )
                else:
                    st.error(f"خطا در ذخیره‌سازی: {e}")
