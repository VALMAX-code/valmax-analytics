"""Tests for data parsing, normalization, and calculations."""
import pytest
import re
from datetime import datetime


# === BUDGET PARSING ===

def parse_budget(val):
    """Extract numeric value from budget string."""
    if not val or val == "Unknown":
        return 0
    nums = re.findall(r'[\d,]+', str(val).replace(',', ''))
    if nums:
        try:
            return max(int(n) for n in nums)
        except:
            return 0
    return 0


class TestParseBudget:
    def test_simple_number(self):
        assert parse_budget("$6,000") == 6000

    def test_plus_sign(self):
        assert parse_budget("$6,000+") == 6000

    def test_range_takes_max(self):
        assert parse_budget("$2,500-$5,000") == 5000

    def test_unknown(self):
        assert parse_budget("Unknown") == 0

    def test_empty(self):
        assert parse_budget("") == 0
        assert parse_budget(None) == 0

    def test_tilde(self):
        assert parse_budget("~$3,000") == 3000

    def test_no_dollar(self):
        assert parse_budget("5000") == 5000


# === BUDGET NORMALIZATION ===

BUDGET_FIXES = {
    '$800+': '<$1,000', '$800': '<$1,000', '$500': '<$1,000',
    '$2,500': '$2,500-$5,000', '$2500': '$2,500-$5,000',
    '$2,000-$3,000': '$2,500-$5,000',
    '$1000-$15000': '$1,000-$2,500',
    '$1,000-$15,000': '$1,000-$2,500',
    '$3000-$5000': '$2,500-$5,000', '$3,000-$5,000': '$2,500-$5,000',
    '$5000-$10000': '$5,000-$10,000',
    '$10000-$15000': '$10,000-$15,000',
    '$15000+': '$15,000-$20,000',
}

VALID_BUDGETS = {'<$1,000', '$1,000-$2,500', '$2,500-$5,000', '$5,000-$10,000',
                 '$10,000-$15,000', '$15,000-$20,000', '>$20,000', 'Unknown'}


class TestBudgetNormalization:
    def test_all_fixes_map_to_valid(self):
        for orig, fixed in BUDGET_FIXES.items():
            assert fixed in VALID_BUDGETS, f"'{orig}' maps to '{fixed}' which is not valid"

    def test_800_plus(self):
        assert BUDGET_FIXES.get('$800+') == '<$1,000'

    def test_3000_5000(self):
        assert BUDGET_FIXES.get('$3000-$5000') == '$2,500-$5,000'

    def test_valid_budgets_unchanged(self):
        for b in VALID_BUDGETS:
            assert b not in BUDGET_FIXES, f"Valid budget '{b}' should not be in fixes"


# === PROJECT TYPE NORMALIZATION ===

PROJECT_TYPE_FIXES = {'Logo Design': 'Branding', 'Logo design': 'Branding', 'Branding/Design': 'Branding'}


class TestProjectTypeNormalization:
    def test_logo_to_branding(self):
        assert PROJECT_TYPE_FIXES['Logo Design'] == 'Branding'
        assert PROJECT_TYPE_FIXES['Logo design'] == 'Branding'

    def test_branding_design_to_branding(self):
        assert PROJECT_TYPE_FIXES['Branding/Design'] == 'Branding'


# === CRM STATUS VALIDATION ===

VALID_CRM = {'Lost ❌', 'Open 💙', 'Won ✅', 'No matches 🔄'}


class TestCRMValidation:
    def test_valid_statuses(self):
        for s in VALID_CRM:
            assert s in VALID_CRM

    def test_stray_values_invalid(self):
        assert '2' not in VALID_CRM
        assert '' not in VALID_CRM
        assert 'Won' not in VALID_CRM  # missing emoji

    def test_empty_maps_to_no_matches(self):
        val = ''
        result = 'No matches 🔄' if not val.strip() else val
        assert result == 'No matches 🔄'


# === MONTH SORTING ===

_mo = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
       'July':7,'August':8,'September':9,'October':10,'November':11,'December':12,
       'Январь':1,'Февраль':2,'Март':3,'Апрель':4,'Май':5,'Июнь':6,
       'Июль':7,'Август':8,'Сентябрь':9,'Октябрь':10,'Ноябрь':11,'Декабрь':12}


def _month_sort_key(m):
    p = str(m).split()
    if len(p)==2 and p[0] in _mo:
        return int(p[1])*100+_mo.get(p[0],0)
    if len(p)==1 and p[0] in _mo:
        return _mo.get(p[0],0)
    return 0


_ru_to_en_m = {'Январь':'January','Февраль':'February','Март':'March','Апрель':'April',
               'Май':'May','Июнь':'June','Июль':'July','Август':'August',
               'Сентябрь':'September','Октябрь':'October','Ноябрь':'November','Декабрь':'December'}


