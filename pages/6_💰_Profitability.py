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

# --- Current Freelancer Rates (constant) ---
st.markdown("### 💲 Поточні ставки фрілансерів")
st.caption("Актуальна вартість шота та сету від кожного фрілансера (за домовленістю)")

FREELANCER_NAMES = [
    'Stepanchykov Oleh',
    'Nadezhda Galahova',
    'Tetiana Prykhodko',
    'Kateryna Fediakina',
    'Andrii Muzalov',
    'Mykyta Laptov',
]

def _gs_connect():
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    c = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return gspread.authorize(c).open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')

@st.cache_data(ttl=60)
def load_rates():
    ws = _gs_connect().worksheet('💰 Rates')
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=['Freelancer', 'Cost per Shot ($)', 'Cost per Set ($)'])
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def load_work_log():
    ws = _gs_connect().worksheet('💰 Work Log')
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=['Month', 'Freelancer', 'Shots', 'Sets'])
    return pd.DataFrame(data)

try:
    df_rates = load_rates()
    for col in ['Cost per Shot ($)', 'Cost per Set ($)']:
        if col in df_rates.columns:
            df_rates[col] = pd.to_numeric(df_rates[col].astype(str).str.replace('$','').str.replace(',',''), errors='coerce').fillna(0).astype(int)

    edited_rates = st.data_editor(
        df_rates, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Freelancer": st.column_config.SelectboxColumn("Freelancer", options=FREELANCER_NAMES, width="medium"),
            "Cost per Shot ($)": st.column_config.NumberColumn("$/Shot", min_value=0, format="$%d"),
            "Cost per Set ($)": st.column_config.NumberColumn("$/Set", min_value=0, format="$%d"),
        },
        key="rates_editor"
    )
    if st.button("💾 Зберегти ставки", key="save_rates", type="primary"):
        ws = _gs_connect().worksheet('💰 Rates')
        ws.clear()
        ws.update('A1', [edited_rates.columns.tolist()] + edited_rates.values.tolist())
        st.success("✅ Ставки збережено!")
        st.cache_data.clear()
except Exception as e:
    st.error(f"Помилка: {e}")

st.divider()

# --- Work Log per month ---
st.markdown("### 📝 Виконана робота фрілансерів")
st.caption("Вписуйте кількість шотів та сетів. Місяці та фрілансери заповнені автоматично. Оплата — з QuickBooks.")

try:
    df_wl = load_work_log()
    for col in ['Shots', 'Sets']:
        if col in df_wl.columns:
            df_wl[col] = pd.to_numeric(df_wl[col], errors='coerce').fillna(0).astype(int)

    # Show per-month tabs
    wl_months = df_wl['Month'].unique().tolist() if not df_wl.empty else []
    
    if wl_months:
        tabs = st.tabs(wl_months)
        edited_parts = {}
        for i, month in enumerate(wl_months):
            with tabs[i]:
                month_df = df_wl[df_wl['Month'] == month][['Freelancer', 'Shots', 'Sets']].reset_index(drop=True)
                edited = st.data_editor(
                    month_df, use_container_width=True, hide_index=True,
                    column_config={
                        "Freelancer": st.column_config.TextColumn("Freelancer", disabled=True, width="medium"),
                        "Shots": st.column_config.NumberColumn("Shots", min_value=0, format="%d"),
                        "Sets": st.column_config.NumberColumn("Sets", min_value=0, format="%d"),
                    },
                    key=f"work_{month}"
                )
                # Show QB payment for this month
                fl_pay = {}
                month_prof = df[df['Month'] == month]
                if not month_prof.empty:
                    row = month_prof.iloc[0]
                    for col in freelancer_cols:
                        name = col.replace('Freelancer: ', '')
                        if row[col] > 0:
                            fl_pay[name] = row[col]
                
                if fl_pay:
                    st.markdown("**💳 Оплати з QuickBooks:**")
                    pay_str = " · ".join([f"{n}: **${v:,.0f}**" for n, v in fl_pay.items()])
                    st.markdown(pay_str)
                
                edited_parts[month] = edited

        if st.button("💾 Зберегти роботу", key="save_work", type="primary"):
            # Rebuild full df
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
    else:
        st.info("Додайте місяці в таблицю '💰 Profitability' — вони з'являться тут автоматично")

    # --- Charts ---
    if not df_wl.empty and (df_wl['Shots'].sum() > 0 or df_wl['Sets'].sum() > 0):
        st.divider()
        st.markdown("### 📊 Продуктивність фрілансерів")

        # Shots per freelancer (total)
        fl_totals = df_wl.groupby('Freelancer').agg(Shots=('Shots','sum'), Sets=('Sets','sum')).reset_index()
        fl_totals = fl_totals[(fl_totals['Shots'] > 0) | (fl_totals['Sets'] > 0)]
        
        if not fl_totals.empty:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### 📸 Шоти по фрілансерах")
                fig_s = px.bar(fl_totals.sort_values('Shots'), x='Shots', y='Freelancer', orientation='h',
                              text='Shots', color_discrete_sequence=['#3498db'])
                fig_s.update_traces(textposition='outside')
                fig_s.update_layout(height=max(250, len(fl_totals)*50), yaxis_title='')
                st.plotly_chart(fig_s, use_container_width=True)
            with col_b:
                st.markdown("#### 📦 Сети по фрілансерах")
                fig_st = px.bar(fl_totals.sort_values('Sets'), x='Sets', y='Freelancer', orientation='h',
                               text='Sets', color_discrete_sequence=['#2ecc71'])
                fig_st.update_traces(textposition='outside')
                fig_st.update_layout(height=max(250, len(fl_totals)*50), yaxis_title='')
                st.plotly_chart(fig_st, use_container_width=True)

        # Monthly trend
        if len(wl_months) > 1:
            monthly_totals = df_wl.groupby('Month').agg(Shots=('Shots','sum'), Sets=('Sets','sum')).reset_index()
            st.markdown("#### 📈 Шоти та сети по місяцях")
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=monthly_totals['Month'], y=monthly_totals['Shots'], name='Shots', marker_color='#3498db'))
            fig_m.add_trace(go.Bar(x=monthly_totals['Month'], y=monthly_totals['Sets'], name='Sets', marker_color='#2ecc71'))
            fig_m.update_layout(barmode='group', height=350, yaxis_title='Count')
            st.plotly_chart(fig_m, use_container_width=True)

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
