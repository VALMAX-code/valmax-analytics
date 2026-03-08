import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

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
def load_data():
    """Load competitor data from Google Sheet or local JSON."""
    # Try Google Sheet first
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        
        try:
            ws = sh.worksheet("🏆 Competitors")
            rows = ws.get_all_records()
            if rows:
                return pd.DataFrame(rows), None, "sheet"
        except:
            pass
    except:
        pass
    
    # Try local JSON (competitor shots data)
    try:
        with open('/Users/openzlo/.openclaw/workspace/memory/competitors-shots.json') as f:
            shots_data = json.load(f)
        with open('/Users/openzlo/.openclaw/workspace/memory/competitors-data.json') as f:
            profile_data = json.load(f)
        return build_from_json(shots_data, profile_data)
    except:
        pass
    
    # Fallback: profile-only data
    try:
        with open('/Users/openzlo/.openclaw/workspace/memory/competitors-data.json') as f:
            profile_data = json.load(f)
        return build_from_profiles(profile_data)
    except:
        return pd.DataFrame(), None, "empty"

def parse_date(date_str):
    """Parse dates like 'March 7, 2026' or 'February 28 2026'."""
    for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y']:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    return None

def build_from_json(shots_data, profile_data):
    """Build DataFrames from scraped JSON data."""
    profile_map = {p['username']: p for p in profile_data}
    
    profiles = []
    all_shots = []
    
    for username, data in shots_data.items():
        name = data.get('name', username)
        shots = data.get('shots', [])
        p_info = profile_map.get(username, {})
        
        # Parse shot dates and calculate stats
        dates = []
        total_views = 0
        total_likes = 0
        total_saves = 0
        total_comments = 0
        all_tags = []
        
        for s in shots:
            views = s.get('views', 0)
            likes = s.get('likes', 0)
            saves = s.get('saves', 0)
            comments = s.get('comments', 0)
            total_views += views
            total_likes += likes
            total_saves += saves
            total_comments += comments
            
            d = parse_date(s.get('date', ''))
            if d:
                dates.append(d)
            
            tags = s.get('tags', [])
            all_tags.extend(tags)
            
            all_shots.append({
                'Profile': name,
                'Username': username,
                'Shot Name': s.get('name', ''),
                'Date': d.strftime('%Y-%m-%d') if d else '',
                'Views': views,
                'Likes': likes,
                'Saves': saves,
                'Comments': comments,
                'Tags': ', '.join(tags[:10]),
                'URL': s.get('url', '')
            })
        
        n_shots = len(shots)
        avg_views = total_views // n_shots if n_shots else 0
        avg_likes = total_likes // n_shots if n_shots else 0
        
        # Posting frequency: shots per month based on date range
        if len(dates) >= 2:
            date_range_days = (max(dates) - min(dates)).days
            posts_per_month = round(n_shots / max(date_range_days / 30, 1), 1) if date_range_days > 0 else n_shots
        else:
            posts_per_month = 0
        
        # Last post
        last_post = max(dates).strftime('%Y-%m-%d') if dates else '?'
        
        # Engagement rate
        followers = p_info.get('followers', 0)
        engagement = round((total_likes / (followers * n_shots)) * 100, 2) if followers and n_shots else 0
        
        # Top tags (most frequent)
        from collections import Counter
        tag_counts = Counter(all_tags)
        top_tags = ', '.join([t for t, _ in tag_counts.most_common(8)])
        
        profiles.append({
            'Profile': name,
            'Username': username,
            'Followers': followers,
            'Total Likes (profile)': p_info.get('likes', 0),
            'Shots Scraped': n_shots,
            'Total Views': total_views,
            'Avg Views/Shot': avg_views,
            'Avg Likes/Shot': avg_likes,
            'Total Saves': total_saves,
            'Posts/Month': posts_per_month,
            'Last Post': last_post,
            'Engagement %': engagement,
            'Top Tags': top_tags
        })
    
    df_profiles = pd.DataFrame(profiles)
    df_shots = pd.DataFrame(all_shots)
    return df_profiles, df_shots, "json"

def build_from_profiles(profile_data):
    """Fallback: build from profile data only (no shot details)."""
    rows = []
    for p in profile_data:
        rows.append({
            'Profile': p['name'],
            'Username': p['username'],
            'Followers': p.get('followers', 0),
            'Total Likes (profile)': p.get('likes', 0),
            'Shots Scraped': 0,
            'Total Views': 0,
            'Avg Views/Shot': 0,
            'Avg Likes/Shot': 0,
            'Total Saves': 0,
            'Posts/Month': 0,
            'Last Post': '?',
            'Engagement %': 0,
            'Top Tags': ''
        })
    return pd.DataFrame(rows), None, "profiles_only"

df, df_shots, source = load_data()

