import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from utils import show_last_updated

st.set_page_config(page_title="Dribbble Profitability", page_icon="💰", layout="wide")

st.markdown("""<style>
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%) !important; }
section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
section[data-testid="stSidebar"] a { color: #c4b5fd !important; }
</style>""", unsafe_allow_html=True)

st.title("💰 Dribbble P&L")
st.caption("Прибутковість Dribbble каналу: Revenue vs Costs, ROI, середній чек, вартість ліду")

# --- Data Loading ---
def _gs_connect():
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    c = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(c).open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')

@st.cache_data(ttl=60)
def load_all():
    sh = _gs_connect()
    costs = pd.DataFrame(sh.worksheet('💰 Profitability').get_all_records())
    revenue = pd.DataFrame(sh.worksheet('💰 Revenue').get_all_records())
    rates = pd.DataFrame(sh.worksheet('💰 Rates').get_all_records())
    work = pd.DataFrame(sh.worksheet('💰 Work Log').get_all_records())
    return costs, revenue, rates, work

try:
    df_costs, df_rev, df_rates, df_work = load_all()
except Exception as e:
    st.error(f"Помилка завантаження: {e}")
    st.stop()

# Convert numeric
for df in [df_costs, df_rev]:
    for col in df.columns:
        if col != 'Month':
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0)

for col in ['Shots', 'Sets']:
    if col in df_work.columns:
        df_work[col] = pd.to_numeric(df_work[col], errors='coerce').fillna(0).astype(int)

for col in ['Cost per Shot ($)', 'Cost per Set ($)']:
    if col in df_rates.columns:
        df_rates[col] = pd.to_numeric(df_rates[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0).astype(int)

# Parse dates for sorting
from datetime import datetime
def parse_month(m):
    try: return datetime.strptime(m.strip(), '%B %Y')
    except: return datetime(2020,1,1)

for df in [df_costs, df_rev]:
    if not df.empty:
        df['_date'] = df['Month'].apply(parse_month)
        df.sort_values('_date', inplace=True)
        df.reset_index(drop=True, inplace=True)

# Merge costs + revenue
if not df_costs.empty:
    df_costs['_quarter'] = df_costs['_date'].apply(lambda d: f"Q{(d.month-1)//3+1} {d.year}")
    df_costs['_year'] = df_costs['_date'].apply(lambda d: str(d.year))

# Merge revenue into costs by month
df = df_costs.copy()
if not df_rev.empty:
    rev_map = df_rev.set_index('Month')[['Deals Won', 'Revenue ($)', 'Deals Lost', 'Deals Open']].to_dict('index')
    for col in ['Deals Won', 'Revenue ($)', 'Deals Lost', 'Deals Open']:
        df[col] = df['Month'].apply(lambda m: rev_map.get(m, {}).get(col, 0))
else:
    for col in ['Deals Won', 'Revenue ($)', 'Deals Lost', 'Deals Open']:
        df[col] = 0

# Leads count from Project Requests
try:
    leads_ws = _gs_connect().worksheet('📋 Project Requests')
    leads_data = leads_ws.get_all_records()
    df_leads = pd.DataFrame(leads_data)
    if 'Місяць' in df_leads.columns:
        leads_by_month = df_leads.groupby('Місяць').size().to_dict()
    else:
        leads_by_month = {}
except:
    leads_by_month = {}

df['Leads'] = df['Month'].apply(lambda m: leads_by_month.get(m, 0))

freelancer_cols = [c for c in df.columns if 'Freelancer' in c]

# --- FILTER ---
st.markdown("### 🔍 Період")
filter_options = ['All Time'] + sorted(df['_year'].unique().tolist(), reverse=True) + sorted(df.get('_quarter', pd.Series()).unique().tolist(), reverse=True) + df['Month'].tolist()[::-1]
selected = st.selectbox("", filter_options, index=0, label_visibility="collapsed")

if selected == 'All Time':
    dff = df.copy()
elif selected in df['_year'].values:
    dff = df[df['_year'] == selected]
elif '_quarter' in df.columns and selected in df['_quarter'].values:
    dff = df[df['_quarter'] == selected]
else:
    dff = df[df['Month'] == selected]

period_label = selected if selected != 'All Time' else 'Весь час'

# --- Calculations ---
total_revenue = dff['Revenue ($)'].sum()
total_costs = dff['TOTAL COSTS'].sum()
profit = total_revenue - total_costs
roi = (profit / total_costs * 100) if total_costs > 0 else 0
deals_won = int(dff['Deals Won'].sum())
total_leads = int(dff['Leads'].sum())
avg_deal = total_revenue / deals_won if deals_won > 0 else 0
cost_per_lead = total_costs / total_leads if total_leads > 0 else 0

st.divider()

# === P&L OVERVIEW ===
st.markdown(f"### 📊 P&L — {period_label}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Revenue", f"${total_revenue:,.0f}")
col2.metric("📉 Costs", f"${total_costs:,.0f}")
profit_color = "normal" if profit >= 0 else "inverse"
col3.metric("📈 Profit", f"${profit:,.0f}", delta=f"{roi:+.0f}% ROI" if total_costs > 0 else None, delta_color=profit_color)
col4.metric("🎯 Channel Status", "✅ Profitable" if profit >= 0 else "❌ Unprofitable")

col5, col6, col7, col8 = st.columns(4)
col5.metric("🤝 Deals Won", f"{deals_won}")
col6.metric("💵 Avg Deal", f"${avg_deal:,.0f}")
col7.metric("📋 Leads", f"{total_leads}")
col8.metric("💸 Cost per Lead", f"${cost_per_lead:,.0f}")

st.divider()

# === MONTHLY P&L TREND ===
if len(dff) > 1:
    st.markdown("### 📈 P&L динаміка по місяцях")
    
    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Bar(x=dff['Month'], y=dff['Revenue ($)'], name='Revenue', marker_color='#2ecc71'))
    fig_pnl.add_trace(go.Bar(x=dff['Month'], y=dff['TOTAL COSTS'], name='Costs', marker_color='#e74c3c'))
    
    # Profit line
    monthly_profit = dff['Revenue ($)'] - dff['TOTAL COSTS']
    fig_pnl.add_trace(go.Scatter(x=dff['Month'], y=monthly_profit, name='Profit',
                                  mode='lines+markers+text', line=dict(color='#f1c40f', width=3),
                                  text=[f'${v:,.0f}' for v in monthly_profit], textposition='top center'))
    
    fig_pnl.update_layout(barmode='group', height=450, yaxis_title='$',
                          legend=dict(orientation='h', y=1.1))
    st.plotly_chart(fig_pnl, use_container_width=True)
    st.divider()

