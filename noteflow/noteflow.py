from fastapi import FastAPI, HTTPException, Path, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import socket
import platform
import subprocess
import webbrowser
import io
import re
from pathlib import Path
import sys
from markdown_it import MarkdownIt
from markdown_it.token import Token
from typing import Optional
from urllib.parse import quote, unquote, urljoin, urlparse
import os
import requests
import base64
import mimetypes
import hashlib
from bs4 import BeautifulSoup
import json
from pathlib import Path
import platformdirs  # You'll need to pip install platformdirs
import signal
from asyncio import get_event_loop
from fastapi.responses import JSONResponse
import psutil  # You might need to: pip install psutil
import tempfile
from urllib3.exceptions import HTTPError
import logging

APP_PORT = None

# Add this function to set the port when the app starts
def set_app_port(port: int):
    global APP_PORT
    APP_PORT = port
    
# Add this list near the top of your file
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

def should_ignore_resource(url):
    """Check if the resource URL should be ignored."""
    try:
        parsed = urlparse(url)
        return any(ignored in parsed.netloc.lower() for ignored in IGNORED_DOMAINS)
    except:
        return False

def saveFullHtmlPage(url, output_path, session=None):
    """Save a complete webpage with all assets."""
    try:
        if session is None:
            session = requests.Session()
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        session.headers.update(headers)
        
        response = session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = urljoin(url, '/')

        # Handle all resources that need to be embedded
        for tag, attrs in [
            ('img', 'src'),
            ('link', 'href'),
            ('script', 'src'),
            ('source', 'src'),
            ('video', 'src'),
            ('audio', 'src'),
            ('picture', 'src'),
        ]:
            for element in soup.find_all(tag):
                src = element.get(attrs, '')
                if not src or src.startswith('data:'):
                    continue
                    
                if should_ignore_resource(src):
                    continue
                
                try:
                    resource_url = urljoin(url, src)
                    resource_response = session.get(resource_url, timeout=10)  # Add timeout
                    if resource_response.ok:
                        content_type = resource_response.headers.get('content-type', '')
                        if not content_type:
                            content_type = mimetypes.guess_type(src)[0] or 'application/octet-stream'
                        resource_data = base64.b64encode(resource_response.content).decode('utf-8')
                        element[attrs] = f'data:{content_type};base64,{resource_data}'
                except Exception as e:
                    if not should_ignore_resource(src):
                        print(f"Error processing resource {src}: {e}")
                    continue

        # Handle CSS files and their resources
        for style in soup.find_all('style') + soup.find_all('link', rel='stylesheet'):
            if style.name == 'link':
                href = style.get('href')
                if not href or should_ignore_resource(href):
                    continue
                try:
                    css_url = urljoin(url, href)
                    css_response = session.get(css_url, timeout=10)
                    if css_response.ok:
                        css_content = css_response.text
                    else:
                        continue
                except:
                    continue
            else:
                css_content = style.string or ''

            # Process CSS URLs
            css_urls = re.findall(r'url\(["\']?([^)"\']+)["\']?\)', css_content)
            for css_url in css_urls:
                if css_url.startswith('data:') or should_ignore_resource(css_url):
                    continue
                try:
                    resource_url = urljoin(url, css_url)
                    resource_response = session.get(resource_url, timeout=10)
                    if resource_response.ok:
                        content_type = resource_response.headers.get('content-type', '')
                        if not content_type:
                            content_type = mimetypes.guess_type(css_url)[0] or 'application/octet-stream'
                        resource_data = base64.b64encode(resource_response.content).decode('utf-8')
                        css_content = css_content.replace(
                            f'url({css_url})',
                            f'url(data:{content_type};base64,{resource_data})'
                        )
                except Exception as e:
                    if not should_ignore_resource(css_url):
                        print(f"Error processing CSS resource {css_url}: {e}")

            if style.name == 'link':
                new_style = soup.new_tag('style')
                new_style.string = css_content
                style.replace_with(new_style)
            else:
                style.string = css_content

        # Add meta charset
        if not soup.find('meta', charset=True):
            meta = soup.new_tag('meta')
            meta['charset'] = 'utf-8'
            soup.head.insert(0, meta)

        # Add archive timestamp
        timestamp_comment = soup.new_tag('div')
        timestamp_comment['style'] = 'position:fixed;top:0;left:0;background:#fff;padding:5px;font-size:12px;'
        timestamp_comment.string = f'Archived on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        soup.body.insert(0, timestamp_comment)

        # Save the modified HTML
        with open(f"{output_path}.html", 'w', encoding='utf-8') as f:
            f.write(str(soup))

    except Exception as e:
        print(f"Error saving webpage: {e}")
        raise

