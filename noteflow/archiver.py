"""Website archiver — pulls a URL into a single self-contained HTML file.

This module was extracted from noteflow.py during the v0.4.0 port of
features from noteflow-go. The behavior loosely tracks go-shiori/obelisk:
  - inline images, stylesheets, scripts, fonts as data: URIs
  - cache + dedupe network fetches within an archive operation
  - per-resource + total-archive timeouts
  - concurrent prefetch (up to MAX_WORKERS in flight) for the obvious
    top-level assets, while the serial inliner handles CSS @import chains

Public surface:
  archive_website(url, folder_path) -> {html, markdown} | None
  process_plus_links(content, folder_path, app_port=None) -> {html, markdown}
"""
from __future__ import annotations

import base64
import re
import time
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


###############################################################################
# Tunables
###############################################################################
CONNECT_TIMEOUT = 5            # seconds to establish the TCP connection
READ_TIMEOUT = 8               # seconds to wait between data chunks
RESOURCE_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
TOTAL_TIMEOUT = 30             # seconds for the whole archive operation
MAX_RESOURCE_BYTES = 8 * 1024 * 1024  # skip resources larger than 8 MiB
MAX_WORKERS = 12               # concurrent prefetch workers
MAX_PREFETCH = 32              # hard cap on URLs we prefetch up front

IGNORED_DOMAINS = {
    'metrics.',
    'analytics.',
    'prismstandard.org',
    'outbrain.com',
    'tapad.com',
    'livefyre.com',
    'trustx.org',
    'tracking.',
    'stats.',
    'ads.',
}


