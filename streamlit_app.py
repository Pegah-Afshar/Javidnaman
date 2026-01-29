import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Friends Information Portal")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 1. SEARCH / DROPDOWN
names_list = df['Name'].dropna().unique().tolist()
search_query = st.selectbox("Search existing names or select 'Add New'", ["+ Add New"] + names_list)

if search_query == "+ Add New":
    st.subheader("Add New Friend")
    with st.form("new_form"):
        new_name = st.text_input("Name")
        new_phone = st.text_input("Phone")
        new_city = st.text_input("City")
        submit = st.form_submit_button("Save New Entry")
        
        if submit:
            # Logic to save goes here
            st.success(f"Added {new_name}!")
else:
    st.subheader(f"Editing: {search_query}")
    # Get the data for the selected person
    user_data = df[df['Name'] == search_query].iloc[0]
    
    with st.form("edit_form"):
        edit_phone = st.text_input("Phone", value=user_data['Phone'])
        edit_city = st.text_input("City", value=user_data['City'])
        update = st.form_submit_button("Update Info")
        
        if update:
            st.info("Update logic triggered!")
