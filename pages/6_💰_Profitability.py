import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from utils import show_last_updated

st.set_page_config(page_title="Dribbble Profitability", page_icon="💰", layout="wide")

st.markdown("""<style>
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
section[data-testid="stSidebar"] * { color: #fff !important; }
section[data-testid="stSidebar"] a { color: #e0d4ff !important; }
</style>""", unsafe_allow_html=True)

st.title("💰 Dribbble Profitability")
st.caption("Аналітика прибутковості Dribbble каналу — витрати, фрілансери, динаміка по місяцях")

@st.cache_data(ttl=60)
def load_profitability():
    import gspread
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
    st.warning("Немає даних. Додайте місяці в Google Sheet '💰 Profitability'")
    st.stop()

# Convert numeric
numeric_cols = [c for c in df.columns if c != 'Month']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0)

# Parse month for sorting/filtering
from datetime import datetime
def parse_month(m):
    try:
        return datetime.strptime(m.strip(), '%B %Y')
    except:
        return datetime(2020,1,1)

df['_date'] = df['Month'].apply(parse_month)
df = df.sort_values('_date').reset_index(drop=True)
df['_quarter'] = df['_date'].apply(lambda d: f"Q{(d.month-1)//3+1} {d.year}")
df['_year'] = df['_date'].apply(lambda d: str(d.year))

# --- Filters ---
st.markdown("### 🔍 Фільтр")
filter_options = ['All Time'] + sorted(df['_year'].unique().tolist(), reverse=True) + sorted(df['_quarter'].unique().tolist(), reverse=True) + df['Month'].tolist()[::-1]
selected = st.selectbox("Період", filter_options, index=0)

if selected == 'All Time':
    dff = df.copy()
elif selected in df['_year'].values:
    dff = df[df['_year'] == selected]
elif selected in df['_quarter'].values:
    dff = df[df['_quarter'] == selected]
else:
    dff = df[df['Month'] == selected]

period_label = selected if selected != 'All Time' else 'Весь час'

# Freelancer columns
freelancer_cols = [c for c in dff.columns if 'Freelancer' in c]
freelancer_total = dff[freelancer_cols].sum(axis=1)

# --- KPIs ---
st.markdown(f"### 📊 {period_label}")

total_costs = dff['TOTAL COSTS'].sum()
total_ads = dff['Dribbble Pro Subscription'].sum()
total_boost = dff.get('Dribbble Boosting/SaaS', pd.Series([0]*len(dff))).sum() + dff.get('Dribbble Designers (outsource)', pd.Series([0]*len(dff))).sum()
total_free = dff[freelancer_cols].sum().sum()
total_team = dff['Team (Dribbble share)'].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Total Costs", f"${total_costs:,.0f}")
col2.metric("📢 Dribbble Ads", f"${total_ads:,.0f}", help="Офіційна реклама: Pro subscription, promoted shots")
col3.metric("🚀 Boosting", f"${total_boost:,.0f}", help="Неофіційний промоушен: engagement boosting, SaaS сервіси")
col4.metric("🎨 Freelancers", f"${total_free:,.0f}")
col5.metric("👥 Team Share", f"${total_team:,.0f}")

st.divider()

# --- Monthly Costs Trend ---
if len(dff) > 1:
    st.markdown("### 📈 Динаміка витрат по місяцях")
    st.caption("Як змінюються загальні витрати на Dribbble канал")
    
    # Stacked bar
    chart_data = []
    for _, row in dff.iterrows():
        chart_data.append({'Month': row['Month'], 'Category': '📢 Dribbble Ads', 'Amount': row['Dribbble Pro Subscription']})
        boost = row.get('Dribbble Boosting/SaaS', 0) + row.get('Dribbble Designers (outsource)', 0)
        chart_data.append({'Month': row['Month'], 'Category': '🚀 Boosting', 'Amount': boost})
        fl = sum(row[c] for c in freelancer_cols)
        chart_data.append({'Month': row['Month'], 'Category': '🎨 Freelancers', 'Amount': fl})
        chart_data.append({'Month': row['Month'], 'Category': '👥 Team Share', 'Amount': row['Team (Dribbble share)']})
    
    df_chart = pd.DataFrame(chart_data)
    df_chart = df_chart[df_chart['Amount'] > 0]
    
    fig = px.bar(df_chart, x='Month', y='Amount', color='Category', 
                 color_discrete_map={'📢 Dribbble Ads': '#e74c3c', '🚀 Boosting': '#f39c12', '🎨 Freelancers': '#3498db', '👥 Team Share': '#2ecc71'},
                 barmode='stack')
    fig.update_layout(yaxis_title='Costs ($)', xaxis_title='', height=450, legend=dict(orientation='h', y=1.1))
    
    # Add total line
    totals = dff.set_index('Month')['TOTAL COSTS']
    fig.add_trace(go.Scatter(x=totals.index, y=totals.values, mode='lines+markers+text',
                             name='Total', line=dict(color='white', width=2, dash='dot'),
                             text=[f'${v:,.0f}' for v in totals.values], textposition='top center',
                             textfont=dict(size=12)))
    
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

