import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CSS ---
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
    h1, h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=300)
def load_race_data():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        
        ws = sh.worksheet("🏎️ March 2026 Race")
        rows = ws.get_all_records()
        df_summary = pd.DataFrame(rows)
        
        ws2 = sh.worksheet("🏎️ Race Detail")
        detail_rows = ws2.get_all_records()
        df_detail = pd.DataFrame(detail_rows)
        
        return df_summary, df_detail
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame(), pd.DataFrame()

df, df_detail = load_race_data()

# --- HEADER ---
st.markdown("# 🏎️ Monthly Race")
from utils import show_last_updated
show_last_updated("Competitors")

if df.empty:
    st.warning("No race data found")
    st.stop()

month = "March 2026"
st.markdown(f"### 📅 {month}")

st.divider()

# --- VALMAX POSITION ---
valmax = df[df['Username'] == 'valmax']
valmax_row = valmax.iloc[0] if len(valmax) > 0 else None
df_ranked = df.sort_values('Total Views', ascending=False).reset_index(drop=True)
valmax_rank = df_ranked[df_ranked['Username'] == 'valmax'].index[0] + 1 if valmax_row is not None else '?'
leader = df_ranked.iloc[0]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🏁 VALMAX Position", f"#{valmax_rank} of {len(df)}")
col2.metric("👁️ Our Views", f"{valmax_row['Total Views']:,}" if valmax_row is not None else "?")
col3.metric("📸 Our Shots", valmax_row['Shots'] if valmax_row is not None else "?")
if valmax_row is not None:
    gap = leader['Total Views'] - valmax_row['Total Views']
    col4.metric("📉 Gap to Leader", f"-{gap:,}", help=f"Leader: {leader['Profile']}")
    col5.metric("🏆 Leader", leader['Profile'], f"{leader['Total Views']:,} views")

# --- KEY INSIGHT ---
if valmax_row is not None:
    st.divider()
    st.markdown("### 💡 Ключовий інсайт")
    
    # Avg views comparison
    valmax_avg = valmax_row['Avg Views/Shot']
    leader_avg = leader['Avg Views/Shot']
    leader_shots = leader['Shots']
    valmax_shots = valmax_row['Shots']
    
    ins_col1, ins_col2, ins_col3, ins_col4 = st.columns(4)
    ins_col1.metric("📸 Наших шотів", valmax_shots)
    ins_col2.metric("📸 Шотів лідера", leader_shots, help=leader['Profile'])
    ins_col3.metric("⚡ Наш Avg Views/Shot", f"{valmax_avg:,}")
    ins_col4.metric("⚡ Лідер Avg Views/Shot", f"{leader_avg:,}", help=leader['Profile'])
    
    if valmax_avg > leader_avg:
        diff_pct = int((valmax_avg / leader_avg - 1) * 100)
        st.success(f"🔥 **Якість VALMAX вища на {diff_pct}%!** Наш avg views/shot ({valmax_avg:,}) > лідер ({leader_avg:,}). Проблема не в якості, а в кількості шотів ({valmax_shots} vs {leader_shots}).")
    else:
        st.warning(f"⚠️ Лідер ({leader['Profile']}) має вищий avg views/shot ({leader_avg:,} vs наші {valmax_avg:,}). Потрібно підвищити якість контенту.")

st.divider()

# --- RACE CHART (cumulative views by date) ---
st.markdown("### 🏎️ The Race — Cumulative Views")
st.caption("Кумулятивні перегляди за місяць. Кожна лінія — конкурент. Хто набирає перегляди швидше?")

if len(df_detail) > 0 and 'Date' in df_detail.columns:
    df_detail['Date'] = pd.to_datetime(df_detail['Date'])
    df_detail = df_detail.sort_values('Date')
    
    # Build cumulative views per profile per day
    profiles = df_detail['Profile'].unique()
    
    # Get daily cumulative
    race_rows = []
    for profile in profiles:
        p_data = df_detail[df_detail['Profile'] == profile].sort_values('Date')
        cumulative = 0
        for _, row in p_data.iterrows():
            cumulative += row['Views']
            race_rows.append({
                'Profile': profile,
                'Date': row['Date'],
                'Cumulative Views': cumulative
            })
    
    race_df = pd.DataFrame(race_rows)
    
    # Color VALMAX differently
    color_map = {p: '#b0b0b0' for p in profiles}
    if 'VALMAX' in color_map:
        color_map['VALMAX'] = '#43e97b'
    # Top 3 get distinct colors
    top3 = df_ranked.head(3)['Profile'].tolist()
    race_colors = ['#f5576c', '#ffa726', '#667eea']
    for i, p in enumerate(top3):
        if p != 'VALMAX':
            color_map[p] = race_colors[i] if i < len(race_colors) else '#667eea'
    
    fig = px.line(race_df, x='Date', y='Cumulative Views', color='Profile',
                  color_discrete_map=color_map, template="plotly_white")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#636e72"), height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # Make VALMAX line thicker
    for trace in fig.data:
        if trace.name == 'VALMAX':
            trace.line.width = 4
        else:
            trace.line.width = 2
    
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- TOTAL VIEWS RANKING ---
st.markdown("### 🏆 Total Views Ranking")

