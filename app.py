import streamlit as st

st.set_page_config(page_title="VALMAX Analytics", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

pages = st.navigation({
    "VALMAX Analytics": [
        st.Page("pages/0_📋_Leads_Analytics.py", title="Leads Analytics", icon="📋"),
        st.Page("pages/1_📸_Shots_Analytics.py", title="Shots Analytics", icon="📸"),
        st.Page("pages/2_🏆_Competitors.py", title="Competitors", icon="🏆"),
        st.Page("pages/3_🏷️_Tag_Positions.py", title="Tag Positions", icon="🏷️"),
    ]
})

pages.run()