# === COST BREAKDOWN ===
st.markdown(f"### 🥧 Структура витрат — {period_label}")

total_ads = dff['Dribbble Pro Subscription'].sum()
total_boost = dff.get('Dribbble Boosting/SaaS', pd.Series([0])).sum() + dff.get('Dribbble Designers (outsource)', pd.Series([0])).sum()
total_free = dff[freelancer_cols].sum().sum()
total_team = dff['Team (Dribbble share)'].sum()

col_a, col_b = st.columns(2)

with col_a:
    categories = {'📢 Dribbble Ads': total_ads, '🚀 Boosting': total_boost, '🎨 Freelancers': total_free, '👥 Team': total_team}
    categories = {k: v for k, v in categories.items() if v > 0}
    if categories:
        fig_pie = px.pie(names=list(categories.keys()), values=list(categories.values()),
                         color_discrete_map={'📢 Dribbble Ads': '#e74c3c', '🚀 Boosting': '#f39c12', '🎨 Freelancers': '#3498db', '👥 Team': '#2ecc71'})
        fig_pie.update_traces(textposition='inside', textinfo='percent+value+label', texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})')
        fig_pie.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

with col_b:
    st.markdown("#### Деталізація")
    cost_detail = [
        {'Category': '📢 Dribbble Ads (Pro)', 'Amount': f'${total_ads:,.0f}'},
        {'Category': '🚀 Boosting / SaaS', 'Amount': f'${total_boost:,.0f}'},
        {'Category': '🎨 Freelancers', 'Amount': f'${total_free:,.0f}'},
        {'Category': '👥 Team (Dribbble share)', 'Amount': f'${total_team:,.0f}'},
        {'Category': '**TOTAL**', 'Amount': f'**${total_costs:,.0f}**'},
    ]
    st.dataframe(pd.DataFrame(cost_detail), use_container_width=True, hide_index=True)

