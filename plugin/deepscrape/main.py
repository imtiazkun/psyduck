"""
DeepScrape plugin for Psyduck CLI

Command:
  deepscrape "<TOPIC or SEARCH TERM>" --results=<NUMBER> --platforms="<STRING>" --depth=<0|1|2|3> --timeout=<NUMBER>

Behavior:
  - Uses OpenAI to interpret platforms and depth intent
  - Performs vision-assisted web search collection to gather results
  - Depth controls how much detail to extract from result pages
  - Timeout stops the operation regardless of progress
  - Writes CSV to ./data/deepscrape_<term>.csv
"""

import os
import re
import csv
import time
import asyncio
import base64
from typing import List, Dict, Tuple
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    from openai import OpenAI
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: DeepScrape plugin dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
USER_DATA_DIR = os.path.join(DATA_DIR, 'deepscrape_user')


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(USER_DATA_DIR, exist_ok=True)


def _sanitize_filename(text: str) -> str:
    sanitized = re.sub(r'[^\w\s-]', '', text)
    sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
    return sanitized[:60] if sanitized else 'results'


def _get_openai():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


async def _take_screenshot(page) -> bytes:
    return await page.screenshot()


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode('utf-8')


async def _analyze_platforms_and_plan(term: str, platforms_hint: str, depth: int) -> Dict:
    """Use OpenAI (text) to plan which sources to target and what to extract per depth."""
    client = _get_openai()
    if not client:
        return {
            'targets': [
                {'engine': 'duckduckgo', 'reason': 'generic news/web coverage'}
            ],
            'strategy': 'Fallback: use DuckDuckGo for broad coverage.'
        }
    prompt = f"""
You are planning a scraping strategy.
Topic: {term}
User platform hint: {platforms_hint}
Depth: {depth}

Depth semantics:
0: just collect links
1: collect page title, author/name if visible, key summary
2: also extract comments/discussions if present (e.g. forums/social)
3: also extract comment metadata (author, time, likes) if present

Return JSON with fields:
{{
  "targets": [
    {{"engine": "duckduckgo|google|bing", "reason": "why"}}
  ],
  "strategy": "short guidance"
}}
Only return JSON.
"""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        txt = r.choices[0].message.content
        start = txt.find('{')
        end = txt.rfind('}') + 1
        if start != -1 and end > start:
            import json
            return json.loads(txt[start:end])
    except Exception:
        pass
    return {
        'targets': [
            {'engine': 'duckduckgo', 'reason': 'generic news/web coverage'}
        ],
        'strategy': 'Fallback: use DuckDuckGo for broad coverage.'
    }


def _search_url(engine: str, term: str) -> str:
    q = term.replace(' ', '+')
    e = engine.lower()
    if e == 'google':
        return f"https://www.google.com/search?q={q}&tbm=nws"
    if e == 'bing':
        return f"https://www.bing.com/news/search?q={q}"
    return f"https://duckduckgo.com/?q={q}&t=h_&ia=web"


async def _extract_search_results_via_vision(page, engine: str) -> List[Dict]:
    client = _get_openai()
    if not client:
        return []
    shot = await _take_screenshot(page)
    b64 = _b64(shot)
    if engine.lower() == 'google':
        engine_prompt = 'Analyze this Google search results page.'
    elif engine.lower() == 'bing':
        engine_prompt = 'Analyze this Bing search results page.'
    else:
        engine_prompt = 'Analyze this DuckDuckGo search results page.'
    prompt = f"""
{engine_prompt} Extract visible results as JSON array of objects with:
{{"title": str, "url": str, "excerpt": str, "publisher": str, "date": str, "rank": int}}
Only return the JSON array.
"""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }],
            max_tokens=2500
        )
        content = r.choices[0].message.content
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            import json
            return json.loads(content[start:end])
    except Exception:
        return []
    return []


async def _analyze_page_depth(page, url: str, depth: int) -> Dict:
    """Navigate to a URL and extract data according to depth using vision."""
    data: Dict = {"url": url}
    if depth <= 0:
        return data
    client = _get_openai()
    if not client:
        return data
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        shot = await _take_screenshot(page)
        b64 = _b64(shot)
        prompt = f"""
Extract information from this page screenshot as JSON with keys:
"url", "title", "author", "date", "summary", "has_comments", "comments".
Depth = {depth}:
- If depth >= 1: include title, author if visible, date if visible, and a concise summary.
- If depth >= 2: if comments/discussion are visible, set has_comments=true and include an array of top comments with text.
- If depth >= 3: for each comment also include author, time, and likes if visible.
Only return the JSON object.
URL: {url}
"""
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }],
            max_tokens=2000
        )
        content = r.choices[0].message.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            import json
            parsed = json.loads(content[start:end])
            parsed["url"] = url
            return parsed
    except Exception:
        return data
    return data