# --- Cost Breakdown Pie ---
st.markdown("### 🥧 Розподіл витрат")
st.caption(f"Структура витрат за {period_label}")

categories = {
    '📢 Dribbble Ads': total_ads,
    '🚀 Boosting': total_boost,
    '🎨 Freelancers': total_free,
    '👥 Team Share': total_team,
}
categories = {k: v for k, v in categories.items() if v > 0}

if categories:
    fig_pie = px.pie(names=list(categories.keys()), values=list(categories.values()),
                     color_discrete_map={'📢 Dribbble Ads': '#e74c3c', '🚀 Boosting': '#f39c12', '🎨 Freelancers': '#3498db', '👥 Team Share': '#2ecc71'})
    fig_pie.update_traces(textposition='inside', textinfo='percent+value+label', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
    fig_pie.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --- Freelancers Ranking ---
st.markdown("### 🏆 Топ фрілансерів за витратами")
st.caption(f"Хто коштує найбільше за {period_label}")

freelancer_totals = {}
for col in freelancer_cols:
    total = dff[col].sum()
    if total > 0:
        name = col.replace('Freelancer: ', '')
        freelancer_totals[name] = total

if freelancer_totals:
    df_fl = pd.DataFrame([{'Freelancer': k, 'Total': v} for k, v in freelancer_totals.items()])
    df_fl = df_fl.sort_values('Total', ascending=True)
    
    fig_fl = px.bar(df_fl, x='Total', y='Freelancer', orientation='h', text='Total',
                    color_discrete_sequence=['#3498db'])
    fig_fl.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig_fl.update_layout(yaxis_title='', xaxis_title='Total ($)', height=max(300, len(df_fl)*50))
    st.plotly_chart(fig_fl, use_container_width=True)
    
    # Monthly breakdown per freelancer
    if len(dff) > 1:
        st.markdown("#### 📅 Фрілансери по місяцях")
        fl_monthly = []
        for _, row in dff.iterrows():
            for col in freelancer_cols:
                if row[col] > 0:
                    fl_monthly.append({'Month': row['Month'], 'Freelancer': col.replace('Freelancer: ', ''), 'Amount': row[col]})
        
        if fl_monthly:
            df_fl_m = pd.DataFrame(fl_monthly)
            fig_fl_m = px.bar(df_fl_m, x='Month', y='Amount', color='Freelancer', barmode='group',
                              text='Amount')
            fig_fl_m.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_fl_m.update_layout(height=400, legend=dict(orientation='h', y=1.15))
            st.plotly_chart(fig_fl_m, use_container_width=True)
else:
    st.info("Немає даних по фрілансерах за обраний період")

st.divider()

# --- Rate Card (editable) ---
st.markdown("### 💲 Вартість роботи фрілансерів")
st.caption("Вартість шота та сету від кожного фрілансера. Редагуйте прямо тут — зміни зберігаються автоматично.")

@st.cache_data(ttl=60)
def load_rates():
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc').worksheet('💰 Rates')
    return pd.DataFrame(ws.get_all_records())

def save_rates(df_rates):
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc').worksheet('💰 Rates')
    ws.update('A1', [df_rates.columns.tolist()] + df_rates.values.tolist())

try:
    df_rates = load_rates()
    for col in ['Cost per Shot ($)', 'Cost per Set ($)']:
        if col in df_rates.columns:
            df_rates[col] = pd.to_numeric(df_rates[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0).astype(int)
    
    edited_rates = st.data_editor(
        df_rates,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Freelancer": st.column_config.TextColumn("Freelancer", width="medium"),
            "Cost per Shot ($)": st.column_config.NumberColumn("Cost per Shot ($)", min_value=0, format="$%d"),
            "Cost per Set ($)": st.column_config.NumberColumn("Cost per Set ($)", min_value=0, format="$%d"),
        },
        key="rates_editor"
    )
    
    if st.button("💾 Зберегти тарифи", key="save_rates"):
        save_rates(edited_rates)
        st.success("✅ Тарифи збережено!")
        st.cache_data.clear()
except Exception as e:
    st.error(f"Помилка: {e}")

st.divider()

# --- Work Log (editable) ---
st.markdown("### 📝 Виконана робота фрілансерів")
st.caption("Кількість шотів та сетів від кожного фрілансера за місяць. Редагуйте прямо тут.")

@st.cache_data(ttl=60)
def load_work_log():
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc').worksheet('💰 Work Log')
    return pd.DataFrame(ws.get_all_records())

def save_work_log(df_wl):
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc').worksheet('💰 Work Log')
    ws.clear()
    ws.update('A1', [df_wl.columns.tolist()] + df_wl.values.tolist())

try:
    df_wl = load_work_log()
    for col in ['Shots', 'Sets']:
        if col in df_wl.columns:
            df_wl[col] = pd.to_numeric(df_wl[col], errors='coerce').fillna(0).astype(int)
    
    # Get available months from profitability data
    available_months = df['Month'].tolist()
    
    edited_wl = st.data_editor(
        df_wl,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Month": st.column_config.SelectboxColumn("Month", options=available_months, width="medium"),
            "Freelancer": st.column_config.TextColumn("Freelancer", width="medium"),
            "Shots": st.column_config.NumberColumn("Shots", min_value=0, format="%d"),
            "Sets": st.column_config.NumberColumn("Sets", min_value=0, format="%d"),
        },
        key="work_editor"
    )
    
    if st.button("💾 Зберегти роботу", key="save_work"):
        save_work_log(edited_wl)
        st.success("✅ Дані збережено!")
        st.cache_data.clear()
    
    # Calculate cost based on rates
    if not df_rates.empty and not df_wl.empty:
        st.markdown("#### 💰 Розрахунок вартості")
        rates_dict = {}
        for _, r in edited_rates.iterrows():
            rates_dict[r['Freelancer']] = {'shot': r.get('Cost per Shot ($)', 0), 'set': r.get('Cost per Set ($)', 0)}
        
        calc_data = []
        for _, row in edited_wl.iterrows():
            name = row['Freelancer']
            shots = row.get('Shots', 0)
            sets = row.get('Sets', 0)
            rate = rates_dict.get(name, {'shot': 0, 'set': 0})
            cost_shots = shots * rate['shot']
            cost_sets = sets * rate['set']
            total = cost_shots + cost_sets
            if shots > 0 or sets > 0:
                calc_data.append({
                    'Month': row['Month'],
                    'Freelancer': name,
                    'Shots': shots,
                    '× Rate': f"${rate['shot']}",
                    '= Shots Cost': f"${cost_shots:,.0f}",
                    'Sets': sets,
                    '× Rate ': f"${rate['set']}",
                    '= Sets Cost': f"${cost_sets:,.0f}",
                    'TOTAL': f"${total:,.0f}"
                })
        
        if calc_data:
            st.dataframe(pd.DataFrame(calc_data), use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Помилка: {e}")

st.divider()

# --- Full Detail Table ---
st.markdown("### 📋 Повна деталізація")
st.caption("Всі витрати на Dribbble канал по категоріях та місяцях")

display_cols = ['Month'] + [c for c in dff.columns if c not in ['Month', 'TOTAL COSTS', '_date', '_quarter', '_year'] and dff[c].sum() > 0] + ['TOTAL COSTS']
df_display = dff[display_cols].copy()

for col in display_cols:
    if col != 'Month':
        df_display[col] = df_display[col].apply(lambda x: f'${x:,.0f}' if x > 0 else '—')

st.dataframe(df_display, use_container_width=True, hide_index=True)

# Totals row
if len(dff) > 1:
    totals_row = {'Month': '**TOTAL**'}
    for col in display_cols:
        if col not in ['Month']:
            val = dff[col].sum() if col in dff.columns else 0
            totals_row[col] = f'**${val:,.0f}**'
    st.markdown("**Загалом за період: $" + f"{total_costs:,.0f}**")

st.divider()

# --- Data Source ---
st.markdown("### ℹ️ Джерело даних")
st.markdown("""
- **📢 Dribbble Ads** — акаунт 6332 (Dribbble Pro subscription) з QuickBooks
- **🚀 Boosting** — акаунт 6334 (Dribbble SaaS & Engagement boosting) з QuickBooks
- **🎨 Freelancers** — акаунт 5201 (Freelance UI/UX Designers) з QuickBooks
- **👥 Team Share** — відсоток зарплат команди на Dribbble: Kseniia 70%, Lev 50%, Stanislav 25%, Iryna 5%
- **Валюти**: EUR ×1.04, UAH ÷43.79
""")

show_last_updated("profitability")
