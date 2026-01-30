import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="ثبت اطلاعات", layout="wide")
st.title("📋 فرم ثبت و ویرایش اطلاعات")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# Define all your columns exactly as they are in the sheet
cols = [
    "اسم", "شهر", "محله/خیابان", "استان", "تاریخ", "تاریخ میلادی", 
    "سن", "جنسیت", "توضیحات", "محل دقیق کشته شدن", "طریقه‌ی کشته شدن", 
    "آرامگاه", "محل تولد", "تاریخ تولد", "اکانت در شبکه‌های اجتماعی", 
    "بستگان در شبکه‌های اجتماعی"
]

# Search / Autocomplete by 'اسم'
names_list = df['اسم'].dropna().unique().tolist()
search_query = st.selectbox("جستجوی نام یا انتخاب جدید:", ["+ افزودن مورد جدید"] + names_list)

if search_query == "+ افزودن مورد جدید":
    st.subheader("📝 ورود اطلاعات جدید")
    with st.form("add_form", clear_on_submit=True):
        inputs = {}
        # Create input boxes for every column
        for col in cols:
            inputs[col] = st.text_input(col)
        
        submit = st.form_submit_button("ذخیره اطلاعات جدید")
        
        if submit:
            if inputs["اسم"] == "":
                st.error("وارد کردن 'اسم' الزامی است.")
            elif inputs["اسم"] in names_list:
                st.error("این اسم قبلاً ثبت شده است. لطفاً از بخش ویرایش استفاده کنید.")
            else:
                new_row = pd.DataFrame([inputs])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"اطلاعات {inputs['اسم']} با موفقیت ذخیره شد.")

else:
    st.subheader(f"🔄 ویرایش اطلاعات: {search_query}")
    user_data = df[df['اسم'] == search_query].iloc[0]
    
    with st.form("edit_form"):
        updated_inputs = {}
        for col in cols:
            # We skip 'اسم' so they don't accidentally change the primary name
            if col == "اسم":
                updated_inputs[col] = search_query
                st.write(f"**نام:** {search_query}")
            else:
                updated_inputs[col] = st.text_input(col, value=str(user_data[col]))
        
        update_btn = st.form_submit_button("بروزرسانی تغییرات")
        
        if update_btn:
            # Update the row in the dataframe
            df.loc[df['اسم'] == search_query, cols] = [updated_inputs[c] for c in cols]
            conn.update(data=df)
            st.success("تغییرات با موفقیت در گوگل شیت اعمال شد.")
