import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
    section[data-testid="stSidebar"] * { color: #fff !important; }
    section[data-testid="stSidebar"] a { color: #e0d4ff !important; }
    h1, h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 💰 Dribbble Profitability")
st.caption("P&L аналітика Dribbble каналу — витрати vs дохід, ROI, окупність")

# --- MONTHLY DATA ---
# Real costs data (manually provided by user)
monthly_data = {
    'March 2026': {
        'revenue': 0,
        'costs': {
            'Реклама (офіційна)': 7000,
            'Фрілансери': 600,
            'Внутрішня команда': 1000,
            'Бустинг шотів': 500,
            'Тулзи/підписки': 50,
        },
        'leads': 6,  # March leads count
        'shots': 6,
        'note': 'Прогноз на основі поточних даних',
    },
    # Placeholder for previous months - fill with real data when available
    'February 2026': {
        'revenue': 0,
        'costs': {
            'Реклама (офіційна)': 7000,
            'Фрілансери': 600,
            'Внутрішня команда': 1000,
            'Бустинг шотів': 500,
            'Тулзи/підписки': 50,
        },
        'leads': 4,
        'shots': 7,
        'note': 'Приблизні дані',
    },
    'January 2026': {
        'revenue': 0,
        'costs': {
            'Реклама (офіційна)': 7000,
            'Фрілансери': 600,
            'Внутрішня команда': 1000,
            'Бустинг шотів': 500,
            'Тулзи/підписки': 50,
        },
        'leads': 5,
        'shots': 11,
        'note': 'Приблизні дані',
    },
}

# Calculate totals
for month, data in monthly_data.items():
    data['total_costs'] = sum(data['costs'].values())
    data['profit'] = data['revenue'] - data['total_costs']
    data['roi'] = ((data['revenue'] - data['total_costs']) / data['total_costs'] * 100) if data['total_costs'] > 0 else 0
    data['cpl'] = data['total_costs'] / data['leads'] if data['leads'] > 0 else 0
    data['cps'] = data['total_costs'] / data['shots'] if data['shots'] > 0 else 0

# --- PERIOD SELECTOR ---
st.divider()
period = st.radio("📅 Період", ["Поточний місяць (March 2026)", "Квартал (Q1 2026)", "За весь час"], horizontal=True)

if "Поточний" in period:
    months_to_show = ['March 2026']
    period_label = "March 2026"
elif "Квартал" in period:
    months_to_show = ['January 2026', 'February 2026', 'March 2026']
    period_label = "Q1 2026 (Jan-Mar)"
else:
    months_to_show = list(monthly_data.keys())
    period_label = "All Time"

total_revenue = sum(monthly_data[m]['revenue'] for m in months_to_show)
total_costs = sum(monthly_data[m]['total_costs'] for m in months_to_show)
total_profit = total_revenue - total_costs
total_roi = ((total_revenue - total_costs) / total_costs * 100) if total_costs > 0 else 0
total_leads = sum(monthly_data[m]['leads'] for m in months_to_show)
total_shots = sum(monthly_data[m]['shots'] for m in months_to_show)

# --- KPIs ---
st.markdown(f"### 📊 {period_label}")

k1, k2, k3, k4 = st.columns(4)
k1.metric("💵 Revenue", f"${total_revenue:,.0f}", help="Дохід від закритих угод з Dribbble лідів")
k2.metric("💸 Total Costs", f"${total_costs:,.0f}", help="Всі витрати на Dribbble канал")
k3.metric("📈 ROI", f"{total_roi:.0f}%", help="(Revenue - Costs) / Costs × 100%")
k4.metric("💰 Profit / Loss", f"${total_profit:,.0f}", 
          delta=f"{'Прибуток' if total_profit >= 0 else 'Збиток'}", 
          delta_color="normal" if total_profit >= 0 else "inverse")

k5, k6, k7, k8 = st.columns(4)
k5.metric("👥 Leads", total_leads, help="Кількість вхідних лідів")
k6.metric("📸 Shots", total_shots, help="Кількість опублікованих шотів")
k7.metric("💵 Cost per Lead", f"${total_costs/total_leads:,.0f}" if total_leads > 0 else "—", help="Витрати / кількість лідів")
k8.metric("💵 Cost per Shot", f"${total_costs/total_shots:,.0f}" if total_shots > 0 else "—", help="Витрати / кількість шотів")

# --- COST BREAKDOWN ---
st.divider()
st.markdown("### 💸 Структура витрат")

cost_col1, cost_col2 = st.columns(2)

with cost_col1:
    # Aggregate costs by category
    cost_cats = {}
    for m in months_to_show:
        for cat, val in monthly_data[m]['costs'].items():
            cost_cats[cat] = cost_cats.get(cat, 0) + val
    
    cost_df = pd.DataFrame([
        {'Категорія': k, 'Сума': v, 'Відсоток': f"{v/total_costs*100:.0f}%"} 
        for k, v in sorted(cost_cats.items(), key=lambda x: -x[1])
    ])
    
    fig = px.pie(cost_df, values='Сума', names='Категорія', 
                 color_discrete_sequence=['#667eea', '#764ba2', '#f5576c', '#ffa726', '#43e97b'])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350)
    st.plotly_chart(fig, use_container_width=True)

with cost_col2:
    st.markdown("**Деталі витрат:**")
    for _, row in cost_df.iterrows():
        st.markdown(f"- **{row['Категорія']}**: ${row['Сума']:,.0f} ({row['Відсоток']})")
    st.markdown(f"\n**Всього: ${total_costs:,.0f}**")

# --- MONTHLY COMPARISON ---
if len(months_to_show) > 1:
    st.divider()
    st.markdown("### 📈 Динаміка по місяцях")
    
    months_sorted = sorted(months_to_show, key=lambda m: list(monthly_data.keys()).index(m))
    
    chart_data = pd.DataFrame([{
        'Month': m,
        'Revenue': monthly_data[m]['revenue'],
        'Costs': monthly_data[m]['total_costs'],
        'Profit': monthly_data[m]['profit'],
        'Leads': monthly_data[m]['leads'],
    } for m in months_sorted])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Revenue', x=chart_data['Month'], y=chart_data['Revenue'], marker_color='#43e97b'))
    fig.add_trace(go.Bar(name='Costs', x=chart_data['Month'], y=chart_data['Costs'], marker_color='#f5576c'))
    fig.add_trace(go.Scatter(name='Profit', x=chart_data['Month'], y=chart_data['Profit'], 
                             mode='lines+markers', line=dict(color='#667eea', width=3)))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#636e72"), height=400, barmode='group')
    st.plotly_chart(fig, use_container_width=True)

# --- UNIT ECONOMICS ---
st.divider()
st.markdown("### 🎯 Unit Economics")
st.caption("Ключові показники ефективності Dribbble каналу")

ue1, ue2, ue3 = st.columns(3)

with ue1:
    st.markdown("**💵 Cost per Lead (CPL)**")
    for m in months_to_show:
        d = monthly_data[m]
        cpl = d['total_costs'] / d['leads'] if d['leads'] > 0 else 0
        st.markdown(f"- {m}: **${cpl:,.0f}**")

with ue2:
    st.markdown("**📸 Cost per Shot**")
    for m in months_to_show:
        d = monthly_data[m]
        cps = d['total_costs'] / d['shots'] if d['shots'] > 0 else 0
        st.markdown(f"- {m}: **${cps:,.0f}**")

with ue3:
    st.markdown("**📊 Conversion Rate**")
    st.markdown("- Won deals / Total leads")
    st.markdown(f"- **0%** (поки немає закритих угод)")
    st.caption("Оновиться коли ліди конвертуються в CRM")

# --- DATA SOURCE ---
st.divider()
st.markdown("### 📝 Джерело даних")
st.info("""
**Поточний стан**: Дані вводяться вручну.  
**В планах**: Автоматичне підтягування з QuickBooks API (верифікація app в процесі).

Щоб оновити дані — скинь мені нові цифри витрат/доходів за місяць.
""")

st.divider()
st.caption("💰 Profitability | Дані: ручний ввід + Pipedrive CRM | QuickBooks API в процесі підключення")