df_bar = df.sort_values('Total Views', ascending=True)
colors = ['#43e97b' if u == 'valmax' else '#667eea' for u in df_bar['Username']]

fig = go.Figure(go.Bar(
    x=df_bar['Total Views'], y=df_bar['Profile'], orientation='h',
    marker_color=colors,
    text=[f"{v:,}" for v in df_bar['Total Views']], textposition='outside'
))
fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                 height=max(400, len(df)*30), xaxis_title="Total Views (March)",
                 margin=dict(r=100))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- EFFICIENCY: AVG VIEWS PER SHOT ---
st.markdown("### ⚡ Efficiency: Avg Views per Shot")
st.caption("Хто отримує більше переглядів за менший об'єм шотів?")

df_eff = df[df['Avg Views/Shot'] > 0].sort_values('Avg Views/Shot', ascending=True)
colors_eff = ['#43e97b' if u == 'valmax' else '#ffa726' for u in df_eff['Username']]

fig = go.Figure(go.Bar(
    x=df_eff['Avg Views/Shot'], y=df_eff['Profile'], orientation='h',
    marker_color=colors_eff,
    text=[f"{v:,}" for v in df_eff['Avg Views/Shot']], textposition='outside'
))
fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                 height=max(350, len(df_eff)*30), xaxis_title="Avg Views/Shot",
                 margin=dict(r=80))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- BEST SHOTS OF THE MONTH ---
st.markdown("### 🔥 Best Shots of the Month")

best_shots = df[['Profile', 'Best Shot', 'Best Shot Views', 'Shots']].sort_values('Best Shot Views', ascending=False)
st.dataframe(
    best_shots,
    column_config={
        "Profile": st.column_config.TextColumn("Profile", width="medium"),
        "Best Shot": st.column_config.TextColumn("🏆 Best Shot", width="large"),
        "Best Shot Views": st.column_config.NumberColumn("👁️ Views", format="%d"),
        "Shots": st.column_config.NumberColumn("📸 Total Shots", format="%d"),
    },
    use_container_width=True, hide_index=True
)

st.divider()

# --- VALMAX GAP ANALYSIS ---
st.markdown("### 📉 VALMAX Gap Analysis")
st.caption("Різниця між VALMAX та кожним конкурентом по ключових метриках")

