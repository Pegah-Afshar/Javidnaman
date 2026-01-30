import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
st.set_page_config(
    page_title="ثبت و ویرایش اطلاعات",
    layout="wide"
)
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
input, textarea { direction: rtl; text-align: right; }
div[data-baseweb="select"] { direction: rtl; }
.stButton button {
    display: block;
    margin-left: auto;
    background-color: #4CAF50;
    color: white;
}
</style>
""", unsafe_allow_html=True)
st.title("📋 پنل جامع ثبت و ویرایش اطلاعات")

try:
    spreadsheet_url = st.secrets["public_gsheets_url"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=spreadsheet_url, ttl=0)
except Exception as e:
    st.error(f"خطا در اتصال به گوگل‌شیت: {e}")
    st.stop()
if "اسم" not in df.columns:
    st.error("ستون «اسم» در شیت وجود ندارد.")
    st.stop()
names_list = (
    df["اسم"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
if "editing_name" not in st.session_state:
    st.session_state.editing_name = None

if "prefill" not in st.session_state:
    st.session_state.prefill = None
st.markdown("### ۱. نام")
name = st.combobox(
    "نام",
    options=names_list,
    placeholder="نام",
)
if not name:
    st.stop()
if name in names_list:
    st.session_state.editing_name = name
    row = df[df["اسم"].astype(str) == name].iloc[0]
    st.session_state.prefill = row.to_dict()
else:
    st.session_state.editing_name = None
    st.session_state.prefill = None
if st.session_state.editing_name:
    st.info(f" ویرایش اطلاعات: **{name}**")
def get_val(key):
    if not st.session_state.prefill:
        return ""
    val = st.session_state.prefill.get(key, "")
    return "" if pd.isna(val) else str(val)
with st.form("main_form"):
    st.markdown("### 👤 اطلاعات شخصی)")

    col1, col2, col3 = st.columns(3)
    with col1:
        v_bday = st.text_input("تاریخ تولد", value=get_val("تاریخ تولد"))
    with col2:
        v_age = st.text_input("سن", value=get_val("سن"))
    with col3:
        v_gender = st.text_input("جنسیت", value=get_val("جنسیت"))

    v_birth_place = st.text_input("محل تولد", value=get_val("محل تولد"))

    st.divider()
    st.markdown("### 🔍 جزئیات واقعه ")

    c1, c2, c3 = st.columns(3)
    with c1:
        v_province = st.text_input("استان", value=get_val("استان"))
    with c2:
        v_city = st.text_input("شهر", value=get_val("شهر"))
    with c3:
        v_street = st.text_input("محله/خیابان", value=get_val("محله/خیابان"))

    d1, d2 = st.columns(2)
    with d1:
        v_date_shamsi = st.text_input("تاریخ شمسی", value=get_val("تاریخ شمسی"))
    with d2:
        v_date_en = st.text_input("تاریخ میلادی", value=get_val("تاریخ میلادی"))

    v_exact_loc = st.text_input("محل دقیق کشته شدن", value=get_val("محل دقیق کشته شدن"))
    v_method = st.text_input("طریقه‌ی کشته شدن", value=get_val("طریقه‌ی کشته شدن"))
    v_grave = st.text_input("آرامگاه", value=get_val("آرامگاه"))

    st.divider()
    st.markdown("### اطلاعات تکمیلی ")

    v_social = st.text_input(
        "اکانت در شبکه‌های اجتماعی",
        value=get_val("اکانت در شبکه‌های اجتماعی")
    )
    v_relatives = st.text_input(
        "بستگان در شبکه‌های اجتماعی",
        value=get_val("بستگان در شبکه‌های اجتماعی")
    )
    v_notes = st.text_area("توضیحات", value=get_val("توضیحات"))

    submitted = st.form_submit_button("💾 ذخیره نهایی")

if submitted:
    data = {
        "اسم": name,
        "تاریخ تولد": v_bday,
        "سن": v_age,
        "جنسیت": v_gender,
        "محل تولد": v_birth_place,
        "استان": v_province,
        "شهر": v_city,
        "محله/خیابان": v_street,
        "تاریخ شمسی": v_date_shamsi,
        "تاریخ میلادی": v_date_en,
        "محل دقیق کشته شدن": v_exact_loc,
        "طریقه‌ی کشته شدن": v_method,
        "آرامگاه": v_grave,
        "اکانت در شبکه‌های اجتماعی": v_social,
        "بستگان": v_relatives,
        "توضیحات": v_notes,
    }

    current_df = conn.read(spreadsheet=spreadsheet_url, ttl=0)

    if st.session_state.editing_name:
        mask = current_df["اسم"].astype(str) == name
        for k, v in data.items():
            if k in current_df.columns:
                current_df.loc[mask, k] = v
        conn.update(spreadsheet=spreadsheet_url, data=current_df)
        st.success("اطلاعات با موفقیت به‌روزرسانی شد.")
    else:
        current_df = pd.concat(
            [current_df, pd.DataFrame([data])],
            ignore_index=True
        )
        conn.update(spreadsheet=spreadsheet_url, data=current_df)
        st.success("اطلاعات جدید ذخیره شد.")

    st.session_state.editing_name = None
    st.session_state.prefill = None
    st.rerun()

st.divider()

if st.button("🆕 شروع ورود جدید"):
    st.session_state.editing_name = None
    st.session_state.prefill = None
    st.rerun()
