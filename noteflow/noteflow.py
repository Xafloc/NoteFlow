from fastapi import FastAPI, HTTPException, Path, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import socket
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

def saveFullHtmlPage(url, pagepath='page', session=requests.Session(), html=None):
    """Save web page html and supported contents"""
    def savenRename(soup, pagefolder, session, url, tag, inner):
        if not os.path.exists(pagefolder):
            os.makedirs(pagefolder, exist_ok=True)
        
        for res in soup.findAll(tag):
            if res.has_attr(inner):
                try:
                    # Get the URL and remove query parameters
                    original_url = res.get(inner)
                    clean_url = original_url.split('?')[0]
                    
                    # Get original extension
                    original_ext = os.path.splitext(clean_url)[1]
                    if original_ext:
                        # Keep original extension if it exists
                        ext = original_ext
                    else:
                        # Try to guess extension from content type
                        ext = mimetypes.guess_extension(session.get(clean_url).headers.get('content-type', '')) or '.txt'
                    
                    # Create base filename without extension
                    base_filename = os.path.splitext(os.path.basename(clean_url))[0]
                    if not base_filename:  # If filename is empty after cleaning
                        continue
                        
                    # Clean the base filename
                    base_filename = re.sub('\W+', '_', base_filename)
                    base_filename = base_filename.strip('_')
                    
                    # Combine clean base filename with original extension
                    filename = base_filename + ext
                    
                    fileurl = urljoin(url, original_url)
                    filepath = os.path.join(pagefolder, filename)
                    
                    # Update the reference in the HTML
                    res[inner] = os.path.join(os.path.basename(pagefolder), filename)
                    
                    if not os.path.isfile(filepath):
                        try:
                            response = session.get(fileurl)
                            if response.status_code == 200:
                                with open(filepath, 'wb') as file:
                                    file.write(response.content)
                        except Exception as e:
                            print(f"Failed to download {fileurl}: {e}")
                            continue
                            
                except Exception as exc:
                    print(f"Error processing {tag} {inner}: {exc}")
                    continue

    if not html:
        html = session.get(url).text
    
    soup = BeautifulSoup(html, "html.parser")
    path, _ = os.path.splitext(pagepath)
    pagefolder = path+'_files'
    
    tags_inner = {'img': 'src', 'link': 'href', 'script': 'src'}
    for tag, inner in tags_inner.items():
        savenRename(soup, pagefolder, session, url, tag, inner)
    
    with open(path+'.html', 'wb') as file:
        file.write(soup.prettify('utf-8'))

