import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_meta, show_last_updated, CRON_SCHEDULE

st.set_page_config(page_title="Dribbble Profitability", page_icon="💰", layout="wide")

# Sidebar


st.title("💰 Dribbble Profitability")
st.caption("Аналітика прибутковості Dribbble каналу — тільки витрати пов'язані з Dribbble")

# Load data
@st.cache_data(ttl=60)
def load_profitability():
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc').worksheet('💰 Profitability')
    data = ws.get_all_records()
    return pd.DataFrame(data)

try:
    df = load_profitability()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

if df.empty:
    st.warning("Немає даних")
    st.stop()

# Convert numeric columns
numeric_cols = [c for c in df.columns if c != 'Month']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0)

# --- KPIs ---
latest = df.iloc[-1]
total_cost = latest['TOTAL COSTS']
st.markdown(f"### 📊 {latest['Month']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Costs", f"${total_cost:,.0f}", help="Загальні витрати на Dribbble за останній місяць")
col2.metric("🏷️ Subscriptions", f"${latest['Dribbble Pro Subscription']:,.0f}")
col3.metric("🎨 Freelancers", f"${sum(latest[c] for c in df.columns if 'Freelancer' in c):,.0f}")
col4.metric("👥 Team Share", f"${latest['Team (Dribbble share)']:,.0f}")

st.divider()

# --- Cost Breakdown Pie ---
st.markdown("### 🥧 Розподіл витрат")
st.caption("Структура витрат на Dribbble канал за останній місяць")

categories = {
    '🏷️ Subscriptions': latest['Dribbble Pro Subscription'] + latest.get('Dribbble Boosting/SaaS', 0) + latest.get('Dribbble Designers (outsource)', 0),
    '🎨 Freelancers': sum(latest[c] for c in df.columns if 'Freelancer' in c),
    '👥 Team Share': latest['Team (Dribbble share)'],
}
categories = {k: v for k, v in categories.items() if v > 0}

if categories:
    fig_pie = px.pie(
        names=list(categories.keys()),
        values=list(categories.values()),
        color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+value+label', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
    fig_pie.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --- Monthly Trend ---
if len(df) > 1:
    st.markdown("### 📈 Динаміка витрат по місяцях")
    st.caption("Загальні витрати на Dribbble канал по місяцях")
    
    fig_bar = px.bar(df, x='Month', y='TOTAL COSTS', text='TOTAL COSTS',
                     color_discrete_sequence=['#e74c3c'])
    fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig_bar.update_layout(yaxis_title='Costs ($)', xaxis_title='', height=400)
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()

# --- Freelancers Detail ---
st.markdown("### 🎨 Фрілансери — деталізація")
st.caption("Оплати фрілансерам за роботу над Dribbble шотами")

freelancer_cols = [c for c in df.columns if 'Freelancer' in c]
freelancer_data = []
for _, row in df.iterrows():
    for col in freelancer_cols:
        if row[col] > 0:
            name = col.replace('Freelancer: ', '')
            freelancer_data.append({
                'Month': row['Month'],
                'Freelancer': name,
                'Amount': row[col]
            })

if freelancer_data:
    df_fl = pd.DataFrame(freelancer_data)
    
    # Table
    pivot = df_fl.pivot_table(index='Freelancer', columns='Month', values='Amount', aggfunc='sum', fill_value=0)
    pivot['Total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('Total', ascending=False)
    
    # Format as currency
    styled = pivot.style.format('${:,.0f}')
    st.dataframe(styled, use_container_width=True)
else:
    st.info("Немає даних по фрілансерах")

st.divider()

# --- Cost Breakdown Table ---
st.markdown("### 📋 Повна деталізація")
st.caption("Всі витрати на Dribbble канал по категоріях")

display_cols = ['Month'] + [c for c in df.columns if c not in ['Month', 'TOTAL COSTS'] and df[c].sum() > 0] + ['TOTAL COSTS']
df_display = df[display_cols].copy()

# Format
for col in display_cols:
    if col != 'Month':
        df_display[col] = df_display[col].apply(lambda x: f'${x:,.0f}' if x > 0 else '—')

st.dataframe(df_display, use_container_width=True, hide_index=True)

st.divider()

# --- Data Source ---
st.markdown("### ℹ️ Джерело даних")
st.caption("Дані автоматично завантажуються з QuickBooks API")
st.markdown("""
- **Підписки та реклама** — акаунт 6330 (Dribbble) з QuickBooks
- **Фрілансери** — акаунт 5201 (Freelance UI/UX Designers) з QuickBooks
- **Team Share** — відсоток зарплат команди, що працює над Dribbble контентом
- **Валюти**: EUR конвертовано по ~1.04, UAH по ~43.79
""")

show_last_updated("profitability")
