import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
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
    h1 { color: #2d3436 !important; font-weight: 800 !important; }
    h2, h3 { color: #2d3436 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=300)
def load_tag_data():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws = sh.worksheet("🏷️ Tag Positions")
        rows = ws.get_all_records()
        if rows:
            return pd.DataFrame(rows), "live"
    except:
        pass
    
    # Fallback: load from JSON
    try:
        with open('/Users/openzlo/.openclaw/workspace/memory/dribbble-tag-positions.json') as f:
            data = json.load(f)
        rows = []
        for r in data:
            for p in r.get('positions', []):
                rows.append({
                    'Tag': r['tag'],
                    'Position': p['position'],
                    'Total on Page': r.get('total_on_page', 25),
                    'Shot Name': p.get('name', ''),
                    'Views': p.get('views', 0),
                    'Shot URL': f"https://dribbble.com{p['url']}" if p.get('url', '').startswith('/') else p.get('url', ''),
                    'Tag URL': r.get('tag_url', ''),
                    'Checked': r.get('checked_at', '')[:10]
                })
        return pd.DataFrame(rows), "json"
    except:
        return pd.DataFrame(), "empty"

df, source = load_tag_data()

# --- HEADER ---
st.markdown("# 🏷️ Tag Position Tracker")
if source == "json":
    st.caption("📂 Data from local scan results (top 25 per tag)")
elif source == "live":
    st.caption("Live data from Google Sheets")
else:
    st.caption("No data available yet")
    st.stop()

if df.empty:
    st.warning("No tag position data found")
    st.stop()

st.divider()

# --- KPIs ---
total_tags_with_positions = df['Tag'].nunique()
total_positions = len(df)
unique_shots = df['Shot Name'].nunique()
num_first = len(df[df['Position'] == 1])
num_top3 = len(df[df['Position'] <= 3])
num_top5 = len(df[df['Position'] <= 5])
num_top10 = len(df[df['Position'] <= 10])

num_top20 = len(df[df['Position'] <= 20])
num_top30 = len(df[df['Position'] <= 30])
num_top40 = len(df[df['Position'] <= 40])
num_top50 = len(df[df['Position'] <= 50])
num_top100 = len(df[df['Position'] <= 100])
num_over100 = len(df[df['Position'] > 100])

row1 = st.columns(6)
row1[0].metric("🏷️ Total Unique Tags", 1272)
row1[1].metric("✅ Tags with VALMAX", total_tags_with_positions)
row1[2].metric("📍 Total Positions", total_positions)
row1[3].metric("🥇 #1", num_first)
row1[4].metric("🥉 Top 5", num_top5)
row1[5].metric("🔟 Top 10", num_top10)

row2 = st.columns(6)
row2[0].metric("🏅 Top 20", num_top20)
row2[1].metric("📊 Top 30", num_top30)
row2[2].metric("📈 Top 40", num_top40)
row2[3].metric("🎯 Top 50", num_top50)
row2[4].metric("💯 Top 100", num_top100)
row2[5].metric("📭 100+", num_over100)

st.caption("""
**🏷️ Total Unique Tags** — усі унікальні теги на 210 шотах VALMAX  ·  
**✅ Tags with VALMAX** — теги, де хоча б один шот VALMAX з'являється у видачі (top 25 просканований, deep scan top 100 в процесі)  ·  
**📍 Total Positions** — загальна кількість знайдених позицій шот×тег (один шот може бути в кількох тегах)
""")

# --- FILTERS ---
st.divider()
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    position_range = st.slider("Position range", 1, int(df['Position'].max()), (1, 25))

with col_f2:
    shots_list = sorted(df['Shot Name'].unique())
    selected_shot = st.selectbox("Filter by shot", ["All"] + shots_list)

with col_f3:
    search_tag = st.text_input("Search tag", "")

# Apply filters
filtered = df[(df['Position'] >= position_range[0]) & (df['Position'] <= position_range[1])]
if selected_shot != "All":
    filtered = filtered[filtered['Shot Name'] == selected_shot]
if search_tag:
    filtered = filtered[filtered['Tag'].str.contains(search_tag, case=False, na=False)]

# --- POSITION DISTRIBUTION ---
st.divider()
st.markdown("### 📊 Position Distribution")

col_d1, col_d2 = st.columns(2)

with col_d1:
    bins = [0, 1, 3, 5, 10, 15, 25, 100]
    labels = ['#1', '#2-3', '#4-5', '#6-10', '#11-15', '#16-25']
    if df['Position'].max() > 25:
        labels.append('#26-100')
    else:
        bins = bins[:-1]
    
    dist = pd.cut(df['Position'], bins=bins[:len(labels)+1], labels=labels[:len(bins)-1])
    dist_counts = dist.value_counts().reindex(labels[:len(bins)-1]).fillna(0)
    
    colors = ['#43e97b', '#38f9d7', '#667eea', '#764ba2', '#f093fb', '#c471ed', '#bdc3c7']
    fig = go.Figure(go.Bar(
        x=dist_counts.index, y=dist_counts.values,
        marker_color=colors[:len(dist_counts)],
        text=[int(v) for v in dist_counts.values],
        textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=350, xaxis_title="Position Range", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

with col_d2:
    # Top shots by number of tags they appear in
    shot_counts = df.groupby('Shot Name').agg(
        tags=('Tag', 'count'),
        avg_pos=('Position', 'mean'),
        best_pos=('Position', 'min'),
    ).reset_index().sort_values('tags', ascending=False).head(10)
    shot_counts['avg_pos'] = shot_counts['avg_pos'].round(1)
    shot_counts['label'] = shot_counts['Shot Name'].str[:35]
    shot_counts = shot_counts.sort_values('tags', ascending=True)
    
    fig = go.Figure(go.Bar(
        x=shot_counts['tags'], y=shot_counts['label'], orientation='h',
        marker_color='#667eea',
        text=[f"{t} tags (avg #{a})" for t, a in zip(shot_counts['tags'], shot_counts['avg_pos'])],
        textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=350, xaxis_title="Number of tags", title="Top Shots by Tag Appearances",
                     margin=dict(r=120))
    st.plotly_chart(fig, use_container_width=True)

st.caption("""
**📊 Position Distribution** — скільки позицій VALMAX тримає в кожному діапазоні (#1, #2-3, #4-5 тощо)  ·  
**🎯 Top Shots by Tag Appearances** — які шоти з'являються в найбільшій кількості тегів. Більше тегів = ширше охоплення в пошуку Dribbble. `avg #N` — середня позиція цього шота по всіх тегах
""")

# --- TOP #1 POSITIONS ---
st.divider()
st.markdown("### 🥇 All #1 Positions")

first_places = filtered[filtered['Position'] == 1].sort_values('Views', ascending=False)
if len(first_places) > 0:
    display_1st = first_places[['Tag', 'Shot Name', 'Views', 'Total on Page']].copy()
    display_1st['Views'] = display_1st['Views'].apply(lambda v: f"{v:,}")
    
    # Tag as clickable link
    tag_urls = filtered[filtered['Position'] == 1].set_index('Tag')['Tag URL'].to_dict()
    
    st.dataframe(
        display_1st,
        column_config={
            "Tag": st.column_config.TextColumn("Tag", width="medium"),
            "Shot Name": st.column_config.TextColumn("Shot", width="large"),
            "Views": st.column_config.TextColumn("Views", width="small"),
            "Total on Page": st.column_config.NumberColumn("Competitors", help="Скільки всього шотів у видачі цього тегу (конкуренція)", width="small"),
        },
        use_container_width=True, hide_index=True
    )
else:
    st.info("No #1 positions in current filter")

st.caption("**Competitors** — кількість шотів у видачі тегу. Макс. 25 = ліміт першої сторінки Dribbble (deep scan до 100 в процесі). 2 = низька конкуренція, легше утримувати #1")

# --- BEST SHOTS BY TAG COUNT ---
st.divider()
st.markdown("### 🎯 Best Performing Shots (by tag appearances)")

shot_stats = filtered.groupby('Shot Name').agg(
    tags_count=('Tag', 'count'),
    avg_position=('Position', 'mean'),
    best_position=('Position', 'min'),
    first_places=('Position', lambda x: (x == 1).sum()),
    top5_count=('Position', lambda x: (x <= 5).sum()),
    top10_count=('Position', lambda x: ((x > 5) & (x <= 10)).sum()),
    outside10=('Position', lambda x: (x > 10).sum()),
    views=('Views', 'first')
).reset_index().sort_values('tags_count', ascending=False)

shot_stats['avg_position'] = shot_stats['avg_position'].round(1)

st.dataframe(
    shot_stats.head(20),
    column_config={
        "Shot Name": st.column_config.TextColumn("Shot", width="large"),
        "tags_count": st.column_config.NumberColumn("Tags Found", help="В скількох тегах шот знайдений у видачі", width="small"),
        "avg_position": st.column_config.NumberColumn("Avg Pos", help="Середня позиція по всіх тегах", width="small"),
        "best_position": st.column_config.NumberColumn("Best", help="Найкраща позиція (1 = перше місце)", width="small"),
        "first_places": st.column_config.NumberColumn("#1", help="В скількох тегах на 1 місці", width="small"),
        "top5_count": st.column_config.NumberColumn("Top 5", help="В скількох тегах в топ-5", width="small"),
        "top10_count": st.column_config.NumberColumn("Top 6-10", help="В скількох тегах на позиціях 6-10", width="small"),
        "outside10": st.column_config.NumberColumn("11+", help="В скількох тегах за межами топ-10", width="small"),
        "views": st.column_config.NumberColumn("Views", format="%d", width="small"),
    },
    use_container_width=True, hide_index=True
)

st.caption("**Tags Found** — в скількох тегах шот знайдений · **Avg Position** — середня позиція · **Best** — найкраща · **#1 Count** — скільки разів на 1 місці · **Top 5** — скільки разів в топ-5")

# --- SCATTER: VIEWS vs POSITION ---
st.divider()
st.markdown("### 📈 Views vs Tag Position")

scatter_data = filtered.copy()
scatter_data['Shot Short'] = scatter_data['Shot Name'].str[:30]

fig = px.scatter(scatter_data, x='Position', y='Views', 
                 color='Shot Short', hover_data=['Tag', 'Shot Name'],
                 template="plotly_white",
                 color_discrete_sequence=px.colors.qualitative.Set2)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                 font=dict(color="#636e72"), height=450,
                 xaxis_title="Position in Tag", yaxis_title="Shot Views",
                 showlegend=False)
fig.update_xaxes(autorange="reversed")
st.plotly_chart(fig, use_container_width=True)

st.caption("Кожна точка = один шот в одному тегу. Чим лівіше (ближче до #1) і вище (більше views) — тим краще. Якщо шот з високими views далеко від #1, є потенціал для покращення позиції")

# --- TAG CATEGORIES ---
st.divider()
st.markdown("### 🗂️ Tag Categories")

# Auto-categorize tags
categories = {
    'UI/UX': ['ui', 'ux', 'uxui', 'user interface', 'user experience', 'interface', 'interaction'],
    'Web Design': ['web design', 'website', 'landing', 'homepage', 'web', 'responsive'],
    'Dashboard': ['dashboard', 'analytics', 'admin', 'panel', 'saas', 'crm'],
    'Mobile': ['mobile', 'app', 'ios', 'android', 'mobile app'],
    'Branding': ['brand', 'logo', 'identity', 'branding', 'logotype'],
    'E-commerce': ['ecommerce', 'e-commerce', 'shop', 'store', 'shopify'],
    'Healthcare': ['health', 'medical', 'fitness', 'wellness', 'dental'],
    'Fintech': ['fintech', 'crypto', 'finance', 'banking', 'investment'],
    'Animation': ['animation', 'motion', 'scroll', 'interaction design'],
    'Real Estate': ['real estate', 'property', 'apartment', 'mortgage', 'housing'],
}

cat_data = []
for cat_name, keywords in categories.items():
    cat_tags = filtered[filtered['Tag'].str.lower().apply(
        lambda t: any(k in t for k in keywords)
    )]
    if len(cat_tags) > 0:
        cat_data.append({
            'Category': cat_name,
            'Tags': cat_tags['Tag'].nunique(),
            'Positions': len(cat_tags),
            'Avg Position': round(cat_tags['Position'].mean(), 1),
            'Best Position': cat_tags['Position'].min(),
            '#1 Count': (cat_tags['Position'] == 1).sum(),
            'Top 5': (cat_tags['Position'] <= 5).sum()
        })

if cat_data:
    cat_df = pd.DataFrame(cat_data).sort_values('Positions', ascending=False)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        fig = px.bar(cat_df, x='Positions', y='Category', orientation='h',
                     color='Avg Position', color_continuous_scale='RdYlGn_r',
                     text='Positions', template="plotly_white")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col_c2:
        st.dataframe(cat_df, use_container_width=True, hide_index=True)

st.caption("Автоматична категоризація тегів. Колір = середня позиція (зелений = краще, червоний = гірше). Показує в яких нішах VALMAX найсильніший")

# --- ALL POSITIONS TABLE ---
st.divider()
st.markdown("### 📋 All Tag Positions")

col_at1, col_at2 = st.columns(2)
with col_at1:
    search_tag_all = st.text_input("🔍 Пошук по тегу", "", key="all_tags_search")
with col_at2:
    pos_filter = st.selectbox("📍 Фільтр по позиції", ["All", "#1", "Top 3", "Top 5", "Top 10", "Top 25", "25+"])

display_all = filtered.copy()
if search_tag_all:
    display_all = display_all[display_all['Tag'].str.contains(search_tag_all, case=False, na=False)]
if pos_filter == "#1":
    display_all = display_all[display_all['Position'] == 1]
elif pos_filter == "Top 3":
    display_all = display_all[display_all['Position'] <= 3]
elif pos_filter == "Top 5":
    display_all = display_all[display_all['Position'] <= 5]
elif pos_filter == "Top 10":
    display_all = display_all[display_all['Position'] <= 10]
elif pos_filter == "Top 25":
    display_all = display_all[display_all['Position'] <= 25]
elif pos_filter == "25+":
    display_all = display_all[display_all['Position'] > 25]

display_all = display_all.sort_values('Position').copy()
display_all['Views'] = display_all['Views'].apply(lambda v: f"{v:,}")

# Medal emojis
def medal(pos):
    if pos == 1: return "🥇"
    elif pos == 2: return "🥈"
    elif pos == 3: return "🥉"
    elif pos <= 5: return "🏅"
    elif pos <= 10: return "🔟"
    return ""

display_all['Medal'] = display_all['Position'].apply(medal)
display_all['Rank'] = display_all.apply(lambda r: f"{r['Medal']} #{r['Position']}", axis=1)

st.dataframe(
    display_all[['Rank', 'Tag', 'Shot Name', 'Views', 'Total on Page']],
    column_config={
        "Rank": st.column_config.TextColumn("Position", width="small"),
        "Tag": st.column_config.TextColumn("Tag", width="medium"),
        "Shot Name": st.column_config.TextColumn("Shot", width="large"),
        "Views": st.column_config.TextColumn("Views", width="small"),
        "Total on Page": st.column_config.NumberColumn("Total", width="small"),
    },
    use_container_width=True, hide_index=True,
    height=600
)

# --- TAG PERSPECTIVENESS SCORE ---
st.divider()
st.markdown("### 🎯 Tag Perspectiveness Score")
st.caption("Формула перспективності тегу для бізнесу VALMAX. Score 0-100: чим вище — тим більше потенціал для росту.")

# Commercial value keywords (high = clients search these)
COMMERCIAL_HIGH = ['dashboard', 'saas', 'fintech', 'healthcare', 'crm', 'analytics', 'ecommerce', 
                   'e-commerce', 'b2b', 'startup', 'platform', 'management', 'admin', 'portal',
                   'banking', 'insurance', 'logistics', 'hr', 'erp', 'marketplace', 'subscription',
                   'payment', 'trading', 'investment', 'real estate', 'mortgage', 'enterprise']
COMMERCIAL_MED = ['web design', 'website', 'landing', 'mobile app', 'app design', 'ui design',
                  'brand', 'branding', 'logo', 'identity', 'corporate', 'business', 'agency',
                  'product design', 'ux', 'interface', 'responsive', 'modern', 'clean']
COMMERCIAL_LOW = ['skiing', 'snowboarding', 'nature', 'sports', 'gaming', 'tournament',
                  'scoreboard', 'fitness', 'food', 'recipe', 'travel', 'music', 'art',
                  'illustration', 'animation', 'motion', 'scroll', '3d']

# VALMAX service relevance
VALMAX_RELEVANT = ['dashboard', 'saas', 'web design', 'website', 'landing', 'ui', 'ux', 'uxui',
                   'b2b', 'crm', 'analytics', 'admin', 'platform', 'fintech', 'healthcare',
                   'ecommerce', 'e-commerce', 'branding', 'brand identity', 'corporate',
                   'startup', 'product design', 'data', 'management', 'enterprise', 'portal',
                   'clean design', 'modern', 'responsive', 'mobile app']

@st.cache_data(ttl=300)
def load_seo_data():
    """Load search volume data from Google Sheet or local JSON."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws = sh.worksheet("🔍 SEO Data")
        rows = ws.get_all_records()
        return {r['Tag']: r for r in rows}
    except:
        pass
    try:
        with open('/Users/openzlo/.openclaw/workspace/memory/tag-search-volumes.json') as f:
            return json.load(f)
    except:
        return {}

seo_data = load_seo_data()

def calc_perspectiveness(tag, position, total_on_page):
    tag_lower = tag.lower()
    tag_seo = seo_data.get(tag, seo_data.get(tag_lower, {}))
    
    # Real volume from DataForSEO
    volume = tag_seo.get('volume', tag_seo.get('Volume/mo', 0)) or 0
    cpc = tag_seo.get('cpc', tag_seo.get('CPC ($)', 0)) or 0
    dribbble_gpos = tag_seo.get('Dribbble Google Pos', 0) or 0
    
    # 1. Position score (25%) — goal is top 12
    if position <= 12:
        pos_score = 0  # Already achieved
    elif position <= 15:
        pos_score = 90  # Almost there
    elif position <= 20:
        pos_score = 70
    elif position <= 25:
        pos_score = 50
    elif position <= 50:
        pos_score = 30
    else:
        pos_score = 10  # Far from goal
    
    # 2. Search volume (25%) — real data from DataForSEO
    if volume >= 10000:
        vol_score = 100
    elif volume >= 5000:
        vol_score = 85
    elif volume >= 1000:
        vol_score = 70
    elif volume >= 500:
        vol_score = 55
    elif volume >= 100:
        vol_score = 35
    elif volume > 0:
        vol_score = 15
    else:
        vol_score = 5  # No data
    
    # 3. Commercial value (20%) — CPC as proxy + keywords
    if cpc >= 15:
        comm_score = 100
    elif cpc >= 8:
        comm_score = 80
    elif cpc >= 3:
        comm_score = 50
    elif cpc > 0:
        comm_score = 25
    elif any(k in tag_lower for k in COMMERCIAL_HIGH):
        comm_score = 80
    elif any(k in tag_lower for k in COMMERCIAL_MED):
        comm_score = 50
    elif any(k in tag_lower for k in COMMERCIAL_LOW):
        comm_score = 10
    else:
        comm_score = 20
    
    # 4. Google visibility (15%) — Dribbble tag page position in Google
    if dribbble_gpos and 1 <= dribbble_gpos <= 3:
        google_score = 100
    elif dribbble_gpos and 4 <= dribbble_gpos <= 5:
        google_score = 80
    elif dribbble_gpos and 6 <= dribbble_gpos <= 10:
        google_score = 50
    elif total_on_page >= 20:
        google_score = 40  # Proxy: popular tags likely indexed
    else:
        google_score = 10
    
    # 5. VALMAX relevance (15%)
    if any(k in tag_lower for k in VALMAX_RELEVANT):
        rel_score = 100
    else:
        rel_score = 15
    
    total = (pos_score * 0.25 + vol_score * 0.25 + comm_score * 0.20 + 
             google_score * 0.15 + rel_score * 0.15)
    
    return round(total, 1), pos_score, vol_score, comm_score, google_score, rel_score, volume, cpc

# Calculate for all tags (best position per tag)
tag_best = df.groupby('Tag').agg(
    best_position=('Position', 'min'),
    total_on_page=('Total on Page', 'max'),
    shot=('Shot Name', 'first'),
    views=('Views', 'max')
).reset_index()

scores = []
for _, row in tag_best.iterrows():
    total, pos_s, vol_s, comm_s, goog_s, rel_s, volume, cpc = calc_perspectiveness(
        row['Tag'], row['best_position'], row['total_on_page']
    )
    scores.append({
        'Tag': row['Tag'],
        'Position': row['best_position'],
        'Score': total,
        'Volume': volume,
        'CPC': round(cpc, 2),
        'Pos (25%)': pos_s,
        'Volume (25%)': vol_s,
        'Commercial (20%)': comm_s,
        'Google (15%)': goog_s,
        'Relevant (15%)': rel_s,
        'Shot': row['shot'],
        'Views': row['views'],
        'Status': '✅ Achieved' if row['best_position'] <= 12 else '🎯 Opportunity'
    })

score_df = pd.DataFrame(scores).sort_values('Score', ascending=False)

# Filters
score_col1, score_col2 = st.columns(2)
with score_col1:
    status_filter = st.selectbox("Статус", ["🎯 Opportunities only", "All", "✅ Achieved only"])
with score_col2:
    min_score = st.slider("Min Score", 0, 100, 30)

if status_filter == "🎯 Opportunities only":
    score_filtered = score_df[score_df['Status'] == '🎯 Opportunity']
elif status_filter == "✅ Achieved only":
    score_filtered = score_df[score_df['Status'] == '✅ Achieved']
else:
    score_filtered = score_df

score_filtered = score_filtered[score_filtered['Score'] >= min_score]

# KPIs
s_col1, s_col2, s_col3, s_col4 = st.columns(4)
achieved = len(score_df[score_df['Status'] == '✅ Achieved'])
opportunities_count = len(score_df[score_df['Status'] == '🎯 Opportunity'])
high_potential = len(score_df[(score_df['Status'] == '🎯 Opportunity') & (score_df['Score'] >= 60)])
s_col1.metric("✅ Achieved (Top 12)", achieved)
s_col2.metric("🎯 Opportunities", opportunities_count)
s_col3.metric("🔥 High Potential (60+)", high_potential)
s_col4.metric("📊 Avg Score", f"{score_df['Score'].mean():.0f}")

# Table
st.dataframe(
    score_filtered,
    column_config={
        "Tag": st.column_config.TextColumn("Tag", width="medium"),
        "Position": st.column_config.NumberColumn("Pos", width="small"),
        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f", width="small"),
        "Volume": st.column_config.NumberColumn("🔍 Vol/mo", help="Місячний обсяг пошуку в Google (DataForSEO)", format="%d", width="small"),
        "CPC": st.column_config.NumberColumn("💲 CPC", help="Вартість кліку в Google Ads ($) — індикатор комерційності", format="$%.2f", width="small"),
        "Pos (25%)": st.column_config.NumberColumn("📍 Pos", help="Позиція: 0=вже в top 12, 90=майже в цілі #13-15", width="small"),
        "Volume (25%)": st.column_config.NumberColumn("📈 Vol", help="Score на основі search volume", width="small"),
        "Commercial (20%)": st.column_config.NumberColumn("💰 Comm", help="Комерційна цінність: CPC + тип запиту", width="small"),
        "Google (15%)": st.column_config.NumberColumn("🔍 SEO", help="Позиція Dribbble tag page в Google", width="small"),
        "Relevant (15%)": st.column_config.NumberColumn("🎯 Rel", help="Релевантність послугам VALMAX", width="small"),
        "Shot": st.column_config.TextColumn("Best Shot", width="large"),
        "Views": st.column_config.NumberColumn("Views", format="%d", width="small"),
        "Status": st.column_config.TextColumn("Status", width="small"),
    },
    use_container_width=True, hide_index=True,
    height=500
)

st.caption("""
**Як читати Score (дані: DataForSEO API):**
- **🔍 Vol/mo** — реальний місячний обсяг пошуку в Google
- **💲 CPC** — ціна кліку в Google Ads (вище = комерційніший запит)
- **📍 Pos (25%)** — 0 = вже досягнуто (top 12), 90 = майже в цілі (#13-15)
- **📈 Vol (25%)** — score на основі search volume (10K+ = 100, 1K+ = 70, 100+ = 35)
- **💰 Comm (20%)** — комерційна цінність на основі CPC ($15+ = 100, $8+ = 80)
- **🔍 SEO (15%)** — позиція Dribbble tag page в Google (#1-3 = 100, #4-5 = 80)
- **🎯 Rel (15%)** — відповідність послугам VALMAX
""")

# --- TOP OPPORTUNITIES CHART ---
top_opps = score_filtered[score_filtered['Status'] == '🎯 Opportunity'].head(15)
if len(top_opps) > 0:
    top_opps_sorted = top_opps.sort_values('Score', ascending=True)
    fig = go.Figure(go.Bar(
        x=top_opps_sorted['Score'], y=top_opps_sorted['Tag'], orientation='h',
        marker_color=['#f5576c' if s >= 70 else '#ffa726' if s >= 50 else '#667eea' for s in top_opps_sorted['Score']],
        text=[f"#{p} → Score {s}" for p, s in zip(top_opps_sorted['Position'], top_opps_sorted['Score'])],
        textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=max(350, len(top_opps)*28), xaxis_title="Perspectiveness Score",
                     title="🔥 Top Opportunities", margin=dict(r=120))
    st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.divider()
st.caption("🏷️ VALMAX Tag Position Tracker | Scanned 1,272 tags | Deep scan (top 100) in progress")
