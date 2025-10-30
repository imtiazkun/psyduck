"""
Facebook hashtag scraper plugin using Playwright with OpenAI Vision.

Command:
  fb-scrape <TAG> [max_posts]

Behavior:
  - Launches Chromium with a persistent profile in ./data/fb_user
  - Opens Facebook and prompts user to log in on first run
  - Navigates to https://web.facebook.com/hashtag/<TAG>
  - Uses OpenAI Vision to identify post elements and extract data
  - Extracts text posts, author names, likes, and top comments
  - Skips media-only posts, extracts text from images via OCR
  - Saves results to CSV in ./data/fb_<TAG>_posts.csv
"""

import os
import csv
import asyncio
import random
import base64
import io
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    from openai import OpenAI
    from PIL import Image
    import pytesseract
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Facebook plugin dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
USER_DATA_DIR = os.path.join(DATA_DIR, 'fb_user')

# Initialize OpenAI client lazily (only when needed)
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


async def _take_screenshot(page, element=None) -> bytes:
    """Take screenshot of page or specific element"""
    if element:
        return await element.screenshot()
    return await page.screenshot()


def _encode_image(image_bytes: bytes) -> str:
    """Encode image bytes to base64 for OpenAI API"""
    return base64.b64encode(image_bytes).decode('utf-8')


async def _analyze_page_with_vision(page) -> Tuple[List[Dict], int, float]:
    """Use OpenAI Vision to analyze the current page and identify posts"""
    screenshot = await _take_screenshot(page)
    base64_image = _encode_image(screenshot)
    
    client = get_openai_client()
    if not client:
        print("OpenAI client not available")
        return [], 0, 0.0
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this Facebook hashtag page screenshot. Identify all visible posts and return a JSON array with this structure for each post:

{
  "post_id": "unique_identifier",
  "has_text_content": true/false,
  "author_name": "author name if visible",
  "post_text": "main text content (full text if 'See more' is visible)",
  "likes_count": "number or text like '1.2K'",
  "comments_count": "number or text",
  "has_media": true/false,
  "media_type": "image/video/none",
  "image_text": "text extracted from images if any",
  "has_see_more": true/false,
  "is_hashtag_only": true/false,
  "top_comments": [
    {
      "author": "commenter name",
      "text": "comment text",
      "likes": "number or text"
    }
  ]
}