if valmax_row is not None:
    gap_data = []
    for _, row in df_ranked.iterrows():
        if row['Username'] == 'valmax':
            continue
        gap_data.append({
            'Profile': row['Profile'],
            'Views Gap': row['Total Views'] - valmax_row['Total Views'],
            'Likes Gap': row['Total Likes'] - valmax_row['Total Likes'],
            'Shots Gap': row['Shots'] - valmax_row['Shots'],
            'Avg Views Gap': row['Avg Views/Shot'] - valmax_row['Avg Views/Shot'],
        })
    
    gap_df = pd.DataFrame(gap_data)
    
    # Color: red if we're behind, green if ahead
    def color_gap(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return 'color: #f5576c'  # behind
            elif val < 0:
                return 'color: #43e97b'  # ahead
        return ''
    
    styled = gap_df.style.map(color_gap, subset=['Views Gap', 'Likes Gap', 'Shots Gap', 'Avg Views Gap'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    st.caption("""
    **Як читати таблицю:**
    - **Views Gap** — різниця в загальних переглядах за місяць (+ = конкурент попереду, - = ми попереду)
    - **Likes Gap** — різниця в лайках за місяць
    - **Shots Gap** — різниця в кількості опублікованих шотів (+ = конкурент постить більше)
    - **Avg Views Gap** — різниця в середніх переглядах на 1 шот (- = наші шоти якісніші)
    - 🔴 Червоний = конкурент попереду VALMAX · 🟢 Зелений = VALMAX попереду
    """)

st.divider()

# --- POPULAR LEADERBOARD ---
st.markdown("### ⭐ Popular Leaderboard")
st.caption("Конкуренти в Dribbble Popular по категоріях. Хто нас обходить? Оновлюється щоденно.")

@st.cache_data(ttl=300)
def load_popular_competitors():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_pc = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc_pc = gspread.authorize(creds_pc)
        sh_pc = gc_pc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws_pc = sh_pc.worksheet("⭐ Popular Competitors")
        return pd.DataFrame(ws_pc.get_all_records())
    except:
        return pd.DataFrame()

pop_comp = load_popular_competitors()
if not pop_comp.empty:
    # Timeframe filter
    timeframes = ["All (all timeframes)"] + sorted(pop_comp['Category'].unique().tolist())
    selected_tf = st.selectbox("📅 Timeframe", timeframes)
    
    if selected_tf != "All (all timeframes)":
        pop_comp = pop_comp[pop_comp['Category'] == selected_tf]

if not pop_comp.empty:
    # Summary: who appears most across categories
    summary = pop_comp.groupby('Profile').agg(
        total_appearances=('Appearances', 'sum'),
        best_position=('Best Position', 'min'),
        categories=('Category', 'nunique')
    ).sort_values('total_appearances', ascending=False).reset_index()
    
    # KPIs
    pc1, pc2, pc3 = st.columns(3)
    valmax_pop = summary[summary['Profile'] == 'VALMAX']
    if len(valmax_pop) > 0:
        pc1.metric("📍 VALMAX Best Popular Pos", f"#{valmax_pop.iloc[0]['best_position']}")
        pc2.metric("📊 VALMAX Appearances", valmax_pop.iloc[0]['total_appearances'])
    else:
        pc1.metric("📍 VALMAX in Popular", "❌ Not found")
        pc2.metric("📊 Appearances", 0)
    pc3.metric("🏆 Most Active", f"{summary.iloc[0]['Profile']} ({summary.iloc[0]['total_appearances']}x)")
    
    # Summary table
    def highlight_valmax_pop(row):
        if row.get('Profile') == 'VALMAX':
            return ['background-color: #43e97b22'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        summary.style.apply(highlight_valmax_pop, axis=1),
        column_config={
            "Profile": st.column_config.TextColumn("👤 Profile"),
            "total_appearances": st.column_config.NumberColumn("📊 Appearances", help="Скільки разів з'являється в Popular (всі категорії)"),
            "best_position": st.column_config.NumberColumn("🏆 Best Pos", help="Найкраща позиція в Popular серед всіх категорій"),
            "categories": st.column_config.NumberColumn("📂 Categories", help="В скількох категоріях з'являється"),
        },
        use_container_width=True, hide_index=True
    )
    
    # Detail by category
    with st.expander("📋 Деталі по категоріях"):
        for cat in pop_comp['Category'].unique():
            cat_data = pop_comp[pop_comp['Category'] == cat].sort_values('Best Position')
            st.markdown(f"**{cat}:**")
            for _, row in cat_data.iterrows():
                emoji = "🟢" if row['Profile'] == 'VALMAX' else "⚪"
                st.markdown(f"  {emoji} {row['Profile']} — {row['Positions']} ({row['Appearances']}x)")
    
    st.caption("Дані: Dribbble Popular по 7 timeframes (Today, Week, Month × 5 категорій). Оновлюється щоденно о 12:00 CET (пн-пт)")

st.divider()

# --- RECOMMENDATIONS ---
st.markdown("### 💡 Recommendations")

if valmax_row is not None:
    # Calculate needed pace
    days_left = 31 - 8  # March 8 = day 8
    current_pace = valmax_row['Total Views'] / 8  # views per day so far
    leader_pace = leader['Total Views'] / 8
    
    projected_valmax = int(valmax_row['Total Views'] + current_pace * days_left)
    projected_leader = int(leader['Total Views'] + leader_pace * days_left)
    needed_daily = int((leader['Total Views'] - valmax_row['Total Views'] + leader_pace * days_left) / days_left)
    
    rec_col1, rec_col2, rec_col3 = st.columns(3)
    rec_col1.metric("📈 Projected VALMAX (end of month)", f"{projected_valmax:,}", help="At current pace")
    rec_col2.metric("🏁 Projected Leader", f"{projected_leader:,}", help=f"{leader['Profile']} at current pace")
    rec_col3.metric("🎯 Daily Views Needed to Win", f"{needed_daily:,}", help="Views per day to catch the leader")
    
    st.markdown(f"""
    **Аналіз:**
    - VALMAX поточний темп: **{int(current_pace):,} views/day** ({valmax_row['Shots']} shots за 8 днів)
    - Лідер ({leader['Profile']}): **{int(leader_pace):,} views/day** ({leader['Shots']} shots)
    - Щоб наздогнати лідера до кінця місяця: **{needed_daily:,} views/day**
    
    **Рекомендації:**
    1. 📸 Збільшити кількість шотів: зараз {valmax_row['Shots']} за 8 днів → потрібно **2-3 шоти/тиждень**
    2. 🏷️ Використовувати перспективні теги з Tag Positions (Score 60+)
    3. 🔥 Фокус на якість: наш avg views/shot ({valmax_row['Avg Views/Shot']:,}) — конкурентний
    4. ⏰ Публікувати в пікові години (вт-чт, 10:00-14:00 UTC)
    """)

# --- FOOTER ---
st.divider()
st.caption("🏎️ Monthly Race | Data updates daily via cron | Compare month-over-month performance")
