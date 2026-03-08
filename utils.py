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

def show_last_updated(dataset_name):
    """Display last updated caption for a specific dataset."""
    meta = load_meta()
    ts = meta.get(dataset_name, None)
    if ts:
        st.caption(f"🕐 Останнє оновлення даних: {ts} CET")
    else:
        import datetime as _dt
        _now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=1)))
        st.caption(f"🕐 Останнє оновлення даних: {_now.strftime('%d %B %Y, %H:%M')} CET")
