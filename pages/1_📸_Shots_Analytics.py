import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import gspread
import pandas as pd
import numpy as np
from google.oauth2.service_account import Credentials
from datetime import datetime



# --- Modern Light Theme CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f5f7fb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
    section[data-testid="stSidebar"] * { color: #fff !important; }
    section[data-testid="stSidebar"] a { color: #e0d4ff !important; }
    [data-testid="stMetric"] { 
        background: #ffffff; padding: 18px; border-radius: 14px; 
        box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: none;
    }
    [data-testid="stMetricValue"] { color: #667eea; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #8892a4; }
    h1 { color: #2d3436 !important; font-weight: 800 !important; }
    h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab"] { color: #667eea; font-weight: 600; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #667eea; }
    .stDivider { border-color: #e8ecf1 !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    div[data-testid="stNumberInput"] input { border-radius: 10px; }
    div[data-baseweb="select"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=300)
def load_data():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
    
    ws = sh.worksheet("📊 Shots Analytics")
    # Read only shot data columns A-K (skip profile stats in M-R)
    all_vals = ws.get('A1:K250')
    if len(all_vals) < 2:
        return pd.DataFrame(), {}, {}
    headers = all_vals[0]
    rows = [r + [''] * (len(headers) - len(r)) for r in all_vals[1:] if any(r)]
    df = pd.DataFrame(rows, columns=headers)
    df = df[df['Название'].astype(str).str.strip() != '']
    
    # Parse numeric columns
    for col in ['Просмотры', 'Лайки', 'Сохранения', 'Комментарии', 'Кол-во тегов']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Parse engagement
    if 'Engagement %' in df.columns:
        df['Engagement'] = df['Engagement %'].str.replace('%', '').astype(float)
    
    # Parse dates
    if 'Дата' in df.columns:
        df['Date'] = pd.to_datetime(df['Дата'], format='mixed', errors='coerce')
        df['Year'] = df['Date'].dt.year
        df['Month_num'] = df['Date'].dt.month
        df['Week'] = df['Date'].dt.isocalendar().week.astype(int)
        df['Year_Week'] = df['Date'].dt.strftime('%Y-W%W')
    
    # Profile stats (from M column area)
    profile = {}
    try:
        vals = ws.get('M1:N12')
        for row in vals:
            if len(row) >= 2:
                profile[row[0]] = row[1]
    except:
        pass
    
    # Monthly summary
    monthly = {}
    try:
        vals = ws.get('M14:R60')
        if vals and len(vals) > 0:
            headers = vals[0]
            for row in vals[1:]:
                if len(row) >= 6 and row[0]:
                    monthly[row[0]] = {
                        'shots': int(row[1]) if row[1] else 0,
                        'views': int(row[2]) if row[2] else 0,
                        'likes': int(row[3]) if row[3] else 0,
                        'saves': int(row[4]) if row[4] else 0,
                        'comments': int(row[5]) if row[5] else 0,
                    }
    except:
        pass
    
    return df, profile, monthly

df, profile, monthly = load_data()

# --- HEADER ---
st.markdown("# 📸 VALMAX Shots Analytics")
st.markdown("Аналітика по шотам на Dribbble")

# --- PROFILE STATS ---
st.divider()
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("📊 Усього шотів", len(df))
p2.metric("👥 Підписники", profile.get('Подписчики', '?'))
p3.metric("👁️ Усього переглядів", f"{df['Просмотры'].sum():,}")
p4.metric("❤️ Усього лайків", f"{df['Лайки'].sum():,}")
p5.metric("💾 Усього збережень", f"{df['Сохранения'].sum():,}")

# --- FILTERS ---
st.divider()
st.markdown("#### 🔍 Фільтри")
col_f1, col_f2, col_f3 = st.columns(3)

# Month filter with English month names, sorted newest first
if "Месяц" in df.columns:
    ru_to_en = {'Январь':'January','Февраль':'February','Март':'March','Апрель':'April',
                'Май':'May','Июнь':'June','Июль':'July','Август':'August',
                'Сентябрь':'September','Октябрь':'October','Ноябрь':'November','Декабрь':'December'}
    month_num = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
                 'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
    
    # Build English month labels
    en_months_set = set()
    month_map = {}  # en_label -> original value
    for m in df["Месяц"].unique():
        parts = str(m).split()
        if len(parts) == 2 and parts[0] in ru_to_en:
            en_label = f"{ru_to_en[parts[0]]} {parts[1]}"
            en_months_set.add(en_label)
            month_map[en_label] = m
    
    sorted_en_months = sorted(en_months_set, 
        key=lambda x: int(x.split()[1])*100 + month_num.get(x.split()[0], 0), reverse=True)
    months_available = ["All"] + sorted_en_months
else:
    months_available = ["All"]
    month_map = {}

with col_f1:
    month_filter = st.selectbox("📅 Month", months_available)

# Date range
with col_f2:
    if 'Date' in df.columns:
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()
        date_range = st.date_input("📆 Date range", value=(min_date, max_date), 
                                    min_value=min_date, max_value=max_date)
    else:
        date_range = None

# Views range
with col_f3:
    max_views_val = int(df['Просмотры'].max()) if len(df) > 0 else 100000
    views_range = st.slider("👁️ Views range", min_value=0, max_value=max_views_val, 
                            value=(0, max_views_val), step=1000)

# Apply filters
filtered = df.copy()
if month_filter != "All":
    original_month = month_map.get(month_filter, month_filter)
    filtered = filtered[filtered["Месяц"] == original_month]
if date_range and len(date_range) == 2 and 'Date' in filtered.columns:
    filtered = filtered[(filtered['Date'].dt.date >= date_range[0]) & (filtered['Date'].dt.date <= date_range[1])]
filtered = filtered[(filtered['Просмотры'] >= views_range[0]) & (filtered['Просмотры'] <= views_range[1])]
filtered = filtered.sort_values('Просмотры', ascending=False)

# Filtered metrics
st.divider()
fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
fc1.metric("Шотів", len(filtered))
fc2.metric("Перегляди", f"{filtered['Просмотры'].sum():,}")
fc3.metric("Лайки", f"{filtered['Лайки'].sum():,}")
fc4.metric("Збереження", f"{filtered['Сохранения'].sum():,}")
fc5.metric("Коментарі", f"{filtered['Комментарии'].sum():,}")
avg_eng = filtered['Engagement'].mean() if 'Engagement' in filtered.columns and len(filtered) > 0 else 0
fc6.metric("Avg Engagement", f"{avg_eng:.2f}%")

# --- MONTHLY DYNAMICS ---
st.divider()
st.markdown("### 📈 Динаміка по місяцях")

_ru_to_en_m = {'Январь':'January','Февраль':'February','Март':'March','Апрель':'April',
               'Май':'May','Июнь':'June','Июль':'July','Август':'August',
               'Сентябрь':'September','Октябрь':'October','Ноябрь':'November','Декабрь':'December'}

def _to_en_month(m):
    parts = str(m).split()
    if len(parts) == 2 and parts[0] in _ru_to_en_m:
        return f"{_ru_to_en_m[parts[0]]} {parts[1]}"
    return m

if monthly:
    month_order = {'Январь':1,'Февраль':2,'Март':3,'Апрель':4,'Май':5,'Июнь':6,
                   'Июль':7,'Август':8,'Сентябрь':9,'Октябрь':10,'Ноябрь':11,'Декабрь':12}
    
    mdf_rows = []
    for m, d in monthly.items():
        parts = m.split()
        if len(parts) == 2:
            sort_key = int(parts[1]) * 100 + month_order.get(parts[0], 0)
            mdf_rows.append({
                'Month': _to_en_month(m), 'sort': sort_key,
                'Shots': d['shots'], 'Views': d['views'], 
                'Likes': d['likes'], 'Saves': d['saves'], 'Comments': d['comments'],
                'Avg Views/Shot': round(d['views'] / d['shots']) if d['shots'] > 0 else 0,
                'Avg Likes/Shot': round(d['likes'] / d['shots']) if d['shots'] > 0 else 0,
            })
    
    mdf = pd.DataFrame(mdf_rows).sort_values('sort')
    mdf_recent = mdf.tail(12)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Views", "Likes", "Shots/month", "Avg Views/Shot"])
    
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mdf_recent['Month'], y=mdf_recent['Views'], name='Views',
                            marker_color='#667eea'))
        fig.add_trace(go.Scatter(x=mdf_recent['Month'], y=mdf_recent['Views'], name='Trend',
                                line=dict(color='#43e97b', width=2), mode='lines+markers'))
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", 
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mdf_recent['Month'], y=mdf_recent['Likes'], name='Likes', marker_color='#f093fb'))
        fig.add_trace(go.Bar(x=mdf_recent['Month'], y=mdf_recent['Saves'], name='Saves', marker_color='#feca57'))
        fig.add_trace(go.Bar(x=mdf_recent['Month'], y=mdf_recent['Comments'], name='Comments', marker_color='#43e97b'))
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=400, barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = px.bar(mdf_recent, x='Month', y='Shots', template="plotly_white",
                     color_discrete_sequence=['#667eea'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mdf_recent['Month'], y=mdf_recent['Avg Views/Shot'],
                                mode='lines+markers', name='Avg Views/Shot',
                                line=dict(color='#667eea', width=3), marker=dict(size=10)))
        fig.add_trace(go.Scatter(x=mdf_recent['Month'], y=mdf_recent['Avg Likes/Shot'],
                                mode='lines+markers', name='Avg Likes/Shot',
                                line=dict(color='#f093fb', width=3), marker=dict(size=10), yaxis='y2'))
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=400,
                         yaxis2=dict(title='Avg Likes/Shot', overlaying='y', side='right', showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

    # Growth comparison: monthly + weekly toggle
    st.markdown("### 📊 Growth comparison")
    growth_mode = st.radio("Compare by:", ["Month vs previous month", "Week vs previous week"], horizontal=True)
    
    if growth_mode == "Month vs previous month":
        if len(mdf_recent) >= 2:
            growth_rows = []
            mdf_desc = mdf_recent.iloc[::-1]  # newest first
            for i in range(len(mdf_desc) - 1):
                curr = mdf_desc.iloc[i]
                prev = mdf_desc.iloc[i + 1]
                views_g = ((curr['Views'] - prev['Views']) / prev['Views'] * 100) if prev['Views'] > 0 else 0
                likes_g = ((curr['Likes'] - prev['Likes']) / prev['Likes'] * 100) if prev['Likes'] > 0 else 0
                growth_rows.append({
                    'Month': curr['Month'],
                    'vs': prev['Month'],
                    'Views Δ%': f"{views_g:+.1f}%",
                    'Likes Δ%': f"{likes_g:+.1f}%",
                    'Shots': curr['Shots'],
                    'Views': f"{curr['Views']:,}",
                    'Likes': f"{curr['Likes']:,}",
                })
            st.dataframe(pd.DataFrame(growth_rows), use_container_width=True, hide_index=True)
    else:
        # Week-over-week from raw shot data
        if 'Date' in df.columns and 'Year_Week' in df.columns:
            weekly = df.groupby('Year_Week').agg({
                'Просмотры': 'sum', 'Лайки': 'sum', 'Сохранения': 'sum',
                'Комментарии': 'sum', 'Название': 'count'
            }).rename(columns={'Название': 'Shots', 'Просмотры': 'Views', 
                              'Лайки': 'Likes', 'Сохранения': 'Saves', 'Комментарии': 'Comments'})
            weekly = weekly.sort_index()
            
            wg_rows = []
            weeks_list = weekly.index.tolist()
            for i in range(len(weeks_list) - 1, 0, -1):
                curr_w = weeks_list[i]
                prev_w = weeks_list[i - 1]
                c = weekly.loc[curr_w]
                p = weekly.loc[prev_w]
                vg = ((c['Views'] - p['Views']) / p['Views'] * 100) if p['Views'] > 0 else 0
                lg = ((c['Likes'] - p['Likes']) / p['Likes'] * 100) if p['Likes'] > 0 else 0
                wg_rows.append({
                    'Week': curr_w,
                    'vs': prev_w,
                    'Views Δ%': f"{vg:+.1f}%",
                    'Likes Δ%': f"{lg:+.1f}%",
                    'Shots': int(c['Shots']),
                    'Views': f"{int(c['Views']):,}",
                    'Likes': f"{int(c['Likes']):,}",
                })
            st.dataframe(pd.DataFrame(wg_rows[:20]), use_container_width=True, hide_index=True)

# --- TOP SHOTS ---
st.divider()
st.markdown("### 🏆 Топ шоти")

top_col1, top_col2 = st.columns(2)

with top_col1:
    st.markdown("**By views (All-time)**")
    top_views = df.nlargest(10, 'Просмотры')[['Название', 'Просмотры', 'Лайки', 'Дата']].reset_index(drop=True)
    top_views.index = top_views.index + 1
    st.dataframe(top_views, use_container_width=True)

with top_col2:
    st.markdown("**By likes (All-time)**")
    top_likes = df.nlargest(10, 'Лайки')[['Название', 'Лайки', 'Просмотры', 'Дата']].reset_index(drop=True)
    top_likes.index = top_likes.index + 1
    st.dataframe(top_likes, use_container_width=True)

# --- ENGAGEMENT ANALYSIS ---
st.divider()
st.markdown("### 🎯 Engagement аналіз")

eng_col1, eng_col2 = st.columns(2)

with eng_col1:
    st.markdown("**Engagement Rate by month**")
    if 'Date' in df.columns:
        monthly_eng = df.groupby('Месяц').agg({
            'Engagement': 'mean',
            'Просмотры': 'sum'
        }).reset_index()
        def month_sort(m):
            mo = {'Январь':1,'Февраль':2,'Март':3,'Апрель':4,'Май':5,'Июнь':6,
                  'Июль':7,'Август':8,'Сентябрь':9,'Октябрь':10,'Ноябрь':11,'Декабрь':12}
            p = m.split()
            return int(p[1])*100+mo.get(p[0],0) if len(p)==2 and p[0] in mo else 0
        
        monthly_eng['sort'] = monthly_eng['Месяц'].apply(month_sort)
        monthly_eng = monthly_eng.sort_values('sort').tail(12)
        monthly_eng['Month'] = monthly_eng['Месяц'].apply(_to_en_month)
        
        fig = px.line(monthly_eng, x='Month', y='Engagement', template="plotly_white",
                     markers=True, color_discrete_sequence=['#43e97b'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350, yaxis_title="Engagement %")
        st.plotly_chart(fig, use_container_width=True)

with eng_col2:
    st.markdown("**Views vs Engagement (scatter)**")
    if 'Engagement' in df.columns:
        fig = px.scatter(df, x='Просмотры', y='Engagement', hover_name='Название',
                        size='Лайки', template="plotly_white",
                        color_discrete_sequence=['#667eea'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- TAGS ANALYSIS ---
st.divider()
st.markdown("### 🏷️ Топ теги")

if 'Теги' in df.columns:
    # Collect all tags with their shot metrics
    tag_stats = {}
    for _, row in df.iterrows():
        tags = str(row.get('Теги', '')).split(', ')
        for tag in tags:
            tag = tag.strip()
            if not tag:
                continue
            if tag not in tag_stats:
                tag_stats[tag] = {'count': 0, 'total_views': 0, 'total_likes': 0}
            tag_stats[tag]['count'] += 1
            tag_stats[tag]['total_views'] += row.get('Просмотры', 0)
            tag_stats[tag]['total_likes'] += row.get('Лайки', 0)
    
    tags_df = pd.DataFrame([
        {'Тег': tag, 'Шотов': d['count'], 
         'Всего просмотров': d['total_views'],
         'Avg Views/Shot': round(d['total_views'] / d['count']) if d['count'] > 0 else 0,
         'Всего лайков': d['total_likes'],
         'Avg Likes/Shot': round(d['total_likes'] / d['count']) if d['count'] > 0 else 0}
        for tag, d in tag_stats.items()
    ])
    
    tag_col1, tag_col2 = st.columns(2)
    
    with tag_col1:
        st.markdown("**Самые используемые теги**")
        top_used = tags_df.nlargest(15, 'Шотов')
        fig = px.bar(top_used, x='Шотов', y='Тег', orientation='h', template="plotly_white",
                     color_discrete_sequence=['#667eea'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    
    with tag_col2:
        st.markdown("**Теги с лучшим Avg Views/Shot** (мин. 3 шота)")
        best_tags = tags_df[tags_df['Шотов'] >= 3].nlargest(15, 'Avg Views/Shot')
        fig = px.bar(best_tags, x='Avg Views/Shot', y='Тег', orientation='h', template="plotly_white",
                     color_discrete_sequence=['#43e97b'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

# --- PROJECT TYPES ---
st.divider()
st.markdown("### 🎨 Типи проєктів")

def classify_shot(name):
    name = str(name).lower()
    if any(k in name for k in ['dashboard', 'analytics', 'crm', 'saas', 'admin']):
        return 'Dashboard/SaaS'
    elif any(k in name for k in ['mobile', 'app ui', 'app design']):
        return 'Mobile App'
    elif any(k in name for k in ['website', 'web design', 'landing', 'e-commerce', 'shopify']):
        return 'Website/Landing'
    elif any(k in name for k in ['brand', 'logo', 'identity', 'guidelines']):
        return 'Branding'
    elif any(k in name for k in ['animation', 'motion', 'scroll']):
        return 'Animation'
    else:
        return 'Other'

if 'Название' in df.columns:
    df['Тип проекта'] = df['Название'].apply(classify_shot)
    
    type_col1, type_col2 = st.columns(2)
    
    with type_col1:
        type_counts = df['Тип проекта'].value_counts().reset_index()
        type_counts.columns = ['Тип', 'Кол-во']
        fig = px.pie(type_counts, names='Тип', values='Кол-во', template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with type_col2:
        type_perf = df.groupby('Тип проекта').agg({
            'Просмотры': 'mean', 'Лайки': 'mean', 'Engagement': 'mean'
        }).round(0).reset_index()
        type_perf.columns = ['Тип', 'Avg Views', 'Avg Likes', 'Avg Engagement']
        fig = px.bar(type_perf, x='Тип', y='Avg Views', template="plotly_white",
                     color='Avg Engagement', color_continuous_scale=['#f5576c', '#00d4aa'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- ALL SHOTS TABLE ---
st.divider()
st.markdown("### 📋 Усі шоти")
display_cols = ['Месяц', 'Дата', 'Название', 'Просмотры', 'Лайки', 'Сохранения', 'Комментарии', 'Engagement %', 'Кол-во тегов']
available_cols = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available_cols], use_container_width=True, height=500)

# --- FOOTER ---
st.divider()
st.caption("📸 VALMAX Dribbble Shots Analytics | Оновлюється щотижня (пн 8:00 CET)")