# Cost trend stacked
if len(dff) > 1:
    chart_data = []
    for _, row in dff.iterrows():
        chart_data.append({'Month': row['Month'], 'Category': '📢 Ads', 'Amount': row['Dribbble Pro Subscription']})
        boost = row.get('Dribbble Boosting/SaaS', 0) + row.get('Dribbble Designers (outsource)', 0)
        chart_data.append({'Month': row['Month'], 'Category': '🚀 Boosting', 'Amount': boost})
        fl = sum(row[c] for c in freelancer_cols)
        chart_data.append({'Month': row['Month'], 'Category': '🎨 Freelancers', 'Amount': fl})
        chart_data.append({'Month': row['Month'], 'Category': '👥 Team', 'Amount': row['Team (Dribbble share)']})
    df_chart = pd.DataFrame(chart_data)
    df_chart = df_chart[df_chart['Amount'] > 0]
    
    fig_stack = px.bar(df_chart, x='Month', y='Amount', color='Category', barmode='stack',
                       color_discrete_map={'📢 Ads': '#e74c3c', '🚀 Boosting': '#f39c12', '🎨 Freelancers': '#3498db', '👥 Team': '#2ecc71'})
    fig_stack.update_layout(height=350, legend=dict(orientation='h', y=1.1), yaxis_title='$')
    st.plotly_chart(fig_stack, use_container_width=True)

st.divider()

# === FREELANCER RANKING ===
st.markdown(f"### 🏆 Фрілансери — {period_label}")

freelancer_totals = {}
for col in freelancer_cols:
    total = dff[col].sum()
    if total > 0:
        freelancer_totals[col.replace('Freelancer: ', '')] = total

if freelancer_totals:
    df_fl = pd.DataFrame([{'Freelancer': k, 'QB Payment': v} for k, v in freelancer_totals.items()])
    df_fl = df_fl.sort_values('QB Payment', ascending=True)
    
    fig_fl = px.bar(df_fl, x='QB Payment', y='Freelancer', orientation='h', text='QB Payment',
                    color_discrete_sequence=['#3498db'])
    fig_fl.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig_fl.update_layout(yaxis_title='', xaxis_title='Payment ($)', height=max(250, len(df_fl)*50))
    st.plotly_chart(fig_fl, use_container_width=True)

st.divider()

# === RATE CARD ===
st.markdown("### 💲 Поточні ставки фрілансерів")
st.caption("Актуальна вартість за домовленістю (константа)")

FREELANCER_NAMES = ['Stepanchykov Oleh','Nadezhda Galahova','Tetiana Prykhodko','Kateryna Fediakina','Andrii Muzalov','Mykyta Laptov']

try:
    edited_rates = st.data_editor(
        df_rates, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Freelancer": st.column_config.SelectboxColumn("Freelancer", options=FREELANCER_NAMES, width="medium"),
            "Cost per Shot ($)": st.column_config.NumberColumn("$/Shot", min_value=0, format="$%d"),
            "Cost per Set ($)": st.column_config.NumberColumn("$/Set", min_value=0, format="$%d"),
        }, key="rates_editor"
    )
    if st.button("💾 Зберегти ставки", key="save_rates", type="primary"):
        ws = _gs_connect().worksheet('💰 Rates')
        ws.clear()
        ws.update('A1', [edited_rates.columns.tolist()] + edited_rates.values.tolist())
        st.success("✅ Збережено!")
        st.cache_data.clear()
except Exception as e:
    st.error(f"Помилка: {e}")

st.divider()

# === WORK LOG ===
st.markdown("### 📝 Виконана робота")
st.caption("Кількість шотів та сетів за місяць. Оплата — автоматично з QuickBooks.")