Rules:
- Focus on posts with substantial text content (not just hashtags)
- Skip posts that are only hashtags (is_hashtag_only: true)
- If you see 'See more' or 'See less' buttons, set has_see_more: true
- Extract full text content, not truncated versions
- Skip posts that are only images/videos without meaningful text
- If you see 'View more comments' buttons, note them
- Return only the JSON array, no other text"""
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
            max_tokens=4000
        )
        
        # Track token usage
        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = tokens_used * 0.00015  # GPT-4o-mini vision pricing: $0.00015 per 1K tokens
        
        print(f"[fb] Token usage - Prompt: {usage.prompt_tokens if usage else 0}, Completion: {usage.completion_tokens if usage else 0}, Total: {tokens_used}")
        print(f"[fb] Estimated cost: ${cost:.4f} (GPT-4o-mini vision)")
        
        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            posts_data = json.loads(json_str)
            return posts_data, tokens_used, cost
        return [], tokens_used, cost
        
    except Exception as e:
        print(f"Vision analysis error: {e}")
        return [], 0, 0.0


async def _extract_text_from_image(image_element) -> str:
    """Extract text from image using OCR"""
    try:
        image_bytes = await image_element.screenshot()
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, config='--psm 6')
        return text.strip()
    except Exception as e:
        print(f"OCR error: {e}")
        return ""


async def _expand_text_for_post(post_element):
    """Click 'See more' buttons to expand full text"""
    try:
        # Look for various text expansion buttons
        text_buttons = [
            'div[role="button"]:has-text("See more")',
            'div[role="button"]:has-text("See less")',
            'span:has-text("See more")',
            'span:has-text("See less")',
            'a:has-text("See more")',
            'a:has-text("See less")',
            '[data-testid*="see-more"]',
            '[aria-label*="See more"]'
        ]
        
        for selector in text_buttons:
            buttons = await post_element.query_selector_all(selector)
            for btn in buttons[:2]:  # Limit to first 2 buttons
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        break  # Only click one "See more" per post
                except Exception:
                    pass
    except Exception:
        pass


async def _expand_comments_for_post(post_element):
    """Click 'View more comments' buttons within a post"""
    try:
        # Look for various comment expansion buttons
        comment_buttons = [
            'div[role="button"]:has-text("View more comments")',
            'div[role="button"]:has-text("View previous comments")',
            'div[role="button"]:has-text("View")',
            'span:has-text("View more comments")',
            'span:has-text("View")'
        ]
        
        for selector in comment_buttons:
            buttons = await post_element.query_selector_all(selector)
            for btn in buttons[:3]:  # Limit to first 3 buttons
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(random.uniform(1, 2))
                except Exception:
                    pass
    except Exception:
        pass


async def _get_post_element_by_id(page, post_id: str):
    """Find post element by ID or other identifier"""
    try:
        # Try various selectors to find the post
        selectors = [
            f'[data-ft*="{post_id}"]',
            f'[id*="{post_id}"]',
            f'[data-testid*="{post_id}"]'
        ]
        
        for selector in selectors:
            element = await page.query_selector(selector)
            if element:
                return element
        return None
    except Exception:
        return None


async def _analyze_post_comments(post_element, post_id: str) -> List[Dict]:
    """Analyze a specific post to extract detailed comments using vision"""
    try:
        # Take screenshot of just this post
        post_screenshot = await _take_screenshot(post_element)
        base64_image = _encode_image(post_screenshot)
        
        client = get_openai_client()
        if not client:
            print("OpenAI client not available for comment analysis")
            return []
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this Facebook post screenshot and extract the top 5 most engaged comments. Return a JSON array with this structure:

[
  {
    "author": "commenter name",
    "text": "full comment text",
    "likes": "number or text like '5' or '1.2K'",
    "replies": "number of replies if visible",
    "time": "time posted if visible like '2h' or '1d'"
  }
]

Focus on:
- Comments with the most likes/reactions
- Comments that are substantial (not just emojis or single words)
- Extract full comment text, not truncated
- Include author names and engagement metrics
- Return only the JSON array, no other text"""
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
            max_tokens=2000
        )
        
        # Track token usage for comment analysis
        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = tokens_used * 0.00015
        
        print(f"[fb] Comment analysis tokens: {tokens_used}, cost: ${cost:.4f}")
        
        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            comments = json.loads(json_str)
            print(f"[fb] Found {len(comments)} detailed comments for post {post_id}")
            return comments
        return []
        
    except Exception as e:
        print(f"[fb] Error analyzing comments for post {post_id}: {e}")
        return []


async def _login_if_needed(page):
    # If not logged in, Facebook shows a login form
    try:
        await page.wait_for_selector('input[name="email"], input[id="email"]', timeout=3000)
        print("\n[fb] Please log in in the opened browser. Press Enter here when done...")
        input()
    except PlaywrightTimeoutError:
        # Likely already logged in
        pass