def create_directories():
    # Define the directories to be created relative to the current working directory
    base_path = Path.cwd()
    directories = [
        base_path / "assets",
        base_path / "assets/images",
        base_path / "assets/files",
        base_path / "assets/sites"
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Ensure directories are created before mounting
create_directories()

app = FastAPI()

# Mount the local directories
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/fonts", StaticFiles(directory=Path(__file__).parent / "fonts"), name="fonts")
app.mount("/assets", StaticFiles(directory=Path.cwd() / "assets"), name="assets")  # Use Path.cwd() to ensure correct path

# Define the new separator
NOTE_SEPARATOR = "\n---\n"

# Define available themes
THEMES = {
    'light-blue': {
        # Main colors
        'background': '#1e3c72',          # Main background color
        'accent': '#ff8c00',              # Accent color
        'text_color': '#757575',          # Global text color
        'link_color': '#4a90e2',          # Link color
        'visited_link_color': '#7c7c9c',  # Visited link color
        'hover_link_color': '#66b3ff',    # Hovered link color

        # Labels
        'label_background': '#000000',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'header_text': '#666666',         # Label text color

        # Content boxes
        'box_background': '#ffffff',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#ffffff',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
        'button_border': '#313437',
        'button_hover': '#3a3f47',

        # Admin Panel Colors
        'admin_button_bg': '#313437',
        'admin_button_text': '#ff8c00',
        'admin_label_border': '#000000',
        'admin_border': '#000000',

        # Table colors for light theme
        'table_border': '#e0e0e0',
        'table_header_bg': '#f5f5f5',
        'table_header_text': '#333333',
        'table_row_bg': '#ffffff',
        'table_row_alt_bg': '#f9f9f9',
        'table_cell_text': '#333333',
    },
    'dark-blue': {
        # Main colors
        'background': '#1e3c72',          # Main background color
        'accent': '#ff8c00',              # Accent color
        'text_color': '#c0c0c0',          # Global text color
        'link_color': '#4a90e2',          # Link color
        'visited_link_color': '#7c7c9c',  # Visited link color
        'hover_link_color': '#66b3ff',    # Hovered link color

        # Labels
        'label_background': '#000000',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'header_text': '#666666',         # Label text color

        # Content boxes
        'box_background': '#26292c',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#313437',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
        'button_border': '#313437',
        'button_hover': '#3a3f47',

        # Admin Panel Colors
        'admin_button_bg': '#313437',
        'admin_button_text': '#ff8c00',
        'admin_label_border': '#000000',
        'admin_border': '#000000',

        # New table-specific colors
        'table_border': '#404040',        # Table and cell borders
        'table_header_bg': '#26292c',     # Table header background
        'table_header_text': '#df8a3e',   # Table header text color
        'table_row_bg': '#313437',        # Default row background
        'table_row_alt_bg': '#26292c',    # Alternating row background
        'table_cell_text': '#c0c0c0',     # Table cell text color
    },
    'dark-orange': {
        # Main colors
        'background': '#313437',          # Main background color
        'accent': '#df8a3e',              # Accent color
        'text_color': '#c0c0c0',          # Global text color
        'link_color': '#66d9ff',          # Link color
        'visited_link_color': '#8c8c8c',  # Visited link color
        'hover_link_color': '#00bfff',    # Hovered link color

        # Labels
        'label_background': '#313437',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'header_text': '#5084a7',         # Label text color

        # Content boxes
        'box_background': '#26292c',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#26292c',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
        'button_border': '#313437',
        'button_hover': '#3a3f47',

        # Admin Panel Colors
        'admin_button_bg': '#313437',
        'admin_button_text': '#ff8c00',
        'admin_label_border': '#000000',
        'admin_border': '#000000',

        # New table-specific colors
        'table_border': '#404040',        # Table and cell borders
        'table_header_bg': '#26292c',     # Table header background
        'table_header_text': '#df8a3e',   # Table header text color
        'table_row_bg': '#313437',        # Default row background
        'table_row_alt_bg': '#26292c',    # Alternating row background
        'table_cell_text': '#c0c0c0',     # Table cell text color
    }
}

# Serve the fonts
@app.get("/fonts/{path:path}")
async def serve_fonts(path: str):
    return StaticFiles(directory=Path(__file__).parent / "fonts")(path)

# Serve the favicon
@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")

# Enhanced regex to match "[ ] task", "- [ ] task", and sub-bullets like "  - [ ] task"
checkbox_pattern = re.compile(r'^(\s*-\s*(?:\*\*|\*|__)?\[)([ xX])(\](?:\*\*|\*|__)?.*)$')

# Data model for new notes
class Note(BaseModel):
    title: Optional[str] = None
    content: str

# Get an available port
def find_free_port(start_port=8000):
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("No free ports found")

# Initialize or read notes.md
def init_notes_file():
    notes_file = Path("notes.md")
    if not notes_file.exists():
        notes_file.write_text("")
    return notes_file

def task_list_plugin(md):
    def task_list_rule(state, silent):
        if state.src[state.pos] != '[':
            return False

        pos = state.pos + 1
        if pos < len(state.src) and state.src[pos] in ' xX':
            if pos + 1 < len(state.src) and state.src[pos + 1] == ']':
                if not silent:
                    token = state.push('checkbox', 'input', 0)
                    token.attrSet('type', 'checkbox')
                    if state.src[pos] in 'xX':
                        token.attrSet('checked', 'true')
                    
                    # Ensure we have an environment
                    if not hasattr(state, 'env'):
                        state.env = {}
                    if 'checkbox_index' not in state.env:
                        state.env['checkbox_index'] = 0
                    if 'note_index' not in state.env:
                        state.env['note_index'] = 0
                    
                    # Create unique ID for the checkbox
                    checkbox_index = state.env['checkbox_index']
                    note_index = state.env['note_index']
                    task_id = f'task_{note_index}_{checkbox_index}'
                    
                    # Store in token metadata
                    token.meta = {
                        'checkbox_index': checkbox_index,
                        'task_id': task_id
                    }
                    
                    # Set both id and name attributes directly on token
                    token.attrSet('id', task_id)
                    token.attrSet('name', task_id)
                    
                    state.env['checkbox_index'] = checkbox_index + 1
                    state.pos += 3
                return True
        return False

    def render_checkbox(tokens, idx, options, env):
        token = tokens[idx]
        checked = 'checked' if token.attrGet('checked') == 'true' else ''
        checkbox_index = token.meta.get('checkbox_index', 0)
        task_id = token.meta.get('task_id', f'task_0_{checkbox_index}')
        
        # Always include id and name, with fallback values if needed
        return f'<input type="checkbox" {checked} data-checkbox-index="{checkbox_index}" id="{task_id}" name="{task_id}">'

    # Make sure we're registering both the rule and the renderer
    md.inline.ruler.before('emphasis', 'task_list', task_list_rule)
    md.renderer.rules['checkbox'] = render_checkbox

# API routes
@app.get("/", response_class=HTMLResponse)
async def get_index():
    # Get colors for current theme
    colors = THEMES[CURRENT_THEME]
    
    themed_styles = f"""
    <style>
        @font-face {{
            font-family: 'space_monoregular';
            src: url('/fonts/spacemono-regular-webfont.woff2') format('woff2'),url('/fonts/spacemono-regular-webfont.woff') format('woff'),url('/fonts/spacemono-regular-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}
        @font-face {{
            font-family: 'space_monobold';
            src: url('/fonts/spacemono-bold-webfont.woff2') format('woff2'),url('/fonts/spacemono-bold-webfont.woff') format('woff'),url('/fonts/spacemono-bold-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'space_monobold_italic';
            src: url('/fonts/spacemono-bolditalic-webfont.woff2') format('woff2'),url('/fonts/spacemono-bolditalic-webfont.woff') format('woff'),url('/fonts/spacemono-bolditalic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'space_monoitalic';
            src: url('/fonts/spacemono-italic-webfont.woff2') format('woff2'),url('/fonts/spacemono-italic-webfont.woff') format('woff'),url('/fonts/spacemono-italic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'hackregular';
            src: url('/fonts/hack-regular-webfont.woff2') format('woff2'),
            url('/fonts/hack-regular-webfont.woff') format('woff'),
            url('/fonts/hack-regular-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}
        @font-face {{
            font-family: 'hackbold';
            src: url('/fonts/hack-bold-webfont.woff2') format('woff2'),
            url('/fonts/hack-bold-webfont.woff') format('woff'),
            url('/fonts/hack-bold-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'hackbold_italic';
            src: url('/fonts/hack-bolditalic-webfont.woff2') format('woff2'),
            url('/fonts/hack-bolditalic-webfont.woff') format('woff'),
            url('/fonts/hack-bolditalic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'hackitalic';
            src: url('/fonts/hack-italic-webfont.woff2') format('woff2'),
            url('/fonts/hack-italic-webfont.woff') format('woff'),
            url('/fonts/hack-italic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        body {{
            margin: 0;
            padding: 0;
            background-color: {colors['background']};
            color: {colors['text_color']};
            font-family: 'space_monoregular', Arial, sans-serif;
        }}
        .container {{
            display: flex;
            max-width: 100%;
            margin: 0 auto;
            gap: 15px;
        }}
        .site-title {{
            background-color: {colors['label_background']};
            color: {colors['accent']};
            padding: 1px 10px;
            font-family: monospace;
            font-size: 12px;
            display: flex;
            align-items: center;
        }}
        .site-title a {{
            color: {colors['accent']};
            text-decoration: none;
        }}
        .site-path {{
            margin-left: 10px;
            color: {colors['text_color']};
        }}
        .left-column, .right-column {{
            display: flex;
            flex-direction: column;
            gap: 0px;
        }}
        .left-column {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
            padding-left: 10px;
            padding-right: 0px;
        }}
        .right-column {{
            flex: 0 0 325px;
            width: 325px;
            margin-top: 0;  /* Ensure no top margin */
            padding-top: 0; /* Ensure no top padding */
            padding-right: 10px;
        }}
        .input-box {{
            background: {colors['box_background']};
            margin-top: 0px;
            padding: 5px;
            border: 1px solid #000;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            box-sizing: border-box;
        }}
        .task-box {{
            background: {colors['box_background']};
            margin-top: 0px;
            padding: 5px;
            border: 1px solid {colors['tasks_border']};
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            box-sizing: border-box;
        }}
        .links-box {{
            background: {colors['box_background']};
            padding: 5px;
            border: 1px solid {colors['links_border']};
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            margin-top: 0px;
            margin-left: 16px;
            box-sizing: border-box;
            font-size: 0.7rem;
            min-height: 75px;
        }}
        .links-box a {{
            color: blue;
            text-decoration: none;
            display: block;
            padding: 2px 0;
        }}
        .links-label {{
            position: absolute;
            top: 0;
            left: -4px;
            background: {colors['label_background']};
            color: {colors['accent']};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border: 1px solid {colors['links_label_border']};
            border-radius: 7px 0 0 7px;
        }}
        .links-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}
        .input-box input[type="text"] {{
            width: 100%;
            box-sizing: border-box;
            font-family: inherit;
            padding: 4px 8px;
            border: 1px solid {colors['input_border']};
            margin-bottom: 5px;
            height: 18px;
            background-color: {colors['input_background']};
        }}
        .input-box textarea {{
            width: 100%;
            box-sizing: border-box;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
            padding: 8px;
            color: {colors['text_color']};
            border: 1px solid {colors['input_border']};
            background-color: {colors['input_background']};
        }}
        .section-container {{
            position: relative;
            margin-bottom: 5px;
            margin-top: 5px;
            margin-left: 2px;
        }}
        .section-label {{
            position: absolute;
            top: 0;
            left: -20px;
            background: {colors['label_background']};
            color: {colors['accent']};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border: 1px solid {colors['note_label_border']};
            border-radius: 7px 0 0 7px;
        }}
        .section-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}
        #noteTitle {{
            border: 1px solid {colors['input_border']};
        }}
        .title-input-container {{
            display: flex;
            align-items: flex-start;
            gap: 10px; /* Space between input and button */
        }}
        .title-input-container input[type="text"] {{
            flex: 1; /* Take up remaining space */
            box-sizing: border-box;
            font-family: inherit;
            padding: 4px 8px;
            border: 1px solid {colors['input_border']};
            margin-bottom: 5px;
            height: 25px;
            color: {colors['text_color']};
        }}
        .save-note-button {{   
            width: 75px;
            background: {colors['button_bg']};
            hover: {colors['button_hover']};
            color: {colors['accent']};
            border: none;
            padding: 4px 0;
            cursor: pointer;
            font-family: inherit;
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            border-bottom-left-radius: 4px;
        }}
        .notes-item {{
            background: {colors['box_background']};
            padding-left: 5px;
            padding-top: 15px;
            padding-right: 5px;
            padding-bottom: 5px;
            margin-right: 15px;
            border: 1px solid {colors['note_border']};
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            min-height: 60px;
            box-sizing: border-box;
        }}
        .post-header {{
            font-weight: normal;
            font-size: 10px;
            margin-top: -10px;
            margin-bottom: 10px;
            color: {colors['header_text']};
        }}
        .links-box a {{
            color: blue;
            text-decoration: none;
            display: block;
            padding: 2px 0;
        }}
        .note-content {{
            scroll-margin-top: 100px;
        }}
        .markdown-body {{
            font-size: 0.9rem;
        }}
        .markdown-body ul {{
            list-style-type: disc;
        }}
        .markdown-body ul ul {{
            list-style-type: circle;
        }}
        .markdown-body ul ul ul {{
            list-style-type: square;
        }}
        .markdown-body ul,.markdown-body ol {{
            list-style-position: outside;
            padding-left: 1.5em;
            margin-top: 0.1rem;
            margin-bottom: 0.1rem;
        }}
        .markdown-body li {{
            margin-bottom: 0.1rem;
        }}
        .markdown-body input[type="checkbox"] {{
            margin-right: 0.5rem;
        }}
        .markdown-body h4 {{
            margin-top: 5px;
            margin-bottom: 5px;
        }}
        .markdown-body h2 {{
            font-size: 1.5rem;
            font-weight: bold;
            margin: 1rem 0;
            color: {colors['text_color']};
        }}
        .markdown-body p {{
            margin: 5px 0;
        }}
        .markdown-body a {{
            color: {colors['link_color']} !important;
            text-decoration: none;
        }}
        .markdown-body a:visited {{
            color: {colors['visited_link_color']} !important;
        }}
        .markdown-body a:hover {{
            color: {colors['hover_link_color']} !important;
            text-decoration: underline;
        }}
        /* Table styles */
        .markdown-body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            border: 1px solid {colors['table_border']};
        }}

        .markdown-body table thead {{
            background-color: {colors['table_header_bg']};
        }}

        .markdown-body table th {{
            padding: 8px 12px;
            border: 1px solid {colors['table_border']};
            color: {colors['table_header_text']};
            font-weight: 600;
            text-align: left;
        }}

        .markdown-body table td {{
            padding: 8px 12px;
            border: 1px solid {colors['table_border']};
            color: {colors['table_cell_text']};
        }}

        .markdown-body table tr {{
            background-color: {colors['table_row_bg']};
        }}

        .markdown-body table tr:nth-child(even) {{
            background-color: {colors['table_row_alt_bg']};
        }}

        /* Optional hover effect */
        .markdown-body table tr:hover {{
            background-color: {colors['button_hover']};
        }}
        .notes-container {{
            width: 100%;
            margin-left: 15px;
            margin-right: 0;
            padding-left: 0;
            padding-right: 0;
        }}
        #noteForm {{
            width: 100%;
        }}
        .notes-item .edit-label {{
            color: {colors['accent']};
        }}
        #activeTasks {{
            word-wrap: break-word;
            overflow-wrap: break-word;
            max-height: none;
        }}
        #activeTasks .task-item {{
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            padding: 0.1rem 0;
        }}
        #activeTasks .task-text {{
            flex: 1;
            min-width: 0;
            padding-top: 2px;
            word-break: break-word;
            white-space: pre-wrap;
            font-size: 0.7rem;
        }}
        #noteForm button {{
            width: 100px;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }}
        pre {{
            background-color: {colors['code_background']};
            margin: 0 0;
            padding: 0 0;
        }}
        pre code {{
            background-color: {colors['code_background']};
            padding: 0.2em;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.7rem;
        }}
        .markdown-body pre code.hljs {{
            background-color: {colors['code_background']};
            padding: 0.3em !important;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }}
        .notes-item pre code {{
            background-color: {colors['code_background']};
            padding: 0.3em;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }}
        /* Inline code styling */
        .markdown-body code {{
            background-color: {colors['code_background']};
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.85em;
            color: #333;  /* You might want to make this a theme color */
        }}
        .input-box input[type="text"] {{
            width: 100%;
            box-sizing: border-box;
            font-family: inherit;
            padding: 4px 8px;
            border: 1px solid #ccc;
            margin-bottom: 5px;
            height: 18px;
            color: {colors['text_color']};
        }}
        .input-box textarea::placeholder {{
            font-size: 10px;
            color: #999;
        }}
        .input-box input::placeholder {{
            font-size: 10px;
            color: {colors['text_color']};
        }}
        .loading-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .loading-spinner {{
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        .loading-text {{
            color: {colors['text_color']};
            margin-top: 10px;
            font-family: 'space_monoregular', monospace;
        }}
        @keyframes spin {{
            0% {{
                transform: rotate(0deg);
            }}
            100% {{
                transform: rotate(360deg);
            }}
        }}
        .archived-link {{
            margin-bottom: 3px;
            line-height: 1.2;
        }}
        .archived-link a {{
            color: {colors['accent']};
            text-decoration: none;
        }}
        .archive-reference {{
            display: block;
            margin-left: 20px;
            margin-top: 0px;
            font-size: 100%;
        }}
        .archive-reference + .archive-reference {{
            margin-top: 1px;
        }}
        .archive-reference a {{
            color: {colors['accent']};
            text-decoration: none;
            line-height: 1.1;
        }}
        .archive-reference a:hover {{
            color: {colors['text_color']};
            text-decoration: underline;
        }}
        .markdown-body img {{
            max-width: 100%;
            max-height: 400px;
            width: auto;
            height: auto;
            display: block;
            margin: 10px auto;
        }}
        .admin-panel {{
            position: fixed;
            bottom: 15px;
            right: 0;
            display: flex;
            align-items: flex-start;
            z-index: 1000;
            transform: translateX(calc(100% - 19px)); /* Hide content, show label */
            transition: transform 0.3s ease;
        }}

        .admin-panel:hover {{
            transform: translateX(0); /* Show everything on hover */
        }}

        .admin-label {{
            background: {colors['label_background']};
            color: {colors['accent']};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border-radius: 7px 0 0 7px;
            border: 1px solid {colors['admin_label_border']};
            cursor: pointer;
        }}

        .admin-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}

        .admin-content {{
            background: {colors['box_background']};
            padding: 10px;
            border: 1px solid {colors['admin_border']};
            border-left: none;
            border-bottom-left-radius: 7px;
            width: 150px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .admin-button {{
            background: {colors['admin_button_bg']};
            color: {colors['admin_button_text']};
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.8rem;
            width: 100%;
        }}

        .admin-button:hover {{
            opacity: 0.9;
        }}

        #themeSelector {{
            width: 100%;
            margin-top: 5px;
            padding: 5px;
            border: 1px solid {colors['input_border']};
            border-radius: 4px;
            background: {colors['input_background']};
            color: {colors['text_color']};
            font-family: inherit;
            font-size: 0.8rem;
        }}

        #themeSelector option {{    
            background: {colors['input_background']};
            color: {colors['text_color']};
            padding: 5px;
        }}
        .delete-label {{
            color: {colors['accent']};
            margin-left: 4px;  /* Add some spacing between edit and delete labels */
        }}
        .delete-label:hover {{
            color: {colors['accent']};
            text-decoration: underline;
        }}

        @keyframes flash {{ 
            0% {{ background-color: transparent; }}
            10% {{ background-color: rgba(255, 255, 255, 0.8); }}
            100% {{ background-color: transparent; }}
        }}

        .flash-highlight {{
            animation: flash 0.75s ease-out;
        }}

        .flash-highlight-delay1 {{
            animation: flash 0.75s ease-out 0.1s;
        }}

        .flash-highlight-delay2 {{
            animation: flash 0.75s ease-out 0.2s;
        }}

        .note-title {{
            color: {colors['link_color']};
            cursor: pointer;
            text-decoration: none;
            display: inline;
        }}
        .note-title:hover {{
            opacity: 0.8;  /* Subtle hover effect */
        }}
        .directory-bar {{
            background: {colors['button_bg']};
            padding: 2px 6px;
            margin: 0;  /* Remove all margins */
            font-size: 0.55rem;
            font-family: 'space_monoregular', monospace;
            color: {colors['accent']};
            display: flex;
            flex-flow: row nowrap;
            align-items: center;
            overflow: hidden;
        }}
        .directory-bar-content {{
            white-space: nowrap;
            animation: scroll-left 20s linear infinite;
            max-width: none;
            padding-right: 50px;
            flex-shrink: 0;
            display: inline-block;
        }}
        @keyframes scroll-left {{
            0% {{
                transform: translate(0, 0);
            }}
            100% {{
                transform: translate(-100%, 0);
            }}
        }}
    </style>
"""

    html_content = """
<body>
    <div class="container">
        <!-- Left Column -->
        <div class="left-column">
            <form id="noteForm">
                <!-- Input Section -->
                <div class="input-box">
                    <div class="title-input-container">
                        <input type="text" id="noteTitle" name="noteTitle" placeholder="Enter note title here...">
                        <button id="saveNoteButton" class="save-note-button" onclick="handleSubmit(event)">Save Note</button>
                    </div>
                    <textarea id="noteInput" name="noteInput" placeholder="Enter note in Markdown format.."></textarea>
                </div>

                <!-- Notes Section -->
                <div class="notes-container" id="notes">
                </div>
            </form>

        </div>

        <!-- Right Column -->
        <div class="right-column">
            <!-- Directory Bar -->
            <div class="directory-bar">
                <span class="directory-bar-content">""" + str(Path.cwd().absolute()) + """&nbsp;</span>
                <span class="directory-bar-content">""" + str(Path.cwd().absolute()) + """&nbsp;</span>
                <span class="directory-bar-content">""" + str(Path.cwd().absolute()) + """&nbsp;</span>
            </div>
            <!-- Tasks Box -->
            <div id="activeTasks" class="task-box">
                <!-- Task items will be dynamically inserted here -->
            </div>
            <!-- Links Section -->
            <div class="section-container">
                <div class="links-label">
                    <span>l</span>
                    <span>i</span>
                    <span>n</span>
                    <span>k</span>
                    <span>s</span>
                </div>
                <div id="linksSection" class="links-box">
                    <script>
                        const handleSubmit = async (e) => {
                            e.preventDefault();
                            let userTitle = $('#noteTitle').val().trim();
                            const content = $('#noteInput').val().trim();
                            
                            if (!content) return;
                            
                            // Check if we're editing an existing note
                            const editingNoteIndex = $('#noteForm').attr('data-editing-note');
                            const isEditing = editingNoteIndex !== undefined;
                            
                            // Create the new timestamp title
                            const now = new Date();
                            const timestamp = now.toISOString().slice(0, 19).replace('T', ' ');
                            const title = `## ${timestamp} - ${userTitle}`;
                            
                            // Check if content contains a +http link
                            const hasArchiveLink = content.includes('+http');
                            if (hasArchiveLink) {
                                $('.loading-overlay').css('display', 'flex');
                            }
                            
                            try {
                                const url = isEditing ? `/api/notes/${editingNoteIndex}` : '/api/notes';
                                const method = isEditing ? 'PUT' : 'POST';
                                
                                const response = await fetch(url, {
                                    method: method,
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ 
                                        title: title,  // Send just the new title
                                        content: content 
                                    })
                                });
                                
                                if (!response.ok) {
                                    throw new Error(`Failed to ${isEditing ? 'update' : 'add'} note`);
                                }
                                
                                // Clear form and editing state
                                $('#noteTitle').val('');
                                $('#noteInput').val('');
                                $('#noteInput').css('height', 'auto');
                                $('#noteForm').removeAttr('data-editing-note');
                                
                                // Refresh both notes and links
                                await loadNotes();
                                loadLinks();
                                
                            } catch (error) {
                                console.error(`Error ${isEditing ? 'updating' : 'adding'} note:`, error);
                                alert(`Failed to ${isEditing ? 'update' : 'add'} note`);
                            } finally {
                                $('.loading-overlay').css('display', 'none');
                            }
                        }; // Removed extra }; here

                        $(document).ready(function() {
                            // Form handling
                            const form = $('#noteForm');
                            const noteInput = $('#noteInput');

                            // Initialize notes and links
                            loadNotes();
                            loadLinks();
                            updateActiveTasks();

                            // Form submission handlers
                            form.on('submit', handleSubmit);

                            // Ctrl+Enter handler
                            noteInput.on('keydown', function(e) {
                                if (e.ctrlKey && e.key === 'Enter') {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            });

                            // Tab handler
                            noteInput.on('keydown', function(e) {
                                if (e.key === 'Tab') {
                                    e.preventDefault();
                                    const start = this.selectionStart;
                                    const end = this.selectionEnd;
                                    this.value = this.value.substring(0, start) + '\t' + this.value.substring(end);
                                    this.selectionStart = this.selectionEnd = start + 1;
                                }
                            });

                            // Drag and drop handlers
                            const editNoteContent = $('#editNoteContent');
                            if (editNoteContent.length) {  // Check if element exists
                                editNoteContent.on('dragover', function(e) {
                                    e.preventDefault();
                                });

                                editNoteContent.on('drop', async function(e) {
                                    e.preventDefault();
                                    const files = e.dataTransfer.files;
                                    if (files.length > 0) {
                                        const file = files[0];
                                        const formData = new FormData();
                                        formData.append('file', file);

                                        try {
                                            const response = await fetch('/api/upload-file', {
                                                method: 'POST',
                                                body: formData
                                            });

                                            if (response.ok) {
                                                const { filePath } = await response.json();
                                                const markdownLink = `![${file.name}](<${filePath}>)`;
                                                insertAtCursor(editNoteContent[0], markdownLink);
                                            } else {
                                                alert('Failed to upload file');
                                            }
                                        } catch (error) {
                                            console.error('Error uploading image:', error);
                                        }
                                    }
                                });
                            }

                            // Initialize theme selector
                            initializeTheme();
                        });

                        function loadLinks() {
                            $.get('/api/links')
                                .done(function(response) {
                                    const htmlContent = response.html || response;
                                    $('#linksSection').html(htmlContent);
                                })
                                .fail(function(error) {
                                    console.error('Error loading links:', error);
                                });
                        }

                        async function loadNotes() {
                            const response = await fetch('/api/notes');
                            const html = await response.text();
                            document.getElementById('notes').innerHTML = html;
                            document.querySelectorAll('pre code').forEach((block) => {
                                hljs.highlightElement(block);
                            });
                            await updateActiveTasks();
                        }

                        async function submitNoteForm() {
                            const titleInput = document.getElementById('noteTitle');
                            const noteInput = document.getElementById('noteInput');
                            const title = titleInput.value.trim();
                            const content = noteInput.value.trim();
                            
                            if (!content) return;

                            try {
                                const response = await fetch('/api/notes', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ title, content })
                                });

                                if (!response.ok) {
                                    throw new Error('Failed to add note');
                                }
                                
                                titleInput.value = '';
                                noteInput.value = '';
                                noteInput.style.height = 'auto';

                                await loadNotes();
                            } catch (error) {
                                console.error('Error adding note:', error);
                                alert('Failed to add note');
                            }
                        }

                        document.addEventListener('click', async (event) => {
                            if (event.target.matches('input[type="checkbox"]')) {
                                const checkbox = event.target;
                                const checkboxIndex = checkbox.getAttribute('data-checkbox-index');
                                const isChecked = checkbox.checked;
                                
                                // Validate checkbox index
                                if (!checkboxIndex || isNaN(parseInt(checkboxIndex))) {
                                    console.error('Invalid checkbox index:', checkboxIndex);
                                    checkbox.checked = !isChecked; // Revert the checkbox
                                    return;
                                }
                                
                                const payload = {
                                    checked: isChecked,
                                    checkbox_index: parseInt(checkboxIndex)
                                };
                                
                                try {
                                    const response = await fetch('/api/update-checkbox', {
                                        method: 'PATCH',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify(payload)
                                    });
                                    
                                    if (!response.ok) {
                                        const errorData = await response.json();
                                        console.error('Server error:', errorData);
                                        throw new Error(`Failed to update checkbox`);
                                    }
                                    
                                    const result = await response.json();
                                    if (result.status === 'success') {
                                        await loadNotes();
                                        await updateActiveTasks();
                                    } else {
                                        checkbox.checked = !isChecked;
                                        console.error('Failed to update checkbox:', result.message);
                                    }
                                } catch (error) {
                                    checkbox.checked = !isChecked;
                                    console.error('Error updating checkbox:', error);
                                }
                            }
                        });

                        async function updateActiveTasks() {
                            const response = await fetch('/api/notes');
                            const tasksContainer = document.getElementById('activeTasks');
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(await response.text(), 'text/html');
                            
                            const uncheckedTasks = Array.from(doc.querySelectorAll('input[type="checkbox"]:not(:checked)'));
                            
                            tasksContainer.innerHTML = '';
                            
                            uncheckedTasks.forEach((checkbox) => {
                                const originalCheckboxIndex = checkbox.getAttribute('data-checkbox-index');
                                const originalTaskId = checkbox.getAttribute('id') || `task_0_${originalCheckboxIndex}`;
                                const activeTaskId = `active_${originalTaskId}`;
                                const taskItem = checkbox.closest('li') || checkbox.closest('p');

                                if (taskItem) {
                                    const taskText = taskItem.textContent.trim();
                                    
                                    const taskElement = document.createElement('div');
                                    taskElement.className = 'task-item';
                                    taskElement.innerHTML = `
                                        <input type="checkbox" 
                                            class="mt-1 consolidated-task" 
                                            data-checkbox-index="${originalCheckboxIndex}"
                                            id="${activeTaskId}"
                                            name="${activeTaskId}"
                                            data-original-task="${originalTaskId}">
                                        <span class="task-text text-sm text-gray-700">${taskText}</span>
                                    `;
                                    tasksContainer.appendChild(taskElement);
                                }
                            });

                            if (uncheckedTasks.length === 0) {
                                tasksContainer.innerHTML = '<div class="text-sm text-gray-500">No active tasks</div>';
                            }
                        }

                        document.addEventListener('DOMContentLoaded', updateActiveTasks);

                        document.getElementById('noteInput').placeholder = `Create note in MARKDOWN format... [Ctrl+Enter to save]
Drag & Drop images/files to upload...
Start Links with + to archive websites (e.g., +https://www.google.com)

# Scroll down for Markdown Examples
- [ ] Tasks
- Bullets
    - Sub-bullets
- **Bold** and *italic*
- 2 spaces after a line to create a line break OR extra line between paragraphs`;
                        loadNotes();

                        const noteInput = document.getElementById('noteInput');

                        noteInput.addEventListener('dragover', (e) => {
                            e.preventDefault();
                        });

                        noteInput.addEventListener('drop', async (e) => {
                            e.preventDefault();
                            const files = e.dataTransfer.files;
                            if (files.length > 0) {
                                const file = files[0];
                                const formData = new FormData();
                                formData.append('file', file);

                                try {
                                    const response = await fetch('/api/upload-file', {
                                        method: 'POST',
                                        body: formData
                                    });

                                    if (response.ok) {
                                        const { filePath } = await response.json();
                                        const markdownLink = `![${file.name}](<${filePath}>)`;
                                        insertAtCursor(noteInput, markdownLink);
                                    } else {
                                        alert('Failed to upload file');
                                    }
                                } catch (error) {
                                    console.error('Error uploading image:', error);
                                }
                            }
                        });

                        function insertAtCursor(input, textToInsert) {
                            const start = input.selectionStart;
                            const end = input.selectionEnd;
                            input.value = input.value.substring(0, start) + textToInsert + input.value.substring(end);
                            input.selectionStart = input.selectionEnd = start + textToInsert.length;
                        }

                        let currentEditingNoteIndex = null;

                        async function editNote(noteIndex) {
                            try {
                                const response = await fetch(`/api/notes/${noteIndex}`);
                                if (!response.ok) throw new Error('Failed to fetch note');
                                
                                const noteData = await response.json();
                                
                                // Populate the form fields
                                document.getElementById('noteTitle').value = noteData.title || '';
                                document.getElementById('noteInput').value = noteData.content;
                                
                                // Store the note index being edited
                                document.getElementById('noteForm').setAttribute('data-editing-note', noteIndex);
                                
                                // Add flash effects with cascading timing
                                const inputBox = document.querySelector('.input-box');
                                inputBox.classList.add('flash-highlight');
                                document.getElementById('noteTitle').classList.add('flash-highlight-delay1');
                                document.getElementById('noteInput').classList.add('flash-highlight-delay2');
                                
                                // Remove the classes after animations complete
                                setTimeout(() => {
                                    inputBox.classList.remove('flash-highlight');
                                    document.getElementById('noteTitle').classList.remove('flash-highlight-delay1');
                                    document.getElementById('noteInput').classList.remove('flash-highlight-delay2');
                                }, 1000); // Wait for all animations to complete
                                
                                // Scroll to the top of the page
                                window.scrollTo(0, 0);
                                
                                // Focus the input field
                                document.getElementById('noteInput').focus();
                            } catch (error) {
                                console.error('Error fetching note:', error);
                                alert('Failed to load note for editing');
                            }
                        }

                        async function saveTheme() {
                            const selectedTheme = document.getElementById('themeSelector').value;
                            try {
                                const formData = new FormData();
                                formData.append('theme', selectedTheme);
                                
                                const response = await fetch('/api/save-theme', {
                                    method: 'POST',
                                    body: formData
                                });
                                
                                if (!response.ok) {
                                    throw new Error('Failed to save theme');
                                }
                                
                                // Reload the page to apply the new theme
                                window.location.reload();
                            } catch (error) {
                                console.error('Error saving theme:', error);
                                alert('Failed to save theme');
                            }
                        }
                        async function shutdownServer() {
                            if (confirm('Are you sure you want to shutdown this server instance?')) {
                                try {
                                    const response = await fetch('/api/shutdown', { 
                                        method: 'POST',
                                        // Add timeout to prevent hanging
                                        signal: AbortSignal.timeout(5000)
                                    });
                                    
                                    if (response.ok) {
                                        alert('Server is shutting down...');
                                        // Wait a moment then close the window
                                        setTimeout(() => {
                                            try {
                                                window.close();
                                            } catch (e) {
                                                // If window.close() fails, suggest manual closure
                                                alert('Please close this window manually');
                                            }
                                        }, 1000);
                                    } else {
                                        alert('Failed to shutdown server. Please close this window and terminate the process manually.');
                                    }
                                } catch (error) {
                                    console.error('Error shutting down server:', error);
                                    alert('Error shutting down server. Please close this window and terminate the process manually.');
                                }
                            }
                        }
                    </script>
                </div>
            </div>
        </div>
    </div>
    <!-- Add this right before </body> -->
    <div class="loading-overlay">
        <div style="text-align: center;">
            <div class="loading-spinner"></div>
            <div class="loading-text">Archiving website...</div>
        </div>
    </div>
    <!-- Add before </body> -->
    <div class="admin-panel">
        <div class="admin-label">
            <span>a</span>
            <span>d</span>
            <span>m</span>
            <span>i</span>
            <span>n</span>
        </div>
        <div class="admin-content">
            <select id="themeSelector">
                <!-- Will be populated dynamically -->
            </select>
            <button class="admin-button" onclick="saveTheme()">Save Theme</button>
            <button class="admin-button" onclick="shutdownServer()">Shutdown</button>
        </div>
    </div>
</body>
</html>
    """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Notes</title>
        {themed_styles}
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/{colors['code_style']}.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        // Add this at the start of your JavaScript
        const CURRENT_THEME = "{CURRENT_THEME}";  // Add this line to make current theme available to JS
        
        async function initializeTheme() {{
            try {{
                const response = await fetch('/api/themes');
                const themes = await response.json();
                
                const selector = document.getElementById('themeSelector');
                themes.forEach(theme => {{
                    const option = document.createElement('option');
                    option.value = theme;
                    option.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
                    if (theme === CURRENT_THEME) {{  // Use the CURRENT_THEME variable
                        option.selected = true;
                    }}
                    selector.appendChild(option);
                }});
            }} catch (error) {{
                console.error('Error loading themes:', error);
            }}
        }}

        async function deleteNote(noteIndex) {{
            if (!confirm('Are you sure you want to delete this note?')) {{
                return;
            }}
            try {{
                const response = await fetch(`/api/notes/${{noteIndex}}`, {{
                    method: 'DELETE',
                    headers: {{
                        'Content-Type': 'application/json'
                    }}
                }});
                if (!response.ok) {{
                    throw new Error('Failed to delete note');
                }}
                await loadNotes();
                loadLinks();
            }} catch (error) {{
                console.error('Error deleting note:', error);
                alert('Failed to delete note');
            }}
        }}
        
    </script>
</head>
    """ + html_content

@app.get("/api/notes")
async def get_notes():
    notes_file = init_notes_file()
    try:
        # First try UTF-8
        content = notes_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            # If UTF-8 fails, try Windows-1252 (cp1252)
            content = notes_file.read_text(encoding='cp1252')
        except UnicodeDecodeError:
            # If both fail, use UTF-8 with error handling
            content = notes_file.read_text(encoding='utf-8', errors='replace')
    
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    html_notes = []
    global_checkbox_index = 0
    
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        timestamp = lines[0]
        note_content = '\n'.join(lines[1:])
        
        env = {
            'note_index': note_index, 
            'checkbox_index': global_checkbox_index
        }
        
        rendered_content = render_markdown(note_content, env)
        
        global_checkbox_index = env.get('checkbox_index')
        
        html_note = f'''
        <div class="section-container">
            <div class="section-label">
                <span>n</span>
                <span>o</span>
                <span>t</span>
                <span>e</span>
            </div>
            <div class="notes-item markdown-body">
                <div class="post-header">
                    <span class="note-title" onclick="editNote({note_index});">Posted: {timestamp} (click to edit)</span>
                    <span class="delete-label" onclick="deleteNote({note_index});" style="cursor: pointer;">(delete)</span>
                </div>
                {rendered_content}
            </div>
        </div>
        '''
        html_notes.append(html_note)
    
    html_content = ''.join(html_notes)
    return HTMLResponse(html_content)

# Add new endpoint to get a specific note
@app.get("/api/notes/{note_index}")
async def get_note(note_index: int):
    notes_file = init_notes_file()
    content = notes_file.read_text()
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    if 0 <= note_index < len(notes):
        lines = notes[note_index].split('\n')
        timestamp = lines[0]
        
        # Extract title if it exists (assuming it's in the format "## timestamp - title")
        title = ""
        if timestamp.startswith("##"):
            parts = timestamp.split(" - ", 1)
            if len(parts) > 1:
                title = parts[1]
        
        note_content = '\n'.join(lines[1:])
        return {"timestamp": timestamp, "content": note_content, "title": title}
    
    raise HTTPException(status_code=404, detail="Note not found")

# Add new endpoint to update a specific note
@app.put("/api/notes/{note_index}")
async def update_note(note_index: int, note: Note):
    notes_file = init_notes_file()
    try:
        content = notes_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = notes_file.read_text(encoding='cp1252')
        except UnicodeDecodeError:
            content = notes_file.read_text(encoding='utf-8', errors='replace')

    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    if 0 <= note_index < len(notes):
        # Process links and get both HTML and Markdown versions
        processed = await process_plus_links(note.content)
        
        # Use the new title directly (it already includes timestamp from client)
        formatted_note = f"{note.title}\n{processed['markdown'].strip()}"
        
        # Replace the note at the specified index
        notes[note_index] = formatted_note
        
        # Join all notes back together with consistent separator
        updated_content = f"\n---\n".join(notes)
        
        # Write back to file
        notes_file.write_text(updated_content)
        
        return {"status": "success"}
    
    raise HTTPException(status_code=404, detail="Note not found")

# Add delete endpoint
@app.delete("/api/notes/{note_index}")
async def delete_note(note_index: int):
    notes_file = init_notes_file()
    content = notes_file.read_text()
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    if 0 <= note_index < len(notes):
        # Remove the note at the specified index
        notes.pop(note_index)
        
        # Join remaining notes back together with consistent separator
        updated_content = f"\n---\n".join(notes)
        
        # Write back to file
        with notes_file.open('w') as f:
            f.write(updated_content)
        
        return {"status": "success"}
    
    raise HTTPException(status_code=404, detail="Note not found")

async def process_plus_links(content):
    """Process +https:// links in the content and create local copies."""
    async def replace_link(match):
        url = match.group(1)
        
        # Check if URL is pointing to our own server
        parsed_url = urlparse(url)
        host = parsed_url.netloc.split(':')[0]
        is_localhost = host in ('localhost', '127.0.0.1', '0.0.0.0')
        is_same_port = APP_PORT and str(parsed_url.port) == str(APP_PORT)
        
        if is_localhost and is_same_port:
            # Return URL without the plus and add a note
            return {
                'html': f'{url} <em>(self-referencing link removed)</em>',
                'markdown': f'{url} *(self-referencing link removed)*'
            }
            
        result = archive_website(url)
        if result:
            return result
        return {'html': url, 'markdown': url}

    pattern = r'\+((https?://)[^\s]+)'
    matches = re.finditer(pattern, content)
    replacements = []
    for match in matches:
        replacement = await replace_link(match)
        replacements.append((match.start(), match.end(), replacement))
    
    # Create both HTML and Markdown versions of the content
    html_result = list(content)
    markdown_result = list(content)
    
    for start, end, replacement in reversed(replacements):
        html_result[start:end] = replacement['html']
        markdown_result[start:end] = replacement['markdown']
    
    return {
        'html': ''.join(html_result),
        'markdown': ''.join(markdown_result)
    }

@app.post("/api/notes")
async def add_note(note: Note):
    notes_file = init_notes_file()
    current_content = notes_file.read_text().strip()
    
    # Process +https:// links in the content
    processed_content = await process_plus_links(note.content)
    
    # Format new note - use the markdown version for notes.md
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f" - {note.title}" if note.title else ""
    formatted_note = f"## {timestamp}{title}\n\n{processed_content['markdown']}"  # Use markdown version
    
    # Combine with existing content
    if current_content:
        new_content = f"{formatted_note}\n---\n{current_content}"
    else:
        new_content = formatted_note
    
    # Write back to file
    with notes_file.open('w') as f:
        f.write(new_content)
    
    return {"status": "success", "refresh_links": True}

class UpdateNoteRequest(BaseModel):
    checked: bool
    checkbox_index: int

@app.patch("/api/update-checkbox")
async def update_checkbox(request: UpdateNoteRequest):
    notes_file = init_notes_file()
    try:
        content = notes_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = notes_file.read_text(encoding='cp1252')
        except UnicodeDecodeError:
            content = notes_file.read_text(encoding='utf-8', errors='replace')

    # Use the consistent NOTE_SEPARATOR
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    checkbox_index = request.checkbox_index
    current_index = 0  # Global index to track checkbox positions
    
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        modified = False
        
        for i, line in enumerate(lines):
            match = checkbox_pattern.match(line)
            if match:
                if current_index == checkbox_index:
                    checked_char = 'x' if request.checked else ' '
                    lines[i] = f"{match.group(1)}{checked_char}{match.group(3)}"
                    modified = True
                    break
                current_index += 1
        
        if modified:
            notes[note_index] = '\n'.join(lines)
            # Join notes with the consistent separator
            updated_content = NOTE_SEPARATOR.join(notes)
            notes_file.write_text(updated_content)
            return {"status": "success"}
    
    return {"status": "error", "message": f"Checkbox not found (index {checkbox_index}, checked {current_index} boxes)"}

@app.post("/api/upload-file")
async def upload_file(file: UploadFile = File(...)):
    # Get file extension and MIME type
    extension = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
    
    # Determine if it's an image
    is_image = content_type and content_type.startswith('image/')
    
    # Choose appropriate directory based on file type
    if is_image:
        assets_path = Path("assets/images")
        relative_path = "images"
    else:
        assets_path = Path("assets/files")
        relative_path = "files"
    
    # Create directory if it doesn't exist
    assets_path.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    file_path = assets_path / file.filename
    with file_path.open("wb") as buffer:
        buffer.write(await file.read())
    
    return {
        "filePath": f"/assets/{relative_path}/{file.filename}",
        "isImage": is_image,
        "contentType": content_type
    }

def render_markdown(content, env):
    # Initialize markdown-it with zero preset and enable needed features
    md = MarkdownIt('zero')
    md.enable('table')        # Enable tables
    md.enable('emphasis')     # Enable bold/italic
    md.enable('link')        # Enable links
    md.enable('paragraph')   # Enable paragraphs
    md.enable('heading')     # Enable headings
    md.enable('list')        # Enable lists
    md.enable('image')       # Enable images
    md.enable('code')        # Enable code blocks
    md.enable('fence')       # Enable fenced code blocks
    md.enable('blockquote')  # Enable blockquotes
    md.enable('strikethrough')    # ~~strikethrough text~~
    md.enable('escape')          # Backslash escapes
    md.enable('backticks')    # Extended backtick features
    md.enable('inline')       # Enable inline-level rules
    
    md.use(task_list_plugin)  # Add our custom task list plugin
    
    # Add custom image renderer
    def render_image(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src')
        alt = token.content
        title = token.attrGet('title')
        
        # Remove angle brackets if present (from drag-and-drop)
        src = src.strip('<>')
        
        # Only render as image if it's in the images directory or is a remote image
        if src.startswith(('http://', 'https://')) or '/assets/images/' in src:
            # Handle both local and remote images
            img_url = src if src.startswith(('http://', 'https://', '/')) else f'/{src}'
            title_attr = f' title="{title}"' if title else ''
            
            # Wrap image in a link that opens in new window
            return (
                f'<a href="{img_url}" target="_blank" rel="noopener noreferrer">'
                f'<img src="{img_url}" alt="{alt}"{title_attr}>'
                f'</a>'
            )
        else:
            # For non-image files, render as a regular link
            filename = os.path.basename(src)
            return (
                f'<a href="{src}" target="_blank" rel="noopener noreferrer" '
                f'class="file-link">📎 {filename}</a>'
            )
    
    def render_checkbox(tokens, idx, options, env):
        token = tokens[idx]
        checked = 'checked' if token.attrGet('checked') == 'true' else ''
        checkbox_index = token.meta.get('checkbox_index', 0)
        task_id = token.meta.get('task_id', f'task_0_{checkbox_index}')
        
        # Always include id and name, with fallback values if needed
        return f'<input type="checkbox" {checked} data-checkbox-index="{checkbox_index}" id="{task_id}" name="{task_id}">'

    
    md.renderer.rules['image'] = render_image
    md.renderer.rules['checkbox'] = render_checkbox
    return md.render(content, env)

def clean_title(title):
    """Clean up title for filename use."""
    # Replace multiple spaces/underscores/hyphens with a single underscore
    cleaned = re.sub(r'[\s_-]+', '_', title)
    # Remove any non-alphanumeric characters (except underscores and periods)
    cleaned = re.sub(r'[^\w.-]', '', cleaned)
    return cleaned.strip('_')

def archive_website(url):
    """Archive a website to a single self-contained HTML file."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract domain from URL
        domain = urlparse(url).netloc

        # Create timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        display_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract title for filename
        title = clean_title(soup.title.string.strip()) if soup.title else "Untitled"
        base_filename = f"{timestamp}_{title}-{domain}"
        html_filename = f"{base_filename}.html"  # Store the exact filename
        
        # Create paths
        sites_path = Path("assets/sites")
        sites_path.mkdir(parents=True, exist_ok=True)
        
        # Save complete webpage with all assets
        save_path = sites_path / base_filename
        print(f"Saving to: {save_path}")
        
        # Create a session with headers
        session = requests.Session()
        session.headers.update(headers)
        
        # Save the complete webpage
        saveFullHtmlPage(url, str(save_path), session=session)
        
        # Extract metadata for .tags file
        description = None
        keywords = None
        
        # Extract meta description and keywords
        for meta in soup.find_all('meta'):
            if meta.get('name', '').lower() == 'description':
                description = meta.get('content', '')
            elif meta.get('name', '').lower() == 'keywords':
                keywords = meta.get('content', '')
        
        # If no description found, try to get first paragraph
        if not description:
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text().strip()[:200] + '...'

        # Save meta tags to .tags file
        tags_content = (
            f"URL: {url}\n"
            f"Title: {soup.title.string.strip() if soup.title else 'No title'}\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
            f"Keywords: {keywords if keywords else 'No keywords found'}\n"
            f"Description: {description if description else 'No description found'}\n"
        )
        tags_path = save_path.with_suffix('.tags')
        tags_path.write_text(tags_content, encoding='utf-8')

        return {
            'html': f'<div class="archived-link">'
                   f'<a href="{url}">{domain}</a><br/>'
                   f'<span class="archive-reference">'
                   f'<a href="/assets/sites/{html_filename}">site archive [{display_timestamp}]</a>'
                   f'</span>'
                   f'</div>',
            'markdown': f"[{domain} - [{display_timestamp}]](/assets/sites/{html_filename})"
        }

    except Exception as e:
        print(f"Error archiving website: {e}")
        return None

@app.get("/api/links")
async def get_links():
    """API endpoint to get the links section."""
    sites_path = Path("assets/sites")
    link_groups = {}
    
    if sites_path.exists():
        # First, filter for just HTML files
        html_files = [f for f in sites_path.glob("*.html")]
        
        for file in html_files:
            try:
                filename = file.name
                match = re.match(r'(\d{4}_\d{2}_\d{2}_\d{6})_([^-]+)-(.+?)\.html$', filename)
                if match:
                    timestamp, title, domain = match.groups()
                    display_timestamp = datetime.strptime(timestamp, "%Y_%m_%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                    
                    if domain not in link_groups:
                        link_groups[domain] = {
                            'domain': domain,
                            'archives': []
                        }
                    
                    link_groups[domain]['archives'].append({
                        'timestamp': display_timestamp,
                        'filename': filename
                    })
                    
                    # Sort archives by timestamp (newest first)
                    link_groups[domain]['archives'].sort(
                        key=lambda x: x['timestamp'],
                        reverse=True
                    )
            
            except Exception as e:
                print(f"Error processing link {file}: {e}")
                continue

    # Generate HTML output
    html_parts = []
    
    # Sort domains alphabetically
    for domain in sorted(link_groups.keys()):
        data = link_groups[domain]
        # Add domain as header
        html_parts.append(f'<div class="domain-group">')
        html_parts.append(f'<h3>{domain}</h3>')
        
        # Add archives for this domain
        for archive in data['archives']:
            file_path = f"/assets/sites/{archive['filename']}"
            html_parts.append(
                f'<div class="archived-link">'
                f'<span class="archive-reference">'
                f'<a href="{file_path}" target="_blank">site archive [{archive["timestamp"]}]</a>'
                f'</span>'
                f'</div>'
            )
        html_parts.append('</div>')

    result = {
        'html': '\n'.join(html_parts),
        'markdown': '\n'.join([
            f"[{data['domain']} - [{archive['timestamp']}]]({'/assets/sites/' + archive['filename']})" 
            for data in link_groups.values() 
            for archive in data['archives']
        ])
    }
    
    return result

@app.get("/api/themes")
async def get_themes():
    """Return list of available themes"""
    return list(THEMES.keys())

def get_config_file():
    """Get the path to the config file, creating directories if needed."""
    # Get the config directory for the current platform
    config_dir = Path(platformdirs.user_config_dir("noteflow"))
    
    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir / "noteflow.json"

def load_config():
    """Load configuration from JSON file or create default if not exists."""
    config_file = get_config_file()
    
    # Default configuration
    default_config = {
        "theme": "dark-orange"
    }
    
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                # If theme doesn't exist, update config file with default theme
                if config.get('theme') not in THEMES:
                    print(f"Warning: Theme '{config.get('theme')}' not found, defaulting to dark-orange")
                    config['theme'] = default_config['theme']
                    # Save the updated config with the default theme
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4)
                return config
        else:
            # Create new config file with defaults
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config

def save_config(config):
    """Save configuration to JSON file."""
    config_file = get_config_file()
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Update the CURRENT_THEME initialization
config = load_config()
CURRENT_THEME = config.get('theme', 'light-blue')
if CURRENT_THEME not in THEMES:  # Double-check the theme exists
    CURRENT_THEME = 'dark-orange'
    
# Add new endpoint to save theme
@app.post("/api/save-theme")
async def save_theme(theme: str = Form(...)):
    if theme not in THEMES:
        raise HTTPException(status_code=400, detail="Invalid theme")
    
    config = load_config()
    config['theme'] = theme
    
    if save_config(config):
        global CURRENT_THEME
        CURRENT_THEME = theme
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save theme")
    
@app.post("/api/shutdown")
async def shutdown():
    """Shutdown this specific instance of the application using multiple approaches"""
    pid = os.getpid()
    
    def shutdown_server():
        try:
            # Get the current process
            process = psutil.Process(pid)
            
            # First try to terminate all child processes
            children = process.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                    time.sleep(0.1)  # Give it a moment to terminate
                    if child.is_running():
                        child.kill()  # Force kill if still running
                except:
                    pass
            
            # Try different shutdown approaches based on platform
            if platform.system() == 'Windows':
                os.kill(pid, signal.CTRL_C_EVENT)
            else:
                # macOS/Linux specific handling
                try:
                    # Try SIGTERM first
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)  # Give it time to terminate gracefully
                    
                    # If still running, try SIGINT
                    if psutil.pid_exists(pid):
                        os.kill(pid, signal.SIGINT)
                        time.sleep(0.5)
                    
                    # If still running, force kill
                    if psutil.pid_exists(pid):
                        process.kill()
                except:
                    # Last resort: force kill
                    process.kill()
            
        except Exception as e:
            # Force exit if all else fails
            os._exit(0)
    
    # Schedule the shutdown with a slight delay
    from asyncio import get_event_loop
    loop = get_event_loop()
    loop.call_later(0.5, shutdown_server)
    
    return JSONResponse({"status": "shutting down"})

def open_browser(url):
    system = platform.system()
    try:
        if system == "Windows":
            webbrowser.open(url, new=2)
        elif system == "Darwin":  # macOS
            webbrowser.get('safari').open(url, new=2)
        elif system == "Linux":
            if "microsoft" in platform.uname().release.lower():
                # Windows Subsystem for Linux
                webbrowser.get('windows-default').open(url, new=2)
            else:
                webbrowser.open(url, new=2)
        else:
            webbrowser.open(url, new=2)
    except webbrowser.Error as e:
        print(f"Could not open browser: {e}. Please open manually.")

def main():
    print("Running noteflow...")
    # Get current directory name
    current_dir = Path.cwd().name
    
    # Find available port
    port = find_free_port()
    set_app_port(port)
    
    # Initialize notes file
    init_notes_file()
    
    # Open web browser before starting server
    open_browser(f'http://localhost:{port}')
    
    # Configure logging to suppress access logs
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "DEBUG"
    
    # Start server with modified logging
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="debug",
        log_config=log_config,
        access_log=False
    )

if __name__ == "__main__":
    main()