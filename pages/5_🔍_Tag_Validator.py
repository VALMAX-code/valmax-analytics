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
@st.cache_data(ttl=120)
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

@st.cache_data(ttl=120)
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

@st.cache_data(ttl=120)
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

@st.cache_data(ttl=120)
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
    def parse_cpc(val):
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.replace('$', '').replace(',', '').strip() or 0)
        return 0.0
    
    if not kw_match.empty:
        volume = int(kw_match.iloc[0].get('Volume/mo', 0) or 0)
        cpc = parse_cpc(kw_match.iloc[0].get('CPC ($)', 0))
    if not volume and seo:
        volume = int(seo.get('Volume/mo', 0) or 0)
        cpc = parse_cpc(seo.get('CPC ($)', 0))
    
    # Fix CPC from Google Sheets (SEO Data sheet still has ×100 bug)
    if seo and cpc > 100:
        cpc = cpc / 100
    
    # Live volume check if volume seems low or missing
    if volume <= 50:
        import requests as req_vol
        try:
            vol_payload = [{"keywords": [tag_space], "language_code": "en", "location_code": 2840}]
            vol_resp = req_vol.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                json=vol_payload,
                headers={"Authorization": "Basic aGVsbG9AdmFsbWF4LmFnZW5jeTo1NTUyMWMyNjViOTczMzll"},
                timeout=15
            )
            vol_result = vol_resp.json()
            vol_items = vol_result.get('tasks', [{}])[0].get('result', [])
            if vol_items:
                new_vol = vol_items[0].get('search_volume', 0)
                new_cpc = vol_items[0].get('cpc', 0)
                if new_vol and new_vol > volume:
                    volume = new_vol
                if new_cpc and new_cpc > 0:
                    cpc = new_cpc
        except:
            pass
    
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
                headers={"Authorization": "Basic aGVsbG9AdmFsbWF4LmFnZW5jeTo1NTUyMWMyNjViOTczMzll"},
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
        except Exception as serp_err:
            serp_error = str(serp_err)
    
    if not live_serp and dribbble_gpos is None:
        st.warning("⚠️ Live SERP недоступний (баланс DataForSEO вичерпано). Поповніть на app.dataforseo.com/billing")
    
    # VALMAX position in tag
    valmax_pos = None
    tag_competition = 0
    if not tag_pos_df.empty:
        tag_lower = tag_pos_df['Tag'].str.lower()
        tag_match = tag_pos_df[(tag_lower == tag) | (tag_lower == tag_hyphen) | (tag_lower == tag_space)]
        if not tag_match.empty:
            valmax_pos = int(tag_match.iloc[0].get('Position', 0))
            tag_competition = int(tag_match.iloc[0].get('Total on Page', 0))
    
    # Live competition check — count total shots via Dribbble tag page API
    if tag_competition == 0:
        import requests as req2
        try:
            # Dribbble tag pages load more via ?page=N, check first 4 pages (96 shots)
            total_ids = set()
            for pg in range(1, 5):
                tag_url = f"https://dribbble.com/tags/{tag_hyphen}?page={pg}"
                resp_tag = req2.get(tag_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'en-US,en;q=0.9',
                })
                if resp_tag.status_code == 200:
                    import re
                    page_ids = set(re.findall(r'/shots/(\d+)', resp_tag.text))
                    if not page_ids:
                        break
                    total_ids.update(page_ids)
                else:
                    break
            if total_ids:
                tag_competition = len(total_ids)
        except:
            pass
    if tag_competition == 0 and dribbble_gpos and dribbble_gpos > 0:
        tag_competition = 24
    
    # --- KPIs ---
    if live_serp:
        st.caption("🔴 **LIVE** — дані отримані з Google в реальному часі через DataForSEO ($0.002)")
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔍 Google Volume", f"{volume:,}/mo" if volume else "No data")
    k2.metric("🌐 Dribbble in Google", f"#{dribbble_gpos}" if dribbble_gpos else "Not in top 20")
    k3.metric("🚀 Est. Traffic to Dribbble", f"{est_traffic:,}/mo" if est_traffic else "0")
    if 'mentioned' in str(ai_vis).lower():
        ai_label = "✅ Dribbble in AI"
    elif 'Yes' in str(ai_vis):
        ai_label = "⚠️ AI active"
    else:
        ai_label = "❌ No AI Overview"
    k4.metric("🤖 Google AI Overview", ai_label, help="Чи є AI Overview в Google для цього запиту. Це НЕ ChatGPT — це Google SGE.")
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
    
    # --- SUGGESTED TAGS (via DataForSEO Related Keywords API) ---
    st.divider()
    st.markdown("### 💡 Рекомендовані теги")
    st.caption("Семантично схожі keywords з Google — теги навколо тієї ж теми. Дані: DataForSEO Related Keywords API (~$0.01)")
    
    import requests as req_rel
    try:
        rel_payload = [{
            "keyword": tag_space,
            "language_code": "en",
            "location_code": 2840,
            "limit": 50,
            "include_seed_keyword": False
        }]
        rel_resp = req_rel.post(
            "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live",
            json=rel_payload,
            headers={"Authorization": "Basic aGVsbG9AdmFsbWF4LmFnZW5jeTo1NTUyMWMyNjViOTczMzll"},
            timeout=20
        )
        rel_result = rel_resp.json()
        rel_items = rel_result.get('tasks', [{}])[0].get('result', [{}])[0].get('items', [])
        
        if rel_items:
            rel_rows = []
            for ri in rel_items:
                # keyword_suggestions format
                kw_name = ri.get('keyword', '') or ri.get('keyword_data', {}).get('keyword', '')
                ki = ri.get('keyword_info', {}) or ri.get('keyword_data', {}).get('keyword_info', {})
                if not kw_name:
                    continue
                if kw_name.lower() in (tag, tag_hyphen, tag_space):
                    continue
                vol_r = ki.get('search_volume', 0) or 0
                cpc_r = ki.get('cpc', 0) or 0
                # Score each tag for marketers
                tag_score = 0
                if vol_r >= 10000: tag_score += 40
                elif vol_r >= 1000: tag_score += 30
                elif vol_r >= 100: tag_score += 20
                elif vol_r >= 10: tag_score += 10
                
                if cpc_r >= 10: tag_score += 25
                elif cpc_r >= 5: tag_score += 20
                elif cpc_r >= 1: tag_score += 10
                
                comp = ki.get('competition_level', '')
                if comp == 'LOW': tag_score += 20
                elif comp == 'MEDIUM': tag_score += 10
                
                # Verdict
                if tag_score >= 60: verdict = "🔥 Must use"
                elif tag_score >= 40: verdict = "👍 Good"
                elif tag_score >= 25: verdict = "🤔 Maybe"
                else: verdict = "⚪ Weak"
                
                # Check Dribbble competition (shots count) for this tag
                dribbble_tag = kw_name.replace(' ', '-').lower()
                dribbble_shots = 0
                try:
                    dr_resp = req_rel.get(f"https://dribbble.com/tags/{dribbble_tag}", timeout=5, 
                        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
                    if dr_resp.status_code == 200:
                        import re as re2
                        dr_ids = set(re2.findall(r'/shots/(\d+)', dr_resp.text))
                        dribbble_shots = len(dr_ids)
                        # Adjust score: fewer shots = easier to rank
                        if dribbble_shots < 10: tag_score += 15
                        elif dribbble_shots < 20: tag_score += 5
                except:
                    pass
                
                rel_rows.append({
                    'Tag': kw_name,
                    'Volume/mo': vol_r,
                    'CPC ($)': f"${cpc_r:.2f}",
                    'Ads Comp': comp,
                    'Dribbble': dribbble_shots if dribbble_shots > 0 else '?',
                    'Score': tag_score,
                    'Verdict': verdict,
                })
            if rel_rows:
                rel_df = pd.DataFrame(rel_rows).sort_values('Score', ascending=False)
                
                # HTML table with copy buttons
                html_rel = """
                <style>
                .rel-table { width:100%; border-collapse:collapse; font-family:sans-serif; font-size:13px; }
                .rel-table th { background:#667eea; color:white; padding:6px 10px; text-align:left; }
                .rel-table td { padding:5px 10px; border-bottom:1px solid #eee; }
                .rel-table tr:hover { background:#f0f2ff; }
                .cp-btn { background:none; border:1px solid #ddd; border-radius:4px; cursor:pointer; padding:1px 5px; font-size:11px; }
                .cp-btn:hover { background:#667eea; color:white; }
                </style>
                <script>function cpTag(t,b){navigator.clipboard.writeText(t);b.textContent='✅';setTimeout(()=>b.textContent='📋',800);}</script>
                <table class="rel-table">
                <tr><th>📋</th><th>🏷️ Tag</th><th>📈 Vol</th><th>💰 CPC</th><th>📢 Ads</th><th>🎯 Dribbble</th><th>⭐</th><th>Verdict</th></tr>
                """
                for _, row in rel_df.iterrows():
                    t = str(row['Tag']).replace("'", "\\'")
                    dr_val = row.get('Dribbble', '?')
                    dr_color = '#43e97b' if isinstance(dr_val, int) and dr_val < 15 else ('#ffa726' if isinstance(dr_val, int) and dr_val < 24 else '#f5576c' if isinstance(dr_val, int) else '#999')
                    html_rel += f"""<tr>
                        <td><button class="cp-btn" onclick="cpTag('{t}',this)">📋</button></td>
                        <td>{row['Tag']}</td><td>{row['Volume/mo']:,}</td><td>{row['CPC ($)']}</td>
                        <td>{row.get('Ads Comp','')}</td>
                        <td style="color:{dr_color};font-weight:bold">{dr_val} shots</td>
                        <td>{row['Score']}</td><td>{row['Verdict']}</td>
                    </tr>"""
                html_rel += "</table>"
                st.components.v1.html(html_rel, height=min(400, 40 + len(rel_df)*32), scrolling=True)
                
                # Copyable tag list
                all_tags = ", ".join(rel_df['Tag'].tolist())
                st.text_area("📋 Копіювати всі теги:", all_tags, height=80)
                
                # --- RELATED THEMES from our 297K keywords DB ---
                st.divider()
                st.markdown("### 🎯 Схожі тематики на Dribbble")
                st.caption("Tag pages з нашої бази 297K keywords, згруповані по тематиках. Кожна тема — реальні Dribbble теги з Google трафіком.")
                
                if not kw_df.empty:
                    # Find tag pages that share words with the input
                    input_words = [w for w in tag_space.split() if len(w) > 2]
                    
                    # For each input word, find top tag pages
                    theme_data = {}
                    for word in input_words:
                        matches = kw_df[kw_df['Tag Page'].str.lower().str.contains(word, na=False)]
                        if not matches.empty:
                            # Group by Tag Page
                            for tp in matches['Tag Page'].unique():
                                if tp not in theme_data:
                                    tp_rows = matches[matches['Tag Page'] == tp]
                                    best = tp_rows.sort_values('Est. Traffic/mo', ascending=False).iloc[0]
                                    theme_data[tp] = {
                                        'tag_page': tp,
                                        'top_keyword': best.get('Keyword', ''),
                                        'volume': int(best.get('Volume/mo', 0) or 0),
                                        'traffic': int(best.get('Est. Traffic/mo', 0) or 0),
                                        'position': int(best.get('Google Pos', 0) or 0),
                                    }
                    
                    if theme_data:
                        # Sort by traffic and show top themes
                        sorted_themes = sorted(theme_data.values(), key=lambda x: -x['traffic'])[:15]
                        
                        html_themes = """
                        <style>
                        .theme-table { width:100%; border-collapse:collapse; font-family:sans-serif; font-size:13px; }
                        .theme-table th { background:#764ba2; color:white; padding:6px 10px; text-align:left; }
                        .theme-table td { padding:5px 10px; border-bottom:1px solid #eee; }
                        .theme-table tr:hover { background:#f5f0ff; }
                        .cp2 { background:none; border:1px solid #ddd; border-radius:4px; cursor:pointer; padding:1px 5px; font-size:11px; }
                        .cp2:hover { background:#764ba2; color:white; }
                        </style>
                        <script>function cp2(t,b){navigator.clipboard.writeText(t);b.textContent='✅';setTimeout(()=>b.textContent='📋',800);}</script>
                        <table class="theme-table">
                        <tr><th>📋</th><th>🏷️ Dribbble Tag</th><th>🔑 Top Keyword</th><th>📈 Vol</th><th>🚀 Traffic</th><th>🔍 Pos</th></tr>
                        """
                        for t in sorted_themes:
                            tp_escaped = t['tag_page'].replace("'", "\\'")
                            html_themes += f"""<tr>
                                <td><button class="cp2" onclick="cp2('{tp_escaped}',this)">📋</button></td>
                                <td><b>{t['tag_page']}</b></td>
                                <td>{t['top_keyword']}</td>
                                <td>{t['volume']:,}</td>
                                <td>{t['traffic']:,}</td>
                                <td>#{t['position']}</td>
                            </tr>"""
                        html_themes += "</table>"
                        st.components.v1.html(html_themes, height=min(500, 40 + len(sorted_themes)*32), scrolling=True)
                        
                        all_theme_tags = ", ".join([t['tag_page'] for t in sorted_themes])
                        st.text_area("📋 Копіювати всі теги тематик:", all_theme_tags, height=60)
                    else:
                        st.info("Не знайдено схожих тематик в базі")
                else:
                    st.info("База keywords не завантажена")
            else:
                st.info("Немає схожих keywords")
        else:
            st.info("API не знайшов схожих keywords для цього запиту")
    except Exception as e:
        st.warning(f"⚠️ Related Keywords API недоступний: {e}")

# --- FULL KEYWORDS TABLE ---
st.divider()
st.markdown("### 📊 Повна база: Keywords де Dribbble в Google Top 20")
st.caption(f"Keywords де dribbble.com/tags/ ранжується в Google (US). Дані: DataForSEO Ranked Keywords API")

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
    
    # Build HTML table with copy buttons
    display_rows = display_kw.head(500)
    html_table = """
    <style>
    .kw-table { width:100%; border-collapse:collapse; font-family:sans-serif; font-size:14px; }
    .kw-table th { background:#667eea; color:white; padding:8px 12px; text-align:left; position:sticky; top:0; }
    .kw-table td { padding:6px 12px; border-bottom:1px solid #eee; }
    .kw-table tr:hover { background:#f0f2ff; }
    .copy-btn { background:none; border:1px solid #ddd; border-radius:4px; cursor:pointer; padding:2px 6px; font-size:12px; }
    .copy-btn:hover { background:#667eea; color:white; border-color:#667eea; }
    .copy-btn:active { background:#43e97b; border-color:#43e97b; }
    </style>
    <script>
    function copyTag(text, btn) {
        navigator.clipboard.writeText(text);
        btn.textContent = '✅';
        setTimeout(() => btn.textContent = '📋', 1000);
    }
    </script>
    <div style="max-height:600px; overflow-y:auto;">
    <table class="kw-table">
    <tr><th>📋</th><th>🏷️ Keyword</th><th>📈 Vol/mo</th><th>💰 CPC</th><th>🔍 Pos</th><th>🚀 Traffic</th><th>Tag</th></tr>
    """
    for _, row in display_rows.iterrows():
        kw_val = str(row.get('Keyword', ''))
        vol = int(row.get('Volume/mo', 0) or 0)
        cpc_val = row.get('CPC ($)', '$0.00')
        pos = int(row.get('Google Pos', 0) or 0)
        traf = int(row.get('Est. Traffic/mo', 0) or 0)
        tag_p = str(row.get('Tag Page', ''))
        kw_escaped = kw_val.replace("'", "\\'")
        html_table += f"""<tr>
            <td><button class="copy-btn" onclick="copyTag('{kw_escaped}', this)">📋</button></td>
            <td>{kw_val}</td><td>{vol:,}</td><td>{cpc_val}</td><td>#{pos}</td><td>{traf:,}</td><td>{tag_p}</td>
        </tr>"""
    html_table += "</table></div>"
    
    st.components.v1.html(html_table, height=620, scrolling=True)
    
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
st.caption(f"🔍 Tag Validator | DataForSEO API | {len(kw_df) if not kw_df.empty else '?'} keywords де Dribbble видно в Google | Оновлюється monthly")