# --- HEADER ---
st.markdown("# 🏆 Competitors Analysis")
source_labels = {
    "sheet": "Live data from Google Sheets",
    "json": "Data from latest scrape",
    "profiles_only": "⚠️ Profile data only — shot scraping in progress",
    "empty": "No data available"
}
st.caption(source_labels.get(source, ""))
if source == "empty":
    st.warning("No competitor data found. Run the scraper first.")
    st.stop()

st.divider()

# --- VALMAX POSITION ---
valmax = df[df['Username'] == 'valmax'].iloc[0] if 'valmax' in df['Username'].values else None
df_sorted = df.sort_values('Followers', ascending=False).reset_index(drop=True)
valmax_rank = df_sorted[df_sorted['Username'] == 'valmax'].index[0] + 1 if valmax is not None else '?'

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏅 VALMAX Rank", f"#{valmax_rank} of {len(df)}")
col2.metric("👥 Followers", f"{valmax['Followers']:,}" if valmax is not None else "?")
if valmax is not None and valmax.get('Avg Views/Shot', 0) > 0:
    col3.metric("📊 Avg Views/Shot", f"{valmax['Avg Views/Shot']:,}")
else:
    col3.metric("📊 Avg Views/Shot", "—")
col4.metric("🎯 Engagement", f"{valmax['Engagement %']}%" if valmax is not None and valmax.get('Engagement %', 0) > 0 else "—")

# --- FOLLOWERS RANKING ---
st.divider()
st.markdown("### 👥 Followers Ranking")

df_rank = df.sort_values('Followers', ascending=True)
colors = ['#43e97b' if u == 'valmax' else '#667eea' for u in df_rank['Username']]

fig = go.Figure(go.Bar(
    x=df_rank['Followers'], y=df_rank['Profile'], orientation='h',
    marker_color=colors,
    text=[f"{v:,}" for v in df_rank['Followers']],
    textposition='outside'
))
fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", 
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), 
                 height=max(400, len(df)*35), xaxis_title="Followers", margin=dict(r=100))
st.plotly_chart(fig, use_container_width=True)

# --- POSTING FREQUENCY & AVG VIEWS ---
if df['Posts/Month'].sum() > 0:
    st.divider()
    st.markdown("### 📅 Posting Frequency & Performance")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        df_freq = df[df['Posts/Month'] > 0].sort_values('Posts/Month', ascending=True)
        if len(df_freq) > 0:
            colors_freq = ['#43e97b' if u == 'valmax' else '#667eea' for u in df_freq['Username']]
            fig = go.Figure(go.Bar(
                x=df_freq['Posts/Month'], y=df_freq['Profile'], orientation='h',
                marker_color=colors_freq,
                text=df_freq['Posts/Month'], textposition='outside'
            ))
            fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                             plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                             height=max(350, len(df_freq)*30), xaxis_title="Shots per month",
                             title="Posting Frequency")
            st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        df_views = df[df['Avg Views/Shot'] > 0].sort_values('Avg Views/Shot', ascending=True)
        if len(df_views) > 0:
            colors_v = ['#43e97b' if u == 'valmax' else '#667eea' for u in df_views['Username']]
            fig = go.Figure(go.Bar(
                x=df_views['Avg Views/Shot'], y=df_views['Profile'], orientation='h',
                marker_color=colors_v,
                text=[f"{v:,}" for v in df_views['Avg Views/Shot']], textposition='outside'
            ))
            fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                             plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                             height=max(350, len(df_views)*30), xaxis_title="Avg Views/Shot",
                             title="Average Views per Shot", margin=dict(r=80))
            st.plotly_chart(fig, use_container_width=True)

# --- ENGAGEMENT SCATTER ---
if df['Engagement %'].sum() > 0:
    st.divider()
    st.markdown("### 🎯 Engagement vs Followers")
    st.caption("Bubble size = Avg Views/Shot. Higher engagement with fewer followers = efficient growth")
    
    scatter_df = df[df['Engagement %'] > 0].copy()
    fig = px.scatter(scatter_df, x='Followers', y='Engagement %', 
                     size='Avg Views/Shot', color='Profile', text='Profile',
                     template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textposition='top center', textfont_size=9)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#636e72"), height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- VIEWS PER FOLLOWER (efficiency) ---