###############################################################################
# Fetching primitives
###############################################################################
def should_ignore_resource(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return any(ignored in parsed.netloc.lower() for ignored in IGNORED_DOMAINS)
    except Exception:
        return False


def _fetch_one(session: requests.Session, url: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Single fetch with content-length + downloaded-size guard."""
    try:
        resp = session.get(url, timeout=RESOURCE_TIMEOUT, stream=True)
        if not resp.ok:
            return None, None
        cl = resp.headers.get('content-length')
        if cl and cl.isdigit() and int(cl) > MAX_RESOURCE_BYTES:
            resp.close()
            return None, None
        content = resp.content
        if len(content) > MAX_RESOURCE_BYTES:
            return None, None
        return content, resp.headers.get('content-type', '')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, None


def fetch_resource(session, url, cache=None, deadline=None):
    """Cache- and deadline-aware single fetch. Returns (bytes, content-type)."""
    if cache is not None and url in cache:
        return cache[url]
    if deadline is not None and time.time() > deadline:
        if cache is not None:
            cache[url] = (None, None)
        return None, None
    result = _fetch_one(session, url)
    if cache is not None:
        cache[url] = result
    return result


def prefetch(session, urls, cache, deadline):
    """Warm the cache for the most important URLs in parallel.

    Bounded by:
      - MAX_PREFETCH       (don't dispatch unbounded work)
      - MAX_WORKERS        (concurrency)
      - the archive deadline (stop waiting on stragglers when it expires)
    """
    seen = set()
    pending = []
    for u in urls:
        if u in cache or u in seen or should_ignore_resource(u):
            continue
        seen.add(u)
        pending.append(u)
        if len(pending) >= MAX_PREFETCH:
            break
    if not pending:
        return

    # Don't enter the threadpool at all if the deadline is already blown.
    remaining = deadline - time.time() if deadline else None
    if remaining is not None and remaining <= 0:
        for u in pending:
            cache[u] = (None, None)
        return

    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {pool.submit(_fetch_one, session, u): u for u in pending}
    try:
        for f in as_completed(futures, timeout=remaining):
            u = futures[f]
            try:
                cache[u] = f.result()
            except Exception:
                cache[u] = (None, None)
    except concurrent.futures.TimeoutError:
        # Deadline hit while we still had pending fetches. Mark whatever
        # didn't complete as failed and move on — the serial walker can
        # still write out a partial archive with the assets we did get.
        for f, u in futures.items():
            if u not in cache:
                cache[u] = (None, None)
    finally:
        # cancel_futures cancels anything that hasn't started yet; threads
        # that are mid-request will exit naturally as their per-request
        # read timeout fires.
        pool.shutdown(wait=False, cancel_futures=True)


def convert_to_data_uri(content_bytes: bytes, content_type: Optional[str]) -> str:
    if not content_type:
        content_type = 'application/octet-stream'
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    return f"data:{content_type};base64,{b64}"


###############################################################################
# Inlining passes
###############################################################################
def inline_css_resources(session, css_content, base_url, cache=None, deadline=None):
    done = False
    while not done:
        done = True
        import_pattern = re.compile(r'@import\s+["\']([^"\']+)["\'];')
        imports = import_pattern.findall(css_content)
        for imp in imports:
            if imp.startswith('data:'):
                continue
            done = False
            css_url = urljoin(base_url, imp)
            content, _ = fetch_resource(session, css_url, cache=cache, deadline=deadline)
            if content:
                sub_css = content.decode('utf-8', errors='replace')
                sub_css = inline_css_resources(session, sub_css, css_url, cache=cache, deadline=deadline)
                css_content = css_content.replace(f'@import "{imp}";', sub_css)
            else:
                css_content = css_content.replace(f'@import "{imp}";', '')

        url_pattern = re.compile(r'url\(["\']?([^)"\']+)["\']?\)')
        urls = url_pattern.findall(css_content)
        for u in urls:
            if u.startswith('data:') or u.endswith('.map'):
                continue
            done = False
            resource_url = urljoin(base_url, u)
            cbytes, ctype = fetch_resource(session, resource_url, cache=cache, deadline=deadline)
            if cbytes:
                css_content = css_content.replace(f'url({u})', f'url({convert_to_data_uri(cbytes, ctype)})')
    return css_content


def _collect_top_level_urls(soup, base_url) -> list:
    """Return absolute URLs for obvious top-level assets to prefetch."""
    urls = []

    def add(src):
        if not src or src.startswith('data:'):
            return
        urls.append(urljoin(base_url, src))

    for img in soup.find_all('img'):
        add(img.get('src'))
        srcset = img.get('srcset') or ''
        for part in srcset.split(','):
            url_part = part.strip().split(' ')[0]
            add(url_part)
    for source in soup.find_all('source'):
        add(source.get('src'))
        srcset = source.get('srcset') or ''
        for part in srcset.split(','):
            url_part = part.strip().split(' ')[0]
            add(url_part)
    for script in soup.find_all('script'):
        add(script.get('src'))
    for link in soup.find_all('link', rel='stylesheet'):
        add(link.get('href'))
    return urls


def inline_html_resources(session, soup, base_url, cache=None, deadline=None):
    # Images and srcset
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith('data:') and not should_ignore_resource(src):
            full_url = urljoin(base_url, src)
            cbytes, ctype = fetch_resource(session, full_url, cache=cache, deadline=deadline)
            if cbytes:
                img['src'] = convert_to_data_uri(cbytes, ctype)

        srcset = img.get('srcset')
        if srcset:
            parts = []
            for part in srcset.split(','):
                urlpart = part.strip().split(' ')[0]
                if urlpart and not urlpart.startswith('data:') and not should_ignore_resource(urlpart):
                    full_url = urljoin(base_url, urlpart)
                    cbytes, ctype = fetch_resource(session, full_url, cache=cache, deadline=deadline)
                    if cbytes:
                        rest = part.strip()[len(urlpart):]
                        parts.append(convert_to_data_uri(cbytes, ctype) + rest)
                    else:
                        parts.append(part)
                else:
                    parts.append(part)
            img['srcset'] = ', '.join(parts)

    for source in soup.find_all('source'):
        ssrc = source.get('src')
        if ssrc and not ssrc.startswith('data:') and not should_ignore_resource(ssrc):
            full_url = urljoin(base_url, ssrc)
            cbytes, ctype = fetch_resource(session, full_url, cache=cache, deadline=deadline)
            if cbytes:
                source['src'] = convert_to_data_uri(cbytes, ctype)
        srcset = source.get('srcset')
        if srcset:
            parts = []
            for part in srcset.split(','):
                urlpart = part.strip().split(' ')[0]
                if urlpart and not urlpart.startswith('data:') and not should_ignore_resource(urlpart):
                    full_url = urljoin(base_url, urlpart)
                    cbytes, ctype = fetch_resource(session, full_url, cache=cache, deadline=deadline)
                    if cbytes:
                        rest = part.strip()[len(urlpart):]
                        parts.append(convert_to_data_uri(cbytes, ctype) + rest)
                    else:
                        parts.append(part)
                else:
                    parts.append(part)
            source['srcset'] = ', '.join(parts)

    for script in soup.find_all('script'):
        src = script.get('src')
        if src and not src.startswith('data:') and not should_ignore_resource(src):
            res_url = urljoin(base_url, src)
            cbytes, _ = fetch_resource(session, res_url, cache=cache, deadline=deadline)
            if cbytes:
                script.string = cbytes.decode('utf-8', errors='replace')
                del script['src']

    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href and not should_ignore_resource(href):
            css_url = urljoin(base_url, href)
            cbytes, _ = fetch_resource(session, css_url, cache=cache, deadline=deadline)
            if cbytes:
                css_text = cbytes.decode('utf-8', errors='replace')
                css_text = inline_css_resources(session, css_text, css_url, cache=cache, deadline=deadline)
                style_tag = soup.new_tag('style')
                style_tag.string = css_text
                link.replace_with(style_tag)

    for elem in soup.find_all(style=True):
        style_val = elem['style']
        urls = re.findall(r'url\(["\']?([^)"\']+)["\']?\)', style_val)
        for u in urls:
            if not u.startswith('data:') and not should_ignore_resource(u):
                full_url = urljoin(base_url, u)
                cbytes, ctype = fetch_resource(session, full_url, cache=cache, deadline=deadline)
                if cbytes:
                    style_val = style_val.replace(u, convert_to_data_uri(cbytes, ctype))
        elem['style'] = style_val

    return soup


def inline_all_resources(url: str, source_html: str) -> str:
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    base_url = urljoin(url, '/')

    cache: Dict[str, Tuple[Optional[bytes], Optional[str]]] = {}
    deadline = time.time() + TOTAL_TIMEOUT

    soup = BeautifulSoup(source_html, 'html.parser')

    # Prefetch top-level assets concurrently to warm the cache; the serial
    # walker below then mostly hits cache and writes back data: URIs.
    prefetch(session, _collect_top_level_urls(soup, base_url), cache, deadline)

    for _ in range(5):  # bounded number of passes
        if time.time() > deadline:
            break
        before = str(soup)
        soup = inline_html_resources(session, soup, base_url, cache=cache, deadline=deadline)
        if str(soup) == before:
            break

    return str(soup)


###############################################################################
# Public entry points
###############################################################################
def archive_website(url: str, folder_path: Path) -> Optional[Dict[str, str]]:
    """Archive `url` into folder_path/assets/sites/. Returns html/markdown links."""
    try:
        archive_dir = folder_path / "assets" / "sites"
        archive_dir.mkdir(parents=True, exist_ok=True)

        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})

        response = session.get(url, timeout=RESOURCE_TIMEOUT)
        if not response.ok:
            print("Failed to fetch main page for archiving.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
        domain = urlparse(url).netloc

        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        display_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_title = re.sub(r'[^\w\-_]', '_', title)
        base_filename = f"{timestamp}_{safe_title}-{domain}"

        final_html = inline_all_resources(url, response.text)

        # Stamp the archive with a corner timestamp.
        soup_final = BeautifulSoup(final_html, 'html.parser')
        if soup_final.body:
            stamp = soup_final.new_tag('div')
            stamp['style'] = 'position:fixed;top:0;left:0;background:#fff;padding:5px;font-size:12px;'
            stamp.string = f'Archived on {display_timestamp}'
            soup_final.body.insert(0, stamp)
        final_html = str(soup_final)

        html_filename = f"{base_filename}.html"
        html_path = archive_dir / html_filename
        html_path.write_text(final_html, encoding='utf-8')

        # Sidecar metadata for the links pane.
        description = None
        keywords = None
        for meta in soup.find_all('meta'):
            if meta.get('name', '').lower() == 'description':
                description = meta.get('content', '')
            elif meta.get('name', '').lower() == 'keywords':
                keywords = meta.get('content', '')
        if not description:
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text().strip()[:200] + '...'

        tags_content = (
            f"URL: {url}\n"
            f"Title: {title}\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
            f"Keywords: {keywords if keywords else 'No keywords found'}\n"
            f"Description: {description if description else 'No description found'}\n"
        )
        (archive_dir / f"{base_filename}.tags").write_text(tags_content, encoding='utf-8')

        return {
            'html': (
                f'<div class="archived-link">'
                f'<a href="{url}">{domain}</a><br/>'
                f'<span class="archive-reference">'
                f'<a href="/assets/sites/{html_filename}" target="_blank">site archive [{display_timestamp}]</a>'
                f'</span></div>'
            ),
            'markdown': f"[{domain} - [{display_timestamp}]](/assets/sites/{html_filename})",
        }
    except Exception as e:
        print(f"Error saving webpage: {e}")
        return None


async def process_plus_links(content: str, folder_path: Path, app_port: Optional[int] = None) -> Dict[str, str]:
    """Replace `+http(s)://...` markers with archived links."""
    print("Processing content for +links...")

    async def replace_link(match):
        url = match.group(1)
        print(f"Found +link: {url}")

        parsed_url = urlparse(url)
        host = parsed_url.netloc.split(':')[0]
        is_localhost = host in ('localhost', '127.0.0.1', '0.0.0.0')
        is_same_port = app_port and parsed_url.port and str(parsed_url.port) == str(app_port)
        if is_localhost and is_same_port:
            return {
                'html': f'{url} <em>(self-referencing link removed)</em>',
                'markdown': f'{url} *(self-referencing link removed)*',
            }

        result = archive_website(url, folder_path)
        if result:
            return result
        return {'html': url, 'markdown': url}

    pattern = r'\+((https?://)[^\s]+)'
    matches = re.finditer(pattern, content)
    replacements = []
    for match in matches:
        replacement = await replace_link(match)
        replacements.append((match.start(), match.end(), replacement))

    html_result = list(content)
    markdown_result = list(content)
    for start, end, replacement in reversed(replacements):
        html_result[start:end] = replacement['html']
        markdown_result[start:end] = replacement['markdown']

    return {
        'html': ''.join(html_result),
        'markdown': ''.join(markdown_result),
    }
