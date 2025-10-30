"""
Webscrape plugin for Psyduck CLI
Scrapes search results from DuckDuckGo, Google, or Bing using vision AI

Command:
  webscrape "<SEARCH TERM>" <LIMIT> --location=<duckduckgo|google|bing>

Behavior:
  - Launches Chromium with a persistent profile
  - Navigates to selected search engine
  - Uses OpenAI Vision to analyze search results
  - Extracts headlines, links, excerpts, publisher names, dates
  - Saves results to CSV in ./data/webscrape_<engine>_<term>.csv
"""

import os
import csv
import asyncio
import random
import base64
import io
import re
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    from openai import OpenAI
    from PIL import Image
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Webscrape plugin dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
USER_DATA_DIR = os.path.join(DATA_DIR, 'webscrape_user')


def get_openai_client():
    if not DEPENDENCIES_AVAILABLE:
        return None
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(USER_DATA_DIR, exist_ok=True)


def _sanitize_filename(text: str) -> str:
    """Sanitize text for use in filename"""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^\w\s-]', '', text)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized[:50]  # Limit length


def _get_search_url(search_term: str, engine: str) -> str:
    """Generate search URL for the specified engine"""
    encoded_term = search_term.replace(' ', '+')
    
    if engine.lower() == 'duckduckgo':
        return f"https://duckduckgo.com/?q={encoded_term}&t=h_&ia=web"
    elif engine.lower() == 'google':
        return f"https://www.google.com/search?q={encoded_term}&tbm=nws"
    elif engine.lower() == 'bing':
        return f"https://www.bing.com/news/search?q={encoded_term}"
    else:
        raise ValueError(f"Unsupported search engine: {engine}")


async def _take_screenshot(page, element=None) -> bytes:
    """Take screenshot of page or specific element"""
    if element:
        return await element.screenshot()
    return await page.screenshot()


def _encode_image(image_bytes: bytes) -> str:
    """Encode image bytes to base64 for OpenAI API"""
    return base64.b64encode(image_bytes).decode('utf-8')