def create_directories():
    # Define the directories to be created relative to the current working directory
    base_path = Path.cwd()
    directories = [
        base_path / "assets",
        base_path / "assets/images",
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
        'default-light': {
         # Main colors
        'background': '#1e3c72',          # Main background color
        'accent': '#ff8c00',              # Accent color
        'text_color': '#757575',          # Global text color

        # Labels
        'label_background': '#000000',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'theme_label_border': '#000000',
        'header_text': '#666666',         # Label text color

        # Content boxes
        'box_background': '#ffffff',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'theme_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#ffffff',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Edit popup
        'edit_overlay_background': '#313437',  # Popup overlay
        'edit_background': '#ffffff',         # Popup background
        'edit_border': '#000000',             # Popup border
        'edit_input_background': '#ffffff',    # Popup input background
        'edit_input_border': '#26292c',        # Popup input border

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
    },
    'default-dark': {
         # Main colors
        'background': '#1e3c72',          # Main background color
        'accent': '#ff8c00',              # Accent color
        'text_color': '#757575',          # Global text color

        # Labels
        'label_background': '#000000',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'theme_label_border': '#000000',
        'header_text': '#666666',         # Label text color

        # Content boxes
        'box_background': '#26292c',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'theme_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#313437',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Edit popup
        'edit_overlay_background': '#313437',  # Popup overlay
        'edit_background': '#26292c',         # Popup background
        'edit_border': '#000000',             # Popup border
        'edit_input_background': '#26292c',    # Popup input background
        'edit_input_border': '#26292c',        # Popup input border

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
    },
    'dark-orange': {
        # Main colors
        'background': '#313437',          # Main background color
        'accent': '#df8a3e',              # Accent color
        'text_color': '#757575',          # Global text color

        # Labels
        'label_background': '#313437',    # Label backgrounds
        'note_label_border': '#000000',   # Label borders
        'links_label_border': '#000000',
        'theme_label_border': '#000000',
        'header_text': '#5084a7',         # Label text color

        # Content boxes
        'box_background': '#26292c',      # Box backgrounds
        'note_border': '#000000',         # Box borders
        'tasks_border': '#000000',
        'theme_border': '#000000',
        'links_border': '#000000',

        # Input fields
        'input_background': '#26292c',    # Input backgrounds
        'input_border': '#26292c',        # Input borders

        # Edit popup
        'edit_overlay_background': '#313437',  # Popup overlay
        'edit_background': '#26292c',         # Popup background
        'edit_border': '#000000',             # Popup border
        'edit_input_background': '#26292c',    # Popup input background
        'edit_input_border': '#26292c',        # Popup input border

        # Code highlighting
        'code_background': '#fdf6e3',     # Code block background
        'code_style': 'github',           # Highlight.js theme

        # Button Colors
        'button_bg': '#313437',
        'button_text': '#ff8c00',
    }
}

# Manual theme selector (change this value to test different themes)
CURRENT_THEME = 'default-dark'  # Change to 'dark' to test dark theme

# Serve the fonts
@app.get("/fonts/{path:path}")
async def serve_fonts(path: str):
    return StaticFiles(directory=Path(__file__).parent / "fonts")(path)

# Serve the favicon
@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")

