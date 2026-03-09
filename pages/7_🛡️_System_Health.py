import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

st.set_page_config(page_title="System Health", page_icon="🛡️", layout="wide")

# --- STYLE ---
st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
[data-testid="stSidebar"] * { color: white !important; }
.health-ok { background: #d4edda; border-left: 4px solid #28a745; padding: 12px; border-radius: 4px; margin: 8px 0; }
.health-warn { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 4px; margin: 8px 0; }
.health-error { background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; border-radius: 4px; margin: 8px 0; }
.rule-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 8px 0; }
</style>""", unsafe_allow_html=True)

st.markdown("# 🛡️ System Health & Operations")
st.caption("Автоматична перевірка даних, правила, крони, документація")

# --- LOAD DATA ---
@st.cache_data(ttl=120)
def run_health_check():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key("1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc")
    
    checks = []
    
    # 1. Shots check
    ws = sh.worksheet("📊 Shots Analytics")
    titles = ws.get('C2:C250')
    shot_count = len([r for r in titles if r and r[0] and r[0].strip()])
    
    # Engagement check
    eng_data = ws.get('H2:H250')
    bad_eng = 0
    for r in eng_data:
        if r and r[0]:
            try:
                val = float(r[0].replace('%', ''))
                if val > 50:
                    bad_eng += 1
            except:
                pass
    
    # Monthly summary
    monthly = ws.get('M14:M16')
    has_monthly = bool(monthly and monthly[0] and monthly[0][0])
    
    # Profile stats
    profile = ws.get('M1:N2')
    has_profile = bool(profile and len(profile) >= 2)
    
    # Duplicates
    title_list = [r[0] for r in titles if r and r[0]]
    dupes = [t for t in set(title_list) if title_list.count(t) > 1]
    
    checks.append({
        'section': '📸 Shots Analytics',
        'checks': [
            {'name': 'Кількість шотів', 'value': shot_count, 'expected': '210+', 
             'status': 'ok' if shot_count >= 200 else ('warn' if shot_count >= 150 else 'error')},
            {'name': 'Engagement% < 50%', 'value': f'{bad_eng} помилок', 'expected': '0',
             'status': 'ok' if bad_eng == 0 else 'error'},
            {'name': 'Monthly Summary (M14:R)', 'value': '✅ Є' if has_monthly else '❌ Відсутній', 'expected': 'Є',
             'status': 'ok' if has_monthly else 'error'},
            {'name': 'Profile Stats (M1:N5)', 'value': '✅ Є' if has_profile else '❌ Відсутній', 'expected': 'Є',
             'status': 'ok' if has_profile else 'error'},
            {'name': 'Дублікати', 'value': f'{len(dupes)} ({", ".join(dupes[:2])})' if dupes else '0', 'expected': '0',
             'status': 'ok' if not dupes else 'warn'},
        ]
    })
    
    # 2. Leads check
    ws_leads = sh.worksheet("📋 Project Requests")
    lead_data = ws_leads.get('C2:C50')
    lead_count = len([r for r in lead_data if r and r[0] and r[0].strip()])
    
    checks.append({
        'section': '📋 Leads (Project Requests)',
        'checks': [
            {'name': 'Кількість лідів', 'value': lead_count, 'expected': '9+',
             'status': 'ok' if lead_count >= 9 else 'warn'},
        ]
    })
    
    # 3. Keywords check
    ws_kw = sh.worksheet("🔑 Dribbble Keywords")
    kw_count = len(ws_kw.col_values(1)) - 1  # minus header
    
    checks.append({
        'section': '🔑 Keywords Database',
        'checks': [
            {'name': 'Кількість keywords', 'value': f'{kw_count:,}', 'expected': '297K+',
             'status': 'ok' if kw_count >= 290000 else ('warn' if kw_count >= 100000 else 'error')},
        ]
    })
    
    # 4. Tag Positions
    ws_tp = sh.worksheet("🏷️ Tag Positions")
    tp_count = len(ws_tp.col_values(1)) - 1
    
    checks.append({
        'section': '🏷️ Tag Positions',
        'checks': [
            {'name': 'Позицій в тегах', 'value': tp_count, 'expected': '327+',
             'status': 'ok' if tp_count >= 300 else 'warn'},
        ]
    })
    
    return checks, shot_count, lead_count

try:
    checks, shot_count, lead_count = run_health_check()
    
    # --- HEALTH STATUS ---
    st.markdown("## 🔍 Live Data Validation")
    st.caption("Автоматична перевірка всіх Google Sheet таблиць на цілісність")
    
    total_ok = sum(1 for s in checks for c in s['checks'] if c['status'] == 'ok')
    total_warn = sum(1 for s in checks for c in s['checks'] if c['status'] == 'warn')
    total_error = sum(1 for s in checks for c in s['checks'] if c['status'] == 'error')
    total = total_ok + total_warn + total_error
    
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("✅ Passed", total_ok)
    h2.metric("⚠️ Warnings", total_warn)
    h3.metric("🚨 Errors", total_error)
    h4.metric("📊 Total Checks", total)
    
    if total_error > 0:
        st.error("🚨 Є критичні помилки! Потрібна ручна перевірка.")
    elif total_warn > 0:
        st.warning("⚠️ Є попередження — не критично, але варто перевірити.")
    else:
        st.success("✅ Всі перевірки пройдені! Дані в нормі.")
    
    for section in checks:
        st.markdown(f"### {section['section']}")
        for check in section['checks']:
            icon = {'ok': '✅', 'warn': '⚠️', 'error': '🚨'}[check['status']]
            css_class = {'ok': 'health-ok', 'warn': 'health-warn', 'error': 'health-error'}[check['status']]
            st.markdown(f"""<div class="{css_class}">
                {icon} <b>{check['name']}</b>: {check['value']} (очікується: {check['expected']})
            </div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Не вдалося виконати перевірку: {e}")

