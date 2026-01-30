import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ─── صفحه و استایل ───
st.set_page_config(page_title="ثبت و ویرایش اطلاعات", layout="wide")

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

# ─── اتصال به گوگل‌شیت ───
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

NEW_PERSON_LABEL = "— نام جدید؛ در لیست نیست —"

# ─── Session state ───
if "name" not in st.session_state:
    st.session_state.name = ""
if "name_input" not in st.session_state:
    st.session_state.name_input = ""
if "editing_name" not in st.session_state:
    st.session_state.editing_name = None
if "prefill" not in st.session_state:
    st.session_state.prefill = None
if "_df" not in st.session_state:
    st.session_state._df = df

def on_dropdown_pick():
    """وقتی کاربر از dropdown یک نام موجود را انتخاب کند، داده را بارگذاری کن."""
    chosen = st.session_state.get("name_picker")
    if not chosen or chosen == NEW_PERSON_LABEL:
        st.session_state.editing_name = None
        st.session_state.prefill = None
        return
    d = st.session_state._df
    row = d[d["اسم"].astype(str) == chosen]
    if not row.empty:
        st.session_state.editing_name = chosen
        st.session_state.name = chosen
        st.session_state["name_input"] = chosen
        st.session_state.prefill = row.iloc[0].to_dict()

# ─── فقط یک باکس برای نام ───
st.markdown("### نام (الزامی)")
st.caption("نام را تایپ کنید، سپس یک بار بیرون از باکس کلیک کنید یا Tab بزنید تا لیست اسامی مشابه ظاهر شود. اگر نام در لیست بود انتخاب کنید (ویرایش)، وگرنه ادامه تایپ و ذخیره.")

# تنها باکس نام — فقط از key استفاده می‌کنیم تا مقدار همیشه از session بیاید
st.text_input(
    "نام",
    key="name_input",
    placeholder="نام را اینجا تایپ کنید... بعد Tab یا کلیک به باکس بعدی.",
    label_visibility="visible",
)
# منبع واحد برای «متن تایپ‌شده» از باکس نام
current_name = (st.session_state.get("name_input") or "").strip()
st.session_state.name = current_name

# dropdown اسامی مشابه — همیشه وقتی کاربر چیزی تایپ کرده نشان داده می‌شود
st.session_state._df = df
matches = [n for n in names_list if current_name and current_name.lower() in n.lower()]
pick_options = [NEW_PERSON_LABEL] + matches

# اگر مقدار ذخیره‌شدهٔ dropdown در لیست فعلی نیست، به «نام جدید» برگردان
if "name_picker" in st.session_state and st.session_state["name_picker"] not in pick_options:
    st.session_state["name_picker"] = NEW_PERSON_LABEL

if current_name:
    if matches:
        st.markdown(f"**اسامی مشابه ({len(matches)} مورد) — برای ویرایش یکی را انتخاب کنید:**")
    else:
        st.markdown("**هیچ نام مشابهی در لیست نیست؛ همین نام به‌عنوان مورد جدید ذخیره می‌شود.**")
    chosen = st.selectbox(
        "اسامی مشابه",
        options=pick_options,
        index=pick_options.index(st.session_state.get("name_picker", NEW_PERSON_LABEL)) if st.session_state.get("name_picker", NEW_PERSON_LABEL) in pick_options else 0,
        key="name_picker",
        label_visibility="collapsed",
        on_change=on_dropdown_pick,
    )
    if chosen == NEW_PERSON_LABEL and st.session_state.editing_name is not None:
        st.session_state.editing_name = None
        st.session_state.prefill = None
else:
    if st.session_state.editing_name is not None:
        st.session_state.editing_name = None
        st.session_state.prefill = None
    st.session_state["name_picker"] = NEW_PERSON_LABEL

editing_name = st.session_state.editing_name
prefill = st.session_state.prefill

def get_val(key, default=""):
    if prefill is None:
        return default
    v = prefill.get(key, default)
    return "" if pd.isna(v) else str(v)

# ─── فرم: بقیهٔ فیلدها (نام فقط در باکس بالا است) ───
st.divider()
if editing_name:
    st.info(f"در حال ویرایش: **{editing_name}**")

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
    c1, c2, c3 = st.columns(3)
    with c1:
        v_province = st.text_input("استان", value=get_val("استان"))
    with c2:
        v_city = st.text_input("شهر", value=get_val("شهر"))
    with c3:
        v_district_street = st.text_input("محله/خیابان", value=get_val("محله/خیابان"))
    d1, d2 = st.columns(2)
    with d1:
        v_date_shamsi = st.text_input("تاریخ شمسی", value=get_val("تاریخ شمسی"))
    with d2:
        v_date_en = st.text_input("تاریخ میلادی", value=get_val("تاریخ میلادی"))
    v_exact_loc = st.text_input("محل دقیق کشته شدن", value=get_val("محل دقیق کشته شدن"))
    v_method = st.text_input("طریقه‌ی کشته شدن", value=get_val("طریقه‌ی کشته شدن"))
    v_grave = st.text_input("آرامگاه", value=get_val("آرامگاه"))

    st.divider()
    st.markdown("### اطلاعات تکمیلی (اختیاری)")
    v_social = st.text_input("اکانت در شبکه‌های اجتماعی", value=get_val("اکانت در شبکه‌های اجتماعی"))
    v_relatives = st.text_input("بستگان در شبکه‌های اجتماعی", value=get_val("بستگان در شبکه‌های اجتماعی"))
    v_notes = st.text_area("توضیحات", value=get_val("توضیحات"))

    submitted = st.form_submit_button("💾 ذخیره نهایی")

    if submitted:
        final_name = st.session_state.name
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
                    current_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
                    new_df = pd.concat([current_df, pd.DataFrame([data_to_save])], ignore_index=True)
                    conn.update(spreadsheet=spreadsheet_url, data=new_df)
                    st.success("اطلاعات با موفقیت ذخیره شد.")
                st.session_state.editing_name = None
                st.session_state.prefill = None
                st.session_state.name = ""
                if "name_input" in st.session_state:
                    st.session_state.name_input = ""
                if hasattr(st, "rerun"):
                    st.rerun()
                else:
                    st.experimental_rerun()
            except Exception as e:
                err_msg = str(e)
                if "cannot be written" in err_msg.lower() or "unsupported" in err_msg.lower():
                    st.error("ذخیره فقط با اتصال سرویس‌اکانت ممکن است. شیت عمومی فقط خواندنی است.")
                else:
                    st.error(f"خطا در ذخیره‌سازی: {e}")

st.divider()
if st.button("🆕 شروع ورود جدید"):
    st.session_state.name = ""
    st.session_state.editing_name = None
    st.session_state.prefill = None
    if "name_input" in st.session_state:
        st.session_state.name_input = ""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()
