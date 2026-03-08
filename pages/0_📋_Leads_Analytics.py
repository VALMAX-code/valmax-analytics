import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import json





# --- Modern Light Theme ---
st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
    section[data-testid="stSidebar"] * { color: #fff !important; }
    section[data-testid="stSidebar"] a { color: #e0d4ff !important; }
    .block-container { padding-top: 1rem; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: none;
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricValue"] { color: #667eea; font-size: 2rem; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #8892a4; }
    h1 { color: #2d3436 !important; font-weight: 800 !important; }
    h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
    .stDivider { border-color: #e8ecf1 !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
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

# Add year to month if missing (extract from date column)
if 'Месяц' in df.columns and 'Дата заявки' in df.columns:
    def _add_year(row):
        m = str(row.get('Месяц', ''))
        if m and len(m.split()) == 1:
            try:
                d = str(row.get('Дата заявки', ''))
                year = d.split('.')[-1] if '.' in d else ''
                return f"{m} {year}" if year else m
            except:
                return m
        return m
    df['Месяц'] = df.apply(_add_year, axis=1)

# --- HEADER ---
st.markdown("# 📊 VALMAX Dribbble Analytics")
st.markdown("*Дані в реальному часі з Google Sheets*")
st.divider()

# --- FILTERS ---
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

def _month_sort_key(m):
    _mo = {'Січень':1,'Лютий':2,'Березень':3,'Квітень':4,'Травень':5,'Червень':6,
           'Липень':7,'Серпень':8,'Вересень':9,'Жовтень':10,'Листопад':11,'Грудень':12,
           'Январь':1,'Февраль':2,'Март':3,'Апрель':4,'Май':5,'Июнь':6,
           'Июль':7,'Август':8,'Сентябрь':9,'Октябрь':10,'Ноябрь':11,'Декабрь':12,
           'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
           'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
    p = str(m).split()
    if len(p)==2 and p[0] in _mo:
        return int(p[1])*100+_mo.get(p[0],0)
    if len(p)==1 and p[0] in _mo:
        return _mo.get(p[0],0)
    return 0
_ru_to_en_m = {'Январь':'January','Февраль':'February','Март':'March','Апрель':'April',
               'Май':'May','Июнь':'June','Июль':'July','Август':'August',
               'Сентябрь':'September','Октябрь':'October','Ноябрь':'November','Декабрь':'December'}
def _to_en_month(m):
    parts = str(m).split()
    if len(parts) == 2 and parts[0] in _ru_to_en_m:
        return f"{_ru_to_en_m[parts[0]]} {parts[1]}"
    if len(parts) == 1 and parts[0] in _ru_to_en_m:
        return _ru_to_en_m[parts[0]]
    return m

if "Месяц" in df.columns:
    en_months_map = {}
    for m in df["Месяц"].unique():
        en_months_map[_to_en_month(m)] = m
    months = ["All"] + sorted(en_months_map.keys(), key=lambda x: _month_sort_key(en_months_map[x]), reverse=True)
else:
    months = ["All"]
    en_months_map = {}
with col_f1:
    month_filter = st.selectbox("📅 Month", months)
    
managers = ["All"] + sorted([m for m in df["Менеджер"].unique() if m]) if "Менеджер" in df.columns else ["Усі"]
with col_f2:
    manager_filter = st.selectbox("👨‍💼 Manager", managers)

relevance = ["All", "Relevant", "Unrelevant", "Unknown"]
with col_f3:
    rel_filter = st.selectbox("✅ Relevant", relevance)

crm_statuses = ["All"] + sorted([s for s in df["CRM статус"].unique() if s]) if "CRM статус" in df.columns else ["Усі"]
with col_f4:
    crm_filter = st.selectbox("📊 CRM статус", crm_statuses)

# Apply filters
filtered = df.copy()
if month_filter != "All":
    orig_month = en_months_map.get(month_filter, month_filter)
    filtered = filtered[filtered["Месяц"] == orig_month]
if manager_filter != "All":
    filtered = filtered[filtered["Менеджер"] == manager_filter]
if rel_filter != "All":
    filtered = filtered[filtered["Relevant"] == rel_filter]
if crm_filter != "All":
    filtered = filtered[filtered["CRM статус"] == crm_filter]

# --- KPI METRICS ---
st.markdown("### 🎯 Ключові метрики")
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

row1[0].metric("Усього заявок", total)
row1[1].metric("Relevant", relevant)
row1[2].metric("Unrelevant", unrelevant)
row1[3].metric("Unknown", unknown_rel)
row1[4].metric("Meetings", meetings)
row1[5].metric("Лід відповів", lead_replied)
row1[6].metric("Конверсія в Meeting", meeting_conv)

row2[0].metric("🏆 Виграних угод", won)
row2[1].metric("📈 Конверсія в угоду", deal_conv)
row2[2].metric("💰 Зароблений бюджет", budget_str)
row2[3].metric("📊 Середній чек", f"${total_budget // won:,}" if won > 0 else "—")

st.divider()

# --- ROW 1: Заявки + География ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Заявки по місяцях")
    if "Месяц" in df.columns and "Relevant" in df.columns:
        month_data = df.groupby(["Месяц", "Relevant"]).size().reset_index(name="Count"); month_data["Month"] = month_data["Месяц"].apply(_to_en_month)
        fig = px.bar(month_data, x="Month", y="Count", color="Relevant",
                     color_discrete_map={"Relevant": "#43e97b", "Unrelevant": "#f5576c", "Unknown": "#b2bec3"},
                     barmode="stack", template="plotly_white")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 🌍 Географія лідів")
    if "Страна/Город" in filtered.columns:
        geo = filtered["Страна/Город"].value_counts().reset_index()
        geo.columns = ["Country", "Count"]
        fig = px.pie(geo, names="Country", values="Count", template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- ROW 2: CRM статус + Бюджеты ---
st.divider()
col_crm, col_budget = st.columns(2)

with col_crm:
    st.markdown("### 📊 CRM статус")
    if "CRM статус" in filtered.columns:
        crm = filtered["CRM статус"].value_counts().reset_index()
        crm.columns = ["Status", "Count"]
        color_map = {"Open 💙": "#667eea", "Lost ❌": "#f5576c", "Won ✅": "#43e97b", "No matches 🔄": "#b2bec3"}
        fig = px.pie(crm, names="Status", values="Count", template="plotly_white",
                     color="Status", color_discrete_map=color_map)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

with col_budget:
    st.markdown("### 💰 Budgets")
    if "Бюджет (CRM / ~Dribbble)" in filtered.columns:
        budgets = filtered["Бюджет (CRM / ~Dribbble)"].value_counts().reset_index()
        budgets.columns = ["Budget", "Count"]
        budget_order = ["Unknown", "$1000-$3000", "$3000-$5000", "$5000-$10000", "$10000-$15000", "$15000+"]
        budgets["sort"] = budgets["Budget"].apply(lambda x: next((i for i, o in enumerate(budget_order) if str(x).strip() == o), 99))
        budgets = budgets.sort_values("sort")
        fig = px.bar(budgets, x="Budget", y="Count", template="plotly_white",
                     color_discrete_sequence=["#667eea"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# --- ROW 3: Время ответа + Типы проектов ---
st.divider()
col3, col4 = st.columns(2)

with col3:
    st.markdown("### ⏰ Час першої відповіді")
    if "Время ответа" in filtered.columns:
        time_data = filtered["Время ответа"].value_counts().reset_index()
        time_data.columns = ["Time", "Count"]
        order = ["<30 мин", "<1ч", "<2ч", "<4ч", "<24ч", ">24ч"]
        time_data["sort"] = time_data["Time"].apply(lambda x: next((i for i, o in enumerate(order) if str(x).strip() == o), 99))
        time_data = time_data.sort_values("sort")
        fig = px.bar(time_data, x="Time", y="Count", template="plotly_white",
                     color="Count", color_continuous_scale=["#f5576c", "#43e97b"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.markdown("### 🎨 Типи проєктів")
    if "Тип проекта" in filtered.columns:
        types = filtered["Тип проекта"].value_counts().reset_index()
        types.columns = ["Type", "Count"]
        fig = px.pie(types, names="Type", values="Count", template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- FUNNEL ---
st.divider()
st.markdown("### 🔻 Conversion Funnel")

funnel_stages = ["All leads", "VALMAX replied", "Lead replied", "Meeting", "Won"]
funnel_counts = [
    len(filtered),
    len(filtered[filtered.get("VALMAX ответил?", pd.Series()) == "Да"]) if "VALMAX ответил?" in filtered.columns else 0,
    len(filtered[filtered.get("Лид ответил?", pd.Series()) == "Да"]) if "Лид ответил?" in filtered.columns else 0,
    meetings,
    won,
]
funnel_colors = ["#667eea", "#818cf8", "#a78bfa", "#c084fc", "#43e97b"]
total = funnel_counts[0] if funnel_counts[0] > 0 else 1

# Custom visual funnel with metric cards
funnel_cols = st.columns(5)
for i, (stage, count, color) in enumerate(zip(funnel_stages, funnel_counts, funnel_colors)):
    pct = round(count / total * 100)
    arrow = f" → {pct}%" if i > 0 else ""
    with funnel_cols[i]:
        st.markdown(f"""
        <div style="text-align:center; padding:16px 8px; background:linear-gradient(135deg, {color}22, {color}11); 
                    border-left:4px solid {color}; border-radius:12px; margin-bottom:8px;">
            <div style="font-size:28px; font-weight:800; color:{color};">{count}</div>
            <div style="font-size:13px; color:#636e72; font-weight:600;">{stage}</div>
            <div style="font-size:12px; color:#b2bec3;">{pct}% of total</div>
        </div>
        """, unsafe_allow_html=True)

# Conversion between stages
if len(funnel_counts) >= 5:
    drop_text = []
    for i in range(1, len(funnel_counts)):
        prev = funnel_counts[i-1]
        curr = funnel_counts[i]
        conv = round(curr / prev * 100) if prev > 0 else 0
        drop_text.append(f"**{funnel_stages[i-1]}** → **{funnel_stages[i]}**: {conv}%")
    st.caption(" · ".join(drop_text))
st.plotly_chart(fig, use_container_width=True)

# --- MANAGERS ---
st.divider()
st.markdown("### 👨‍💼 Managers")
if "Менеджер" in filtered.columns:
    mgr = filtered["Менеджер"].value_counts().reset_index()
    mgr.columns = ["Менеджер", "Leads"]
    fig = px.bar(mgr, x="Менеджер", y="Leads", template="plotly_white",
                 color="Менеджер", color_discrete_sequence=["#667eea", "#f093fb", "#43e97b"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#636e72"), height=300, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- TABLE ---
st.divider()
st.markdown("### 📋 All leads")
# Rename table columns
table_df = filtered.copy()
col_renames = {
    'Месяц': 'Month', 'Дата заявки': 'Date', 'Клиент': 'Client', 
    'Страна/Город': 'Country', 'Тип проекта': 'Project Type',
    'Бюджет (CRM / ~Dribbble)': 'Budget', 'Тип': 'Type',
    'VALMAX ответил?': 'VALMAX replied?', 'Лид ответил?': 'Lead replied?',
    'Время ответа': 'Response Time', 'Менеджер': 'Manager',
    'Причина отказа': 'Rejection reason', 'Ссылка Dribbble': 'Dribbble',
    'Ссылка Pipedrive': 'Pipedrive'
}
table_df = table_df.rename(columns={k:v for k,v in col_renames.items() if k in table_df.columns})
if 'Month' in table_df.columns:
    table_df['Month'] = table_df['Month'].apply(_to_en_month)
col_config = {}
if "Dribbble" in table_df.columns:
    col_config["Dribbble"] = st.column_config.LinkColumn("Dribbble", display_text="Open ↗")
if "Pipedrive" in table_df.columns:
    col_config["Pipedrive"] = st.column_config.LinkColumn("Pipedrive", display_text="Open ↗")
st.dataframe(table_df, use_container_width=True, height=400, column_config=col_config)

# --- FOOTER ---
st.divider()
st.caption("💙 VALMAX Dribbble Analytics | Powered by Navi | Дані оновлюються автоматично")