async def _analyze_search_results(page, engine: str) -> Tuple[List[Dict], int, float]:
    """Use OpenAI Vision to analyze search results"""
    screenshot = await _take_screenshot(page)
    base64_image = _encode_image(screenshot)
    
    client = get_openai_client()
    if not client:
        print("OpenAI client not available")
        return [], 0, 0.0
    
    # Different prompts for different search engines
    if engine.lower() == 'duckduckgo':
        prompt = """Analyze this DuckDuckGo search results page. Extract all visible search results and return a JSON array with this structure:

[
  {
    "title": "article headline",
    "url": "full URL if visible",
    "excerpt": "description/snippet text",
    "publisher": "publisher name if visible",
    "date": "publication date if visible",
    "rank": 1
  }
]

Focus on:
- Main search results (not ads or related searches)
- Extract full headlines and descriptions
- Include URLs when visible
- Note publisher names and dates
- Number results by rank (1, 2, 3, etc.)
- Return only the JSON array, no other text"""
    
    elif engine.lower() == 'google':
        prompt = """Analyze this Google search results page. Extract all visible search results and return a JSON array with this structure:

[
  {
    "title": "article headline",
    "url": "full URL if visible", 
    "excerpt": "description/snippet text",
    "publisher": "publisher name if visible",
    "date": "publication date if visible",
    "rank": 1
  }
]

Focus on:
- Main search results (not ads or related searches)
- Extract full headlines and descriptions
- Include URLs when visible
- Note publisher names and dates
- Number results by rank (1, 2, 3, etc.)
- Return only the JSON array, no other text"""
    
    else:  # Bing
        prompt = """Analyze this Bing search results page. Extract all visible search results and return a JSON array with this structure:

[
  {
    "title": "article headline",
    "url": "full URL if visible",
    "excerpt": "description/snippet text", 
    "publisher": "publisher name if visible",
    "date": "publication date if visible",
    "rank": 1
  }
]

Focus on:
- Main search results (not ads or related searches)
- Extract full headlines and descriptions
- Include URLs when visible
- Note publisher names and dates
- Number results by rank (1, 2, 3, etc.)
- Return only the JSON array, no other text"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=3000
        )
        
        # Track token usage
        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = tokens_used * 0.00015  # GPT-4o-mini pricing
        
        print(f"[webscrape] Token usage - Prompt: {usage.prompt_tokens if usage else 0}, Completion: {usage.completion_tokens if usage else 0}, Total: {tokens_used}")
        print(f"[webscrape] Estimated cost: ${cost:.4f} (GPT-4o-mini vision)")
        
        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            results = json.loads(json_str)
            return results, tokens_used, cost
        return [], tokens_used, cost
        
    except Exception as e:
        print(f"Vision analysis error: {e}")
        return [], 0, 0.0


async def _scroll_and_collect_results(page, max_results: int, engine: str, search_term: str) -> List[Dict[str, str]]:
    """Scroll through search results and collect data"""
    collected: List[Dict[str, str]] = []
    seen_urls = set()
    fail_rounds = 0
    scroll_count = 0
    max_scrolls = 10  # Prevent infinite scrolling
    
    # Token usage tracking
    total_tokens = 0
    total_cost = 0.0

    while len(collected) < max_results and fail_rounds < 3 and scroll_count < max_scrolls:
        print(f"\n[webscrape] Analyzing {engine} results... (collected: {len(collected)}/{max_results})")
        
        # Analyze current viewport with vision model
        results, tokens_used, cost = await _analyze_search_results(page, engine)
        total_tokens += tokens_used
        total_cost += cost
        
        print(f"[webscrape] Running totals - Tokens: {total_tokens:,}, Cost: ${total_cost:.4f}")
        
        new_count = 0
        for result in results:
            url = result.get('url', '')
            title = result.get('title', '').strip()
            
            # Skip if no title or already seen
            if not title or url in seen_urls:
                continue
                
            seen_urls.add(url)
            
            # Random delay between processing results
            delay = random.uniform(2, 5)
            print(f"[webscrape] Processing result {len(collected)+1}, waiting {delay:.1f}s...")
            await asyncio.sleep(delay)
            
            # Prepare data for CSV
            row_data = {
                'search_term': search_term,
                'engine': engine,
                'rank': result.get('rank', len(collected) + 1),
                'title': title,
                'url': url,
                'excerpt': result.get('excerpt', ''),
                'publisher': result.get('publisher', ''),
                'date': result.get('date', ''),
                'scraped_at': datetime.utcnow().isoformat()
            }
            
            collected.append(row_data)
            new_count += 1
            print(f"[webscrape] ✓ Collected: {title[:50]}...")
            
            if len(collected) >= max_results:
                break
        
        if new_count == 0:
            fail_rounds += 1
            print(f"[webscrape] No new results found (fail round {fail_rounds}/3)")
        else:
            fail_rounds = 0
            
        # Scroll to load more content
        if len(collected) < max_results and scroll_count < max_scrolls:
            print(f"[webscrape] Scrolling to load more results...")
            await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
            await asyncio.sleep(random.uniform(2, 4))
            scroll_count += 1

    # Print total usage summary
    print(f"\n[webscrape] 📊 Total Token Usage Summary:")
    print(f"[webscrape] Total tokens used: {total_tokens:,}")
    print(f"[webscrape] Total estimated cost: ${total_cost:.4f}")
    print(f"[webscrape] Average cost per result: ${total_cost/max(1, len(collected)):.4f}")

    return collected


def _write_csv(search_term: str, engine: str, results: List[Dict[str, str]]):
    """Write results to CSV file"""
    _ensure_dirs()
    sanitized_term = _sanitize_filename(search_term)
    out_path = os.path.join(DATA_DIR, f"webscrape_{engine}_{sanitized_term}.csv")
    
    fieldnames = [
        'search_term', 'engine', 'rank', 'title', 'url', 
        'excerpt', 'publisher', 'date', 'scraped_at'
    ]
    
    now = datetime.utcnow().isoformat()
    new_file = not os.path.exists(out_path)
    
    with open(out_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            writer.writeheader()
        for r in results:
            row = {
                'search_term': search_term,
                'engine': engine,
                'rank': r.get('rank', ''),
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'excerpt': r.get('excerpt', ''),
                'publisher': r.get('publisher', ''),
                'date': r.get('date', ''),
                'scraped_at': now
            }
            writer.writerow(row)
    return out_path


async def _run(search_term: str, max_results: int, engine: str):
    """Main scraping function"""
    _ensure_dirs()
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()
        
        # Generate search URL
        search_url = _get_search_url(search_term, engine)
        print(f"\n[webscrape] Navigating to: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Collect results
        results = await _scroll_and_collect_results(page, max_results, engine, search_term)
        out_path = _write_csv(search_term, engine, results)

        await ctx.close()

    return out_path, len(results)


def webscrape_command(cli_instance, *args):
    from psyduck import Colors

    if not DEPENDENCIES_AVAILABLE:
        print(f"{Colors.RED}Error: Webscrape plugin dependencies not installed{Colors.END}")
        print(f"{Colors.YELLOW}Please run: pip install -r requirements.txt{Colors.END}")
        print(f"{Colors.YELLOW}Then: python -m playwright install chromium{Colors.END}")
        return

    # Parse arguments
    if len(args) < 1:
        print(f"{Colors.RED}Usage: webscrape \"<SEARCH TERM>\" <LIMIT> --location=<duckduckgo|google|bing>{Colors.END}")
        print(f"{Colors.YELLOW}Examples:{Colors.END}")
        print(f"{Colors.YELLOW}  webscrape \"AI is getting scary\" 10 --location=duckduckgo{Colors.END}")
        print(f"{Colors.YELLOW}  webscrape \"climate change\" 20 --location=google{Colors.END}")
        print(f"{Colors.YELLOW}  webscrape \"tech news\" 15 --location=bing{Colors.END}")
        return

    # Parse arguments manually
    search_term = args[0].strip('"\'')  # Remove quotes
    limit = '10'
    location = 'duckduckgo'
    
    # Parse remaining arguments
    for i, arg in enumerate(args[1:], 1):
        if arg.startswith('--location='):
            location = arg.split('=', 1)[1]
        elif arg.isdigit():
            limit = arg
        elif not arg.startswith('--'):
            # If it's not a flag and not a number, treat as search term continuation
            search_term += ' ' + arg.strip('"\'')
    
    if not search_term:
        print(f"{Colors.RED}Error: Search term is required{Colors.END}")
        return

    # Validate engine
    valid_engines = ['duckduckgo', 'google', 'bing']
    if location.lower() not in valid_engines:
        print(f"{Colors.RED}Error: Invalid search engine '{location}'{Colors.END}")
        print(f"{Colors.YELLOW}Valid options: {', '.join(valid_engines)}{Colors.END}")
        return

    try:
        max_results = int(limit)
    except Exception:
        max_results = 10

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print(f"{Colors.RED}Error: OPENAI_API_KEY environment variable not set{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OpenAI API key in .env file or environment{Colors.END}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}🔍 Web Search Scraper (Vision-Enhanced){Colors.END}")
    print(f"{Colors.WHITE}Search Term:{Colors.END} \"{search_term}\"")
    print(f"{Colors.WHITE}Engine:{Colors.END} {location.title()}")
    print(f"{Colors.WHITE}Limit:{Colors.END} {max_results}")
    print(f"{Colors.MAGENTA}Features:{Colors.END} Vision analysis, multi-engine support, structured data extraction")

    try:
        out_path, count = asyncio.run(_run(search_term, max_results, location))
        print(f"\n{Colors.GREEN}✓ Scraped {count} results from {location.title()}. CSV: {out_path}{Colors.END}")
        print(f"{Colors.CYAN}Columns: search_term, engine, rank, title, url, excerpt, publisher, date, scraped_at{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


PLUGIN_INFO = {
    'name': 'webscrape',
    'description': 'Web search result scraping via Playwright and vision AI',
    'version': '0.1.0',
    'commands': {
        'webscrape': {
            'handler': webscrape_command,
            'description': 'Scrape search results from DuckDuckGo, Google, or Bing',
            'usage': 'webscrape "<SEARCH TERM>" <LIMIT> --location=<duckduckgo|google|bing>'
        }
    }
}
