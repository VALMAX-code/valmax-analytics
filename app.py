import streamlit as st

st.set_page_config(page_title="VALMAX Dribbble", page_icon="🎯", layout="wide",
                   initial_sidebar_state="expanded")

pages = st.navigation({
    "📊 Analytics": [
        st.Page("pages/0_📋_Leads_Analytics.py", title="Leads Analytics", icon="📋"),
        st.Page("pages/1_📸_Shots_Analytics.py", title="Shots Analytics", icon="📸"),
        st.Page("pages/4_🏎️_Race.py", title="Monthly Race", icon="🏎️"),
    ],
    "🔎 Research": [
        st.Page("pages/2_🏆_Competitors.py", title="Competitors", icon="🏆"),
        st.Page("pages/3_🏷️_Tag_Positions.py", title="Tag Positions", icon="🏷️"),
        st.Page("pages/5_🔍_Tag_Validator.py", title="Tag Validator", icon="🔍"),
    ],
    "💼 Business": [
        st.Page("pages/6_💰_Profitability.py", title="Profitability", icon="💰"),
    ],
    "⚙️ System": [
        st.Page("pages/7_🛡️_System_Health.py", title="System Health", icon="🛡️"),
    ],
})

pages.run()
