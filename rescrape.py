#!/usr/bin/env python3
"""
Rescrape ALL VALMAX Dribbble shots via Playwright CDP.
Gets REAL data from Shot Details popover: date, views, likes, saves, comments, tags.
Safety: 5-7 sec delays, 60 sec pause every 30 shots.
"""

import json, time, random, re, sys
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

SA_KEY = '/Users/openzlo/.openclaw/workspace/.secrets/google-service-account.json'
SHEET_ID = '1680mdS7XHHB6ax4auS2XHGLXUFa1omqTEfn8hMmSoHc'
PROGRESS_FILE = '/Users/openzlo/.openclaw/workspace/memory/shots-rescrape-real.json'
CDP_URL = 'http://localhost:18800'

def get_sheet_urls():
    creds = Credentials.from_service_account_file(SA_KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(SHEET_ID).worksheet('📊 Shots Analytics')
    data = ws.get('A2:K220')
    shots = []
    for i, row in enumerate(data):
        if row and len(row) >= 11 and row[10] and row[10].strip().startswith('http'):
            shots.append({'row': i + 2, 'url': row[10].strip(), 'title': row[2] if len(row) > 2 else ''})
    return shots

def scrape_shot(page, url, attempt=1):
    """Navigate to shot, click Detail actions, extract real data."""
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        time.sleep(2)
        
        # Check for rate limit
        if 'rate limited' in page.title().lower():
            return {'error': 'RATE_LIMITED'}
        if 'session/new' in page.url:
            return {'error': 'LOGGED_OUT'}
        
        # Click Detail actions button
        detail_btn = page.locator('button:has-text("Detail actions")')
        if detail_btn.count() > 0:
            detail_btn.click()
            time.sleep(1.5)
        else:
            return {'error': 'NO_DETAIL_BUTTON'}
        
        # Extract data from popover
        text = page.evaluate('document.body.innerText')
        
        # Date
        date_match = re.search(r'Posted\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})', text)
        date_str = date_match.group(1) if date_match else ''
        
        # Views
        views_match = re.search(r'Views\s+([\d,]+)', text)
        views = int(views_match.group(1).replace(',', '')) if views_match else 0
        
        # Likes
        likes_match = re.search(r'Likes\s+([\d,]+)', text)
        likes = int(likes_match.group(1).replace(',', '')) if likes_match else 0
        
        # Saves
        saves_match = re.search(r'Saves\s+([\d,]+)', text)
        saves = int(saves_match.group(1).replace(',', '')) if saves_match else 0
        
        # Comments
        comments_match = re.search(r'Comments\s+([\d,]+)', text)
        comments = int(comments_match.group(1).replace(',', '')) if comments_match else 0
        
        # Tags from links
        tags = page.evaluate('''
            Array.from(document.querySelectorAll('a[href*="/tags/"]'))
                .map(a => a.textContent.trim())
                .filter(t => t.length > 0 && t.length < 50)
        ''')
        
        # Title from h1
        title = page.evaluate('document.querySelector("h1")?.textContent?.trim() || ""')
        
        return {
            'title': title,
            'date': date_str,
            'views': views,
            'likes': likes,
            'saves': saves,
            'comments': comments,
            'tags': tags,
            'tag_count': len(tags)
        }
    except Exception as e:
        if attempt < 2:
            time.sleep(5)
            return scrape_shot(page, url, attempt + 1)
        return {'error': str(e)}

def date_to_month(date_str):
    """Convert 'Mar 6, 2026' to 'March 2026'"""
    month_map = {
        'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
        'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August',
        'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
    }
    match = re.match(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+(\d{4})', date_str)
    if match:
        return f"{month_map[match.group(1)]} {match.group(2)}"
    return ''

def date_to_iso(date_str):
    """Convert 'Mar 6, 2026' to '2026-03-06'"""
    from datetime import datetime
    try:
        dt = datetime.strptime(date_str.replace(',', ''), '%b %d %Y')
        return dt.strftime('%Y-%m-%d')
    except:
        return ''

def main():
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    print("Loading shot URLs from Google Sheet...")
    shots = get_sheet_urls()
    print(f"Found {len(shots)} shots")
    
    # Load previous progress
    results = []
    try:
        with open(PROGRESS_FILE) as f:
            results = json.load(f)
        print(f"Resuming from {len(results)} previously scraped shots")
    except:
        pass
    
    done_urls = {r['url'] for r in results}
    remaining = [s for s in shots if s['url'] not in done_urls]
    
    if start_from > 0:
        remaining = remaining[start_from:]
    
    print(f"Remaining: {len(remaining)} shots to scrape")
    
    print("Connecting to browser via CDP...")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.new_page()
        
        for i, shot in enumerate(remaining):
            print(f"\n[{len(results)+1}/{len(shots)}] {shot['title'][:50]}...")
            
            data = scrape_shot(page, shot['url'])
            
            if data.get('error') == 'RATE_LIMITED':
                print("🚨 RATE LIMITED! Stopping immediately.")
                break
            if data.get('error') == 'LOGGED_OUT':
                print("🚨 LOGGED OUT! Stopping immediately.")
                break
            
            if 'error' in data:
                print(f"  ⚠️ Error: {data['error']}")
                data['url'] = shot['url']
                data['row'] = shot['row']
            else:
                data['url'] = shot['url']
                data['row'] = shot['row']
                eng = (data['likes'] + data['saves']) / data['views'] * 100 if data['views'] > 0 else 0
                data['engagement'] = f"{eng:.2f}%"
                data['month'] = date_to_month(data['date'])
                data['date_iso'] = date_to_iso(data['date'])
                print(f"  ✅ {data['date']} | Views: {data['views']:,} | Likes: {data['likes']} | Tags: {data['tag_count']}")
            
            results.append(data)
            
            # Save progress every 10 shots
            if len(results) % 10 == 0:
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"  💾 Progress saved: {len(results)} shots")
            
            # Pause every 30 shots
            if (i + 1) % 30 == 0:
                print(f"  ⏸️ 60 second safety pause...")
                time.sleep(60)
            else:
                delay = random.uniform(5, 7)
                time.sleep(delay)
        
        page.close()
    
    # Final save
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Stats
    successful = [r for r in results if 'error' not in r]
    print(f"\n{'='*50}")
    print(f"DONE: {len(successful)}/{len(shots)} shots scraped successfully")
    if successful:
        max_v = max(r['views'] for r in successful)
        print(f"Max views: {max_v:,}")
        print(f"Total views: {sum(r['views'] for r in successful):,}")
    
    return results

if __name__ == '__main__':
    main()
