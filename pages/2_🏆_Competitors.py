import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# --- Modern Light Theme CSS ---
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
    .stDivider { border-color: #e8ecf1 !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
</style>
""", unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=300)
def load_data():
    # Try loading real data first
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        
        # Try competitors tab
        try:
            ws = sh.worksheet("🏆 Competitors")
            comp_data = ws.get_all_records()
            return pd.DataFrame(comp_data), "live"
        except:
            pass
    except:
        pass
    
    # Mock data
    data = [
        {"Company": "Outcrowd", "Followers": 200404, "Likes": 180134, "Shots (visible)": 24, "Avg Views/Shot": 45000, "Avg Likes/Shot": 520, "Posts/Month": 8, "Top Tags": "ui, ux, web design, animation", "Engagement %": 2.8},
        {"Company": "Ramotion", "Followers": 181188, "Likes": 2027, "Shots (visible)": 24, "Avg Views/Shot": 32000, "Avg Likes/Shot": 380, "Posts/Month": 6, "Top Tags": "branding, logo, ui, animation", "Engagement %": 1.9},
        {"Company": "Halo Lab", "Followers": 118110, "Likes": 36383, "Shots (visible)": 24, "Avg Views/Shot": 28000, "Avg Likes/Shot": 310, "Posts/Month": 10, "Top Tags": "web design, ui, branding, 3d", "Engagement %": 2.3},
        {"Company": "Nixtio", "Followers": 68900, "Likes": 42301, "Shots (visible)": 24, "Avg Views/Shot": 22000, "Avg Likes/Shot": 280, "Posts/Month": 12, "Top Tags": "ui, ux, dashboard, saas", "Engagement %": 2.5},
        {"Company": "Conceptzilla", "Followers": 54880, "Likes": 3691, "Shots (visible)": 24, "Avg Views/Shot": 18000, "Avg Likes/Shot": 200, "Posts/Month": 5, "Top Tags": "web design, branding, ui", "Engagement %": 1.8},
        {"Company": "QClay", "Followers": 26034, "Likes": 34265, "Shots (visible)": 24, "Avg Views/Shot": 15000, "Avg Likes/Shot": 180, "Posts/Month": 7, "Top Tags": "ui, dashboard, saas, fintech", "Engagement %": 2.1},
        {"Company": "Arounda", "Followers": 31117, "Likes": 174032, "Shots (visible)": 24, "Avg Views/Shot": 12000, "Avg Likes/Shot": 150, "Posts/Month": 9, "Top Tags": "web design, branding, ui, mobile", "Engagement %": 2.0},
        {"Company": "Ronas IT", "Followers": 17806, "Likes": 15615, "Shots (visible)": 24, "Avg Views/Shot": 14000, "Avg Likes/Shot": 170, "Posts/Month": 8, "Top Tags": "ui, ux, web design, healthcare", "Engagement %": 2.2},
        {"Company": "Phenomenon", "Followers": 15542, "Likes": 1534, "Shots (visible)": 24, "Avg Views/Shot": 8000, "Avg Likes/Shot": 90, "Posts/Month": 4, "Top Tags": "ui, product design, mobile", "Engagement %": 1.5},
        {"Company": "Habitat", "Followers": 6284, "Likes": 32383, "Shots (visible)": 24, "Avg Views/Shot": 6000, "Avg Likes/Shot": 70, "Posts/Month": 6, "Top Tags": "ui, ux, web design, branding", "Engagement %": 1.7},
        {"Company": "VALMAX", "Followers": 4382, "Likes": 20482, "Shots (visible)": 24, "Avg Views/Shot": 20465, "Avg Likes/Shot": 150, "Posts/Month": 7, "Top Tags": "uxui, design, webdesign, dashboard", "Engagement %": 2.4},
    ]
    return pd.DataFrame(data), "mock"

df, source = load_data()

# --- HEADER ---
st.markdown("# 🏆 Competitors Analysis")
if source == "mock":
    st.caption("⚠️ Preview with estimated data — real data loading after scraping completes")
else:
    st.caption("Live data from Google Sheets")
st.divider()

# --- VALMAX POSITION ---
valmax = df[df['Company'] == 'VALMAX'].iloc[0] if 'VALMAX' in df['Company'].values else None
df_sorted = df.sort_values('Followers', ascending=False).reset_index(drop=True)
valmax_rank = df_sorted[df_sorted['Company'] == 'VALMAX'].index[0] + 1 if valmax is not None else '?'

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏅 VALMAX Rank", f"#{valmax_rank} of {len(df)}")
col2.metric("👥 VALMAX Followers", f"{valmax['Followers']:,}" if valmax is not None else "?")
col3.metric("📊 Avg Views/Shot", f"{valmax['Avg Views/Shot']:,}" if valmax is not None else "?")
col4.metric("🎯 Engagement", f"{valmax['Engagement %']}%" if valmax is not None else "?")

# --- FOLLOWERS RANKING ---
st.divider()
st.markdown("### 👥 Followers Ranking")

df_rank = df.sort_values('Followers', ascending=True)
colors = ['#667eea' if c != 'VALMAX' else '#43e97b' for c in df_rank['Company']]

fig = go.Figure(go.Bar(
    x=df_rank['Followers'], y=df_rank['Company'], orientation='h',
    marker_color=colors,
    text=[f"{v:,}" for v in df_rank['Followers']],
    textposition='outside'
))
fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", 
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"), 
                 height=450, xaxis_title="Followers", margin=dict(r=100))
st.plotly_chart(fig, use_container_width=True)

# --- POSTING FREQUENCY ---
st.divider()
st.markdown("### 📅 Posting Frequency (shots/month)")

col_a, col_b = st.columns(2)

with col_a:
    df_freq = df.sort_values('Posts/Month', ascending=True)
    colors_freq = ['#667eea' if c != 'VALMAX' else '#43e97b' for c in df_freq['Company']]
    fig = go.Figure(go.Bar(
        x=df_freq['Posts/Month'], y=df_freq['Company'], orientation='h',
        marker_color=colors_freq,
        text=df_freq['Posts/Month'], textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=400, xaxis_title="Shots per month")
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("**Avg Views per Shot**")
    df_views = df.sort_values('Avg Views/Shot', ascending=True)
    colors_v = ['#667eea' if c != 'VALMAX' else '#43e97b' for c in df_views['Company']]
    fig = go.Figure(go.Bar(
        x=df_views['Avg Views/Shot'], y=df_views['Company'], orientation='h',
        marker_color=colors_v,
        text=[f"{v:,}" for v in df_views['Avg Views/Shot']], textposition='outside'
    ))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                     height=400, xaxis_title="Avg Views/Shot", margin=dict(r=80))
    st.plotly_chart(fig, use_container_width=True)

# --- ENGAGEMENT COMPARISON ---
st.divider()
st.markdown("### 🎯 Engagement Comparison")

fig = px.scatter(df, x='Followers', y='Engagement %', size='Avg Views/Shot',
                 color='Company', text='Company', template="plotly_white",
                 color_discrete_sequence=px.colors.qualitative.Set2)
fig.update_traces(textposition='top center', textfont_size=10)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                 font=dict(color="#636e72"), height=450, showlegend=False,
                 xaxis_title="Followers", yaxis_title="Engagement %")
st.plotly_chart(fig, use_container_width=True)

# --- VIEWS vs FOLLOWERS (efficiency) ---
st.divider()
st.markdown("### 📈 Efficiency: Views per Follower")

df['Views/Follower'] = (df['Avg Views/Shot'] / df['Followers'] * 100).round(1)
df_eff = df.sort_values('Views/Follower', ascending=True)
colors_e = ['#667eea' if c != 'VALMAX' else '#43e97b' for c in df_eff['Company']]

fig = go.Figure(go.Bar(
    x=df_eff['Views/Follower'], y=df_eff['Company'], orientation='h',
    marker_color=colors_e,
    text=[f"{v}%" for v in df_eff['Views/Follower']], textposition='outside'
))
fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#636e72"),
                 height=400, xaxis_title="Views per 100 followers")
st.plotly_chart(fig, use_container_width=True)

# --- TAG COMPARISON ---
st.divider()
st.markdown("### 🏷️ Tag Strategy")

# Collect all tags
all_tags = {}
for _, row in df.iterrows():
    company = row['Company']
    tags = [t.strip() for t in str(row.get('Top Tags', '')).split(',') if t.strip()]
    for tag in tags:
        if tag not in all_tags:
            all_tags[tag] = []
        all_tags[tag].append(company)

tag_rows = []
for tag, companies in sorted(all_tags.items(), key=lambda x: len(x[1]), reverse=True):
    valmax_uses = "✅" if "VALMAX" in companies else "❌"
    tag_rows.append({
        'Tag': tag,
        'Used by': len(companies),
        'Companies': ', '.join(companies[:5]),
        'VALMAX uses': valmax_uses
    })

tag_df = pd.DataFrame(tag_rows)

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.markdown("**Most popular tags among competitors**")
    st.dataframe(tag_df.head(20), use_container_width=True, hide_index=True)

with col_t2:
    st.markdown("**Tags competitors use but VALMAX doesn't**")
    missing = tag_df[tag_df['VALMAX uses'] == '❌'].head(15)
    if len(missing) > 0:
        st.dataframe(missing, use_container_width=True, hide_index=True)
    else:
        st.info("VALMAX uses all popular competitor tags!")

# --- FULL COMPARISON TABLE ---
st.divider()
st.markdown("### 📋 Full Comparison")

display_df = df.sort_values('Followers', ascending=False).reset_index(drop=True)
display_df.index = display_df.index + 1

# Highlight VALMAX row
def highlight_valmax(row):
    if row['Company'] == 'VALMAX':
        return ['background-color: #43e97b22'] * len(row)
    return [''] * len(row)

styled = display_df[['Company', 'Followers', 'Likes', 'Avg Views/Shot', 'Avg Likes/Shot', 
                       'Posts/Month', 'Engagement %']].style.apply(highlight_valmax, axis=1)
st.dataframe(styled, use_container_width=True)

# --- GAP ANALYSIS ---
st.divider()
st.markdown("### 🎯 Gap to Next Level")

if valmax is not None:
    targets = df_sorted[df_sorted['Followers'] > valmax['Followers']].tail(3)
    if len(targets) > 0:
        gap_cols = st.columns(len(targets))
        for i, (_, target) in enumerate(targets.iterrows()):
            with gap_cols[i]:
                follower_gap = target['Followers'] - valmax['Followers']
                views_gap = target['Avg Views/Shot'] - valmax['Avg Views/Shot']
                st.markdown(f"""
                <div style="text-align:center; padding:20px; background:#fff; border-radius:14px; 
                            box-shadow: 0 2px 12px rgba(0,0,0,0.06);">
                    <div style="font-size:16px; font-weight:700; color:#667eea;">{target['Company']}</div>
                    <div style="font-size:13px; color:#636e72; margin-top:8px;">
                        👥 +{follower_gap:,} followers<br>
                        👁️ {'+' if views_gap > 0 else ''}{views_gap:,} avg views/shot<br>
                        📅 {target['Posts/Month']} shots/month
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("🎉 VALMAX is #1!")

# --- FOOTER ---
st.divider()
st.caption("🏆 VALMAX Competitor Analysis | Data updates weekly")