if df['Avg Views/Shot'].sum() > 0:
    st.divider()
    st.markdown("### 📈 Efficiency: Views per 100 Followers")
    st.caption("How many views each shot gets relative to follower count — higher = content reaches beyond followers")
    
    eff_df = df[(df['Followers'] > 0) & (df['Avg Views/Shot'] > 0)].copy()
    eff_df['Views/100 Followers'] = (eff_df['Avg Views/Shot'] / eff_df['Followers'] * 100).round(1)
    eff_df = eff_df.sort_values('Views/100 Followers', ascending=True)
    
    colors_e = ['#43e97b' if u == 'valmax' else '#667eea' for u in eff_df['Username']]
    fig = go.Figure(go.Bar(
        x=eff_df['Views/100 Followers'], y=eff_df['Profile'], orientation='h',
        marker_color=colors_e,
        text=[f"{v}" for v in eff_df['Views/100 Followers']], textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=max(350, len(eff_df)*30), xaxis_title="Views per 100 followers")
    st.plotly_chart(fig, use_container_width=True)

# --- TAG COMPARISON ---
if df['Top Tags'].str.len().sum() > 0:
    st.divider()
    st.markdown("### 🏷️ Tag Strategy Comparison")
    
    all_tags = {}
    valmax_tags = set()
    for _, row in df.iterrows():
        profile = row['Profile']
        tags = [t.strip().lower() for t in str(row.get('Top Tags', '')).split(',') if t.strip()]
        for tag in tags:
            if tag not in all_tags:
                all_tags[tag] = []
            all_tags[tag].append(profile)
            if row['Username'] == 'valmax':
                valmax_tags.add(tag)
    
    tag_rows = []
    for tag, profiles_list in sorted(all_tags.items(), key=lambda x: len(x[1]), reverse=True):
        tag_rows.append({
            'Tag': tag,
            'Used by': len(profiles_list),
            'Profiles': ', '.join(profiles_list[:6]),
            'VALMAX': "✅" if tag in valmax_tags else "❌"
        })
    
    tag_df = pd.DataFrame(tag_rows)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Most used tags among competitors**")
        st.dataframe(tag_df.head(25), use_container_width=True, hide_index=True)
    
    with col_t2:
        st.markdown("**Tags VALMAX is missing**")
        missing = tag_df[tag_df['VALMAX'] == '❌'].head(20)
        if len(missing) > 0:
            st.dataframe(missing, use_container_width=True, hide_index=True)
        else:
            st.success("VALMAX uses all popular competitor tags! 🎉")

# --- SHOT-LEVEL COMPARISON ---
if df_shots is not None and len(df_shots) > 0:
    st.divider()
    st.markdown("### 🔥 Top Shots Across All Competitors")
    
    top_shots = df_shots.sort_values('Views', ascending=False).head(30)
    display_shots = top_shots[['Profile', 'Shot Name', 'Date', 'Views', 'Likes', 'Saves']].copy()
    
    def highlight_valmax(row):
        if row['Profile'] == 'VALMAX':
            return ['background-color: #43e97b22'] * len(row)
        return [''] * len(row)
    
    styled = display_shots.style.apply(highlight_valmax, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

# --- FULL TABLE ---
st.divider()
st.markdown("### 📋 Full Comparison Table")

display_df = df.sort_values('Followers', ascending=False).reset_index(drop=True)
display_cols = ['Profile', 'Username', 'Followers', 'Shots Scraped']
if df['Avg Views/Shot'].sum() > 0:
    display_cols += ['Avg Views/Shot', 'Avg Likes/Shot', 'Posts/Month', 'Last Post', 'Engagement %']

def highlight_valmax_row(row):
    if row.get('Username') == 'valmax':
        return ['background-color: #43e97b22'] * len(row)
    return [''] * len(row)

styled_full = display_df[display_cols].style.apply(highlight_valmax_row, axis=1)
st.dataframe(styled_full, use_container_width=True)

# --- GAP TO NEXT ---
if valmax is not None:
    st.divider()
    st.markdown("### 🎯 Gap to Next Level")
    
    above = df_sorted[df_sorted['Followers'] > (valmax['Followers'] if valmax is not None else 0)].tail(3)
    if len(above) > 0:
        gap_cols = st.columns(len(above))
        for i, (_, target) in enumerate(above.iterrows()):
            with gap_cols[i]:
                f_gap = target['Followers'] - valmax['Followers']
                st.markdown(f"""
                <div style="text-align:center; padding:20px; background:#fff; border-radius:14px; 
                            box-shadow: 0 2px 12px rgba(0,0,0,0.06);">
                    <div style="font-size:16px; font-weight:700; color:#667eea;">{target['Profile']}</div>
                    <div style="font-size:24px; font-weight:800; color:#2d3436; margin:8px 0;">+{f_gap:,}</div>
                    <div style="font-size:12px; color:#636e72;">followers to catch up</div>
                    <div style="font-size:13px; color:#636e72; margin-top:8px;">
                        📅 {target['Posts/Month']} shots/mo<br>
                        👁️ {target['Avg Views/Shot']:,} avg views
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- FOOTER ---
st.divider()
st.caption("🏆 VALMAX Competitor Analysis | Each profile tracked separately | Data updates weekly")
