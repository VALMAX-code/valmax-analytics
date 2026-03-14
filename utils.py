import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

CET = timezone(timedelta(hours=1))

@st.cache_data(ttl=120)
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
        return {r['Dataset']: r for r in rows}
    except:
        return {}

def _freshness_badge(ts_str):
    """Return emoji based on how fresh the data is."""
    if not ts_str:
        return "⚪", "немає даних"
    try:
        # Try parsing "2026-03-14 02:07" format
        ts = datetime.strptime(ts_str[:16], '%Y-%m-%d %H:%M').replace(tzinfo=CET)
    except:
        try:
            # Try "14 March 2026, 08:00" format
            ts = datetime.strptime(ts_str, '%d %B %Y, %H:%M').replace(tzinfo=CET)
        except:
            return "⚪", ts_str
    
    now = datetime.now(CET)
    age = now - ts
    hours = age.total_seconds() / 3600
    
    if hours < 6:
        return "🟢", f"{int(hours)}г тому"
    elif hours < 25:
        return "🟡", f"{int(hours)}г тому"
    elif hours < 72:
        days = int(hours / 24)
        return "🟠", f"{days}д тому"
    else:
        days = int(hours / 24)
        return "🔴", f"{days}д тому — застарілі!"
    
def show_last_updated(dataset_name):
    """Display freshness badge + last updated + status for a section."""
    meta = load_meta()
    info = meta.get(dataset_name, {})
    
    ts = info.get('Last Updated', '') if isinstance(info, dict) else str(info)
    status = info.get('Status', '') if isinstance(info, dict) else ''
    details = info.get('Details', '') if isinstance(info, dict) else ''
    schedule = info.get('Cron Schedule', '') if isinstance(info, dict) else ''
    
    badge, age_text = _freshness_badge(ts)
    
    # Status icon
    if status == '✅':
        status_text = '✅ Успішно'
    elif status == '⚠️':
        status_text = f'⚠️ Частково ({details})' if details else '⚠️ Частково'
    elif status == '❌':
        status_text = f'❌ Помилка ({details})' if details else '❌ Помилка'
    else:
        status_text = '⏳ Очікує'
    
    line = f"{badge} Оновлено: **{ts}** CET — {age_text}"
    if status_text:
        line += f"  |  {status_text}"
    if schedule:
        line += f"  |  🔄 {schedule}"
    
    st.caption(line)

def show_section_header(title, dataset_name, icon=""):
    """Show section title with freshness badge inline."""
    meta = load_meta()
    info = meta.get(dataset_name, {})
    ts = info.get('Last Updated', '') if isinstance(info, dict) else ''
    status = info.get('Status', '') if isinstance(info, dict) else ''
    details = info.get('Details', '') if isinstance(info, dict) else ''
    schedule = info.get('Cron Schedule', '') if isinstance(info, dict) else ''
    
    badge, age_text = _freshness_badge(ts)
    status_icon = status if status in ('✅', '⚠️', '❌') else '⏳'
    
    st.markdown(f"### {icon} {title}")
    
    if ts:
        caption = f"{badge} {ts} CET · {age_text} · {status_icon}"
        if details:
            caption += f" {details}"
        if schedule:
            caption += f"  |  🔄 {schedule}"
        st.caption(caption)
    else:
        st.caption(f"⚪ Немає даних про оновлення")
