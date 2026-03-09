"""
VALMAX Dashboard Data Validator
Run after any data update to catch issues before they reach users.
"""
import gspread
from google.oauth2.service_account import Credentials
import json
import os

SHEET_ID = '1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc'
SA_PATH = os.path.join(os.path.dirname(__file__), '..', '.secrets', 'google-service-account.json')
STATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'memory', 'dashboard-health.json')

def get_sheet():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)

def load_health_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}

def save_health_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)

def validate_shots(sh):
    errors = []
    warnings = []
    ws = sh.worksheet('📊 Shots Analytics')
    
    # 1. Row count
    titles = ws.get('C2:C250')
    title_list = [r[0] for r in titles if r and r[0] and r[0].strip()]
    row_count = len(title_list)
    
    state = load_health_state()
    prev_count = state.get('shots_count', 0)
    
    if row_count < 200:
        errors.append(f"🚨 SHOTS: Only {row_count} shots (expected 210+)")
    if prev_count > 0 and row_count < prev_count * 0.8:
        errors.append(f"🚨 SHOTS DROP: Was {prev_count}, now {row_count} — data loss!")
    if prev_count > 0 and row_count < prev_count:
        warnings.append(f"⚠️ SHOTS: Count decreased {prev_count} → {row_count}")
    
    # 2. Engagement sanity
    eng_data = ws.get('H2:H250')
    bad_eng = 0
    for i, r in enumerate(eng_data):
        if r and r[0] and r[0] != '0%':
            try:
                val = float(r[0].replace('%', ''))
                if val > 50:
                    bad_eng += 1
            except:
                pass
    if bad_eng > 0:
        errors.append(f"🚨 ENGAGEMENT: {bad_eng} rows with >50% (impossible)")
    
    # 3. Monthly summary
    monthly = ws.get('M14:M16')
    if not monthly or not monthly[0] or not monthly[0][0]:
        errors.append("🚨 MONTHLY SUMMARY: Missing (M14:R)")
    
    # 4. Profile stats
    profile = ws.get('M1:N2')
    if not profile or len(profile) < 2:
        errors.append("🚨 PROFILE STATS: Missing (M1:N5)")
    
    # 5. Duplicates
    dupes = [t for t in set(title_list) if title_list.count(t) > 1]
    if dupes:
        warnings.append(f"⚠️ DUPLICATES: {dupes[:3]}")
    
    # Save state
    state['shots_count'] = row_count
    state['last_shots_check'] = str(__import__('datetime').datetime.now())
    save_health_state(state)
    
    return errors, warnings, row_count

def validate_leads(sh):
    errors = []
    warnings = []
    ws = sh.worksheet('📋 Project Requests')
    
    data = ws.get('C2:C50')
    lead_count = len([r for r in data if r and r[0] and r[0].strip()])
    
    state = load_health_state()
    prev_count = state.get('leads_count', 0)
    
    if prev_count > 0 and lead_count < prev_count:
        errors.append(f"🚨 LEADS DROP: Was {prev_count}, now {lead_count}")
    
    state['leads_count'] = lead_count
    state['last_leads_check'] = str(__import__('datetime').datetime.now())
    save_health_state(state)
    
    return errors, warnings, lead_count

def validate_keywords(sh):
    errors = []
    warnings = []
    ws = sh.worksheet('🔑 Dribbble Keywords')
    
    # Check row count (should be ~297K)
    # Only check first column count for speed
    try:
        cell = ws.acell('A297000')
        if not cell.value:
            # Check rough count
            cell2 = ws.acell('A250000')
            if not cell2.value:
                warnings.append("⚠️ KEYWORDS: Might have fewer than 250K rows")
    except:
        pass
    
    return errors, warnings, 0

def run_all():
    print("🔍 VALMAX Dashboard Validation")
    print("=" * 40)
    
    sh = get_sheet()
    all_errors = []
    all_warnings = []
    
    # Shots
    errors, warnings, count = validate_shots(sh)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    print(f"📸 Shots: {count} rows {'✅' if not errors else '❌'}")
    
    # Leads  
    errors, warnings, count = validate_leads(sh)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    print(f"📋 Leads: {count} rows {'✅' if not errors else '❌'}")
    
    # Print issues
    for e in all_errors:
        print(f"  {e}")
    for w in all_warnings:
        print(f"  {w}")
    
    if not all_errors and not all_warnings:
        print("✅ All checks passed!")
    
    return all_errors, all_warnings

if __name__ == '__main__':
    run_all()
