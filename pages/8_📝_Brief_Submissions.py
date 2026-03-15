import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brief Submissions", page_icon="📝", layout="wide")

@st.cache_data(ttl=120)
def load_data():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        ws = sh.worksheet("📤 Project Intros")
        vals = ws.get_all_values()
        if not vals or len(vals) < 2:
            return pd.DataFrame()
        header = vals[0]
        rows = [r + [''] * (len(header) - len(r)) for r in vals[1:] if any(c.strip() for c in r)]
        return pd.DataFrame(rows, columns=header)
    except Exception as e:
        st.error(f"Failed to load: {e}")
        return pd.DataFrame()

df = load_data()

# --- HEADER ---
st.markdown("# 📝 Brief Submissions")
from utils import show_last_updated
show_last_updated("Brief Submissions")
st.caption("Project Intros відправлені VALMAX у відповідь на брифи клієнтів на Dribbble")
st.divider()

if df.empty:
    st.warning("No Brief Submissions data")
    st.stop()

# Parse dates
if 'Date' in df.columns:
    df['_date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.sort_values('_date', ascending=False)

# --- FILTERS ---
col_f1, col_f2, col_f3 = st.columns(3)
months = ["All"] + sorted(df['Month'].unique().tolist(), reverse=True)
with col_f1:
    month_filter = st.selectbox("📅 Month", months)
crm_options = ["All"] + sorted([s for s in df['CRM Status'].unique() if s])
with col_f2:
    crm_filter = st.selectbox("📊 CRM Status", crm_options)
replied_options = ["All", "Yes", "No"]
with col_f3:
    replied_filter = st.selectbox("💬 Client Replied?", replied_options)

filtered = df.copy()
if month_filter != "All":
    filtered = filtered[filtered['Month'] == month_filter]
if crm_filter != "All":
    filtered = filtered[filtered['CRM Status'] == crm_filter]
if replied_filter != "All":
    filtered = filtered[filtered['Client Replied?'] == replied_filter]

# --- Parse Budget ---
def parse_budget(val):
    if not val or val == 'Unknown':
        return 0
    val = str(val).replace(',', '').replace('+', '').replace('$', '').replace('~', '').strip()
    # Range: take lower bound
    if '-' in val:
        try: return float(val.split('-')[0])
        except: return 0
    try: return float(val)
    except: return 0

# --- KPIs ---
total = len(filtered)
replied = len(filtered[filtered['Client Replied?'] == 'Yes'])
meetings = len(filtered[filtered['Meeting Scheduled'] == 'Yes'])
won = len(filtered[filtered['CRM Status'] == 'Won ✅'])
reply_rate = f"{replied/total*100:.0f}%" if total > 0 else "0%"
conversion = f"{won/total*100:.1f}%" if total > 0 else "0%"

won_df = filtered[filtered['CRM Status'] == 'Won ✅'] if 'CRM Status' in filtered.columns else pd.DataFrame()
total_revenue = won_df['Budget'].apply(parse_budget).sum() if 'Budget' in won_df.columns and len(won_df) > 0 else 0
avg_deal = total_revenue / won if won > 0 else 0

r1 = st.columns(5)
r1[0].metric("📤 Total Intros Sent", total)
r1[1].metric("💬 Client Replied", replied, help=f"Reply rate: {reply_rate}")
r1[2].metric("📊 Reply Rate", reply_rate)
r1[3].metric("📅 Meetings Scheduled", meetings)
r1[4].metric("🏆 Won Deals", won)

r2 = st.columns(4)
r2[0].metric("📈 Conversion", conversion)
r2[1].metric("💰 Revenue", f"${total_revenue:,.0f}")
r2[2].metric("💵 Avg Deal", f"${avg_deal:,.0f}" if avg_deal > 0 else "—")
r2[3].metric("📊 Cost per Win", f"${total_revenue/won:,.0f}" if won > 0 else "—", help="Revenue per won deal")

st.divider()

# --- CHARTS ---
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 📊 Intros per Month")
    monthly = filtered.groupby('Month').size().reset_index(name='Count')
    # Sort by date
    month_order = {'December 2025': 0, 'January 2026': 1, 'February 2026': 2, 'March 2026': 3, 'April 2026': 4}
    monthly['sort'] = monthly['Month'].map(month_order).fillna(99)
    monthly = monthly.sort_values('sort')
    fig = px.bar(monthly, x='Month', y='Count', template='plotly_white',
                 color_discrete_sequence=['#667eea'], text='Count')
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#636e72"), height=350, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("### 📈 Daily Submission Trend")
    if '_date' in filtered.columns:
        daily = filtered.groupby(filtered['_date'].dt.date).size().reset_index(name='Count')
        daily.columns = ['Date', 'Count']
        fig2 = px.line(daily, x='Date', y='Count', template='plotly_white',
                       color_discrete_sequence=['#43e97b'], markers=True)
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"), height=350)
        st.plotly_chart(fig2, use_container_width=True)

# --- CONVERSION FUNNEL ---
st.divider()
st.markdown("### 🔄 Conversion Funnel")

funnel_data = pd.DataFrame({
    'Stage': ['Intros Sent', 'Client Replied', 'Meeting Scheduled', 'Won Deal'],
    'Count': [total, replied, meetings, won],
})
fig_funnel = go.Figure(go.Funnel(
    y=funnel_data['Stage'],
    x=funnel_data['Count'],
    textinfo="value+percent initial",
    marker=dict(color=['#667eea', '#764ba2', '#f093fb', '#43e97b']),
))
fig_funnel.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#636e72"))
st.plotly_chart(fig_funnel, use_container_width=True)

# --- DATA TABLE ---
st.divider()
st.markdown("### 📋 All Brief Submissions")

display_cols = ['Date', 'Client', 'Project Title', 'Client Replied?', 'Meeting Scheduled', 'CRM Status', 'Relevant']
available = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available], use_container_width=True, hide_index=True, height=500)

# --- FOOTER ---
st.divider()
st.caption("📤 Brief Submissions | Updated daily via cron | Track project intro success rate")