def _write_csv(term: str, results: List[Dict]):
    _ensure_dirs()
    out_path = os.path.join(DATA_DIR, f"deepscrape_{_sanitize_filename(term)}.csv")
    # Unified superset of fields; absent ones left blank
    fieldnames = [
        'search_term', 'url', 'title', 'author', 'date', 'publisher', 'rank',
        'excerpt', 'summary', 'has_comments', 'comments', 'scraped_at'
    ]
    now = datetime.utcnow().isoformat()
    new_file = not os.path.exists(out_path)
    with open(out_path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            w.writeheader()
        for r in results:
            w.writerow({
                'search_term': term,
                'url': r.get('url', ''),
                'title': r.get('title', ''),
                'author': r.get('author', ''),
                'date': r.get('date', ''),
                'publisher': r.get('publisher', ''),
                'rank': r.get('rank', ''),
                'excerpt': r.get('excerpt', ''),
                'summary': r.get('summary', ''),
                'has_comments': r.get('has_comments', False),
                'comments': r.get('comments', ''),
                'scraped_at': now,
            })
    return out_path


async def _run(term: str, want_results: int, platforms_hint: str, depth: int, timeout_s: int) -> Tuple[str, int]:
    _ensure_dirs()
    deadline = time.time() + max(1, timeout_s)
    # Plan targets
    plan = await _analyze_platforms_and_plan(term, platforms_hint, depth)
    targets = plan.get('targets', [{'engine': 'duckduckgo'}])

    collected: List[Dict] = []

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        for target in targets:
            if time.time() >= deadline or len(collected) >= want_results:
                break
            engine = target.get('engine', 'duckduckgo')
            url = _search_url(engine, term)
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            fail_rounds = 0
            scrolls = 0
            while len(collected) < want_results and time.time() < deadline and fail_rounds < 3 and scrolls < 8:
                batch = await _extract_search_results_via_vision(page, engine)
                new_in_batch = 0
                for item in batch:
                    if time.time() >= deadline or len(collected) >= want_results:
                        break
                    url = item.get('url')
                    title = item.get('title', '').strip()
                    if not url or not title:
                        continue
                    record = {
                        'url': url,
                        'title': title,
                        'publisher': item.get('publisher', ''),
                        'excerpt': item.get('excerpt', ''),
                        'rank': item.get('rank', ''),
                    }
                    if depth > 0:
                        # Open a temp tab for per-page analysis to not lose position
                        detail = await ctx.new_page()
                        try:
                            detail_data = await _analyze_page_depth(detail, url, depth)
                        finally:
                            await detail.close()
                        record.update(detail_data)
                        # Normalize comments to string for CSV
                        if isinstance(record.get('comments'), list):
                            import json
                            record['comments'] = json.dumps(record['comments'], ensure_ascii=False)
                    collected.append(record)
                    new_in_batch += 1
                    if len(collected) >= want_results:
                        break
                if new_in_batch == 0:
                    fail_rounds += 1
                else:
                    fail_rounds = 0
                if len(collected) < want_results and time.time() < deadline and scrolls < 8:
                    await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
                    await asyncio.sleep(2)
                    scrolls += 1

        await ctx.close()

    out_path = _write_csv(term, collected)
    return out_path, len(collected)


def deepscrape_command(cli_instance, *args):
    from psyduck import Colors

    if not DEPENDENCIES_AVAILABLE:
        print(f"{Colors.RED}Error: DeepScrape dependencies not installed{Colors.END}")
        print(f"{Colors.YELLOW}Please run: pip install -r requirements.txt{Colors.END}")
        print(f"{Colors.YELLOW}Then: python -m playwright install chromium{Colors.END}")
        return

    if len(args) < 1:
        print(f"{Colors.RED}Usage: deepscrape \"<TOPIC or SEARCH TERM>\" --results=<NUMBER> --platforms=\"<STRING>\" --depth=<0|1|2|3> --timeout=<NUMBER>{Colors.END}")
        print(f"{Colors.YELLOW}Example:{Colors.END}")
        print(f"{Colors.YELLOW}  deepscrape \"ocean diversity\" --results=10 --platforms=\"blogs & social media\" --depth=0 --timeout=3600{Colors.END}")
        return

    term = args[0].strip('\"\'')
    want_results = 10
    platforms_hint = ""
    depth = 0
    timeout_s = 900

    for a in args[1:]:
        if a.startswith('--results='):
            try:
                want_results = max(1, int(a.split('=', 1)[1]))
            except Exception:
                pass
        elif a.startswith('--platforms='):
            platforms_hint = a.split('=', 1)[1].strip('\"\'')
        elif a.startswith('--depth='):
            try:
                d = int(a.split('=', 1)[1])
                if d in (0, 1, 2, 3):
                    depth = d
            except Exception:
                pass
        elif a.startswith('--timeout='):
            try:
                timeout_s = max(1, int(a.split('=', 1)[1]))
            except Exception:
                pass

    if not term:
        print(f"{Colors.RED}Error: Topic or search term is required{Colors.END}")
        return

    if not os.getenv('OPENAI_API_KEY'):
        print(f"{Colors.RED}Error: OPENAI_API_KEY not set{Colors.END}")
        print(f"{Colors.YELLOW}Create a .env with OPENAI_API_KEY or export it{Colors.END}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}🧠 DeepScrape (Vision-Enhanced){Colors.END}")
    print(f"{Colors.WHITE}Search Term:{Colors.END} \"{term}\"")
    print(f"{Colors.WHITE}Requested Results:{Colors.END} {want_results}")
    print(f"{Colors.WHITE}Platforms Hint:{Colors.END} {platforms_hint or '-'}")
    print(f"{Colors.White if hasattr(Colors,'White') else Colors.WHITE}Depth:{Colors.END} {depth}")
    print(f"{Colors.WHITE}Timeout (s):{Colors.END} {timeout_s}")

    try:
        out_path, count = asyncio.run(_run(term, want_results, platforms_hint, depth, timeout_s))
        print(f"\n{Colors.GREEN}✓ Collected {count}/{want_results} results. CSV: {out_path}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


PLUGIN_INFO = {
    'name': 'deepscrape',
    'description': 'Depth-configurable cross-platform scraping and analysis',
    'version': '0.1.0',
    'commands': {
        'deepscrape': {
            'handler': deepscrape_command,
            'description': 'Deep scrape across platforms with depth and timeout',
            'usage': 'deepscrape "<TOPIC>" --results=<N> --platforms="<STRING>" --depth=<0|1|2|3> --timeout=<S>'
        }
    }
}