async def _scroll_and_collect_with_vision(page, max_posts: int) -> List[Dict[str, str]]:
    """Use vision model to analyze posts and collect data"""
    collected: List[Dict[str, str]] = []
    seen_ids = set()
    fail_rounds = 0
    scroll_count = 0
    max_scrolls = 20  # Prevent infinite scrolling
    
    # Token usage tracking
    total_tokens = 0
    total_cost = 0.0

    while len(collected) < max_posts and fail_rounds < 5 and scroll_count < max_scrolls:
        print(f"\n[fb] Analyzing page with vision model... (collected: {len(collected)}/{max_posts})")
        
        # Analyze current viewport with vision model
        posts_data, tokens_used, cost = await _analyze_page_with_vision(page)
        total_tokens += tokens_used
        total_cost += cost
        
        print(f"[fb] Running totals - Tokens: {total_tokens:,}, Cost: ${total_cost:.4f}")
        
        new_count = 0
        for post_data in posts_data:
            post_id = post_data.get('post_id', f'post_{len(collected)}')
            
            if post_id in seen_ids:
                continue
                
            seen_ids.add(post_id)
            
            # Skip hashtag-only posts
            if post_data.get('is_hashtag_only', False):
                print(f"[fb] Skipping hashtag-only post: {post_id}")
                continue
                
            # Skip media-only posts without text
            if not post_data.get('has_text_content', False):
                print(f"[fb] Skipping media-only post: {post_id}")
                continue
                
            # Skip if no substantial text content
            post_text = post_data.get('post_text', '').strip()
            if len(post_text) < 10:  # Minimum text length
                print(f"[fb] Skipping post with insufficient text: {post_id}")
                continue
            
            # Random delay between processing posts
            delay = random.uniform(5, 15)
            print(f"[fb] Processing post {len(collected)+1}, waiting {delay:.1f}s...")
            await asyncio.sleep(delay)
            
            # Try to find and expand text/comments for this specific post
            try:
                post_element = await _get_post_element_by_id(page, post_id)
                if post_element:
                    # First expand "See more" to get full text
                    if post_data.get('has_see_more', False):
                        print(f"[fb] Expanding 'See more' for post: {post_id}")
                        await _expand_text_for_post(post_element)
                        await asyncio.sleep(2)
                    
                    # Then expand comments
                    await _expand_comments_for_post(post_element)
                    await asyncio.sleep(2)
                    
                    # Analyze this specific post for detailed comments
                    print(f"[fb] Analyzing top 5 comments for post: {post_id}")
                    detailed_comments = await _analyze_post_comments(post_element, post_id)
                    
                    # Re-analyze this specific post for updated content
                    if post_data.get('has_see_more', False):
                        print(f"[fb] Re-analyzing post after expansion: {post_id}")
                        post_screenshot = await _take_screenshot(post_element)
                        # Could re-analyze just this post here if needed
            except Exception as e:
                print(f"[fb] Error expanding post {post_id}: {e}")
                detailed_comments = []
            
            # Use detailed comments if available, otherwise fall back to initial analysis
            if detailed_comments:
                top_comments = detailed_comments[:5]  # Top 5 comments
            else:
                top_comments = post_data.get('top_comments', [])[:5]
            
            comments_text = []
            comment_authors = []
            comment_likes = []
            comment_replies = []
            comment_times = []
            
            for comment in top_comments:
                author = comment.get('author', 'Unknown')
                text = comment.get('text', '').strip()
                likes = comment.get('likes', '0')
                replies = comment.get('replies', '0')
                time = comment.get('time', '')
                
                if text:
                    comments_text.append(text)
                    comment_authors.append(author)
                    comment_likes.append(likes)
                    comment_replies.append(replies)
                    comment_times.append(time)
            
            # Prepare data for CSV
            row_data = {
                'post_id': post_id,
                'author_name': post_data.get('author_name', 'Unknown'),
                'post_text': post_text,
                'likes_count': post_data.get('likes_count', '0'),
                'comments_count': post_data.get('comments_count', '0'),
                'has_media': post_data.get('has_media', False),
                'media_type': post_data.get('media_type', 'none'),
                'image_text': post_data.get('image_text', ''),
                'has_see_more': post_data.get('has_see_more', False),
                'is_hashtag_only': post_data.get('is_hashtag_only', False),
                'top_comments': ' ||| '.join(comments_text),
                'comment_authors': ' ||| '.join(comment_authors),
                'comment_likes': ' ||| '.join(comment_likes),
                'comment_replies': ' ||| '.join(comment_replies),
                'comment_times': ' ||| '.join(comment_times)
            }
            
            collected.append(row_data)
            new_count += 1
            print(f"[fb] ✓ Collected post from {row_data['author_name']}: {post_text[:50]}...")
            
            if len(collected) >= max_posts:
                break
        
        if new_count == 0:
            fail_rounds += 1
            print(f"[fb] No new posts found (fail round {fail_rounds}/5)")
        else:
            fail_rounds = 0
            
        # Scroll to load more content
        if len(collected) < max_posts and scroll_count < max_scrolls:
            print(f"[fb] Scrolling to load more posts...")
            await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
            await asyncio.sleep(random.uniform(3, 6))
            scroll_count += 1

    # Print total usage summary
    print(f"\n[fb] 📊 Total Token Usage Summary:")
    print(f"[fb] Total tokens used: {total_tokens:,}")
    print(f"[fb] Total estimated cost: ${total_cost:.4f}")
    print(f"[fb] Average cost per post: ${total_cost/max(1, len(collected)):.4f}")

    return collected


