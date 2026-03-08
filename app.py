import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="VALMAX Analytics", page_icon="📊", layout="wide")

# --- Multi-page nav ---
st.sidebar.markdown("## 🧭 Навигация")
st.sidebar.page_link("app.py", label="📋 Leads Analytics")
st.sidebar.page_link("pages/shots.py", label="📸 Shots Analytics")
st.sidebar.divider()

# --- STYLES ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px 20px;
        color: white;
    }
    [data-testid="stMetricValue"] { color: #e94560; font-size: 2rem; }
    [data-testid="stMetricLabel"] { color: #a3b1c6; }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=300)
def load_data():
    scopes = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    
    # Support both local file and Streamlit Cloud secrets
    import os
    local_key = '/Users/openzlo/.openclaw/workspace/.secrets/google-service-account.json'
    if os.path.exists(local_key):
        creds = Credentials.from_service_account_file(local_key, scopes=scopes)
    else:
        from google.oauth2.service_account import Credentials as SACredentials
        creds = SACredentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes)
    
    gc = gspread.authorize(creds)
    sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
    
    ws = sh.sheet1
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df

df = load_data()

# --- HEADER ---
st.markdown("# 📊 VALMAX Dribbble Analytics")
st.markdown("*Данные в реальном времени из Google Sheets*")
st.divider()

# --- FILTERS ---
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

months = ["Все"] + sorted(df["Месяц"].unique().tolist(), reverse=True) if "Месяц" in df.columns else ["Все"]
with col_f1:
    month_filter = st.selectbox("📅 Месяц", months)
    
managers = ["Все"] + sorted([m for m in df["Менеджер"].unique() if m]) if "Менеджер" in df.columns else ["Все"]
with col_f2:
    manager_filter = st.selectbox("👨‍💼 Менеджер", managers)

relevance = ["Все", "Relevant", "Unrelevant", "Unknown"]
with col_f3:
    rel_filter = st.selectbox("✅ Relevant", relevance)

crm_statuses = ["Все"] + sorted([s for s in df["CRM статус"].unique() if s]) if "CRM статус" in df.columns else ["Все"]
with col_f4:
    crm_filter = st.selectbox("📊 CRM статус", crm_statuses)

# Apply filters
filtered = df.copy()
if month_filter != "Все":
    filtered = filtered[filtered["Месяц"] == month_filter]
if manager_filter != "Все":
    filtered = filtered[filtered["Менеджер"] == manager_filter]
if rel_filter != "Все":
    filtered = filtered[filtered["Relevant"] == rel_filter]
if crm_filter != "Все":
    filtered = filtered[filtered["CRM статус"] == crm_filter]

# --- KPI METRICS ---
st.markdown("### 🎯 Ключевые метрики")
row1 = st.columns(7)
row2 = st.columns(4)

total = len(filtered)
relevant = len(filtered[filtered.get("Relevant", pd.Series()) == "Relevant"]) if "Relevant" in filtered.columns else 0
unrelevant = len(filtered[filtered.get("Relevant", pd.Series()) == "Unrelevant"]) if "Relevant" in filtered.columns else 0
unknown_rel = len(filtered[filtered.get("Relevant", pd.Series()) == "Unknown"]) if "Relevant" in filtered.columns else 0
meetings = len(filtered[filtered.get("Meeting Scheduled", pd.Series()) == "Да"]) if "Meeting Scheduled" in filtered.columns else 0
lead_replied = len(filtered[filtered.get("Лид ответил?", pd.Series()) == "Да"]) if "Лид ответил?" in filtered.columns else 0
meeting_conv = f"{round(meetings/total*100)}%" if total > 0 else "0%"
won = len(filtered[filtered.get("CRM статус", pd.Series()) == "Won ✅"]) if "CRM статус" in filtered.columns else 0
deal_conv = f"{round(won/total*100)}%" if total > 0 else "0%"

# Calculate total budget from won deals (parse from Pipedrive data)
def parse_budget(val):
    """Try to extract numeric value from budget string"""
    import re
    if not val or val == "Unknown":
        return 0
    nums = re.findall(r'[\d,]+', str(val).replace(',', ''))
    if nums:
        try:
            return max(int(n) for n in nums)
        except:
            return 0
    return 0

won_filtered = filtered[filtered.get("CRM статус", pd.Series()) == "Won ✅"] if "CRM статус" in filtered.columns else pd.DataFrame()
total_budget = sum(won_filtered["Бюджет (CRM / ~Dribbble)"].apply(parse_budget)) if len(won_filtered) > 0 and "Бюджет (CRM / ~Dribbble)" in won_filtered.columns else 0
budget_str = f"${total_budget:,}" if total_budget > 0 else "$0"

row1[0].metric("Всего заявок", total)
row1[1].metric("Relevant", relevant)
row1[2].metric("Unrelevant", unrelevant)
row1[3].metric("Unknown", unknown_rel)
row1[4].metric("Meetings", meetings)
row1[5].metric("Лид ответил", lead_replied)
row1[6].metric("Конверсия в Meeting", meeting_conv)

row2[0].metric("🏆 Выигранных сделок", won)
row2[1].metric("📈 Конверсия в сделку", deal_conv)
row2[2].metric("💰 Заработанный бюджет", budget_str)
row2[3].metric("📊 Средний чек", f"${total_budget // won:,}" if won > 0 else "—")

st.divider()

# --- ROW 1: Заявки + География ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Заявки по месяцам")
    if "Месяц" in df.columns and "Relevant" in df.columns:
        month_data = df.groupby(["Месяц", "Relevant"]).size().reset_index(name="Кол-во")
        fig = px.bar(month_data, x="Месяц", y="Кол-во", color="Relevant",
                     color_discrete_map={"Relevant": "#00d4aa", "Unrelevant": "#e94560", "Unknown": "#a3b1c6"},
                     barmode="stack", template="plotly_dark")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#a3b1c6"), height=350)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 🌍 География лидов")
    if "Страна/Город" in filtered.columns:
        geo = filtered["Страна/Город"].value_counts().reset_index()
        geo.columns = ["Страна", "Кол-во"]
        fig = px.pie(geo, names="Страна", values="Кол-во", template="plotly_dark",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a3b1c6"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- ROW 2: CRM статус + Бюджеты ---
st.divider()
col_crm, col_budget = st.columns(2)

with col_crm:
    st.markdown("### 📊 CRM статус")
    if "CRM статус" in filtered.columns:
        crm = filtered["CRM статус"].value_counts().reset_index()
        crm.columns = ["Статус", "Кол-во"]
        color_map = {"Open 💙": "#4361ee", "Lost ❌": "#e94560", "Won ✅": "#00d4aa", "No matches 🔄": "#a3b1c6"}
        fig = px.pie(crm, names="Статус", values="Кол-во", template="plotly_dark",
                     color="Статус", color_discrete_map=color_map)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a3b1c6"), height=350)
        st.plotly_chart(fig, use_container_width=True)

with col_budget:
    st.markdown("### 💰 Бюджеты")
    if "Бюджет (CRM / ~Dribbble)" in filtered.columns:
        budgets = filtered["Бюджет (CRM / ~Dribbble)"].value_counts().reset_index()
        budgets.columns = ["Бюджет", "Кол-во"]
        budget_order = ["Unknown", "$1000-$3000", "$3000-$5000", "$5000-$10000", "$10000-$15000", "$15000+"]
        budgets["sort"] = budgets["Бюджет"].apply(lambda x: next((i for i, o in enumerate(budget_order) if str(x).strip() == o), 99))
        budgets = budgets.sort_values("sort")
        fig = px.bar(budgets, x="Бюджет", y="Кол-во", template="plotly_dark",
                     color_discrete_sequence=["#4361ee"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#a3b1c6"), height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# --- ROW 3: Время ответа + Типы проектов ---
st.divider()
col3, col4 = st.columns(2)

with col3:
    st.markdown("### ⏰ Время первого ответа")
    if "Время ответа" in filtered.columns:
        time_data = filtered["Время ответа"].value_counts().reset_index()
        time_data.columns = ["Время", "Кол-во"]
        order = ["<30 мин", "<1ч", "<2ч", "<4ч", "<24ч", ">24ч"]
        time_data["sort"] = time_data["Время"].apply(lambda x: next((i for i, o in enumerate(order) if str(x).strip() == o), 99))
        time_data = time_data.sort_values("sort")
        fig = px.bar(time_data, x="Время", y="Кол-во", template="plotly_dark",
                     color="Кол-во", color_continuous_scale=["#e94560", "#00d4aa"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#a3b1c6"), height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.markdown("### 🎨 Типы проектов")
    if "Тип проекта" in filtered.columns:
        types = filtered["Тип проекта"].value_counts().reset_index()
        types.columns = ["Тип", "Кол-во"]
        fig = px.pie(types, names="Тип", values="Кол-во", template="plotly_dark",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#a3b1c6"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- FUNNEL ---
st.divider()
st.markdown("### 🔻 Конверсионная воронка")

funnel_data = {
    "Этап": ["Все заявки", "VALMAX ответил", "Лид ответил", "Meeting", "Won"],
    "Кол-во": [
        len(filtered),
        len(filtered[filtered.get("VALMAX ответил?", pd.Series()) == "Да"]) if "VALMAX ответил?" in filtered.columns else 0,
        len(filtered[filtered.get("Лид ответил?", pd.Series()) == "Да"]) if "Лид ответил?" in filtered.columns else 0,
        meetings,
        won,
    ]
}
fig = go.Figure(go.Funnel(
    y=funnel_data["Этап"],
    x=funnel_data["Кол-во"],
    textinfo="value+percent initial",
    marker=dict(color=["#4361ee", "#3a86ff", "#f77f00", "#e94560", "#00d4aa"]),
))
fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#a3b1c6"), height=350)
st.plotly_chart(fig, use_container_width=True)

# --- MANAGERS ---
st.divider()
st.markdown("### 👨‍💼 Менеджеры")
if "Менеджер" in filtered.columns:
    mgr = filtered["Менеджер"].value_counts().reset_index()
    mgr.columns = ["Менеджер", "Заявок"]
    fig = px.bar(mgr, x="Менеджер", y="Заявок", template="plotly_dark",
                 color="Менеджер", color_discrete_sequence=["#4361ee", "#e94560", "#00d4aa"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#a3b1c6"), height=300, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- TABLE ---
st.divider()
st.markdown("### 📋 Все заявки")
st.dataframe(filtered, use_container_width=True, height=400)

# --- FOOTER ---
st.divider()
st.caption("💙 VALMAX Dribbble Analytics | Powered by Navi | Данные обновляются автоматически")
