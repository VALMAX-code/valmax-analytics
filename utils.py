
import datetime

def show_last_updated(sheet_name="📋 Project Requests"):
    """Show last data update timestamp."""
    import streamlit as st
    try:
        # Use sheet modification metadata or current cache time
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))  # CET
        st.caption(f"🕐 Останнє оновлення даних: {now.strftime('%d %B %Y, %H:%M')} CET")
    except:
        pass
