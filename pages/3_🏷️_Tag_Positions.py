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

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🏷️ Tags with VALMAX", total_tags_with_positions)
c2.metric("📍 Total Positions", total_positions)
c3.metric("🥇 #1 Positions", num_first)
c4.metric("🥉 Top 5", num_top5)
c5.metric("🔟 Top 10", num_top10)

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
    # Positions per shot (treemap)
    shot_counts = df.groupby('Shot Name').agg(
        tags=('Tag', 'count'),
        avg_pos=('Position', 'mean'),
        best_pos=('Position', 'min'),
        views=('Views', 'first')
    ).reset_index().sort_values('tags', ascending=False).head(15)
    
    fig = px.treemap(shot_counts, path=['Shot Name'], values='tags',
                     color='avg_pos', color_continuous_scale='RdYlGn_r',
                     hover_data=['best_pos', 'views', 'tags'])
    fig.update_layout(template="plotly_white", height=350, 
                     coloraxis_colorbar_title="Avg Position")
    st.plotly_chart(fig, use_container_width=True)

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
            "Total on Page": st.column_config.NumberColumn("Total Shots", width="small"),
        },
        use_container_width=True, hide_index=True
    )
else:
    st.info("No #1 positions in current filter")

# --- BEST SHOTS BY TAG COUNT ---
st.divider()
st.markdown("### 🎯 Best Performing Shots (by tag appearances)")

shot_stats = filtered.groupby('Shot Name').agg(
    tags_count=('Tag', 'count'),
    avg_position=('Position', 'mean'),
    best_position=('Position', 'min'),
    first_places=('Position', lambda x: (x == 1).sum()),
    top5_count=('Position', lambda x: (x <= 5).sum()),
    views=('Views', 'first')
).reset_index().sort_values('tags_count', ascending=False)

shot_stats['avg_position'] = shot_stats['avg_position'].round(1)

st.dataframe(
    shot_stats.head(20),
    column_config={
        "Shot Name": st.column_config.TextColumn("Shot", width="large"),
        "tags_count": st.column_config.NumberColumn("Tags Found", width="small"),
        "avg_position": st.column_config.NumberColumn("Avg Position", width="small"),
        "best_position": st.column_config.NumberColumn("Best", width="small"),
        "first_places": st.column_config.NumberColumn("#1 Count", width="small"),
        "top5_count": st.column_config.NumberColumn("Top 5", width="small"),
        "views": st.column_config.NumberColumn("Views", format="%d", width="small"),
    },
    use_container_width=True, hide_index=True
)

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

# --- ALL POSITIONS TABLE ---
st.divider()
st.markdown("### 📋 All Tag Positions")

display_all = filtered.sort_values('Position').copy()
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

# --- OPPORTUNITY TAGS ---
st.divider()
st.markdown("### 💡 Opportunity Tags")
st.caption("Tags where VALMAX is close to #1 — small improvements could boost ranking")

opportunities = filtered[(filtered['Position'] > 1) & (filtered['Position'] <= 5)].sort_values('Position')
if len(opportunities) > 0:
    opp_display = opportunities[['Tag', 'Position', 'Shot Name', 'Views']].copy()
    opp_display['Gap to #1'] = opp_display['Position'] - 1
    opp_display['Views'] = opp_display['Views'].apply(lambda v: f"{v:,}")
    st.dataframe(opp_display, use_container_width=True, hide_index=True, height=400)
else:
    st.info("No opportunity tags in current filter")

# --- FOOTER ---
st.divider()
st.caption("🏷️ VALMAX Tag Position Tracker | Scanned 1,272 tags | Deep scan (top 100) in progress")
