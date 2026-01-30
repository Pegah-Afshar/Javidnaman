import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Friends Database", layout="centered")
st.title("👯 Friends Info Portal")

# 1. Connect to Google Sheets
# This uses the secrets you just saved
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Read the current data
# We clear the cache so we always see the newest info
df = conn.read(ttl=0) 

# 3. Search / Autocomplete Feature
names_list = df['Name'].dropna().unique().tolist()
search_query = st.selectbox("Type a name to search or Edit:", ["+ Add New Person"] + names_list)

# --- OPTION: ADD NEW PERSON ---
if search_query == "+ Add New Person":
    st.subheader("📝 Add a New Friend")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        city = st.text_input("City")
        notes = st.text_area("Notes")
        
        submit = st.form_submit_button("Save to List")
        
        if submit:
            if name in names_list:
                st.error(f"Error: '{name}' is already in the list! Use the search bar above to edit them.")
            elif name == "":
                st.warning("Please enter a name.")
            else:
                # Create a new row
                new_data = pd.DataFrame([{"Name": name, "Phone": phone, "City": city, "Notes": notes}])
                # Add to existing data
                updated_df = pd.concat([df, new_data], ignore_index=True)
                # Update the Google Sheet
                conn.update(data=updated_df)
                st.success(f"Successfully added {name}!")
                st.balloons()

# --- OPTION: EDIT EXISTING PERSON ---
else:
    st.subheader(f"Update Info for: {search_query}")
    # Pull the current data for this specific person
    user_row = df[df['Name'] == search_query].iloc[0]
    
    with st.form("edit_form"):
        # We fill the boxes with the OLD info so they can just change what they need
        new_phone = st.text_input("Phone Number", value=str(user_row['Phone']))
        new_city = st.text_input("City", value=str(user_row['City']))
        new_notes = st.text_area("Notes", value=str(user_row['Notes']))
        
        update_button = st.form_submit_button("Save Changes")
        
        if update_button:
            # Find where this person is in the list and update them
            df.loc[df['Name'] == search_query, ['Phone', 'City', 'Notes']] = [new_phone, new_city, new_notes]
            # Update the Google Sheet
            conn.update(data=df)
            st.success("Information updated successfully!")