# --- CRON SCHEDULE ---
st.divider()
st.markdown("## ⏰ Cron Jobs (Автоматичні задачі)")
st.caption("Розклад автоматичних перевірок і оновлень")

cron_data = [
    {"Job": "🔔 Dribbble Hourly Check", "Schedule": "Кожну годину (CET)", 
     "What": "Перевіряє ВСІ сторінки Project Requests на нових клієнтів. Повідомляє тільки якщо є нові.",
     "Status": "🟢 Active"},
    {"Job": "📸 Shots Weekly Update", "Schedule": "Понеділок 8:00 CET",
     "What": "Скрейпить НОВІ шоти (не перезаписує старі!). Оновлює monthly summary та profile stats.",
     "Status": "🟢 Active"},
    {"Job": "⭐ Popular Daily Check", "Schedule": "Пн-Пт 12:00 CET",
     "What": "Перевіряє чи є VALMAX шоти в Dribbble Popular. Оновлює Google Sheet.",
     "Status": "🟢 Active"},
    {"Job": "🏷️ Deep Tag Scan", "Schedule": "Щодня 9:00 UTC (батчами)",
     "What": "Скенує теги до позиції 100. ~500 сторінок/день. Прогрес: 360/1272 тегів.",
     "Status": "🟡 In Progress"},
    {"Job": "📊 Daily Validation", "Schedule": "Щодня 8:30 CET",
     "What": "Автоматична перевірка цілісності даних. Алерт якщо щось зламалось.",
     "Status": "🔴 To Create"},
    {"Job": "🏎️ Competitor Race Daily", "Schedule": "Щодня",
     "What": "Скрейпить першу сторінку конкурентів для race dashboard.",
     "Status": "🔴 To Create"},
]

for job in cron_data:
    with st.expander(f"{job['Status']} {job['Job']} — {job['Schedule']}"):
        st.markdown(f"**Що робить:** {job['What']}")

# --- OPERATIONS RULES ---
st.divider()
st.markdown("## 📋 Operations Rules (Жорсткі правила)")
st.caption("Ці правила НІКОЛИ не порушуються при оновленні даних")

rules = [
    {
        "title": "🚫 НІКОЛИ ws.clear() на production sheets",
        "desc": "Стирає profile stats (M1:N5) і monthly summary (M14:R). Замість цього: оновлюй конкретні діапазони.",
        "severity": "critical"
    },
    {
        "title": "🚫 НІКОЛИ перезаписувати всі шоти",
        "desc": "Weekly cron додає ТІЛЬКИ нові шоти (APPEND). Якщо кількість рядків зменшилась — це баг!",
        "severity": "critical"
    },
    {
        "title": "✅ Валідація після кожного запису",
        "desc": "Після будь-якого оновлення Sheet — запустити validate.py. Перевірити: row count, engagement <50%, monthly summary, profile stats.",
        "severity": "critical"
    },
    {
        "title": "✅ Red Flag: різке падіння даних",
        "desc": "Якщо shots count впав >20% від попереднього значення — СТОП. Не записувати. Алерт користувачу.",
        "severity": "critical"
    },
    {
        "title": "📝 Engagement% зберігати як '6.15%'",
        "desc": "Строка з %. Формула: (likes + saves) / views × 100. Якщо > 50% — баг (×100 двічі).",
        "severity": "medium"
    },
    {
        "title": "📝 Місяці англійською",
        "desc": "'March 2026', не 'Март 2026'. Dashboard підтримує обидва формати, але нові дані — англійською.",
        "severity": "medium"
    },
    {
        "title": "📝 CPC як строка '$23.14'",
        "desc": "Google Sheets з європейською локаллю конвертує 0.22 → 0,22 → парсить як 22 (×100 баг).",
        "severity": "medium"
    },
    {
        "title": "📝 Dribbble скрейпінг: browser, не requests",
        "desc": "requests отримує статус 202 (blocked). Використовувати Playwright/CDP через browser profile 'openclaw'.",
        "severity": "medium"
    },
    {
        "title": "📝 Hourly check: ВСІ сторінки",
        "desc": "Перевіряти не 4, а ВСІ сторінки Project Requests. Інакше пропускаємо нових клієнтів.",
        "severity": "medium"
    },
]

