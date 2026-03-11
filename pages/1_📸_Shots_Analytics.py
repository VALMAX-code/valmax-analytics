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
@st.cache_data(ttl=60)
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
    
    # Parse engagement (handle multiple column name formats)
    if 'Engagement %' in df.columns:
        df['Engagement'] = pd.to_numeric(df['Engagement %'].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
    elif 'Engagement%' in df.columns:
        df['Engagement'] = pd.to_numeric(df['Engagement%'].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
    elif 'Engagement' not in df.columns:
        df['Engagement'] = 0.0
    
    # Parse dates
    if 'Дата' in df.columns:
        df['Date'] = pd.to_datetime(df['Дата'], format='mixed', errors='coerce')
        df['Year'] = df['Date'].dt.year
        df['Month_num'] = df['Date'].dt.month
        df['Week'] = df['Date'].dt.isocalendar().week.astype(int)
        # Week label as date range: "Feb 24 – Mar 2"
        week_start = df['Date'] - pd.to_timedelta(df['Date'].dt.weekday, unit='d')
        week_end = week_start + pd.Timedelta(days=6)
        df['Week_Start'] = week_start
        df['Year_Week'] = week_start.dt.strftime('%Y-W%W')
        df['Week_Label'] = week_start.dt.strftime('%b %d') + ' – ' + week_end.dt.strftime('%b %d, %Y')
    
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
            def safe_int(v):
                if not v: return 0
                try: return int(str(v).replace(',', '').replace(' ', ''))
                except: return 0
            for row in vals[1:]:
                if len(row) >= 6 and row[0]:
                    monthly[row[0]] = {
                        'shots': safe_int(row[1]),
                        'views': safe_int(row[2]),
                        'likes': safe_int(row[3]),
                        'saves': safe_int(row[4]),
                        'comments': safe_int(row[5]),
                    }
    except:
        pass
    
    return df, profile, monthly

df, profile, monthly = load_data()

# --- HEADER ---
st.markdown("# 📸 VALMAX Shots Analytics")
from utils import show_last_updated
show_last_updated("Shots Analytics")
st.markdown("Аналітика по шотам на Dribbble")

# --- PROFILE STATS ---
st.divider()
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("📊 Усього шотів", len(df))
p2.metric("👥 Підписники", profile.get('Подписчики', '?'))
p3.metric("👁️ Усього переглядів", f"{df['Просмотры'].sum():,}")
p4.metric("❤️ Усього лайків", f"{df['Лайки'].sum():,}")
p5.metric("💾 Усього збережень", f"{df['Сохранения'].sum():,}")

# --- ⭐ POPULAR TRACKER ---
st.divider()
st.markdown("### ⭐ Popular Tracker")
st.caption("Чи потрапляють шоти VALMAX у Dribbble Popular? Перевірка 15 категорій × top 96 шотів. Timeframes: All Time / Week / Month")

@st.cache_data(ttl=60)
def load_popular():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds2 = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc2 = gspread.authorize(creds2)
        sh2 = gc2.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws_pop = sh2.worksheet("⭐ Popular Tracker")
        return pd.DataFrame(ws_pop.get_all_records())
    except:
        return pd.DataFrame()

pop_df = load_popular()
if not pop_df.empty:
    found_in_popular = pop_df[pop_df['VALMAX Found'] == 'Yes']
    not_found = pop_df[pop_df['VALMAX Found'] == 'No']
    
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("⭐ In Popular", len(found_in_popular), help="Кількість категорій де VALMAX є в Popular")
    p_col2.metric("📊 Categories Checked", len(pop_df))
    if len(found_in_popular) > 0:
        best_pos = found_in_popular['Position'].min()
        p_col3.metric("🏆 Best Position", f"#{best_pos}")
        unique_shots = found_in_popular['Shot Name'].nunique()
        p_col4.metric("📸 Unique Shots", unique_shots)
    
    if len(found_in_popular) > 0:
        st.markdown("**🔥 VALMAX в Popular:**")
        st.dataframe(
            found_in_popular[['Category', 'Position', 'Shot Name', 'Total Shots', 'Check Date']],
            column_config={
                "Category": st.column_config.TextColumn("📂 Category", width="large"),
                "Position": st.column_config.NumberColumn("📍 Position", help="Позиція шота в Popular видачі"),
                "Shot Name": st.column_config.TextColumn("📸 Shot", width="large"),
                "Total Shots": st.column_config.NumberColumn("📊 Total", help="Скільки шотів на сторінці Popular"),
                "Check Date": st.column_config.TextColumn("🕐 Checked"),
            },
            use_container_width=True, hide_index=True
        )
        
        st.markdown("""
        **🚀 Як раскачати шот, який потрапив в Popular:**
        - 📣 **Негайно поширити** — Instagram Stories, Telegram, Twitter, LinkedIn
        - 💬 **Відповідайте на коментарі** — engagement підвищує позицію в Popular
        - 🔄 **Попросіть команду поставити likes + saves** — перші 12-24 год критичні
        - 🏷️ **Перевірте теги** — впевніться що шот в правильних категоріях Popular
        - 👥 **Follow активних дизайнерів** — вони побачать ваш шот і можуть залайкати
        - 📌 **Pin shot** на профілі VALMAX — нові відвідувачі побачать його першим
        """)
    
    if len(not_found) > 0:
        with st.expander(f"❌ Not found in {len(not_found)} categories"):
            st.dataframe(not_found[['Category', 'Total Shots', 'Check Date']], 
                        use_container_width=True, hide_index=True)
    
    with st.expander("💡 Як потрапити в Popular"):
        st.markdown("""
        - 🔥 **Engagement в перші 24-72 години** — likes, saves, comments визначають потрапляння
        - 📸 **Preview image** — перший кадр має бути WOW (люди скролять швидко)
        - 🏷️ **Правильні теги** — Popular фільтрується по категоріях (Web Design, Product Design, Mobile, Branding)
        - ⏰ **Час публікації** — пікові години: вт-чт, 10:00-14:00 UTC
        - 👥 **Follow-база** — ваші 4K followers бачать шот першими і створюють початковий engagement
        - 💬 **Community** — коментуйте чужі шоти, це збільшує видимість вашого профілю
        - 📊 **Benchmark: #38 = найкраща поточна позиція** — потрібно більше engagement для top 20
        """)
else:
    st.info("No Popular data yet. Run the Popular checker first.")

# filtered = all data sorted by date
filtered = df.copy()
if 'Date' in filtered.columns:
    filtered = filtered.sort_values('Date', ascending=False)

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
            # Build week label mapping
            wk_labels = df.groupby('Year_Week')['Week_Label'].first()
            
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
                    'Week': wk_labels.get(curr_w, curr_w),
                    'vs': wk_labels.get(prev_w, prev_w),
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
    st.markdown("**By views (filtered)**")
    top_views = filtered.nlargest(10, 'Просмотры')[['Название', 'Просмотры', 'Лайки', 'Дата', 'Ссылка Dribbble']].reset_index(drop=True) if 'Ссылка Dribbble' in filtered.columns else df.nlargest(10, 'Просмотры')[['Название', 'Просмотры', 'Лайки', 'Дата']].reset_index(drop=True)
    top_views.index = top_views.index + 1
    if 'Ссылка Dribbble' in top_views.columns:
        top_views['Название'] = top_views.apply(lambda r: f'<a href="{r["Ссылка Dribbble"]}" target="_blank">{r["Название"]}</a>', axis=1)
        top_views = top_views.drop(columns=['Ссылка Dribbble'])
        st.markdown(top_views.to_html(escape=False, index=True), unsafe_allow_html=True)
    else:
        st.dataframe(top_views, use_container_width=True)

with top_col2:
    st.markdown("**By likes (filtered)**")
    top_likes = filtered.nlargest(10, 'Лайки')[['Название', 'Лайки', 'Просмотры', 'Дата', 'Ссылка Dribbble']].reset_index(drop=True) if 'Ссылка Dribbble' in filtered.columns else df.nlargest(10, 'Лайки')[['Название', 'Лайки', 'Просмотры', 'Дата']].reset_index(drop=True)
    top_likes.index = top_likes.index + 1
    if 'Ссылка Dribbble' in top_likes.columns:
        top_likes['Название'] = top_likes.apply(lambda r: f'<a href="{r["Ссылка Dribbble"]}" target="_blank">{r["Название"]}</a>', axis=1)
        top_likes = top_likes.drop(columns=['Ссылка Dribbble'])
        st.markdown(top_likes.to_html(escape=False, index=True), unsafe_allow_html=True)
    else:
        st.dataframe(top_likes, use_container_width=True)

# --- ENGAGEMENT ANALYSIS ---
st.divider()
st.markdown("### 🎯 Engagement аналіз")

eng_col1, eng_col2 = st.columns(2)

with eng_col1:
    st.markdown("**Engagement Rate by month**")
    if 'Date' in df.columns:
        eng_col_name = 'Engagement%' if 'Engagement%' in df.columns else 'Engagement'
        view_col_name = 'Просмотры' if 'Просмотры' in df.columns else 'Views'
        if eng_col_name in df.columns and view_col_name in df.columns:
            df[eng_col_name] = pd.to_numeric(df[eng_col_name].astype(str).str.replace('%', ''), errors='coerce')
            df[view_col_name] = pd.to_numeric(df[view_col_name].astype(str).str.replace(',', ''), errors='coerce')
        monthly_eng = df.groupby('Месяц').agg({
            eng_col_name: 'mean',
            view_col_name: 'sum'
        }).reset_index()
        monthly_eng = monthly_eng.rename(columns={eng_col_name: 'Engagement', view_col_name: 'Просмотры'})
        def month_sort(m):
            mo_ru = {'Январь':1,'Февраль':2,'Март':3,'Апрель':4,'Май':5,'Июнь':6,
                  'Июль':7,'Август':8,'Сентябрь':9,'Октябрь':10,'Ноябрь':11,'Декабрь':12}
            mo_en = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
                  'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
            mo = {**mo_ru, **mo_en}
            p = m.split()
            return int(p[1])*100+mo.get(p[0],0) if len(p)==2 and p[0] in mo else 0
        
        monthly_eng['sort'] = monthly_eng['Месяц'].apply(month_sort)
        monthly_eng = monthly_eng.sort_values('sort').tail(12)
        monthly_eng['Month'] = monthly_eng['Месяц']
        
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
st.markdown("### 🏷️ Top tags")

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
        {'Tag': tag, 'Shots': d['count'], 
         'Total Views': d['total_views'],
         'Avg Views/Shot': round(d['total_views'] / d['count']) if d['count'] > 0 else 0,
         'Total Likes': d['total_likes'],
         'Avg Likes/Shot': round(d['total_likes'] / d['count']) if d['count'] > 0 else 0}
        for tag, d in tag_stats.items()
    ])
    
    tag_col1, tag_col2 = st.columns(2)
    
    with tag_col1:
        st.markdown("**Найуживаніші теги**")
        top_used = tags_df.nlargest(15, 'Shots')
        fig = px.bar(top_used, x='Shots', y='Tag', orientation='h', template="plotly_white",
                     color_discrete_sequence=['#667eea'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    
    with tag_col2:
        st.markdown("**Теги з найкращим Avg Views/Shot** (мін. 3 шоти)")
        best_tags = tags_df[tags_df['Shots'] >= 3].nlargest(15, 'Avg Views/Shot')
        fig = px.bar(best_tags, x='Avg Views/Shot', y='Tag', orientation='h', template="plotly_white",
                     color_discrete_sequence=['#43e97b'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    
    # Tag filter + search within this section
    tag_f1, tag_f2 = st.columns(2)
    with tag_f1:
        tag_search = st.text_input("🔍 Search tag", "", key="tag_search")
    with tag_f2:
        min_shots_tag = st.number_input("Min shots", min_value=1, value=1, step=1, key="min_shots_tag")
    
    tags_display = tags_df.copy()
    if tag_search:
        tags_display = tags_display[tags_display['Tag'].str.contains(tag_search, case=False, na=False)]
    tags_display = tags_display[tags_display['Shots'] >= min_shots_tag]
    
    st.markdown(f"**All tags** ({len(tags_display)})")
    tags_display = tags_display.sort_values('Shots', ascending=False).reset_index(drop=True)
    tags_display.index = tags_display.index + 1
    st.dataframe(tags_display, use_container_width=True, height=400)
    
    # Shots by tag
    st.markdown("**🔎 Shots by tag**")
    all_tag_names = sorted(tags_df['Tag'].tolist(), key=lambda t: tags_df[tags_df['Tag']==t]['Shots'].values[0], reverse=True)
    selected_tag = st.selectbox("Select tag", all_tag_names, key="shots_by_tag")
    
    if selected_tag:
        tag_shots = df[df['Теги'].str.contains(selected_tag, case=False, na=False)].copy()
        tag_shots = tag_shots.sort_values('Просмотры', ascending=False).reset_index(drop=True)
        tag_shots.index = tag_shots.index + 1
        
        st.caption(f"{len(tag_shots)} shots with tag **{selected_tag}**")
        
        # Build HTML table with clickable names
        show_all = st.checkbox(f"View all {len(tag_shots)} shots", key="tag_view_all") if len(tag_shots) > 20 else True
        display_shots = tag_shots if show_all else tag_shots.head(20)
        
        rows_html = ""
        for i, row in display_shots.iterrows():
            link = row.get('Ссылка Dribbble', '')
            name = row.get('Название', '')
            name_cell = f'<a href="{link}" target="_blank">{name}</a>' if link else name
            rows_html += f"<tr><td>{i}</td><td>{name_cell}</td><td>{row.get('Просмотры', 0):,}</td><td>{row.get('Лайки', 0):,}</td><td>{row.get('Сохранения', 0):,}</td><td>{row.get('Дата', '')}</td></tr>"
        
        html = f"""<table style="width:100%; border-collapse:collapse; font-size:14px;">
        <thead><tr style="border-bottom:2px solid #e8ecf1; text-align:left;">
            <th style="padding:8px">#</th><th style="padding:8px">Name</th><th style="padding:8px">Views</th>
            <th style="padding:8px">Likes</th><th style="padding:8px">Saves</th><th style="padding:8px">Date</th>
        </tr></thead><tbody>{rows_html}</tbody></table>"""
        st.markdown(html, unsafe_allow_html=True)
        if not show_all and len(tag_shots) > 20:
            st.info(f"⬆️ Showing top 20 of {len(tag_shots)} shots — check **View all** above to see the full list")

# --- PROJECT TYPES ---
st.divider()
st.markdown("### 🎨 Project types")

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
        type_counts.columns = ['Type', 'Count']
        fig = px.pie(type_counts, names='Type', values='Count', template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with type_col2:
        agg_cols = {c: 'mean' for c in ['Просмотры', 'Лайки', 'Engagement'] if c in df.columns}
        type_perf = df.groupby('Тип проекта').agg(agg_cols).round(0).reset_index()
        type_perf.columns = ['Type'] + [f'Avg {c}' for c in agg_cols.keys()]
        if 'Avg Engagement' not in type_perf.columns:
            type_perf['Avg Engagement'] = 0
        fig = px.bar(type_perf, x='Type', y=type_perf.columns[1] if len(type_perf.columns) > 1 else 'Type', template="plotly_white",
                     color='Avg Engagement', color_continuous_scale=['#f5576c', '#00d4aa'])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig, use_container_width=True)

# --- SEO VISIBILITY ---
st.divider()
st.markdown("### 🔍 SEO Visibility (Google via Brave Search)")
st.caption("Які шоти VALMAX видно в Google при пошуку дизайн-запитів. Оновлюється щотижня.")

seo_col1, seo_col2 = st.columns(2)

with seo_col1:
    st.markdown("**✅ VALMAX шоти індексовані в Google (9 шотів):**")
    indexed_shots = [
        "AVISION - Design Platform for Creative Professionals",
        "Sales Analytics Landing Page",
        "Gaming Tournament Platform",
        "Prime Planners - UX/UI design",
        "Struktura — Website for Frame House Builders",
        "Renovating services | UX/UI design",
        "AI Tutor - web design of a learning platform",
        "Intuitive UX/UI Design for a Health Monitoring App",
        "AVISION - a design platform (v2)",
    ]
    for shot in indexed_shots:
        st.markdown(f"- 🟢 {shot}")
    
    st.metric("📊 Indexed Shots", f"9 / 210", delta="4.3%")

with seo_col2:
    st.markdown("**❌ Комерційні запити — VALMAX НЕ в Google Top 10:**")
    seo_queries = {
        "dashboard ui design": ["Outcrowd", "Halo Lab", "Phenomenon"],
        "saas dashboard design": [],
        "fintech dashboard ui": ["Nixtio", "QClay"],
        "healthcare app design": ["Phenomenon", "QClay"],
        "landing page design": [],
        "mobile app ui design": [],
        "crm dashboard design": [],
        "crypto dashboard ui": [],
        "analytics dashboard design": [],
        "b2b saas design": [],
    }
    
    seo_rows = []
    for query, competitors in seo_queries.items():
        comp_str = ", ".join(competitors) if competitors else "—"
        seo_rows.append({"Query": query, "VALMAX": "❌", "Competitors in Top 10": comp_str})
    
    seo_df = pd.DataFrame(seo_rows)
    st.dataframe(seo_df, use_container_width=True, hide_index=True, height=380)

st.caption("💡 **Інсайт:** VALMAX індексується по бренду, але НЕ з'являється по комерційних запитах. Конкуренти (Outcrowd, QClay, Nixtio, Phenomenon) видні по ключових нішах. Це зона росту — потрібно оптимізувати назви шотів та теги під пошукові запити.")

# --- ALL SHOTS TABLE ---
st.divider()
st.markdown("### 📋 All shots")
display_cols = ['Месяц', 'Дата', 'Название', 'Просмотры', 'Лайки', 'Сохранения', 'Комментарии', 'Engagement %', 'Кол-во тегов']
available_cols = [c for c in display_cols if c in filtered.columns]
base_cols = ['Месяц', 'Название', 'Просмотры', 'Лайки', 'Сохранения', 'Комментарии', 'Engagement %', 'Кол-во тегов']
if 'Ссылка Dribbble' in filtered.columns:
    base_cols.append('Ссылка Dribbble')
display_df = filtered[[c for c in base_cols if c in filtered.columns]].copy()
# Use actual datetime for sorting instead of text date
display_df.insert(1, 'Date', filtered['Date'])
display_df = display_df.reset_index(drop=True)
display_df.index = display_df.index + 1
if 'Месяц' in display_df.columns:
    display_df['Месяц'] = display_df['Месяц'].apply(_to_en_month)
col_rename = {'Месяц':'Month', 'Название':'Name', 'Просмотры':'Views', 'Лайки':'Likes', 
              'Сохранения':'Saves', 'Комментарии':'Comments', 'Кол-во тегов':'Tags', 'Ссылка Dribbble':'Link'}
display_df = display_df.rename(columns={k:v for k,v in col_rename.items() if k in display_df.columns})
col_config = {}
if 'Link' in display_df.columns:
    col_config['Link'] = st.column_config.LinkColumn("Link", display_text="Open ↗")
st.dataframe(display_df, use_container_width=True, height=500, column_config=col_config)

# --- FOOTER ---
st.divider()
st.caption("📸 VALMAX Dribbble Shots Analytics | Оновлюється щотижня (пн 8:00 CET)")