# Enhanced regex to match "[ ] task", "- [ ] task", and sub-bullets like "  - [ ] task"
checkbox_pattern = re.compile(r'^(\s*[-*+]? *\[)([xX ]?)(\] .+)')

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
                    # Assign checkbox_index to token
                    checkbox_index = state.env.get('checkbox_index', 0)
                    token.meta = {'checkbox_index': checkbox_index}
                    state.env['checkbox_index'] = checkbox_index + 1  # Increment for next checkbox
                    state.pos += 3
                return True
        return False

    def render_checkbox(tokens, idx, options, env):
        token = tokens[idx]
        checked = 'checked' if token.attrGet('checked') == 'true' else ''
        note_index = env.get('note_index', 0)
        checkbox_index = token.meta['checkbox_index']
        return f'<input type="checkbox" {checked} data-note-index="{note_index}" data-checkbox-index="{checkbox_index}">'

    md.inline.ruler.before('emphasis', 'task_list', task_list_rule)
    md.renderer.rules['checkbox'] = render_checkbox

    def render_checkbox(tokens, idx, options, env):
        token = tokens[idx]
        checked = 'checked' if token.attrGet('checked') == 'true' else ''
        note_index = env.get('note_index', 0)
        checkbox_index = token.meta['checkbox_index']
        return f'<input type="checkbox" {checked} data-note-index="{note_index}" data-checkbox-index="{checkbox_index}">'

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
            padding: 15px;
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
            gap: 15px;
        }}
        .left-column {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 15px;
            width: 100%;
        }}
        .right-column {{
            flex: 0 0 325px;
            width: 325px;
        }}
        .input-box {{
            background: {colors['box_background']};
            margin-top: -15px;
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
            margin-top: -15px;
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
            max-height: 300px;
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
            font-size: 75%;
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
        .edit-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: {colors['edit_overlay_background']};
            z-index: 1000;
        }}
        .edit-container {{
            position: relative;
            width: 80%;
            max-width: 800px;
            margin: 50px auto;
            background: {colors['edit_background']};
            padding: 5px;
            border: 1px solid {colors['edit_border']};
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            font-family: 'space_monoregular', Arial, sans-serif;
        }}
        .edit-textarea {{
            width: 100%;
            min-height: 300px;
            margin: 10px 0;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid {colors['edit_input_border']};
            background-color: {colors['edit_input_background']};
            color: {colors['text_color']};
            font-family: inherit;
            font-size: 0.9rem;
            resize: vertical;
        }}
        .edit-buttons {{
            text-align: right;
            padding: 5px;
        }}
        .edit-button {{
            background: #000;
            color: {colors['accent']};
            border: none;
            padding: 5px 15px;
            margin-left: 10px;
            cursor: pointer;
            font-family: inherit;
        }}
        .theme-selector {{
            position: fixed;
            bottom: 15px;
            right: 0;
            display: flex;
            align-items: flex-start;
            z-index: 1000;
            transform: translateX(calc(100% - 19px)); /* Hide content, show label */
            transition: transform 0.3s ease;
        }}

        .theme-selector:hover {{
            transform: translateX(0); /* Show everything on hover */
        }}

        .theme-label {{
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
            border: 1px solid {colors['theme_label_border']};
            cursor: pointer;
        }}

        .theme-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}

        .theme-content {{
            background: {colors['box_background']};
            padding: 10px;
            border: 1px solid {colors['theme_border']};
            border-left: none;
            border-bottom-left-radius: 7px;
            width: 150px; /* Fixed width for content */
            height: 75px; /* Fixed height for now */
            display: flex;
            flex-direction: column;
            gap: 10px;
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
        .theme-save-btn {{
            background: {colors['button_bg']};
            color: {colors['button_text']};
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.8rem;
            width: 100%;
        }}

        .theme-save-btn:hover {{
            opacity: 0.9;
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
                    <input type="text" id="noteTitle" name="noteTitle" placeholder="Enter note title here...">
                    <textarea id="noteInput" name="noteInput" placeholder="Enter note in Markdown format.."></textarea>
                </div>

                <!-- Notes Section -->
                <div class="notes-container" id="notes">
                </div>
            </form>

        </div>

        <!-- Right Column -->
        <div class="right-column">
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
                        $(document).ready(function() {
                            loadNotes();
                            loadLinks();
                            
                            // Single form submission handler
                            async function handleSubmit(e) {
                                e.preventDefault();
                                const title = $('#noteTitle').val().trim();
                                const content = $('#noteInput').val().trim();
                                
                                if (!content) return;

                                // Check if content contains a +http link
                                const hasArchiveLink = content.includes('+http');
                                if (hasArchiveLink) {
                                    $('.loading-overlay').css('display', 'flex');
                                }

                                try {
                                    const response = await fetch('/api/notes', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ title, content })
                                    });

                                    if (!response.ok) {
                                        throw new Error('Failed to add note');
                                    }
                                    
                                    // Clear inputs
                                    $('#noteTitle').val('');
                                    $('#noteInput').val('');
                                    $('#noteInput').css('height', 'auto');

                                    // Refresh both notes and links
                                    await loadNotes();
                                    loadLinks();
                                    
                                } catch (error) {
                                    console.error('Error adding note:', error);
                                    alert('Failed to add note');
                                } finally {
                                    // Hide loading overlay
                                    $('.loading-overlay').css('display', 'none');
                                }
                            }

                            // Form submission via button
                            $('#noteForm').on('submit', handleSubmit);

                            // Form submission via Ctrl+Enter
                            $('#noteInput').on('keydown', function(e) {
                                if (e.ctrlKey && e.key === 'Enter') {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            });
                        });

                        function loadLinks() {
                            $.get('/api/links')
                                .done(function(html) {
                                    $('#linksSection').html(html);
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

                        document.getElementById('noteForm').addEventListener('keydown', async (e) => {
                            if (e.ctrlKey && e.key === 'Enter') {
                                e.preventDefault();
                                await handleSubmit(e);
                            }
                        });

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

                        document.getElementById('noteForm').addEventListener('submit', async (e) => {
                            e.preventDefault();
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
                        });

                        document.addEventListener('click', async (event) => {
                            if (event.target.matches('input[type="checkbox"]')) {
                                const checkbox = event.target;
                                const checkboxIndex = checkbox.getAttribute('data-checkbox-index');
                                const isChecked = checkbox.checked;
                                
                                if (checkboxIndex !== null) {
                                    try {
                                        const response = await fetch('/api/update-checkbox', {
                                            method: 'PATCH',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({
                                                checked: isChecked,
                                                checkbox_index: parseInt(checkboxIndex)
                                            })
                                        });
                                        
                                        await loadNotes();
                                        await updateActiveTasks();
                                        
                                    } catch (error) {
                                        console.error('Error updating checkbox:', error);
                                    }
                                }
                            }
                        });

                        async function updateActiveTasks() {
                            const response = await fetch('/api/notes');
                            const tasksContainer = document.getElementById('activeTasks');
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(await response.text(), 'text/html');
                            
                            // Select all checkboxes that are unchecked across different formats
                            const uncheckedTasks = Array.from(doc.querySelectorAll('input[type="checkbox"]:not(:checked)'));
                            
                            tasksContainer.innerHTML = ''; // Clear existing tasks
                            
                            uncheckedTasks.forEach((checkbox) => {
                            const originalCheckboxIndex = checkbox.getAttribute('data-checkbox-index');
                            const taskItem = checkbox.closest('li') || checkbox.closest('p'); // Support bullets and inline tasks

                            if (taskItem) {
                                const taskText = taskItem.textContent.trim();
                                
                                const taskElement = document.createElement('div');
                                taskElement.className = 'task-item';
                                taskElement.innerHTML = `
                                    <input type="checkbox" 
                                        class="mt-1 consolidated-task" 
                                        data-checkbox-index="${originalCheckboxIndex}">
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
Drag & Drop images to upload...
Start Links with + to archive websites...

# Scroll for Markdown Examples
- [ ] Tasks
- Bullets
    - Sub-bullets
- **Bold** and *italic*`;
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
                                    const response = await fetch('/api/upload-image', {
                                        method: 'POST',
                                        body: formData
                                    });

                                    if (response.ok) {
                                        const { filePath } = await response.json();
                                        const markdownLink = `![${file.name}](<${filePath}>)`;
                                        insertAtCursor(noteInput, markdownLink);
                                    } else {
                                        alert('Failed to upload image');
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

                        document.addEventListener('DOMContentLoaded', function() {
                            const noteInput = document.getElementById('noteInput');
                            
                            noteInput.addEventListener('keydown', function(e) {
                                if (e.key === 'Tab') {
                                    e.preventDefault();
                                    
                                    // Get cursor position
                                    const start = this.selectionStart;
                                    const end = this.selectionEnd;
                                    
                                    // Insert tab at cursor position
                                    this.value = this.value.substring(0, start) + '\t' + this.value.substring(end);
                                    
                                    // Move cursor after tab
                                    this.selectionStart = this.selectionEnd = start + 1;
                                }
                            });
                        });

                        let currentEditingNoteIndex = null;

                        async function editNote(noteIndex) {
                            currentEditingNoteIndex = noteIndex;
                            
                            try {
                                const response = await fetch(`/api/notes/${noteIndex}`);
                                if (!response.ok) throw new Error('Failed to fetch note');
                                
                                const noteData = await response.json();
                                document.getElementById('editNoteContent').value = noteData.content;
                                document.getElementById('editOverlay').style.display = 'block';
                            } catch (error) {
                                console.error('Error fetching note:', error);
                                alert('Failed to load note for editing');
                            }
                        }

                        async function saveNote() {
                            if (currentEditingNoteIndex === null) return;
                            
                            const content = document.getElementById('editNoteContent').value;
                            
                            try {
                                const response = await fetch(`/api/notes/${currentEditingNoteIndex}`, {
                                    method: 'PUT',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ content })
                                });
                                
                                if (!response.ok) throw new Error('Failed to update note');
                                
                                // Close overlay and refresh notes
                                closeEditOverlay();
                                await loadNotes();
                            } catch (error) {
                                console.error('Error updating note:', error);
                                alert('Failed to update note');
                            }
                        }

                        function closeEditOverlay() {
                            document.getElementById('editOverlay').style.display = 'none';
                            currentEditingNoteIndex = null;
                        }

                        // Add tab capture for edit overlay textarea
                        document.addEventListener('DOMContentLoaded', function() {
                            const editNoteContent = document.getElementById('editNoteContent');
                            
                            editNoteContent.addEventListener('keydown', function(e) {
                                if (e.key === 'Tab') {
                                    e.preventDefault();
                                    
                                    // Get cursor position
                                    const start = this.selectionStart;
                                    const end = this.selectionEnd;
                                    
                                    // Insert tab at cursor position
                                    this.value = this.value.substring(0, start) + '\t' + this.value.substring(end);
                                    
                                    // Move cursor after tab
                                    this.selectionStart = this.selectionEnd = start + 1;
                                }
                            });
                        });

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
    <!-- Edit Note Overlay -->
    <div id="editOverlay" class="edit-overlay">
        <div class="edit-container">
            <div class="section-label">
                <span>e</span>
                <span>d</span>
                <span>i</span>
                <span>t</span>
            </div>
            <textarea id="editNoteContent" class="edit-textarea"></textarea>
            <div class="edit-buttons">
                <button onclick="saveNote()" class="edit-button">Save</button>
                <button onclick="closeEditOverlay()" class="edit-button">Cancel</button>
            </div>
        </div>
    </div>
    <!-- Add before </body> -->
    <div class="theme-selector">
        <div class="theme-label">
            <span>t</span>
            <span>h</span>
            <span>e</span>
            <span>m</span>
            <span>e</span>
        </div>
        <div class="theme-content">
            <select id="themeSelector">
                <!-- Will be populated dynamically -->
            </select>
            <button class="theme-save-btn" onclick="saveTheme()">Save Theme</button>
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

        // Initialize when the page loads
        document.addEventListener('DOMContentLoaded', function() {{
            initializeTheme();
        }});
        
        // ... rest of your JavaScript ...
    </script>
</head>
    """ + html_content

@app.get("/api/notes")
async def get_notes():
    notes_file = init_notes_file()
    content = notes_file.read_text()
    
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    html_notes = []
    global_checkbox_index = 0
    
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        timestamp = lines[0]
        note_content = '\n'.join(lines[1:])
        
        env = {'note_index': note_index, 'checkbox_index': global_checkbox_index}
        
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
                <div class="post-header" onclick="editNote({note_index})" style="cursor: pointer;">
                    Posted: {timestamp} <span class="edit-label">(click to edit)</span>
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
        note_content = '\n'.join(lines[1:])
        return {"timestamp": timestamp, "content": note_content}
    
    raise HTTPException(status_code=404, detail="Note not found")

# Add new endpoint to update a specific note
@app.put("/api/notes/{note_index}")
async def update_note(note_index: int, note: Note):
    notes_file = init_notes_file()
    content = notes_file.read_text()
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    if 0 <= note_index < len(notes):
        # Process any new +https:// links in the updated content
        processed_content = await process_plus_links(note.content)
        
        # Get the original timestamp from the note
        original_timestamp = notes[note_index].split('\n')[0]
        
        # Format updated note with original timestamp
        title = f" - {note.title}" if note.title else ""
        formatted_note = f"{original_timestamp}{title}\n\n{processed_content.strip()}"  # Keep double newline after header
        
        # Replace the note at the specified index
        notes[note_index] = formatted_note
        
        # Join all notes back together with consistent separator
        updated_content = f"\n---\n\n".join(notes)  # Add newlines around separator
        
        # Write back to file
        with notes_file.open('w') as f:
            f.write(updated_content)
        
        return {"status": "success"}
    
    raise HTTPException(status_code=404, detail="Note not found")

async def process_plus_links(content):
    """Process +https:// links in the content and create local copies."""
    async def replace_link(match):
        url = match.group(1)
        local_path = archive_website(url)
        if local_path:
            base_name = Path(local_path).stem
            parts = base_name.split('_', 4)
            
            if len(parts) >= 5:
                timestamp = '_'.join(parts[:4])
                title_domain = parts[4]
                
                title_parts = title_domain.rsplit('-', 1)
                if len(title_parts) >= 2:
                    title = title_parts[0].replace('_', ' ')
                    display_timestamp = datetime.strptime(timestamp, "%Y_%m_%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                    
                    return (
                        f'<div class="archived-link">'
                        f'<a href="{url}">{title}</a><br/>'
                        f'<span class="archive-reference">'
                        f'<a href="/assets/sites/{Path(local_path).name}">site archive [{display_timestamp}]</a>'
                        f'</span>'
                        f'</div>'
                    )
            
        return url

    pattern = r'\+((https?://)[^\s]+)'
    matches = re.finditer(pattern, content)
    replacements = []
    for match in matches:
        replacement = await replace_link(match)
        replacements.append((match.start(), match.end(), replacement))
    
    result = list(content)
    for start, end, replacement in reversed(replacements):
        result[start:end] = replacement
    
    return ''.join(result)

@app.post("/api/notes")
async def add_note(note: Note):
    notes_file = init_notes_file()
    current_content = notes_file.read_text().strip()
    
    # Process +https:// links in the content
    processed_content = await process_plus_links(note.content)
    
    # Format new note
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f" - {note.title}" if note.title else ""
    formatted_note = f"## {timestamp}{title}\n\n{processed_content}"
    
    # Combine with existing content
    if current_content:
        new_content = f"{formatted_note}\n{NOTE_SEPARATOR}\n{current_content}"
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
    content = notes_file.read_text()
    notes = [note.strip() for note in content.split("---") if note.strip()]
    
    checkbox_index = request.checkbox_index
    current_index = 0  # Global index to track checkbox positions
    
    # Try to update the checkbox
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        for i, line in enumerate(lines):
            match = checkbox_pattern.match(line)
            if match:
                if current_index == checkbox_index:
                    # Replace only the checkbox state
                    checked_char = 'x' if request.checked else ' '
                    new_line = f"{match.group(1)}{checked_char}{match.group(3)}"
                    lines[i] = new_line
                    # Update the note and write back to the file
                    notes[note_index] = '\n'.join(lines)
                    updated_content = "\n---\n".join(notes)
                    notes_file.write_text(updated_content)
                    return {"status": "success"}
                current_index += 1
    
    return {"status": "success"}

@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    assets_path = Path("assets/images")
    assets_path.mkdir(parents=True, exist_ok=True)  # Create directories if they don't exist

    file_path = assets_path / file.filename

    with file_path.open("wb") as buffer:
        buffer.write(await file.read())

    return {"filePath": f"/assets/images/{file.filename}"}

def render_markdown(content, env):
    md = MarkdownIt()
    task_list_plugin(md)
    
    # Add custom image renderer
    def render_image(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src')
        alt = token.content
        title = token.attrGet('title')
        
        # Remove angle brackets if present (from drag-and-drop)
        src = src.strip('<>')
        
        # Handle both local and remote images
        if src.startswith(('http://', 'https://')):
            # Remote image - use as is
            img_url = src
        else:
            # Local image - ensure proper path
            img_url = src if src.startswith('/') else f'/{src}'
        
        title_attr = f' title="{title}"' if title else ''
        
        # Wrap image in a link that opens in new window
        return (
            f'<a href="{img_url}" target="_blank" rel="noopener noreferrer">'
            f'<img src="{img_url}" alt="{alt}"{title_attr}>'
            f'</a>'
        )
    
    md.renderer.rules['image'] = render_image
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
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Create timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        
        # Extract title for filename
        title = clean_title(soup.title.string.strip()) if soup.title else "Untitled"
        domain = urlparse(url).netloc
        base_filename = f"{timestamp}_{title}-{domain}"
        
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
            f"Keywords: {keywords if keywords else 'No keywords found'}\n"
            f"Description: {description if description else 'No description found'}\n"
        )
        tags_path = save_path.with_suffix('.tags')
        tags_path.write_text(tags_content, encoding='utf-8')

        return str(save_path.with_suffix('.html'))

    except Exception as e:
        print(f"Error archiving website: {e}")
        return None

def render_links_section():
    """Render the links section by reading directly from the sites directory."""
    sites_path = Path("assets/sites")
    links = []
    
    if sites_path.exists():
        for file in sites_path.glob("*.html"):
            try:
                parts = file.stem.rsplit('-', 1)  # Split on last hyphen
                if len(parts) >= 2:
                    title = parts[0].replace('_', ' ')
                    domain = parts[1]
                    links.append(f'<a href="https://{domain}">{title}</a> - <a href="/assets/sites/{file.name}">local copy</a>')
            except Exception as e:
                print(f"Error processing link {file}: {e}")
                continue

    return HTMLResponse('<br>'.join(links))

@app.get("/api/links")
async def get_links():
    """API endpoint to get the links section."""
    sites_path = Path("assets/sites")
    link_groups = {}  # Dictionary to group archives by domain
    
    if sites_path.exists():
        for file in sites_path.glob("*.html"):
            try:
                parts = file.stem.split('_', 4)
                if len(parts) >= 5:
                    timestamp = '_'.join(parts[:4])
                    title_domain = parts[4]
                    
                    title_parts = title_domain.rsplit('-', 1)
                    if len(title_parts) >= 2:
                        title = title_parts[0].replace('_', ' ')
                        domain = title_parts[1]
                        display_timestamp = datetime.strptime(timestamp, "%Y_%m_%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                        clean_title = title.split('_')[-1] if '_' in title else title
                        
                        # Create archive entry
                        archive_entry = {
                            'timestamp': display_timestamp,
                            'filename': file.name
                        }
                        
                        # Group by domain
                        if domain not in link_groups:
                            link_groups[domain] = {
                                'title': clean_title,
                                'archives': []
                            }
                        link_groups[domain]['archives'].append(archive_entry)
                        
                        # Sort archives by timestamp (newest first)
                        link_groups[domain]['archives'].sort(
                            key=lambda x: x['timestamp'],
                            reverse=True
                        )
                        
            except Exception as e:
                print(f"Error processing link {file}: {e}")
                continue

    # Generate HTML for each group
    html_parts = []
    for domain, data in link_groups.items():
        archives_html = '\n'.join(
            f'<span class="archive-reference">'
            f'<a href="/assets/sites/{archive["filename"]}" target="_blank" rel="noopener noreferrer">site archive [{archive["timestamp"]}]</a>'
            f'</span>'
            for archive in data['archives']
        )
        
        html_parts.append(
            f'<div class="archived-link">'
            f'<a href="https://{domain}" target="_blank" rel="noopener noreferrer">{data["title"]}</a>'
            f'{archives_html}'
            f'</div>'
        )

    return HTMLResponse(''.join(html_parts))

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
        "theme": "default-light"
    }
    
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
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
CURRENT_THEME = config.get('theme', 'default-light')

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

def main():
    print("Running noteflow...")
    # Get current directory name
    current_dir = Path.cwd().name
    
    # Find available port
    port = find_free_port()
    
    # Initialize notes file
    init_notes_file()
    
    # Open browser
    webbrowser.open(f"http://localhost:{port}")
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()