def _to_en_month(m):
    parts = str(m).split()
    if len(parts) == 2 and parts[0] in _ru_to_en_m:
        return f"{_ru_to_en_m[parts[0]]} {parts[1]}"
    if len(parts) == 1 and parts[0] in _ru_to_en_m:
        return _ru_to_en_m[parts[0]]
    return m


class TestMonthSorting:
    def test_english_month_year(self):
        assert _month_sort_key('January 2026') == 202601
        assert _month_sort_key('December 2025') == 202512

    def test_russian_month_year(self):
        assert _month_sort_key('Март 2026') == 202603

    def test_ordering(self):
        months = ['March 2026', 'January 2026', 'February 2026', 'December 2025']
        sorted_m = sorted(months, key=_month_sort_key)
        assert sorted_m == ['December 2025', 'January 2026', 'February 2026', 'March 2026']

    def test_empty(self):
        assert _month_sort_key('') == 0
        assert _month_sort_key('garbage') == 0


class TestMonthTranslation:
    def test_russian_to_english(self):
        assert _to_en_month('Март 2026') == 'March 2026'
        assert _to_en_month('Январь 2026') == 'January 2026'

    def test_english_unchanged(self):
        assert _to_en_month('March 2026') == 'March 2026'

    def test_all_russian_months(self):
        for ru, en in _ru_to_en_m.items():
            assert _to_en_month(f'{ru} 2026') == f'{en} 2026'


# === PROFITABILITY CALCULATIONS ===

MARGIN_RATE = 0.25


class TestProfitability:
    def test_margin_calculation(self):
        revenue = 6500
        margin = revenue * MARGIN_RATE
        assert margin == 1625.0

    def test_profit_calculation(self):
        revenue = 6500
        costs = 3072
        margin = revenue * MARGIN_RATE
        profit = margin - costs
        assert profit == pytest.approx(-1447.0, abs=1)

    def test_roi_calculation(self):
        revenue = 7100
        costs = 3000
        margin = revenue * MARGIN_RATE
        profit = margin - costs
        roi = (profit / costs * 100) if costs > 0 else 0
        assert roi == pytest.approx(-40.83, abs=1)

    def test_zero_costs_no_division_error(self):
        costs = 0
        roi = (100 / costs * 100) if costs > 0 else 0
        assert roi == 0

    def test_total_costs_equals_sum(self):
        official = 7000
        boosting = 402.83
        designers = 80
        team = 0
        total = official + boosting + designers + team
        assert total == pytest.approx(7482.83, abs=0.01)

    def test_cost_categories_non_negative(self):
        categories = [7000, 402.83, 80, 0]
        for c in categories:
            assert c >= 0


# === DATE PARSING ===

def parse_month(m):
    try: return datetime.strptime(m.strip(), '%B %Y')
    except: return datetime(2020,1,1)


class TestParseMonth:
    def test_valid_month(self):
        d = parse_month('January 2026')
        assert d.year == 2026
        assert d.month == 1

    def test_invalid_month(self):
        d = parse_month('garbage')
        assert d.year == 2020

    def test_all_months(self):
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        for m in months:
            d = parse_month(f'{m} 2026')
            assert d.year == 2026


# === FRESHNESS BADGE ===

def freshness(ts_str):
    from datetime import timezone, timedelta
    CET = timezone(timedelta(hours=1))
    if not ts_str:
        return "⚪", "немає даних", 999
    try:
        ts = datetime.strptime(ts_str[:16], '%Y-%m-%d %H:%M').replace(tzinfo=CET)
    except:
        return "⚪", ts_str, 999
    hours = (datetime.now(CET) - ts).total_seconds() / 3600
    if hours < 6: return "🟢", f"{int(hours)}г тому", hours
    elif hours < 25: return "🟡", f"{int(hours)}г тому", hours
    elif hours < 72: return "🟠", f"{int(hours/24)}д тому", hours
    else: return "🔴", f"{int(hours/24)}д тому", hours


class TestFreshness:
    def test_empty(self):
        emoji, _, _ = freshness("")
        assert emoji == "⚪"

    def test_none(self):
        emoji, _, _ = freshness(None)
        assert emoji == "⚪"

    def test_recent(self):
        from datetime import timezone, timedelta
        CET = timezone(timedelta(hours=1))
        now = datetime.now(CET).strftime('%Y-%m-%d %H:%M')
        emoji, _, hours = freshness(now)
        assert emoji == "🟢"
        assert hours < 1

    def test_invalid_format(self):
        emoji, _, _ = freshness("not-a-date")
        assert emoji == "⚪"


# === KEYWORD SCORING ===

VALMAX_SERVICES = ['web design', 'ui/ux', 'branding', 'logo', 'website', 'mobile app',
                   'landing page', 'e-commerce', 'shopify', 'wordpress', 'webflow']