def _write_csv(tag: str, rows: List[Dict[str, str]]):
    _ensure_dirs()
    out_path = os.path.join(DATA_DIR, f"fb_{tag}_posts.csv")
    fieldnames = [
        'tag', 'scraped_at', 'post_id', 'author_name', 'post_text', 
        'likes_count', 'comments_count', 'has_media', 'media_type', 
        'image_text', 'has_see_more', 'is_hashtag_only', 
        'top_comments', 'comment_authors', 'comment_likes', 'comment_replies', 'comment_times'
    ]
    now = datetime.utcnow().isoformat()
    new_file = not os.path.exists(out_path)
    with open(out_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            writer.writeheader()
        for r in rows:
            row = {
                'tag': tag,
                'scraped_at': now,
                'post_id': r.get('post_id', ''),
                'author_name': r.get('author_name', ''),
                'post_text': r.get('post_text', ''),
                'likes_count': r.get('likes_count', ''),
                'comments_count': r.get('comments_count', ''),
                'has_media': r.get('has_media', False),
                'media_type': r.get('media_type', ''),
                'image_text': r.get('image_text', ''),
                'has_see_more': r.get('has_see_more', False),
                'is_hashtag_only': r.get('is_hashtag_only', False),
                'top_comments': r.get('top_comments', ''),
                'comment_authors': r.get('comment_authors', ''),
                'comment_likes': r.get('comment_likes', ''),
                'comment_replies': r.get('comment_replies', ''),
                'comment_times': r.get('comment_times', '')
            }
            writer.writerow(row)
    return out_path


async def _run(url: str, max_posts: int):
    _ensure_dirs()
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await _login_if_needed(page)

        # Extract tag from URL for CSV filename
        tag = "facebook_page"
        if "hashtag" in url:
            tag = url.split("hashtag/")[-1].split("?")[0].split("/")[0]
        elif "facebook.com/" in url:
            # Extract page name from URL
            parts = url.split("facebook.com/")[-1].split("/")[0].split("?")[0]
            if parts and parts != "www.facebook.com":
                tag = parts

        print(f"\n[fb] Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        rows = await _scroll_and_collect_with_vision(page, max_posts=max_posts)
        out_path = _write_csv(tag, rows)

        await ctx.close()

    return out_path, len(rows)


def fb_scrape_command(cli_instance, url: str = None, max_posts: str = '30'):
    from psyduck import Colors

    if not DEPENDENCIES_AVAILABLE:
        print(f"{Colors.RED}Error: Facebook plugin dependencies not installed{Colors.END}")
        print(f"{Colors.YELLOW}Please run: pip install -r requirements.txt{Colors.END}")
        print(f"{Colors.YELLOW}Then: python -m playwright install chromium{Colors.END}")
        return

    if not url:
        print(f"{Colors.RED}Usage: fb-scrape <URL> [max_posts]{Colors.END}")
        print(f"{Colors.YELLOW}Examples:{Colors.END}")
        print(f"{Colors.YELLOW}  fb-scrape 'https://web.facebook.com/hashtag/python' 50{Colors.END}")
        print(f"{Colors.YELLOW}  fb-scrape 'https://www.facebook.com/awamileague' 20{Colors.END}")
        print(f"{Colors.YELLOW}  fb-scrape 'https://www.facebook.com/groups/123456789' 30{Colors.END}")
        return

    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if 'facebook.com' not in url:
        print(f"{Colors.RED}Error: URL must be a Facebook page{Colors.END}")
        print(f"{Colors.YELLOW}Examples: https://web.facebook.com/hashtag/python{Colors.END}")
        return

    try:
        limit = int(max_posts)
    except Exception:
        limit = 30

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print(f"{Colors.RED}Error: OPENAI_API_KEY environment variable not set{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OpenAI API key in .env file or environment{Colors.END}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}🧭 Facebook Scraper (Vision-Enhanced){Colors.END}")
    print(f"{Colors.WHITE}URL:{Colors.END} {url}")
    print(f"{Colors.WHITE}Limit:{Colors.END} {limit}")
    print(f"{Colors.MAGENTA}Features:{Colors.END} Vision analysis, OCR, 'See more' expansion, hashtag filtering, detailed comment analysis")

    try:
        out_path, count = asyncio.run(_run(url, limit))
        print(f"\n{Colors.GREEN}✓ Scraped {count} posts with full metadata. CSV: {out_path}{Colors.END}")
        print(f"{Colors.CYAN}Columns: post_id, author_name, post_text, likes_count, comments_count, has_see_more, is_hashtag_only, top_comments, comment_authors, comment_likes, comment_replies, comment_times{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


PLUGIN_INFO = {
    'name': 'facebook',
    'description': 'Facebook page/group/hashtag scraping via Playwright',
    'version': '0.2.0',
    'commands': {
        'fb-scrape': {
            'handler': fb_scrape_command,
            'description': 'Scrape posts and comments from any Facebook URL',
            'usage': 'fb-scrape <URL> [max_posts]'
        }
    }
}