for rule in rules:
    color = '#dc3545' if rule['severity'] == 'critical' else '#ffc107'
    bg = '#fff5f5' if rule['severity'] == 'critical' else '#fffdf0'
    st.markdown(f"""<div style="background:{bg}; border-left:4px solid {color}; padding:12px; border-radius:4px; margin:8px 0;">
        <b>{rule['title']}</b><br>
        <span style="color:#666">{rule['desc']}</span>
    </div>""", unsafe_allow_html=True)

# --- KNOWN BUGS ---
st.divider()
st.markdown("## 🐛 Known Bugs & Fixes")
st.caption("Задокументовані баги щоб не повторювались")

bugs = [
    {"bug": "Engagement ×100", "cause": "Subagent рахує (L+S)/V×100 і записує як '615.00%' замість '6.15%'", "fix": "Валідація: engagement >50% = баг. Перерахувати."},
    {"bug": "ws.clear() стирає M колонки", "cause": "Profile stats і monthly summary в M:R зникають", "fix": "ЗАБОРОНЕНО ws.clear(). Оновлювати тільки конкретні діапазони."},
    {"bug": "Dribbble 202 статус", "cause": "requests бібліотека отримує 202 замість 200", "fix": "Використовувати browser CDP для скрейпінгу."},
    {"bug": "Місяці не сортуються", "cause": "Sheet має англійські назви, код шукає російські", "fix": "month_sort() підтримує обидва формати."},
    {"bug": "CPC ×100", "cause": "Google Sheets європейська локаль: 0.22 → 0,22 → 22", "fix": "Зберігати як '$0.22' строку. parse_cpc() хендлить обидва формати."},
    {"bug": "Крон перевіряє тільки 4 сторінки", "cause": "Пропускає лідів на сторінках 5+", "fix": "Сканувати ВСІ сторінки до кінця пагінації."},
    {"bug": "get_all_records() падає", "cause": "Дублікати порожніх хедерів з M+ колонок", "fix": "Читати конкретний діапазон A1:K250, не get_all_records()."},
]

for b in bugs:
    with st.expander(f"🐛 {b['bug']}"):
        st.markdown(f"**Причина:** {b['cause']}")
        st.markdown(f"**Фікс:** {b['fix']}")

# --- SHEET STRUCTURE ---
st.divider()
st.markdown("## 📊 Sheet Structure")
st.caption("Структура Google Sheet — що де лежить")

structure = """
| Tab | Колонки | Rows | Оновлення |
|-----|---------|------|-----------|
| 📊 Shots Analytics | A-K: shots, M:N profile, M14:R monthly | 212 | Weekly (Mon) |
| 📋 Project Requests | 17 колонок (Місяць → Pipedrive) | 9 | Hourly check |
| 📤 Project Intros | 17 колонок (ідентичні) | 18 | Manual |
| 🏷️ Tag Positions | Tag, Position, Total, Shot | 327 | Deep scan batch |
| 🔍 SEO Data | Tag, Volume, CPC | 191 | On demand |
| 🔍 SERP Data | Tag, Dribbble Pos, AI Overview | 191 | On demand |
| 🏆 Competitors | Profile data | 21 | Weekly |
| 🏆 Competitor Shots | Shot details | 504 | Weekly |
| 🔑 Dribbble Keywords | Keyword, Vol, CPC, Pos, URL | 297K | Static |
| ⭐ Popular Tracker | Category, Position, Shot | ~10 | Daily |
| 📅 Meta | Timestamps | - | Auto |
"""
st.markdown(structure)