def calc_kw_score(kw, vol, cpc, pos, traf, tag_p, dr_shots):
    s = 0
    kw_lower = kw.lower()
    if traf >= 5000: s += 25
    elif traf >= 1000: s += 20
    elif traf >= 500: s += 15
    elif traf >= 100: s += 10
    elif traf >= 10: s += 5
    if cpc >= 15: s += 20
    elif cpc >= 5: s += 15
    elif cpc >= 1: s += 10
    elif cpc >= 0.5: s += 5
    if pos <= 3: s += 15
    elif pos <= 5: s += 12
    elif pos <= 10: s += 8
    elif pos <= 15: s += 4
    match_count = sum(1 for svc in VALMAX_SERVICES if svc in kw_lower or svc in tag_p.lower().replace('-', ' '))
    if match_count >= 3: s += 25
    elif match_count >= 2: s += 20
    elif match_count >= 1: s += 15
    if dr_shots is not None:
        if dr_shots < 24: s += 15
        elif dr_shots < 50: s += 10
        elif dr_shots < 80: s += 5
    return min(s, 100)


class TestKeywordScoring:
    def test_perfect_keyword(self):
        score = calc_kw_score('web design landing page branding', 10000, 20, 1, 10000, 'web-design', 10)
        assert score == 100

    def test_zero_keyword(self):
        score = calc_kw_score('random', 0, 0, 100, 0, 'random', 1000)
        assert score == 0

    def test_service_match(self):
        score1 = calc_kw_score('web design', 0, 0, 100, 0, '', None)
        score2 = calc_kw_score('random thing', 0, 0, 100, 0, '', None)
        assert score1 > score2

    def test_capped_at_100(self):
        score = calc_kw_score('web design ui/ux branding logo website mobile app', 10000, 20, 1, 10000, 'web-design', 1)
        assert score <= 100

    def test_low_competition_bonus(self):
        score_low = calc_kw_score('test', 0, 0, 100, 0, '', 10)
        score_high = calc_kw_score('test', 0, 0, 100, 0, '', 200)
        assert score_low > score_high


# === PIPEDRIVE MATCHING ===

def normalize_name(name):
    if not name:
        return ''
    return name.strip().lower().replace('  ', ' ')


class TestPipedriveMatching:
    def test_normalize(self):
        assert normalize_name('  Laszlo Mucsi  ') == 'laszlo mucsi'
        assert normalize_name('') == ''
        assert normalize_name(None) == ''

    def test_exact_match_requires_two_words(self):
        """Single-word names should NOT exact-match to avoid 'Alex' type collisions."""
        # Simulating the matching logic
        person = 'alex'
        lookup = {'alex': True, 'alex chee': True, 'laszlo mucsi': True}
        # Our rule: exact match only for 2+ word names
        matched = person in lookup and len(person.split()) >= 2
        assert matched == False  # "alex" should NOT match

    def test_exact_match_two_words(self):
        person = 'laszlo mucsi'
        lookup = {'laszlo mucsi': True}
        matched = person in lookup and len(person.split()) >= 2
        assert matched == True


# === DATE FORMAT VALIDATION ===

class TestDateFormat:
    def test_valid_iso_date(self):
        val = '2026-03-15'
        assert len(val) == 10 and val[4] == '-' and val[7] == '-'

    def test_invalid_dot_format(self):
        val = '15.03.2026'
        assert not (len(val) == 10 and val[4] == '-' and val[7] == '-')

    def test_dot_to_iso_conversion(self):
        val = '15.03.2026'
        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', val)
        assert m is not None
        fixed = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        assert fixed == '2026-03-15'


# === AUTO-UNRELEVANT COUNTRIES ===

AUTO_UNRELEVANT_COUNTRIES = {
    'india', 'pakistan', 'bangladesh', 'sri lanka', 'nepal',
    'iraq', 'iran', 'egypt', 'somalia', 'yemen', 'syria', 'afghanistan',
    'peru', 'bolivia', 'venezuela', 'paraguay',
    'kenya', 'nigeria',
}
EXCEPTIONS = {'south africa'}


class TestAutoUnrelevant:
    def test_india_unrelevant(self):
        assert 'india' in AUTO_UNRELEVANT_COUNTRIES

    def test_south_africa_exception(self):
        assert 'south africa' not in AUTO_UNRELEVANT_COUNTRIES

    def test_usa_not_unrelevant(self):
        assert 'usa' not in AUTO_UNRELEVANT_COUNTRIES
        assert 'united states' not in AUTO_UNRELEVANT_COUNTRIES

    def test_germany_not_unrelevant(self):
        assert 'germany' not in AUTO_UNRELEVANT_COUNTRIES
