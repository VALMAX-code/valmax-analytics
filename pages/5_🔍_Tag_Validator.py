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
@st.cache_data(ttl=600)
def load_keywords():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        
        ws = sh.worksheet("🔑 Dribbble Keywords")
        rows = ws.get_all_records()
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_seo_data():
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
        return {}

@st.cache_data(ttl=600)
def load_serp_data():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key('1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc')
        
        ws = sh.worksheet("🔍 SERP Data")
        rows = ws.get_all_records()
        return {r['Tag']: r for r in rows}
    except:
        return {}

@st.cache_data(ttl=600)
def load_tag_positions():
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
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

kw_df = load_keywords()
seo_data = load_seo_data()
serp_data = load_serp_data()
tag_pos_df = load_tag_positions()

# --- HEADER ---
st.markdown("# 🔍 Tag Validator")
from utils import show_last_updated
show_last_updated("SEO Data (Volume/CPC)")
st.caption("Введіть тег перед публікацією шота — система оцінить його перспективність та дасть рекомендації")

st.divider()

# --- TAG VALIDATOR INPUT ---
tag_input = st.text_input("🏷️ Введіть тег для перевірки", placeholder="dashboard ui design, fintech, saas...")

if tag_input:
    tag = tag_input.strip().lower()
    # Normalize: "fintech dashboard" matches "fintech-dashboard" and vice versa
    tag_hyphen = tag.replace(' ', '-')
    tag_space = tag.replace('-', ' ')
    
    st.divider()
    st.markdown(f"### 📊 Аналіз тегу: `{tag}`")
    
    # Find in keywords database (match both space and hyphen variants)
    if not kw_df.empty:
        kw_lower = kw_df['Keyword'].str.lower()
        kw_match = kw_df[(kw_lower == tag) | (kw_lower == tag_hyphen) | (kw_lower == tag_space)]
        kw_partial = kw_df[kw_lower.str.contains(tag, na=False) | kw_lower.str.contains(tag_hyphen, na=False)]
    else:
        kw_match = pd.DataFrame()
        kw_partial = pd.DataFrame()
    
    # SEO data (try all variants)
    seo = seo_data.get(tag, {}) or seo_data.get(tag_hyphen, {}) or seo_data.get(tag_space, {})
    serp = serp_data.get(tag, {}) or serp_data.get(tag_hyphen, {}) or serp_data.get(tag_space, {})
    
    # Volume & CPC
    volume = 0
    cpc = 0
    if not kw_match.empty:
        volume = int(kw_match.iloc[0].get('Volume/mo', 0) or 0)
        cpc = float(kw_match.iloc[0].get('CPC ($)', 0) or 0)
    if not volume and seo:
        volume = int(seo.get('Volume/mo', 0) or 0)
        cpc = float(seo.get('CPC ($)', 0) or 0)
    
    # Fix CPC ×100 bug from Google Sheets
    if cpc > 100:
        cpc = cpc / 100
    
    # Dribbble Google position — try cached first, then live SERP
    dribbble_gpos = None
    est_traffic = 0
    ai_vis = 'Unknown'
    live_serp = False
    ctr_map = {1:0.28, 2:0.15, 3:0.11, 4:0.08, 5:0.07, 6:0.05, 7:0.04, 8:0.03, 9:0.03, 10:0.02,
               11:0.015, 12:0.012, 13:0.01, 14:0.009, 15:0.008, 16:0.007, 17:0.006, 18:0.005, 19:0.005, 20:0.005}
    
    if not kw_match.empty:
        dribbble_gpos = int(kw_match.iloc[0].get('Google Pos', 0) or 0)
        est_traffic = int(kw_match.iloc[0].get('Est. Traffic/mo', 0) or 0)
    elif serp:
        gp = serp.get('Dribbble Google Pos', 0)
        if gp and gp != '':
            dribbble_gpos = int(gp)
            est_traffic = int(volume * ctr_map.get(dribbble_gpos, 0.01))
    
    if serp:
        ai_vis = serp.get('AI Overview', 'Unknown')
    
    # Live SERP check via DataForSEO if no cached data
    if dribbble_gpos is None or dribbble_gpos == 0 or ai_vis == 'Unknown':
        import requests
        try:
            serp_payload = [{"keyword": tag_space, "language_code": "en", "location_code": 2840, "depth": 20}]
            resp = requests.post(
                "https://api.dataforseo.com/v3/serp/google/organic/live/regular",
                json=serp_payload,
                headers={"Authorization": st.secrets.get("DATAFORSEO_AUTH", "Basic aGVsbG9AdmFsbWF4LmFnZW5jeTo1NTUyMWMyNjViOTczMzll")},
                timeout=15
            )
            serp_result = resp.json()
            items = serp_result.get('tasks', [{}])[0].get('result', [{}])[0].get('items', [])
            
            for item in items:
                url = item.get('url', '')
                if 'dribbble.com' in url:
                    dribbble_gpos = item.get('rank_absolute', 0)
                    est_traffic = int(volume * ctr_map.get(dribbble_gpos, 0.005))
                    break
            
            # Check AI overview
            ai_items = [i for i in items if i.get('type') == 'ai_overview']
            if ai_items:
                ai_vis = 'Yes'
                ai_text = str(ai_items[0])
                if 'dribbble' in ai_text.lower():
                    ai_vis = 'Yes (Dribbble mentioned)'
            else:
                ai_vis = 'No'
            
            live_serp = True
        except:
            pass
    
    # VALMAX position in tag
    valmax_pos = None
    tag_competition = 0
    if not tag_pos_df.empty:
        tag_lower = tag_pos_df['Tag'].str.lower()
        tag_match = tag_pos_df[(tag_lower == tag) | (tag_lower == tag_hyphen) | (tag_lower == tag_space)]
        if not tag_match.empty:
            valmax_pos = int(tag_match.iloc[0].get('Position', 0))
            tag_competition = int(tag_match.iloc[0].get('Total on Page', 0))
    
    # --- KPIs ---
    if live_serp:
        st.caption("🔴 **LIVE** — дані отримані з Google в реальному часі через DataForSEO ($0.002)")
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔍 Google Volume", f"{volume:,}/mo" if volume else "No data")
    k2.metric("🌐 Dribbble in Google", f"#{dribbble_gpos}" if dribbble_gpos else "Not in top 20")
    k3.metric("🚀 Est. Traffic to Dribbble", f"{est_traffic:,}/mo" if est_traffic else "0")
    ai_label = "✅ Yes" if 'Yes' in str(ai_vis) else "❌ No"
    k4.metric("🤖 AI Visibility", ai_label)
    k5.metric("📍 VALMAX Position", f"#{valmax_pos}" if valmax_pos else "Not ranked")
    
    k6, k7, k8 = st.columns(3)
    k6.metric("💰 CPC (Commercial)", f"${cpc:.2f}" if cpc else "No data")
    k7.metric("⚔️ Competition", f"{tag_competition} shots" if tag_competition else "Unknown")
    
    # Overall score
    score = 0
    reasons = []
    
    if volume >= 10000: score += 30; reasons.append("🔥 Високий попит")
    elif volume >= 1000: score += 20; reasons.append("📈 Середній попит")
    elif volume >= 100: score += 10; reasons.append("📊 Низький попит")
    else: reasons.append("⚠️ Попит невідомий або дуже низький")
    
    if dribbble_gpos and dribbble_gpos <= 5: score += 25; reasons.append("🌐 Dribbble в top 5 Google — трафік гарантований")
    elif dribbble_gpos and dribbble_gpos <= 10: score += 20; reasons.append("🌐 Dribbble в top 10 Google")
    elif dribbble_gpos and dribbble_gpos <= 20: score += 10; reasons.append("🌐 Dribbble в top 20 Google")
    else: reasons.append("⚠️ Dribbble НЕ в top 20 Google — трафік з пошуку мінімальний")
    
    if ai_vis == 'Yes': score += 10; reasons.append("🤖 Dribbble з'являється в AI видачі")
    
    if cpc >= 15: score += 15; reasons.append("💰 Дуже комерційний запит (CPC $15+)")
    elif cpc >= 5: score += 10; reasons.append("💰 Комерційний запит (CPC $5+)")
    
    if tag_competition and tag_competition < 15: score += 15; reasons.append("⚔️ Низька конкуренція на Dribbble")
    elif tag_competition and tag_competition < 24: score += 5; reasons.append("⚔️ Середня конкуренція")
    elif tag_competition >= 24: reasons.append("⚔️ Повна сторінка — висока конкуренція")
    
    # VALMAX relevance
    valmax_kws = ['dashboard', 'saas', 'fintech', 'healthcare', 'crm', 'analytics', 'web design', 
                  'landing page', 'ui', 'ux', 'b2b', 'startup', 'brand', 'ecommerce', 'corporate',
                  'mobile app', 'product design', 'interface']
    if any(kw in tag for kw in valmax_kws):
        score += 10; reasons.append("🎯 Релевантний послугам VALMAX")
    
    k8.metric("⭐ Score", f"{score}/100", help="Загальна оцінка перспективності тегу")
    
    # Verdict
    if score >= 70:
        st.success(f"🔥 **ВІДМІННИЙ ТЕГ!** Score: {score}/100 — обов'язково використовувати")
    elif score >= 50:
        st.info(f"👍 **ХОРОШИЙ ТЕГ.** Score: {score}/100 — варто використовувати")
    elif score >= 30:
        st.warning(f"🤔 **СЕРЕДНІЙ ТЕГ.** Score: {score}/100 — використовувати з іншими сильнішими тегами")
    else:
        st.error(f"❌ **СЛАБКИЙ ТЕГ.** Score: {score}/100 — краще замінити на інший")
    
    # Reasons
    with st.expander("📋 Деталі оцінки"):
        for r in reasons:
            st.markdown(f"- {r}")
    
    # --- PLAN TO REACH TOP 8 ---
    st.divider()
    st.markdown("### 🎯 План виходу в Top 8")
    
    if tag_competition and tag_competition > 0:
        # Estimate views needed
        if not tag_pos_df.empty:
            tag_shots = tag_pos_df[tag_pos_df['Tag'].str.lower() == tag]
            if not tag_shots.empty and 'Views' in tag_shots.columns:
                top8_views = tag_shots[tag_shots['Position'] <= 8]['Views'].min() if len(tag_shots[tag_shots['Position'] <= 8]) > 0 else None
                avg_views = tag_shots['Views'].mean()
                
                if top8_views:
                    st.markdown(f"""
                    - 🎯 **Мінімум переглядів для Top 8:** ~{int(top8_views):,}
                    - 📊 **Середні перегляди в тезі:** ~{int(avg_views):,}
                    - ⚔️ **Конкурентів на сторінці:** {tag_competition}
                    """)
        
        if tag_competition >= 20:
            st.markdown("""
            **Рекомендації для насиченого тегу:**
            1. 📸 Опублікувати **2-3 шоти** з цим тегом для більшого шансу
            2. 🔥 Фокус на якість — потрібен WOW-ефект для привернення лайків
            3. ⏰ Публікувати в пікові години (вт-чт, 10:00-14:00 UTC)
            4. 💬 Активно залучати engagement в перші 24-48 годин
            """)
        else:
            st.markdown("""
            **Рекомендації для малоконкурентного тегу:**
            1. 📸 Достатньо **1 якісного шота**
            2. 🏷️ Комбінувати з іншими релевантними тегами
            3. 📈 Навіть середній шот може потрапити в top 8
            """)
    else:
        st.info("Немає даних про конкуренцію. Потрібен скан цього тегу на Dribbble.")
    
    # --- SUGGESTED TAGS ---
    st.divider()
    st.markdown("### 💡 Рекомендовані теги (схожі)")
    st.caption("Теги з бази keywords Dribbble, які пов'язані з вашим запитом і мають трафік")
    
    if not kw_partial.empty:
        related = kw_partial[kw_partial['Keyword'].str.lower() != tag].sort_values('Est. Traffic/mo', ascending=False).head(20)
        if not related.empty:
            st.dataframe(
                related[['Keyword', 'Volume/mo', 'Google Pos', 'Est. Traffic/mo', 'CPC ($)', 'Tag Page', 'Landing URL']],
                column_config={
                    "Keyword": st.column_config.TextColumn("🏷️ Keyword"),
                    "Volume/mo": st.column_config.NumberColumn("📈 Vol/mo", format="%d"),
                    "Google Pos": st.column_config.NumberColumn("🔍 Google #", format="%d"),
                    "Est. Traffic/mo": st.column_config.NumberColumn("🚀 Traffic", format="%d"),
                    "CPC ($)": st.column_config.NumberColumn("💰 CPC", format="$%.2f"),
                    "Tag Page": st.column_config.TextColumn("Tag"),
                    "Landing URL": st.column_config.LinkColumn("🔗 Link", display_text="Open →"),
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Схожих тегів не знайдено")
    else:
        st.info("Немає даних для рекомендацій")

# --- FULL KEYWORDS TABLE ---
st.divider()
st.markdown("### 📊 Повна база: Keywords де Dribbble в Google Top 20")
st.caption(f"3,189 keywords де dribbble.com/tags/ ранжується в Google (US). Дані: DataForSEO Ranked Keywords API")

if not kw_df.empty:
    kw_col1, kw_col2, kw_col3, kw_col4 = st.columns(4)
    kw_col1.metric("🔑 Total Keywords", f"{len(kw_df):,}")
    total_traffic_all = kw_df['Est. Traffic/mo'].sum() if 'Est. Traffic/mo' in kw_df.columns else 0
    kw_col2.metric("🚀 Est. Total Traffic", f"{int(total_traffic_all):,}/mo")
    top3 = len(kw_df[kw_df['Google Pos'] <= 3]) if 'Google Pos' in kw_df.columns else 0
    kw_col3.metric("🥇 Top 3 Positions", top3)
    avg_pos = kw_df['Google Pos'].mean() if 'Google Pos' in kw_df.columns else 0
    kw_col4.metric("📊 Avg Position", f"#{avg_pos:.1f}")
    
    # Search
    kw_search = st.text_input("🔍 Пошук по keyword", "", key="kw_search")
    
    display_kw = kw_df.copy()
    if kw_search:
        display_kw = display_kw[display_kw['Keyword'].str.contains(kw_search, case=False, na=False)]
    
    st.dataframe(
        display_kw.head(500),
        column_config={
            "Keyword": st.column_config.TextColumn("🏷️ Keyword", width="large"),
            "Volume/mo": st.column_config.NumberColumn("📈 Vol/mo", format="%d"),
            "CPC ($)": st.column_config.NumberColumn("💰 CPC", format="$%.2f"),
            "Google Pos": st.column_config.NumberColumn("🔍 Pos", format="%d"),
            "Est. Traffic/mo": st.column_config.NumberColumn("🚀 Traffic", format="%d"),
            "Tag Page": st.column_config.TextColumn("Tag Page"),
            "Landing URL": st.column_config.LinkColumn("🔗", display_text="Open →"),
        },
        use_container_width=True, hide_index=True, height=600
    )
    
    st.caption("""
    **Як користуватися:**
    - **Volume** — скільки разів на місяць люди шукають цей запит в Google
    - **Google Pos** — на якій позиції Dribbble tag page у видачі Google
    - **Traffic** — приблизна кількість кліків з Google на цю сторінку Dribbble
    - **CPC** — вартість кліку в Google Ads (вище = комерційніший запит, клієнти шукають)
    - **Tag Page** — яка сторінка тегу Dribbble ранжується
    - Якщо VALMAX шот потрапить на першу сторінку цього тегу → він отримає частину цього трафіку
    """)

# --- FOOTER ---
st.divider()
st.caption("🔍 Tag Validator | DataForSEO API | 3,189 keywords де Dribbble видно в Google | Оновлюється monthly")
