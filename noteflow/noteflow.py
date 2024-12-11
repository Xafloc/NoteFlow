###############################################################################
# Imports
###############################################################################
import os
import sys
import re
import json
import mimetypes
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse, urljoin, quote, unquote
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Path as FastAPIPath, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from markdown_it import MarkdownIt
import platformdirs
import socket
import psutil
import platform
import signal
import time
from mdit_py_plugins.dollarmath import dollarmath_plugin

###############################################################################
# Constants & Configuration
###############################################################################
NOTE_SEPARATOR = "\n<!-- note -->\n"
APP_PORT = None
CURRENT_THEME = "dark-orange" # Default theme
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

# Theme Definitions
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

        # MathJax colors
        'math_color': '#e65100',
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

        # MathJax colors
        'math_color': '#e65100',
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

        # MathJax colors
        'math_color': '#e65100',
    }
}

def get_config_file():
    """Get the path to the config file, creating directories if needed."""
    config_dir = Path(platformdirs.user_config_dir("noteflow"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "noteflow.json"

def load_config():
    """Load configuration from JSON file or create default if not exists."""
    config_file = get_config_file()
    
    default_config = {
        "theme": "dark-orange"
    }
    
    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                if config.get('theme') not in THEMES:
                    print(f"Warning: Theme '{config.get('theme')}' not found, defaulting to dark-orange")
                    config['theme'] = default_config['theme']
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4)
                return config
        else:
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
    
config = load_config()
CURRENT_THEME = config.get('theme', 'light-blue')
if CURRENT_THEME not in THEMES:
    CURRENT_THEME = 'dark-orange'

###############################################################################
# Core Classes
###############################################################################
class NoteManager:
    """Central manager for notes collection.
    
    Attributes:
        notes (List[Note]): All notes
        checkbox_index (int): Counter for task IDs
        file_path (Path): Notes storage location
        needs_save (bool): Unsaved changes flag
        base_path (Path): Base directory for all file operations
    """
    def __init__(self, base_path: Path):
        self.notes: List[Note] = []
        self.checkbox_index: int = 0
        self.file_path: Optional[Path] = None
        self.needs_save: bool = False
        self.base_path = base_path
        self._load_notes()

    def _load_notes(self):
        """Initialize and load notes from file"""
        self.file_path = self.base_path / "notes.md"
        if not self.file_path.exists():
            self.file_path.write_text("")
            return

        try:
            # First try UTF-8
            content = self.file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # If UTF-8 fails, try Windows-1252 (cp1252)
                content = self.file_path.read_text(encoding='cp1252')
            except UnicodeDecodeError:
                # If both fail, use UTF-8 with error handling
                content = self.file_path.read_text(encoding='utf-8', errors='replace')

        self._parse_notes(content)

    def _parse_notes(self, content: str):
        """Parse raw content into Note objects"""
        self.notes = []
        
        # Split content by note separator and parse each note
        raw_notes = [n.strip() for n in content.split(NOTE_SEPARATOR) if n.strip()]
        for raw_note in raw_notes:
            # Remove excessive newlines
            raw_note = re.sub(r'\n{3,}', '\n', raw_note)
            if raw_note.startswith("## "):
                note = Note.from_text(raw_note, self)
                self.notes.append(note)

    def save(self):
        """Save notes to disk if modified"""
        if self.needs_save:
            content = self.render_notes()
            self.file_path.write_text(content, encoding='utf-8')
            self.needs_save = False

    def render_notes(self) -> str:
        """Render all notes with proper indexing"""
        rendered = []
        for note in self.notes:
            rendered.append(note.render())
        return NOTE_SEPARATOR.join(rendered)

    def get_active_tasks(self) -> List[Dict]:
        """Return all unchecked tasks"""
        tasks = []
        for note in self.notes:
            tasks.extend(note.get_unchecked_tasks())
        return tasks

    def add_note(self, title: str, content: str):
        """Add a new note"""
        note = Note(
            title=title,
            content=content,
            timestamp=datetime.now(),
            manager=self
        )
        self.notes.insert(0, note)  # Add to start of list
        self.needs_save = True

    def update_task(self, task_index: int, checked: bool):
        """Update task completion status"""
        for note in self.notes:
            if note.update_task(task_index, checked):
                self.needs_save = True
                return True
        return False

class Note:
    """Single note with content and tasks.
    
    Attributes:
        title (str): Note title
        content (str): Main content
        timestamp (datetime): Creation time
        manager (NoteManager): Parent manager
        tasks (List[Task]): Tasks in note
    """
    def __init__(self, title: str, content: str, timestamp: datetime, manager: NoteManager):
        self.title = title
        self.content = content
        self.timestamp = timestamp
        self.manager = manager
        self.tasks: List[Task] = []
        self._parse_tasks()

    @classmethod
    def from_text(cls, text: str, manager: NoteManager):
        """Create Note object from markdown text"""
        lines = text.split('\n', 1)
        header = lines[0].replace('## ', '')
        
        # Parse timestamp and title
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?: - )?(.*)?', header)
        if timestamp_match:
            timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S")
            title = timestamp_match.group(2) or ""
        else:
            timestamp = datetime.now()
            title = header

        content = lines[1] if len(lines) > 1 else ''
        return cls(title, content, timestamp, manager)

    def _parse_tasks(self):
        """Extract tasks from note content"""
        self.tasks = []
        checkbox_pattern = re.compile(r'\[([xX ])\]')  # Matches [x], [X], or [ ]
        
        for match in checkbox_pattern.finditer(self.content):
            task = Task(
                index=self.manager.checkbox_index,  # Get unique ID from manager
                checked=match.group(1).lower() == 'x',  # Check if marked with 'x' or 'X'
                text=self._extract_task_text(match.start())  # Get full task text
            )
            self.tasks.append(task)
            self.manager.checkbox_index += 1  # Increment global task counter

    def _extract_task_text(self, checkbox_pos: int) -> str:
        """Extract the full text of a task item"""
        # Find the end of the line
        content_after = self.content[checkbox_pos:]
        line_end = content_after.find('\n')
        if line_end == -1:
            line_end = len(content_after)
        
        # Include the checkbox markers in the task text for exact matching
        return content_after[:line_end].strip()

    def render(self) -> str:
        """Render note with proper task indexing"""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        title_str = f" - {self.title}" if self.title else ""
        # Add an extra newline before the note separator
        return f"## {timestamp_str}{title_str}\n\n{self.content}\n"

    def get_unchecked_tasks(self) -> List[Dict]:
        """Return unchecked tasks"""
        return [
            {
                'index': task.index,
                'text': task.text.replace('[x]', '').replace('[ ]', '').strip(),  # Remove checkbox markers
                'note_title': self.title,
                'timestamp': self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            for task in self.tasks
            if not task.checked
        ]

    def update_task(self, task_index: int, checked: bool) -> bool:
        for task in self.tasks:
            if task.index == task_index:
                old_mark = '[x]' if not checked else '[ ]'
                new_mark = '[x]' if checked else '[ ]'
                
                # The original line for this task
                old_line = task.text
                # Create the new line by replacing the checkbox in the original line
                new_line = old_line.replace('[x]', '[ ]').replace('[ ]', new_mark, 1)
                
                # Update both the note content and the task text using the exact line replacement
                self.content = self.content.replace(old_line, new_line, 1)
                task.text = new_line
                task.checked = checked
                return True
        return False

    def update(self, title: str, content: str):
        """Update note content and title"""
        self.title = title
        self.content = content
        self.tasks = []
        self._parse_tasks()
        self.manager.needs_save = True

class Task:
    """Checkbox task within a note.
    
    Attributes:
        index (int): Unique ID
        checked (bool): Completion state
        text (str): Task description
    """
    def __init__(self, index: int, checked: bool, text: str):
        self.index = index
        self.checked = checked
        self.text = text

###############################################################################
# FastAPI Setup
###############################################################################
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/fonts", StaticFiles(directory=Path(__file__).parent / "fonts"), name="fonts")

# Function to mount assets directory
def mount_assets_directory(app: FastAPI, base_path: Path):
    """Mount the assets directory for the given base path"""
    app.mount("/assets", StaticFiles(directory=base_path / "assets"), name="assets")

###############################################################################
# Helper Functions
###############################################################################
def create_directories(base_path: Path):
    """Create necessary directories relative to the given base path"""
    directories = [
        base_path / "assets",
        base_path / "assets/images",
        base_path / "assets/files",
        base_path / "assets/sites"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def find_free_port(start_port=8000):
    """Find an available port starting from start_port."""
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("No free ports found")

def set_app_port(port: int):
    """Set the application port globally."""
    global APP_PORT
    APP_PORT = port

def parse_markdown(content: str) -> str:
    """Convert markdown to HTML with proper task handling and extended features"""
    md = MarkdownIt('zero')
    
    # Enable core features
    md.enable('table')        # Enable tables
    md.enable('emphasis')     # Enable bold/italic
    md.enable('link')         # Enable links
    md.enable('paragraph')    # Enable paragraphs
    md.enable('heading')      # Enable headings
    md.enable('list')         # Enable lists
    md.enable('image')        # Enable images
    md.enable('code')         # Enable code blocks
    md.enable('fence')        # Enable fenced code blocks
    md.enable('blockquote')   # Enable blockquotes
    md.enable('strikethrough')# ~~strikethrough text~~
    md.enable('escape')       # Backslash escapes
    md.enable('backticks')    # Extended backtick features
    md.enable('html_block')   # Enable HTML blocks
    md.enable('inline')       # Enable inline-level rules
   
    # Use the dollar math plugin
    md.use(dollarmath_plugin)

    # Define the render_math function to handle math tokens
    def render_math(tokens, idx, options, env):
        token = tokens[idx]
        content = token.content
        is_block = token.type == 'math_block'
        
        if is_block:
            # Block math
            return f'<div class="math-display">$${content}$$</div>'
        else:
            # Inline math
            return f'<span class="math-inline">${content}$</span>'
        
    # Set the math renderers
    md.renderer.rules['math_inline'] = render_math
    md.renderer.rules['math_block'] = render_math

    # Custom renderers
    def render_image(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src')
        alt = token.content
        title = token.attrGet('title')
        
        # Remove angle brackets if present (from drag-and-drop)
        src = src.strip('<>')
        
        # Handle both local and remote images
        if src.startswith(('http://', 'https://')) or '/assets/images/' in src:
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

    def render_blockquote_open(tokens, idx, options, env):
        return '<blockquote class="markdown-blockquote">'

    def render_blockquote_close(tokens, idx, options, env):
        return '</blockquote>'

    def render_math(tokens, idx, options, env):
        token = tokens[idx]
        content = token.content
        is_block = token.type == 'math_block'
        
        if is_block:
            return f'<div class="math-display">$${content}$$</div>'
        else:
            return f'<span class="math-inline">${content}$</span>'

    # Custom checkbox rule
    def checkbox_replace(state, silent):
        pos = state.pos
        max_pos = state.posMax
        
        # Check for checkbox pattern
        if (pos + 3 > max_pos or 
            state.src[pos] != '[' or 
            state.src[pos + 2] != ']' or 
            state.src[pos + 1] not in [' ', 'x', 'X']):
            return False
            
        # Don't process if we're just scanning
        if silent:
            return False
            
        checked = state.src[pos + 1].lower() == 'x'
        
        # Get the full line for task matching
        line_start = pos
        while line_start > 0 and state.src[line_start - 1] != '\n':
            line_start -= 1
        
        line_end = pos
        while line_end < max_pos and state.src[line_end] != '\n':
            line_end += 1
            
        task_text = state.src[line_start:line_end].strip()
        
        # Find matching task
        task_index = None
        for note in note_manager.notes:
            for task in note.tasks:
                if task_text == task.text.strip():
                    task_index = task.index
                    break
            if task_index is not None:
                break
                
        # Create token
        token = state.push('checkbox_inline', 'input', 0)
        token.markup = state.src[pos:pos + 3]
        token.attrs = token.attrs or []
        token.attrs.append(['checked', 'true' if checked else 'false'])
        token.attrs.append(['task_index', str(task_index) if task_index is not None else None])
        
        # Update parser position
        state.pos = pos + 3
        return True
        
    # Custom checkbox renderer
    def render_checkbox(tokens, idx, options, env):
        token = tokens[idx]
        checked = dict(token.attrs or {}).get('checked') == 'true'
        task_index = dict(token.attrs or {}).get('task_index')
        
        if task_index == 'None' or task_index is None:
            return f'<input type="checkbox" {"checked" if checked else ""} disabled>'
        
        return (f'<input type="checkbox" {"checked" if checked else ""} '
                f'data-checkbox-index="{task_index}" '
                f'id="task_{task_index}" name="task_{task_index}">')
    
    # Add the custom rule
    md.inline.ruler.before('text', 'checkbox', checkbox_replace)
    md.renderer.rules['checkbox_inline'] = render_checkbox
    
    # Set custom renderers
    md.renderer.rules['image'] = render_image
    md.renderer.rules['blockquote_open'] = render_blockquote_open
    md.renderer.rules['blockquote_close'] = render_blockquote_close
    md.renderer.rules['math_inline'] = render_math
    md.renderer.rules['math_block'] = render_math
    
    # Convert to HTML
    html = md.render(content)
    return html

def validate_folder_path(folder_path_input: Optional[str] = None) -> Path:
    """
    Validate and return the folder path to use for notes.md
    If no path provided, uses current working directory
    """
    if folder_path_input:
        path = Path(folder_path_input).resolve()
        # Create folder if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
    else:
        # Use current working directory
        path = Path.cwd()
    
    return path

def should_ignore_resource(url):
    """Check if the resource URL should be ignored."""
    try:
        parsed = urlparse(url)
        return any(ignored in parsed.netloc.lower() for ignored in IGNORED_DOMAINS)
    except:
        return False

###############################################################################
# Improved Resource Inlining (NEW)
###############################################################################

def fetch_resource(session, url):
    """Fetch a resource and return bytes, or None on failure."""
    try:
        resp = session.get(url, timeout=10)
        if resp.ok:
            return resp.content, resp.headers.get('content-type', '')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None, None

def convert_to_data_uri(content_bytes, content_type):
    if not content_type:
        content_type = 'application/octet-stream'
    b64 = base64.b64encode(content_bytes).decode('utf-8')
    return f"data:{content_type};base64,{b64}"

def inline_css_resources(session, css_content, base_url):
    done = False
    # Inline @import and url(...) multiple times until no external refs remain
    while not done:
        done = True
        import_pattern = re.compile(r'@import\s+["\']([^"\']+)["\'];')
        imports = import_pattern.findall(css_content)
        for imp in imports:
            if imp.startswith('data:'):
                continue
            done = False
            css_url = urljoin(base_url, imp)
            content, ctype = fetch_resource(session, css_url)
            if content:
                sub_css = content.decode('utf-8', errors='replace')
                sub_css = inline_css_resources(session, sub_css, css_url)
                css_content = css_content.replace(f'@import "{imp}";', sub_css)
            else:
                css_content = css_content.replace(f'@import "{imp}";', '')

        url_pattern = re.compile(r'url\(["\']?([^)"\']+)["\']?\)')
        urls = url_pattern.findall(css_content)
        for u in urls:
            if u.startswith('data:'):
                continue
            if u.endswith('.map'):  # Skip source map files
                continue
            done = False
            resource_url = urljoin(base_url, u)
            cbytes, ctype = fetch_resource(session, resource_url)
            if cbytes:
                data_uri = convert_to_data_uri(cbytes, ctype)
                css_content = css_content.replace(f'url({u})', f'url({data_uri})')
            # If fail, we leave it as is

    return css_content

def inline_html_resources(session, soup, base_url):
    # Images and srcset
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith('data:') and not should_ignore_resource(src):
            full_url = urljoin(base_url, src)
            cbytes, ctype = fetch_resource(session, full_url)
            if cbytes:
                img['src'] = convert_to_data_uri(cbytes, ctype)

        # srcset
        srcset = img.get('srcset')
        if srcset:
            parts = []
            for part in srcset.split(','):
                urlpart = part.strip().split(' ')[0]
                if urlpart and not urlpart.startswith('data:') and not should_ignore_resource(urlpart):
                    full_url = urljoin(base_url, urlpart)
                    cbytes, ctype = fetch_resource(session, full_url)
                    if cbytes:
                        data_uri = convert_to_data_uri(cbytes, ctype)
                        rest = part.strip()[len(urlpart):]
                        parts.append(data_uri + rest)
                    else:
                        parts.append(part)
                else:
                    parts.append(part)
            img['srcset'] = ', '.join(parts)

    # <source> tags (picture, audio, video)
    for source in soup.find_all('source'):
        ssrc = source.get('src')
        if ssrc and not ssrc.startswith('data:') and not should_ignore_resource(ssrc):
            full_url = urljoin(base_url, ssrc)
            cbytes, ctype = fetch_resource(session, full_url)
            if cbytes:
                source['src'] = convert_to_data_uri(cbytes, ctype)

        srcset = source.get('srcset')
        if srcset:
            parts = []
            for part in srcset.split(','):
                urlpart = part.strip().split(' ')[0]
                if urlpart and not urlpart.startswith('data:') and not should_ignore_resource(urlpart):
                    full_url = urljoin(base_url, urlpart)
                    cbytes, ctype = fetch_resource(session, full_url)
                    if cbytes:
                        data_uri = convert_to_data_uri(cbytes, ctype)
                        rest = part.strip()[len(urlpart):]
                        parts.append(data_uri + rest)
                    else:
                        parts.append(part)
                else:
                    parts.append(part)
            source['srcset'] = ', '.join(parts)

    # Scripts
    for script in soup.find_all('script'):
        src = script.get('src')
        if src and not src.startswith('data:') and not should_ignore_resource(src):
            res_url = urljoin(base_url, src)
            cbytes, ctype = fetch_resource(session, res_url)
            if cbytes:
                script.string = cbytes.decode('utf-8', errors='replace')
                del script['src']

    # Stylesheets
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href and not should_ignore_resource(href):
            css_url = urljoin(base_url, href)
            cbytes, ctype = fetch_resource(session, css_url)
            if cbytes:
                css_text = cbytes.decode('utf-8', errors='replace')
                css_text = inline_css_resources(session, css_text, css_url)
                style_tag = soup.new_tag('style')
                style_tag.string = css_text
                link.replace_with(style_tag)

    # Inline styles in style attributes
    for elem in soup.find_all(style=True):
        style_val = elem['style']
        urls = re.findall(r'url\(["\']?([^)"\']+)["\']?\)', style_val)
        for u in urls:
            if not u.startswith('data:') and not should_ignore_resource(u):
                full_url = urljoin(base_url, u)
                cbytes, ctype = fetch_resource(session, full_url)
                if cbytes:
                    data_uri = convert_to_data_uri(cbytes, ctype)
                    style_val = style_val.replace(u, data_uri)
        elem['style'] = style_val

    return soup

def inline_all_resources(url, html):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    base_url = urljoin(url, '/')

    soup = BeautifulSoup(html, 'html.parser')
    for _ in range(5): # max 5 passes
        old_html = str(soup)
        soup = inline_html_resources(session, soup, base_url)
        new_html = str(soup)
        if new_html == old_html:
            break

    return str(soup)

###############################################################################
# FastAPI Routes
###############################################################################
# Core routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render the main page"""
    colors = THEMES[CURRENT_THEME]
    
    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path
    
    # First replace theme styles
    html = HTML_TEMPLATE.replace(
        "<!-- THEME_STYLES -->",
        THEMED_STYLES.format(colors=colors)
    )
    # Then safely format folder path
    return html.replace(
        "{folder_path}",
        str(folder_path) if folder_path else ""
    )

# Serve the favicon
@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon"""
    return RedirectResponse(url="/static/favicon.ico")

# Note routes
@app.get("/api/notes")
async def get_notes():
    """Get all notes"""
    content = note_manager.render_notes()
    notes = [note.strip() for note in content.split(NOTE_SEPARATOR) if note.strip()]
    
    html_notes = []
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        timestamp = lines[0].replace('## ', '')  # Remove markdown header
        note_content = '\n'.join(lines[1:])
        
        rendered_content = parse_markdown(note_content)
        
        html_note = """
        <div class="section-container">
            <div id="note-{note_index}" class="notes-item markdown-body">
                <div class="post-header">
                    <span class="note-title" onclick="editNote({note_index});">Posted: {timestamp} (click to edit)</span>
                    <span class="delete-label" onclick="deleteNote({note_index});" style="cursor: pointer;">(delete)</span>
                </div>
                {rendered_content}
            </div>
            <div class="section-label">
                <span>n</span>
                <span>o</span>
                <span>t</span>
                <span>e</span>
                <div class="section-label-menu">
                    <button onclick="toggleNote({note_index})">collapse</button>
                    <button onclick="collapseOthers({note_index})">focus</button>
                </div>
            </div>
        </div>
        """.format(
            note_index=note_index,
            timestamp=timestamp,
            rendered_content=rendered_content
        )
        html_notes.append(html_note)
    
    return HTMLResponse(''.join(html_notes))

@app.post("/api/notes")
async def add_note(request: Request, title: str = Form(...), content: str = Form(...)):
    """Add a new note"""
    
    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path

    # Process any +http links in the content
    if '+http' in content:
        print("Found +http link, processing...")  # Debug statement
        processed = await process_plus_links(content, folder_path)
        content = processed['markdown']  # Use the markdown version for storage
        print("Processed content:", content)  # Debug statement
    
    note_manager.add_note(title, content)
    note_manager.save()
    return {"status": "success"}

@app.delete("/api/notes/{note_index}")
async def delete_note(note_index: int = FastAPIPath(...)):
    """Delete a note by index"""
    try:
        if 0 <= note_index < len(note_manager.notes):
            # Remove the note at the specified index
            note_manager.notes.pop(note_index)
            note_manager.needs_save = True
            note_manager.save()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notes/{note_index}")
async def get_note(note_index: int):
    """Get a specific note for editing"""
    try:
        note = note_manager.notes[note_index]
        return {
            "timestamp": note.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "content": note.content,
            "title": note.title
        }
    except IndexError:
        raise HTTPException(status_code=404, detail="Note not found")

@app.put("/api/notes/{note_index}")
async def update_note(note_index: int, title: str = Form(...), content: str = Form(...)):
    """Update an existing note"""
    try:
        note = note_manager.notes[note_index]
        
        # Process any +http links in the content
        if '+http' in content:
            processed = await process_plus_links(content, note_manager.base_path)
            content = processed['markdown']  # Use the markdown version for storage
        
        # Update the note
        note.update(title, content)
        note_manager.save()
        return {"status": "success"}
    except IndexError:
        raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Task routes
@app.get("/api/tasks")
async def get_tasks():
    """Get active tasks"""
    tasks = note_manager.get_active_tasks()
    
    # Return JSON array of tasks instead of HTML
    return tasks  # FastAPI will automatically convert this to JSON

@app.post("/api/tasks/{task_index}")
async def update_task(request: Request, task_index: int = FastAPIPath(...)):
    """Update task status"""
    try:
        data = await request.json()
        # print(f"Debug - Received data: {data}")  # Debug the incoming data
        # print(f"Debug - Task index: {task_index}")  # Debug the task index
        
        checked = data.get('checked', False)
        
        success = note_manager.update_task(task_index, checked)
        if success:
            note_manager.save()
            return JSONResponse({"status": "success"})
        return JSONResponse({"status": "error", "message": "Task not found"})
    except Exception as e:
        print(f"Debug - Error in update_task: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": str(e)}, 
            status_code=500
        )

# Web Archive routes
@app.post("/api/archive")
async def archive_webpage(request: Request, url: str):
    """Archive a webpage"""

    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path
    
    result = archive_website(url, folder_path)  # Note: removed 'await' since archive_website isn't async
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Failed to archive webpage"}

# Theme routes
@app.post("/api/theme")
async def set_theme(theme: str):
   """Set the current theme"""
   global CURRENT_THEME
   if theme in THEMES:
       CURRENT_THEME = theme
       return {"status": "success", "theme": THEMES[theme]}
   return {"status": "error", "message": "Invalid theme"}

@app.get("/api/themes")
async def get_themes():
   """Get available themes"""
   return list(THEMES.keys())

@app.post("/api/save-theme")
async def save_theme(theme: str = Form(...)):
    """Save user's theme preference"""
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
    
# Shutdown endpoint
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

@app.get("/api/links")
async def get_links(request: Request):
    """API endpoint to get the links section."""
    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path
    
    sites_path = folder_path / "assets" / "sites"  # Use absolute path based on folder_path
    link_groups = {}
    
    if sites_path.exists():
        # First, filter for just HTML files
        html_files = [f for f in sites_path.glob("*.html")]
        
        pattern = re.compile(r'(\d{4}_\d{2}_\d{2}_\d{6})_([^-]+)-(.+?)\.html$')

        for file in html_files:
            match = pattern.match(file.name)
            if match:
                timestamp_str, title, domain = match.groups()
                
                # Convert timestamp to a displayable format
                display_timestamp = datetime.strptime(timestamp_str, "%Y_%m_%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                
                if domain not in link_groups:
                    link_groups[domain] = {
                        'domain': domain,
                        'archives': []
                    }
                
                link_groups[domain]['archives'].append({
                    'timestamp': display_timestamp,
                    'filename': file.name
                })
    # Generate HTML and Markdown output
    # Sort domains alphabetically
    sorted_domains = sorted(link_groups.keys())
    
    html_parts = []
    for domain in sorted_domains:
        data = link_groups[domain]
        html_parts.append(f'<div class="archived-link"><a href="#">{data["domain"]}</a>')
        for archive in data['archives']:
            html_parts.append(
            f'<span class="archive-reference">'
            f'<a href="/assets/sites/{archive["filename"]}" target="_blank">'
            f'site archive [{archive["timestamp"]}]</a>'
            f'<span style="color:red;cursor:pointer;font-size:0.5rem; margin-left:5px;" '
            f'onclick="deleteArchive(\'{archive["filename"]}\')">delete</span>'
            f'</span>'
        )
        html_parts.append('</div>')

    result = {
        'html': '\n'.join(html_parts),
        'markdown': '\n'.join([
            f"[{data['domain']} - [{archive['timestamp']}]](/assets/sites/{archive['filename']})"
            for data in link_groups.values() 
            for archive in data['archives']
        ])
    }
    
    return result

@app.post("/api/archive-delete")
async def delete_archive(request: Request):
    data = await request.json()
    filename = data.get('filename')
    if not filename:
        return JSONResponse({"status": "error", "message": "No filename provided"}, status_code=400)

    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path
    
    sites_path = folder_path / "assets" / "sites"
    html_path = sites_path / filename
    tags_path = html_path.with_suffix('.tags')

    if not html_path.exists():
        return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)

    try:
        # Delete the files
        html_path.unlink()
        if tags_path.exists():
            tags_path.unlink()

        # Update notes.md to mark references as deleted
        changes_made = False

        print(f"Looking for filename: {filename}")  # Debug log

        for note in note_manager.notes:
            lines = note.content.split('\n')
            new_lines = []
            note_changed = False  # Track if this note changed

            for line in lines:
                if filename in line:
                    print(f"Found matching line: {line}")  # Debug log
                    # Replace the line
                    replaced_line = f"~~{line}~~ _(archived link deleted)_"
                    # Only set changed if the replaced line differs
                    if replaced_line != line:
                        note_changed = True
                    new_lines.append(replaced_line)
                else:
                    new_lines.append(line)

            if note_changed:
                print("Updating note content")  # Debug log
                note.content = '\n'.join(new_lines)
                changes_made = True  # Indicate that at least one note was changed

        if changes_made:
            print("Saving changes to notes.md")  # Debug log
            note_manager.needs_save = True
            note_manager.save()
            print("Changes were made to notes")  # Debug log
            return {"status": "success", "changes_made": changes_made}
        else:
            print("No changes were made to notes")  # Debug log
            return {"status": "success", "changes_made": changes_made, "message": "No matching links found in notes"}

    except Exception as e:
        print(f"Error in delete_archive: {str(e)}")  # Debug log
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/current-theme")
async def get_current_theme():
    """Get the currently active theme"""
    return {"theme": CURRENT_THEME}

@app.post("/api/upload-file")
async def upload_file(request: Request, file: UploadFile = File(...)):
    # Get file extension and MIME type
    extension = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0]

    # Retrieve folder_path from app.state
    folder_path = request.app.state.folder_path

    # Determine if it's an image
    is_image = content_type and content_type.startswith('image/')

    # Choose appropriate directory based on file type
    if is_image:
        assets_path = folder_path / "assets" / "images"
        relative_path = "images"
    else:
        assets_path = folder_path / "assets" / "files"
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

###############################################################################
# HTML & CSS Templates
###############################################################################
FONT_FACES = f"""
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
"""

THEMED_STYLES = """
        body {{
            margin: 0;
            padding: 0;
            background-color: {colors[background]};
            color: {colors[text_color]};
            font-family: 'space_monoregular', Arial, sans-serif;
        }}
        .container {{
            display: flex;
            max-width: 100%;
            margin: 0 auto;
            gap: 15px;
        }}
        .site-title {{
            background-color: {colors[label_background]};
            color: {colors[accent]};
            padding: 1px 10px;
            font-family: monospace;
            font-size: 12px;
            display: flex;
            align-items: center;
        }}
        .site-title a {{
            color: {colors[accent]};
            text-decoration: none;
        }}
        .site-path {{
            margin-left: 10px;
            color: {colors[text_color]};
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
            background: {colors[box_background]};
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
            background: {colors[box_background]};
            margin-top: 0px;
            padding: 5px;
            border: 1px solid {colors[tasks_border]};
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            box-sizing: border-box;
        }}
        .links-box {{
            background: {colors[box_background]};
            padding: 5px;
            border: 1px solid {colors[links_border]};
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
            background: {colors[label_background]};
            color: {colors[accent]};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border: 1px solid {colors[links_label_border]};
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
            border: 1px solid {colors[input_border]};
            margin-bottom: 5px;
            height: 18px;
            background-color: {colors[input_background]};
        }}
        .input-box textarea {{
            width: 100%;
            box-sizing: border-box;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
            padding: 8px;
            color: {colors[text_color]};
            border: 1px solid {colors[input_border]};
            background-color: {colors[input_background]};
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
            background: {colors[label_background]};
            color: {colors[accent]};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border: 1px solid {colors[note_label_border]};
            border-radius: 7px 0 0 7px;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }}
        .section-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}
        .section-label-menu {{
            position: absolute;
            left: -80px; /* Position to the left of the label */
            top: 0;
            background: {colors[label_background]};
            border: 1px solid {colors[note_label_border]};
            border-radius: 4px;
            opacity: 0;
            visibility: hidden;
            transform: translateX(10px);
            transition: all 0.2s ease;
            z-index: 1000;
            width: 60px;
            display: flex;
            flex-direction: column;
        }}
        .section-label:hover .section-label-menu {{
            opacity: 1;
            visibility: visible;
            transform: translateX(0);
        }}
        .section-label-menu button {{
            display: block;
            width: 100%;
            padding: 4px 8px;
            background: none;
            border: none;
            color: {colors[accent]};
            font-family: space_monoregular;
            font-size: 10px;
            text-align: left;
            cursor: pointer;
            white-space: nowrap;
        }}
        .section-label-menu button:hover {{
            background: {colors[button_hover]};
        }}
        #noteTitle {{
            border: 1px solid {colors[input_border]};
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
            border: 1px solid {colors[input_border]};
            margin-bottom: 5px;
            height: 25px;
            color: {colors[text_color]};
        }}
        .save-note-button {{   
            width: 75px;
            background: {colors[button_bg]};
            hover: {colors[button_hover]};
            color: {colors[accent]};
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
            background: {colors[box_background]};
            padding-left: 5px;
            padding-top: 15px;
            padding-right: 5px;
            padding-bottom: 5px;
            margin-right: 15px;
            border: 1px solid {colors[note_border]};
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px;
            min-height: 60px;
            box-sizing: border-box;
        }}
        /* Style for collapsed note */
        .notes-item.collapsed {{
            padding: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            background: {colors[label_background]};
            color: {colors[accent]};
            font-size: 11px;
            min-height: auto;
            cursor: pointer;
            margin-left: -20px;
            border-radius: 7px;
        }}
        .notes-item.collapsed + .section-label,
        .notes-item.collapsed ~ .section-label {{
            opacity: 0;
            visibility: hidden;
        }}
        .post-header {{
            font-weight: normal;
            font-size: 10px;
            margin-top: -10px;
            margin-bottom: 10px;
            color: {colors[header_text]};
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
            color: {colors[text_color]};
        }}
        .markdown-body p {{
            margin: 5px 0;
        }}
        .markdown-body a {{
            color: {colors[link_color]} !important;
            text-decoration: none;
        }}
        .markdown-body a:visited {{
            color: {colors[visited_link_color]} !important;
        }}
        .markdown-body a:hover {{
            color: {colors[hover_link_color]} !important;
            text-decoration: underline;
        }}
        /* Table styles */
        .markdown-body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            border: 1px solid {colors[table_border]};
        }}

        .markdown-body table thead {{
            background-color: {colors[table_header_bg]};
        }}

        .markdown-body table th {{
            padding: 8px 12px;
            border: 1px solid {colors[table_border]};
            color: {colors[table_header_text]};
            font-weight: 600;
            text-align: left;
            transition: color 0.2s ease; /* Add transition for headers */
        }}

        .markdown-body table td {{
            padding: 8px 12px;
            border: 1px solid {colors[table_border]};
            color: {colors[table_cell_text]};
            transition: color 0.2s ease;
        }}

        .markdown-body table tr {{
            background-color: {colors[table_row_bg]};
        }}

        .markdown-body table tr:nth-child(even) {{
            background-color: {colors[table_row_alt_bg]};
        }}

        /* Updated hover effects for both headers and cells */
        .markdown-body table tr:hover,
        .markdown-body table thead tr:hover {{
            background-color: {colors[button_hover]};
        }}
        
        .markdown-body table tr:hover td,
        .markdown-body table tr:hover th {{
            color: {colors[accent]};
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
            color: {colors[accent]};
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
            color: {colors[text_color]} !important;
            text-decoration: none;
        }}
        #activeTasks .task-text:hover {{
            color: {colors[accent]} !important;
            text-decoration: underline;
        }}
        #noteForm button {{
            width: 100px;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }}
        pre {{
            background-color: {colors[code_background]};
            margin: 0 0;
            padding: 0 0;
        }}
        pre code {{
            background-color: {colors[code_background]};
            padding: 0.2em;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.7rem;
        }}
        .markdown-body pre code.hljs {{
            background-color: {colors[code_background]};
            padding: 0.3em !important;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }}
        .markdown-body blockquote.markdown-blockquote {{
            border-left: 4px solid {colors[accent]};
            margin: 1em 0;
            padding: 0.5em 1em;
            color: {colors[text_color]};
            background-color: {colors[table_row_bg]};  # Changed to use table row background color
            border-radius: 4px;  # Optional: add slight rounding to match other elements
        }}

        .markdown-body blockquote.markdown-blockquote p {{
            margin: 0;
            white-space: pre-wrap;
            font-family: 'space_monoregular', monospace;
            font-size: 0.9rem;
            line-height: 1.4;
        }}

        .notes-item pre code {{
            background-color: {colors[code_background]};
            padding: 0.3em;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }}
        /* Inline code styling */
        .markdown-body code {{
            background-color: {colors[code_background]};
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
            color: {colors[text_color]};
        }}
        .input-box textarea::placeholder {{
            font-size: 10px;
            color: #999;
        }}
        .input-box input::placeholder {{
            font-size: 10px;
            color: {colors[text_color]};
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
            color: {colors[text_color]};
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
            color: {colors[accent]};
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
            color: {colors[accent]};
            text-decoration: none;
            line-height: 1.1;
        }}
        .archive-reference a:hover {{
            color: {colors[text_color]};
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
            background: {colors[label_background]};
            color: {colors[accent]};
            padding: 2px 2px 2px 2px;
            font-family: space_monoregular;
            font-size: 11px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border-radius: 7px 0 0 7px;
            border: 1px solid {colors[admin_label_border]};
            cursor: pointer;
        }}

        .admin-label span {{
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }}

        .admin-content {{
            background: {colors[box_background]};
            padding: 10px;
            border: 1px solid {colors[admin_border]};
            border-left: none;
            border-bottom-left-radius: 7px;
            width: 150px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .admin-button {{
            background: {colors[admin_button_bg]};
            color: {colors[admin_button_text]};
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
            border: 1px solid {colors[input_border]};
            border-radius: 4px;
            background: {colors[input_background]};
            color: {colors[text_color]};
            font-family: inherit;
            font-size: 0.8rem;
        }}

        #themeSelector option {{    
            background: {colors[input_background]};
            color: {colors[text_color]};
            padding: 5px;
        }}
        .delete-label {{
            color: {colors[accent]};
            margin-left: 4px;  /* Add some spacing between edit and delete labels */
        }}
        .delete-label:hover {{
            color: {colors[accent]};
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
            color: {colors[link_color]};
            cursor: pointer;
            text-decoration: none;
            display: inline;
        }}
        .note-title:hover {{
            opacity: 0.8;  /* Subtle hover effect */
        }}
        .directory-bar {{
            background: {colors[button_bg]};
            padding: 2px 6px;
            margin: 0;  /* Remove all margins */
            font-size: 0.55rem;
            font-family: 'space_monoregular', monospace;
            color: {colors[accent]};
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

        /* Add these CSS rules to your existing styles */
        .math-inline {{
            display: inline-block;
            margin: 0.2em 0;  /* Reduced from default */
            color: {colors[math_color]};
        }}
        .math-display {{
            display: block;
            text-align: left;  /* Changed from center to left */
            margin: 0.5em 0;  /* Reduced from default */
            color: {colors[math_color]};
        }}
        /* If needed, also add these MathJax-specific styles */
        .MathJax {{
            text-align: left !important;
            margin: 0.2em 0 !important;
            color: {colors[math_color]};
        }}
        .MathJax_Display {{
            text-align: left !important;
            margin: 0.5em 0 !important;
            color: {colors[math_color]};
        }}
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoteFlow</title>
    <style>
        """ + FONT_FACES + """    
        <!-- THEME_STYLES -->
    </style>
    <script>
        const CURRENT_THEME = '""" + CURRENT_THEME + """';

        // Core functionality

        function insertAtCursor(input, textToInsert) {
            const start = input.selectionStart;
            const end = input.selectionEnd;
            input.value = input.value.substring(0, start) + textToInsert + input.value.substring(end);
            input.selectionStart = input.selectionEnd = start + textToInsert.length;
        }

        async function addNote() {
            const title = document.getElementById('noteTitle').value;
            const content = document.getElementById('noteContent').value.trim(); // Add trim()
            const editIndex = document.getElementById('noteContent').getAttribute('data-edit-index');
            
            if (!content) return;

            // Check if content contains a +http link
            const hasArchiveLink = content.includes('+http');
            if (hasArchiveLink) {
                document.querySelector('.loading-overlay').style.display = 'flex';
            }

            try {
                const formData = new FormData();
                formData.append('title', title);
                formData.append('content', content);

                // Choose endpoint based on whether we're editing or adding
                const url = editIndex !== null ? `/api/notes/${editIndex}` : '/api/notes';
                const method = editIndex !== null ? 'PUT' : 'POST';

                await fetch(url, {
                    method: method,
                    body: formData
                });

                // Clear form and edit state
                document.getElementById('noteTitle').value = '';
                document.getElementById('noteContent').value = '';
                document.getElementById('noteContent').removeAttribute('data-edit-index');
                
                await updateNotes();
                await updateActiveTasks();
                const notesContainer = document.getElementById('notesContainer');
                await typeset(notesContainer);
                if (hasArchiveLink) {
                    await updateLinks();
                }
            } catch (error) {
                console.error('Error saving note:', error);
                alert('Failed to save note');
            } finally {
                if (hasArchiveLink) {
                    document.querySelector('.loading-overlay').style.display = 'none';
                }
            }
        }

        async function editNote(noteIndex) {
            try {
                const response = await fetch(`/api/notes/${noteIndex}`);
                const data = await response.json();
                
                // Fill the form with note data, trimming any extra whitespace
                document.getElementById('noteTitle').value = (data.title || '').trim();
                document.getElementById('noteContent').value = (data.content || '').trim();
                
                // Store the edit index in a data attribute
                document.getElementById('noteContent').setAttribute('data-edit-index', noteIndex);
                
                // Optional: Scroll to the input area
                document.getElementById('noteContent').scrollIntoView({ behavior: 'smooth' });
            } catch (error) {
                console.error('Error loading note for edit:', error);
                alert('Failed to load note for editing');
            }
        }

        async function updateNotes() {
            try {
                const response = await fetch('/api/notes');
                const notesHtml = await response.text();
                document.getElementById('notesContainer').innerHTML = notesHtml;
                
                // Add event listeners to checkboxes
                document.querySelectorAll('input[type="checkbox"][data-checkbox-index]').forEach(checkbox => {
                    checkbox.addEventListener('change', handleCheckboxChange);
                });
            } catch (error) {
                console.error('Error updating notes:', error);
            }
        }

        async function deleteNote(noteIndex) {
            if (!confirm('Are you sure you want to delete this note?')) {
                return;
            }
            try {
                const response = await fetch(`/api/notes/${noteIndex}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                if (!response.ok) {
                    throw new Error('Failed to delete note');
                }
                await updateNotes();
                await updateLinks();
                await updateActiveTasks();
                const notesContainer = document.getElementById('notesContainer');
                await typeset(notesContainer);
            } catch (error) {
                console.error('Error deleting note:', error);
                alert('Failed to delete note');
            }
        }

        async function updateActiveTasks() {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                const tasksContainer = document.getElementById('activeTasks');
                
                tasksContainer.innerHTML = tasks.length ? '' : '<div>No active tasks</div>';
                
                tasks.forEach(task => {
                    const taskElement = document.createElement('div');
                    taskElement.className = 'task-item';
                    taskElement.innerHTML = `
                        <input type="checkbox" 
                            data-checkbox-index="${task.index}" 
                            id="task_${task.index}_active">
                        <label for="task_${task.index}_active">${task.text}</label>
                    `;
                    tasksContainer.appendChild(taskElement);
                });

                // Add event listeners to task checkboxes
                tasksContainer.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                    checkbox.addEventListener('change', handleCheckboxChange);
                });
            } catch (error) {
                console.error('Error updating tasks:', error);
            }
        }

        async function handleCheckboxChange(event) {
            const checkbox = event.target;
            const taskIndex = checkbox.getAttribute('data-checkbox-index');
            
            try {
                await fetch(`/api/tasks/${taskIndex}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({checked: checkbox.checked})
                });
                
                await updateNotes();
                await updateActiveTasks();
                const notesContainer = document.getElementById('notesContainer');
                await typeset(notesContainer);
            } catch (error) {
                console.error('Error updating task:', error);
                checkbox.checked = !checkbox.checked; // Revert on error
            }
        }

        async function setTheme(theme) {
            try {
                const response = await fetch('/api/theme', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `theme=${theme}`
                });
                
                const result = await response.json();
                if (result.status === 'success') {
                    // Apply theme variables to root
                    const root = document.documentElement;
                    Object.entries(result.theme).forEach(([key, value]) => {
                        root.style.setProperty(`--${key}`, value);
                    });
                }
            } catch (error) {
                console.error('Error setting theme:', error);
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

        async function initializeTheme() {
            try {
                // First get the current theme from server
                const currentThemeResponse = await fetch('/api/current-theme');
                const currentThemeData = await currentThemeResponse.json();
                const currentTheme = currentThemeData.theme;
                
                // Then get available themes
                const response = await fetch('/api/themes');
                const themes = await response.json();
                
                const selector = document.getElementById('themeSelector');
                selector.innerHTML = ''; // Clear existing options
                
                themes.forEach(theme => {
                    const option = document.createElement('option');
                    option.value = theme;
                    option.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
                    if (theme === currentTheme) {  // Use server-provided current theme
                        option.selected = true;
                    }
                    selector.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading themes:', error);
            }
        }

        async function deleteArchive(filename) {
            if (!confirm('Are you sure you want to delete this archived site?')) {
                return;
            }
            try {
                const response = await fetch('/api/archive-delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    await updateLinks();
                    await updateNotes();
                } else {
                    alert('Failed to delete archive: ' + result.message);
                }
            } catch (error) {
                console.error('Error deleting archive:', error);
                alert('Error deleting archive.');
            }
        }

        // Add updateLinks function
        async function updateLinks() {
            try {
                const response = await fetch('/api/links');
                const result = await response.json();
                document.getElementById('linksSection').innerHTML = result.html;
            } catch (error) {
                console.error('Error updating links:', error);
            }
        }

        window.MathJax = {
            tex: {
                inlineMath: [['$', '$']],
                displayMath: [['$$', '$$']],
                processEscapes: true
            },
            startup: {
                pageReady: () => {
                    return MathJax.startup.defaultPageReady();
                }
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
            },
            svg: {
                fontCache: 'global'
            }
        };

        // Initialize
        // Initialize
        document.addEventListener('DOMContentLoaded', async () => {
            await updateNotes();
            await updateActiveTasks();
            await initializeTheme();
            await updateLinks();

            const notesContainer = document.getElementById('notesContainer');
            await typeset(notesContainer);

            // Get the textarea element
            const noteContent = document.getElementById('noteContent');

            // Handle Ctrl+Enter to save
            noteContent.addEventListener('keydown', async function(e) {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    await addNote();
                }
            });
            
            // Handle Tab in textarea
            noteContent.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    e.preventDefault();
                    
                    // Get cursor position
                    const start = this.selectionStart;
                    const end = this.selectionEnd;
                    
                    // Insert tab at cursor position
                    this.value = this.value.substring(0, start) + 
                                '\t' + 
                                this.value.substring(end);
                    
                    // Move cursor after tab
                    this.selectionStart = this.selectionEnd = start + 1;
                }
            });

            // Dragover event - prevent default to allow drop
            noteContent.addEventListener('dragover', (e) => {
                e.preventDefault();
            });

            // Drop event - upload file and insert markdown link
            noteContent.addEventListener('drop', async (e) => {
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
                            insertAtCursor(noteContent, markdownLink);
                        } else {
                            alert('Failed to upload file');
                        }
                    } catch (error) {
                        console.error('Error uploading image/file:', error);
                    }
                }
            });
        });
        
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    <script>
    function typeset(element) {
        if (window.MathJax && window.MathJax.typesetPromise) {
            return window.MathJax.typesetPromise([element]);
        }
        return Promise.resolve();
    }
    </script>
</head>
<body>
    <div class="container">
        <div class="left-column">
            <div class="input-box">
                <div class="title-input-container">
                    <input type="text" id="noteTitle" name="noteTitle" placeholder="Enter note title here...">
                    <button id="saveNoteButton" class="save-note-button" onclick="addNote()">Save Note</button>
                </div>
                <textarea id="noteContent" placeholder="Create note in MARKDOWN format... [Ctrl+Enter to save]
Drag & Drop images/files to upload...
Start Links with + to archive websites (e.g., +https://www.google.com)

# Scroll down for Markdown Examples
- [ ] Tasks
- Bullets
    - Sub-bullets
- **Bold** and *italic* and ~~strikethrough~~
- Links: [Link text](https://example.com)
- Images: ![Alt text](image.jpg)
- Blockquotes: > This is a blockquote.
- Math: $E=mc^2$ (inline) or
$$ 
f(x) = x^2 
$$
- Code: `inline code` or ```python
print('Hello, World!')
```
- Tables:
| Column 1 | Column 2 |
|----------|----------|
| Data 1 | Data 2 |
- 2 spaces after a line to create a line break OR extra line between paragraphs"></textarea>
            </div>
            <div id="notesContainer" class="notes-container"></div>
        </div>
        <div class="right-column">
            <!-- Directory Bar -->
            <div class="directory-bar">
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
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
                    <!-- Links will be dynamically inserted here -->
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div class="loading-overlay">
        <div style="text-align: center;">
            <div class="loading-spinner"></div>
            <div class="loading-text">Archiving website...</div>
        </div>
    </div>

    <!-- Admin Panel -->
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

###############################################################################
# Web Archive Functions
###############################################################################
async def process_plus_links(content: str, folder_path: Path) -> Dict[str, str]:
    """Process +https:// links in the content and create local copies."""
    print("Processing content for +links...")  # Debug statement

    async def replace_link(match):
        url = match.group(1)
        print(f"Found +link: {url}")  # Debug statement
        
        # Check if URL is pointing to our own server
        parsed_url = urlparse(url)
        host = parsed_url.netloc.split(':')[0]
        is_localhost = host in ('localhost', '127.0.0.1', '0.0.0.0')
        is_same_port = APP_PORT and str(parsed_url.port) == str(APP_PORT)
        
        if is_localhost and is_same_port:
            print(f"Self-referencing link detected: {url}")  # Debug statement
            return {
                'html': f'{url} <em>(self-referencing link removed)</em>',
                'markdown': f'{url} *(self-referencing link removed)*'
            }
            
        print(f"Archiving website: {url}")  # Debug statement
        result = archive_website(url, folder_path)
        if result:
            print(f"Archived successfully: {url}")  # Debug statement
            return result
        print(f"Failed to archive: {url}")  # Debug statement
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

def saveFullHtmlPage(url: str, output_path: Path, folder_path: Path, session: Optional[requests.Session] = None):
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

def archive_website(url, folder_path):
    """Archive a website to a single self-contained HTML file."""
    try:
        archive_dir = folder_path / "assets" / "sites"  # Use absolute path based on folder_path
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        session = requests.Session()
        session.headers.update(headers)

        response = session.get(url)
        if not response.ok:
            print("Failed to fetch main page for archiving.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "Untitled"
        domain = urlparse(url).netloc

        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        display_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_title = re.sub(r'[^\w\-_]', '_', title)
        base_filename = f"{timestamp}_{safe_title}-{domain}"

        # Inline all resources
        final_html = inline_all_resources(url, response.text)

        # Insert archive timestamp if not already present
        soup_final = BeautifulSoup(final_html, 'html.parser')
        if soup_final.body:
            timestamp_comment = soup_final.new_tag('div')
            timestamp_comment['style'] = 'position:fixed;top:0;left:0;background:#fff;padding:5px;font-size:12px;'
            timestamp_comment.string = f'Archived on {display_timestamp}'
            soup_final.body.insert(0, timestamp_comment)
        final_html = str(soup_final)

        # Save HTML file directly in the archive_dir
        html_filename = f"{base_filename}.html"
        html_path = archive_dir / html_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

        # Create tags file directly in the archive_dir
        tags_filename = f"{base_filename}.tags"
        tags_path = archive_dir / tags_filename

        # Extract meta tags:
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
            f"Title: {soup.title.string.strip() if soup.title else 'No title'}\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
            f"Keywords: {keywords if keywords else 'No keywords found'}\n"
            f"Description: {description if description else 'No description found'}\n"
        )
        tags_path.write_text(tags_content, encoding='utf-8')

        return {
            'html': f'<div class="archived-link">'
                    f'<a href="{url}">{domain}</a><br/>'
                    f'<span class="archive-reference">'
                    f'<a href="/assets/sites/{html_filename}" target="_blank">site archive [{display_timestamp}]</a>'
                    f'</span>'
                    f'</div>',
            'markdown': f"[{domain} - [{display_timestamp}]](/assets/sites/{html_filename})"
        }
    except Exception as e:
        print(f"Error saving webpage: {e}")
        return None
    
async def get_page_title(url: str) -> str:
   """Get the title of a webpage"""
   try:
       response = requests.get(url)
       soup = BeautifulSoup(response.text, 'html.parser')
       return soup.title.string or "Untitled"
   except:
       return "Untitled"

###############################################################################
# Main Entry Point
###############################################################################
if __name__ == "__main__":
    import uvicorn
    
    # Get and validate folder path
    folder_path_input = sys.argv[1] if len(sys.argv) > 1 else None
    working_dir = validate_folder_path(folder_path_input)
    print(f"Using folder: {working_dir}")

    # Create necessary directories
    create_directories(working_dir)
    mount_assets_directory(app, working_dir)

    # Initialize the note manager with the base path
    note_manager = NoteManager(working_dir)
    
    # Store folder_path in app.state for access in routes and functions
    app.state.folder_path = working_dir

    # Find available port
    port = find_free_port()
    set_app_port(port)
    
    # Configure logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "DEBUG"
    
    # Start server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="debug",
        log_config=log_config,
        access_log=False
    )


