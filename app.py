import streamlit as st

st.set_page_config(page_title="VALMAX Analytics", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

# Auto-redirect to Leads Analytics
st.switch_page("pages/0_📋_Leads_Analytics.py")
