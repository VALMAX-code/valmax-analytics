import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

@st.cache_data(ttl=300)
def load_meta():
    """Load last-updated timestamps from Meta sheet."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws = sh.worksheet("📅 Meta")
        rows = ws.get_all_records()
        return {r['Dataset']: r['Last Updated'] for r in rows}
    except:
        return {}

CRON_SCHEDULE = {
    "Leads (Project Requests)": "Щогодини (hourly cron)",
    "Leads (Project Intros)": "Щогодини (hourly cron)",
    "Shots Analytics": "Щопонеділка, 8:00 CET",
    "Tag Positions": "Щотижня (weekly cron)",
    "SEO Data (Volume/CPC)": "Щомісяця (monthly cron)",
    "SERP Data (Google Pos)": "Щомісяця (monthly cron)",
    "Competitors": "Щоденно, 9:00 CET",
    "Popular Tracker": "Щоденно, 12:00 CET",
}

def show_last_updated(dataset_name):
    """Display last updated + next update caption."""
    meta = load_meta()
    ts = meta.get(dataset_name, None)
    next_update = CRON_SCHEDULE.get(dataset_name, "")
    
    if ts:
        line = f"🕐 Останнє оновлення: {ts} CET"
    else:
        import datetime as _dt
        _now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=1)))
        line = f"🕐 Останнє оновлення: {_now.strftime('%d %B %Y, %H:%M')} CET"
    
    if next_update:
        line += f"  ·  🔄 Наступне: {next_update}"
    
    st.caption(line)
