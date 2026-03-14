import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="System Health", page_icon="🛡️", layout="wide")

CET = timezone(timedelta(hours=1))

st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
[data-testid="stSidebar"] * { color: white !important; }
</style>""", unsafe_allow_html=True)

st.markdown("# 🛡️ System Health & Operations")
st.caption("Live status від усіх data pipelines — оновлюється автоматично з Meta sheet")

# --- LOAD META + DATA ---
@st.cache_data(ttl=120)
def load_all():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key("1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc")
    
    # Meta
    meta_ws = sh.worksheet("📅 Meta")
    meta_rows = meta_ws.get_all_records()
    meta = {r['Dataset']: r for r in meta_rows}
    
    # Live counts
    counts = {}
    try:
        sa = sh.worksheet("📊 Shots Analytics")
        titles = sa.get('C2:C250')
        counts['shots'] = len([r for r in titles if r and r[0] and r[0].strip()])
        profile = sa.get('N1:N5')
        counts['followers'] = profile[0][0] if profile and profile[0] else '?'
    except:
        counts['shots'] = '?'
    
    try:
        pr = sh.worksheet("📋 Project Requests")
        leads = pr.get('C2:C100')
        counts['leads'] = len([r for r in leads if r and r[0] and r[0].strip()])
    except:
        counts['leads'] = '?'
    
    try:
        tp = sh.worksheet("🏷️ Tag Positions")
        counts['tag_positions'] = len(tp.col_values(1)) - 1
    except:
        counts['tag_positions'] = '?'
    
    try:
        comp = sh.worksheet("🏆 Competitors")
        counts['competitors'] = len(comp.get_all_values()) - 1
    except:
        counts['competitors'] = '?'
    
    try:
        pt = sh.worksheet("⭐ Popular Tracker")
        pt_data = pt.get_all_values()
        found = len([r for r in pt_data[1:] if len(r) > 3 and r[3] == 'Yes'])
        counts['popular_found'] = found
    except:
        counts['popular_found'] = '?'
    
    # Cron Log — last 20 entries
    try:
        cl = sh.worksheet("📋 Cron Log")
        log_data = cl.get_all_values()
        counts['cron_log'] = log_data[-20:] if len(log_data) > 20 else log_data[1:]
    except:
        counts['cron_log'] = []
    
    return meta, counts

try:
    meta, counts = load_all()
except Exception as e:
    st.error(f"❌ Не вдалося завантажити дані: {e}")
    st.stop()

# --- FRESHNESS HELPER ---
def freshness(ts_str):
    if not ts_str:
        return "⚪", "немає даних", 999
    try:
        ts = datetime.strptime(ts_str[:16], '%Y-%m-%d %H:%M').replace(tzinfo=CET)
    except:
        try:
            ts = datetime.strptime(ts_str, '%d %B %Y, %H:%M').replace(tzinfo=CET)
        except:
            return "⚪", ts_str, 999
    hours = (datetime.now(CET) - ts).total_seconds() / 3600
    if hours < 6: return "🟢", f"{int(hours)}г тому", hours
    elif hours < 25: return "🟡", f"{int(hours)}г тому", hours
    elif hours < 72: return "🟠", f"{int(hours/24)}д тому", hours
    else: return "🔴", f"{int(hours/24)}д тому", hours

# === OVERVIEW METRICS ===
st.markdown("## 📊 Поточний стан")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("📸 Shots", counts.get('shots', '?'))
m2.metric("👥 Followers", counts.get('followers', '?'))
m3.metric("📋 Leads", counts.get('leads', '?'))
m4.metric("🏷️ Tag Positions", counts.get('tag_positions', '?'))
m5.metric("🏆 Competitors", counts.get('competitors', '?'))

st.divider()

# === PIPELINE STATUS ===
st.markdown("## 🔄 Pipeline Status")
st.caption("Статус кожного data pipeline — дані з Meta sheet")

# Define pipelines with expected freshness
pipelines = [
    {"dataset": "Profile Stats", "icon": "👤", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Shots Analytics", "icon": "📸", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Monthly Summary", "icon": "📈", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Popular Tracker", "icon": "⭐", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Leads (Project Requests)", "icon": "📋", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Leads Normalization", "icon": "🔧", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "Follower Growth", "icon": "📈", "freq": "Monthly (1st)", "max_hours": 800},
    {"dataset": "Tag Positions", "icon": "🏷️", "freq": "Monthly (2nd)", "max_hours": 800},
    {"dataset": "Competitors", "icon": "🏆", "freq": "Monthly (1st)", "max_hours": 800},
    {"dataset": "Competitor Shots", "icon": "🏆", "freq": "Monthly (1st)", "max_hours": 800},
    {"dataset": "Pipedrive Sync", "icon": "🔗", "freq": "Daily (Mon-Fri)", "max_hours": 30},
    {"dataset": "QuickBooks Sync", "icon": "💰", "freq": "Monthly (15th)", "max_hours": 800},
    {"dataset": "Profitability", "icon": "💰", "freq": "Monthly (15th)", "max_hours": 800},
    {"dataset": "SEO Data (Volume/CPC)", "icon": "🔍", "freq": "Weekly (Wed)", "max_hours": 200},
    {"dataset": "SERP Data (Google Pos)", "icon": "🔍", "freq": "Weekly (Wed)", "max_hours": 200},
]

# Count statuses
ok_count = warn_count = error_count = pending_count = 0

for p in pipelines:
    info = meta.get(p["dataset"], {})
    ts = info.get("Last Updated", "")
    status = info.get("Status", "")
    details = info.get("Details", "")
    
    badge, age_text, hours = freshness(ts)
    
    if status == "✅" and hours < p["max_hours"]:
        ok_count += 1
    elif status == "❌":
        error_count += 1
    elif status == "⚠️" or hours > p["max_hours"]:
        warn_count += 1
    else:
        pending_count += 1

h1, h2, h3, h4 = st.columns(4)
h1.metric("✅ OK", ok_count)
h2.metric("⚠️ Warnings", warn_count)
h3.metric("🚨 Errors", error_count)
h4.metric("⏳ Pending", pending_count)

if error_count > 0:
    st.error(f"🚨 {error_count} pipeline(s) з помилками!")
elif warn_count > 0:
    st.warning(f"⚠️ {warn_count} pipeline(s) потребують уваги")
else:
    st.success("✅ Усі pipelines працюють нормально!")

# Pipeline table
rows = []
for p in pipelines:
    info = meta.get(p["dataset"], {})
    ts = info.get("Last Updated", "")
    status = info.get("Status", "⏳")
    details = info.get("Details", "")
    schedule = info.get("Cron Schedule", p["freq"])
    
    badge, age_text, hours = freshness(ts)
    
    # Determine health
    if status == "✅" and hours < p["max_hours"]:
        health = "🟢"
    elif status == "❌":
        health = "🔴"
    elif hours > p["max_hours"] * 2:
        health = "🔴"
    elif status == "⚠️" or hours > p["max_hours"]:
        health = "🟡"
    elif not ts:
        health = "⚪"
    else:
        health = "🟢"
    
    rows.append({
        "": health,
        "Pipeline": f"{p['icon']} {p['dataset']}",
        "Last Updated": ts if ts else "—",
        "Age": age_text if ts else "—",
        "Status": f"{status} {details}" if details else status,
        "Schedule": schedule,
    })

df_pipes = pd.DataFrame(rows)
st.dataframe(df_pipes, use_container_width=True, hide_index=True, height=560)

st.divider()

# === CRON LOG ===
st.markdown("## 📋 Recent Cron Log")
st.caption("Останні 20 записів з Cron Log sheet")

cron_log = counts.get('cron_log', [])
if cron_log:
    # Try to make a dataframe from log entries
    log_rows = []
    for entry in cron_log:
        if len(entry) >= 3:
            log_rows.append({
                "Timestamp": entry[0],
                "Cron": entry[1] if len(entry) > 1 else "",
                "Details": entry[2] if len(entry) > 2 else "",
                "Status": entry[3] if len(entry) > 3 else "",
            })
    if log_rows:
        df_log = pd.DataFrame(log_rows)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
else:
    st.info("Немає записів у Cron Log")

st.divider()

# === OPERATIONS RULES ===
st.markdown("## 📋 Operations Rules")
st.caption("Критичні правила для data pipelines")

rules = [
    ("🚫", "НІКОЛИ ws.clear() на production sheets", "critical"),
    ("🚫", "НІКОЛИ перезаписувати всі шоти — тільки APPEND нові", "critical"),
    ("🚫", "Sonnet crons НЕ повинні генерувати фейкові дані при збої API", "critical"),
    ("✅", "Валідація після кожного запису — перевірити row count", "medium"),
    ("✅", "Red Flag: падіння даних >20% = СТОП + алерт", "medium"),
    ("✅", "Дати завжди YYYY-MM-DD", "medium"),
    ("✅", "Budget (CRM) тільки якщо відрізняється від Dribbble", "medium"),
    ("📝", "Скрейпінг: 5-7с затримка між сторінками, max 100 pages/session", "info"),
    ("📝", "Browser CDP на порті 18800, профіль 'openclaw'", "info"),
]

for icon, text, severity in rules:
    color = {"critical": "#dc3545", "medium": "#ffc107", "info": "#6c757d"}[severity]
    bg = {"critical": "#fff5f5", "medium": "#fffdf0", "info": "#f8f9fa"}[severity]
    st.markdown(f'<div style="background:{bg};border-left:4px solid {color};padding:10px;border-radius:4px;margin:4px 0;">{icon} {text}</div>', unsafe_allow_html=True)