try:
    wl_months = df_work['Month'].unique().tolist() if not df_work.empty else []
    
    if wl_months:
        tabs = st.tabs(wl_months)
        edited_parts = {}
        for i, month in enumerate(wl_months):
            with tabs[i]:
                month_df = df_work[df_work['Month'] == month][['Freelancer', 'Shots', 'Sets']].reset_index(drop=True)
                edited = st.data_editor(
                    month_df, use_container_width=True, hide_index=True,
                    column_config={
                        "Freelancer": st.column_config.TextColumn("Freelancer", disabled=True, width="medium"),
                        "Shots": st.column_config.NumberColumn("Shots", min_value=0, format="%d"),
                        "Sets": st.column_config.NumberColumn("Sets", min_value=0, format="%d"),
                    }, key=f"work_{month}"
                )
                edited_parts[month] = edited
        
        if st.button("💾 Зберегти роботу", key="save_work", type="primary"):
            all_rows = []
            for month, edited in edited_parts.items():
                for _, r in edited.iterrows():
                    all_rows.append({'Month': month, 'Freelancer': r['Freelancer'], 'Shots': r['Shots'], 'Sets': r['Sets']})
            df_save = pd.DataFrame(all_rows)
            ws = _gs_connect().worksheet('💰 Work Log')
            ws.clear()
            ws.update('A1', [df_save.columns.tolist()] + df_save.values.tolist())
            st.success("✅ Збережено!")
            st.cache_data.clear()
        
        # Productivity charts
        if df_work['Shots'].sum() > 0 or df_work['Sets'].sum() > 0:
            fl_totals = df_work.groupby('Freelancer').agg(Shots=('Shots','sum'), Sets=('Sets','sum')).reset_index()
            fl_totals = fl_totals[(fl_totals['Shots'] > 0) | (fl_totals['Sets'] > 0)]
            if not fl_totals.empty:
                col_a, col_b = st.columns(2)
                with col_a:
                    fig_s = px.bar(fl_totals.sort_values('Shots'), x='Shots', y='Freelancer', orientation='h',
                                  text='Shots', color_discrete_sequence=['#3498db'])
                    fig_s.update_traces(textposition='outside')
                    fig_s.update_layout(height=max(250, len(fl_totals)*50), yaxis_title='', title='📸 Shots')
                    st.plotly_chart(fig_s, use_container_width=True)
                with col_b:
                    fig_st = px.bar(fl_totals.sort_values('Sets'), x='Sets', y='Freelancer', orientation='h',
                                   text='Sets', color_discrete_sequence=['#2ecc71'])
                    fig_st.update_traces(textposition='outside')
                    fig_st.update_layout(height=max(250, len(fl_totals)*50), yaxis_title='', title='📦 Sets')
                    st.plotly_chart(fig_st, use_container_width=True)
    else:
        st.info("Додайте місяці в '💰 Profitability'")
except Exception as e:
    st.error(f"Помилка: {e}")

st.divider()

# === FULL TABLE ===
st.markdown("### 📋 Повна таблиця P&L")
summary_cols = ['Month', 'Revenue ($)', 'TOTAL COSTS', 'Deals Won', 'Leads']
avail_cols = [c for c in summary_cols if c in dff.columns]
df_table = dff[avail_cols].copy()
df_table['Profit ($)'] = df_table['Revenue ($)'] - df_table['TOTAL COSTS']
df_table['ROI (%)'] = df_table.apply(lambda r: f"{r['Profit ($)'] / r['TOTAL COSTS'] * 100:.0f}%" if r['TOTAL COSTS'] > 0 else '—', axis=1)

for col in ['Revenue ($)', 'TOTAL COSTS', 'Profit ($)']:
    df_table[col] = df_table[col].apply(lambda x: f'${x:,.0f}')

st.dataframe(df_table, use_container_width=True, hide_index=True)

if len(dff) > 1:
    st.markdown(f"**Загалом: Revenue ${total_revenue:,.0f} — Costs ${total_costs:,.0f} = Profit ${profit:,.0f} (ROI {roi:+.0f}%)**")

st.divider()

st.markdown("### ℹ️ Джерела даних")
st.markdown("""
- **Revenue** — Pipedrive CRM (won deals з "Dribbble" в назві)
- **Costs** — QuickBooks API (акаунти 6330-6334 Dribbble, 5201 Freelancers)
- **Team Share** — % зарплат: Kseniia 70%, Lev 50%, Stanislav 25%, Iryna 5%
- **Leads** — Google Sheet "📋 Project Requests"
""")

show_last_updated("profitability")
