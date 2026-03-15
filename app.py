import streamlit as st
import base64
from pathlib import Path

st.set_page_config(page_title="VALMAX Dribbble", page_icon="🎯", layout="wide",
                   initial_sidebar_state="expanded")

# Logo in sidebar
logo_path = Path(__file__).parent / "assets" / "valmax-logo.png"
if logo_path.exists():
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    st.sidebar.markdown(f"""
    <div style="text-align:center; padding: 10px 0 5px 0;">
        <img src="data:image/png;base64,{logo_b64}" style="width:160px; border-radius:8px;">
    </div>
    """, unsafe_allow_html=True)

# Sidebar styling
st.markdown("""<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%) !important;
}
section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
section[data-testid="stSidebar"] a { color: #c4b5fd !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span {
    font-size: 1.1rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] [data-testid="stSidebarNavSeparator"] span {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8b8ba3 !important;
}
</style>""", unsafe_allow_html=True)

pages = st.navigation({
    "💼 SALES": [
        st.Page("pages/0_📋_Project_Requests.py", title="Project Requests", icon="📋"),
        st.Page("pages/8_📝_Brief_Submissions.py", title="Brief Submissions", icon="📝"),
        st.Page("pages/9_🔎_Browse_Briefs.py", title="Browse Project Briefs", icon="🔎"),
    ],
    "📊 ANALYTICS": [
        st.Page("pages/1_📸_Shots_Analytics.py", title="Shots Analytics", icon="📸"),
        st.Page("pages/4_🏎️_Race.py", title="Monthly Race", icon="🏎️"),
        st.Page("pages/2_🏆_Competitors.py", title="Competitors", icon="🏆"),
    ],
    "🔎 RESEARCH": [
        st.Page("pages/3_🏷️_Tag_Positions.py", title="Tag Positions", icon="🏷️"),
        st.Page("pages/5_🔍_Tag_Validator.py", title="Tag Validator", icon="🔍"),
    ],
    "💼 BUSINESS": [
        st.Page("pages/6_💰_Profitability.py", title="Profitability", icon="💰"),
    ],
    "⚙️ SYSTEM": [
        st.Page("pages/7_🛡️_System_Health.py", title="System Health", icon="🛡️"),
    ],
})

pages.run()
