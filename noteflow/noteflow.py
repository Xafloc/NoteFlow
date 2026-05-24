###############################################################################
# Imports
###############################################################################
import os
import sys
import re
import json
import html
import mimetypes
import argparse
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse, quote
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

from . import archiver
from . import folders as folders_module
from . import ai as ai_module
from . import sigils

###############################################################################
# Constants & Configuration
###############################################################################
__version__ = "0.4.0"
NOTE_SEPARATOR = "\n<!-- note -->\n"
APP_PORT = None
CURRENT_THEME = "dark-orange" # Default theme

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
    # Use a Python-specific dir name so we don't share config / DB with the
    # Go rewrite (noteflow-go) if both are installed on the same machine.
    config_dir = Path(platformdirs.user_config_dir("noteflow-py"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "noteflow.json"

FONT_SCALE_SECTIONS = ("notes", "tasks", "links")
FONT_SCALE_MIN = 0.8
FONT_SCALE_MAX = 1.6

def _default_font_scales():
    return {s: 1.0 for s in FONT_SCALE_SECTIONS}

def _clamp_font_scale(value) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(FONT_SCALE_MIN, min(FONT_SCALE_MAX, v))

def load_config():
    """Load configuration from JSON file or create default if not exists."""
    config_file = get_config_file()

    default_config = {
        "theme": "dark-orange",
        "font_scales": _default_font_scales(),
        "ai": dict(ai_module.DEFAULT_AI_CONFIG),
    }

    try:
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            if config.get('theme') not in THEMES:
                print(f"Warning: Theme '{config.get('theme')}' not found, defaulting to dark-orange")
                config['theme'] = default_config['theme']
            # Normalize font_scales — fill in missing sections, clamp values.
            scales = config.get('font_scales') or {}
            config['font_scales'] = {
                s: _clamp_font_scale(scales.get(s, 1.0)) for s in FONT_SCALE_SECTIONS
            }
            # Normalize AI block — fill in any missing keys.
            config['ai'] = ai_module.merge_ai_config(config)
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
FONT_SCALES = config.get('font_scales') or _default_font_scales()
AI_CONFIG = ai_module.merge_ai_config(config)

def get_git_context(folder_path: Path) -> Dict:
    """Read .git/HEAD directly to detect repo status without shelling out.

    Returns {is_repo: bool, branch: str|None, sha: str|None}.
    Supports both standard repos (.git is a dir) and worktrees (.git is a
    file containing `gitdir: ...`).
    """
    result = {"is_repo": False, "branch": None, "sha": None}
    try:
        git_path = folder_path / ".git"
        if not git_path.exists():
            return result

        if git_path.is_file():
            # Worktree pointer file: "gitdir: /actual/path"
            content = git_path.read_text(errors='replace').strip()
            if content.startswith("gitdir:"):
                git_dir = Path(content.split(":", 1)[1].strip())
                if not git_dir.is_absolute():
                    git_dir = (folder_path / git_dir).resolve()
            else:
                return result
        else:
            git_dir = git_path

        head_file = git_dir / "HEAD"
        if not head_file.exists():
            return result

        head = head_file.read_text(errors='replace').strip()
        result["is_repo"] = True
        if head.startswith("ref: "):
            ref = head[5:].strip()
            result["branch"] = ref.split("/")[-1] if "/" in ref else ref
            ref_path = git_dir / ref
            if ref_path.exists():
                result["sha"] = ref_path.read_text(errors='replace').strip()[:7]
            else:
                # Packed-refs fallback
                packed = git_dir / "packed-refs"
                if packed.exists():
                    for line in packed.read_text(errors='replace').splitlines():
                        if line.endswith(" " + ref):
                            result["sha"] = line.split(" ", 1)[0][:7]
                            break
        else:
            # Detached HEAD — content is the raw SHA.
            result["sha"] = head[:7] if head else None
    except Exception as e:
        print(f"Git context probe failed: {e}")
    return result

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

        # Normalize CRLF to LF — external editors on Windows save with \r\n
        # and stray \r chars corrupt header regex matches downstream.
        content = content.replace('\r\n', '\n').replace('\r', '\n')

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
        """Extract tasks from note content, skipping checkboxes inside code regions."""
        self.tasks = []
        checkbox_pattern = re.compile(r'\[([xX ])\]')

        code_regions = self._code_regions(self.content)

        for match in checkbox_pattern.finditer(self.content):
            if any(start <= match.start() < end for start, end in code_regions):
                continue  # Inside a fenced or inline code region — skip
            task = Task(
                index=self.manager.checkbox_index,
                checked=match.group(1).lower() == 'x',
                text=self._extract_task_text(match.start())
            )
            self.tasks.append(task)
            self.manager.checkbox_index += 1

    @staticmethod
    def _code_regions(text: str) -> List[tuple]:
        """Return (start, end) byte offsets covering markdown code regions.

        Covers fenced code blocks (``` ... ``` or ~~~ ... ~~~) and inline
        code spans (`...`). Used to mask out checkbox markers that are
        actually part of documentation rather than real tasks.
        """
        regions = []
        # Fenced blocks first — they take precedence over inline spans inside them.
        fence_re = re.compile(r'(^|\n)(```|~~~)[^\n]*\n.*?\n\2(?=\n|$)', re.DOTALL)
        for m in fence_re.finditer(text):
            regions.append((m.start(), m.end()))

        # Inline spans — single, double, or triple backtick spans on one line.
        inline_re = re.compile(r'(`+)[^`\n]+?\1')
        for m in inline_re.finditer(text):
            pos = m.start()
            if any(s <= pos < e for s, e in regions):
                continue  # Already covered by a fenced block
            regions.append((m.start(), m.end()))
        return regions

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

###############################################################################
# FastAPI Routes
###############################################################################
# Core routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render the main page"""
    colors = THEMES[CURRENT_THEME]

    folder_path = request.app.state.folder_path

    rendered = HTML_TEMPLATE.replace(
        "<!-- THEME_STYLES -->",
        THEMED_STYLES.format(colors=colors)
    )
    font_vars = "; ".join(
        f"--font-scale-{section}: {FONT_SCALES.get(section, 1.0)}"
        for section in FONT_SCALE_SECTIONS
    ) + ";"
    rendered = rendered.replace("<!-- FONT_SCALE_VARS -->", font_vars)
    return rendered.replace(
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
    
    folder_path = request.app.state.folder_path

    # Expand +file: sigils first so any embedded code is in place before
    # the archiver scans for +http URLs (a +file body wouldn't contain
    # one, but ordering is explicit so future sigils can compose).
    content = sigils.expand_file_sigils(content, folder_path)

    if '+http' in content:
        print("Found +http link, processing...")
        processed = await archiver.process_plus_links(content, folder_path, app_port=APP_PORT)
        content = processed['markdown']

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

        content = sigils.expand_file_sigils(content, note_manager.base_path)

        if '+http' in content:
            processed = await archiver.process_plus_links(content, note_manager.base_path, app_port=APP_PORT)
            content = processed['markdown']

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

    folder_path = request.app.state.folder_path
    result = archiver.archive_website(url, folder_path)
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
        html_parts.append(
            f'<div class="archived-link"><a href="#">{html.escape(data["domain"])}</a>'
        )
        for archive in data['archives']:
            # JSON-encode the filename so quotes/HTML entities can't break the onclick.
            safe_href = html.escape(quote(archive["filename"]), quote=True)
            safe_attr = html.escape(archive["filename"], quote=True)
            html_parts.append(
                f'<span class="archive-reference">'
                f'<a href="/assets/sites/{safe_href}" target="_blank">'
                f'site archive [{archive["timestamp"]}]</a>'
                f'<span style="color:red;cursor:pointer;font-size:0.5rem; margin-left:5px;" '
                f'data-filename="{safe_attr}" '
                f'onclick="deleteArchive(this.dataset.filename)">delete</span>'
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

@app.get("/api/font-scales")
async def get_font_scales():
    """Return the current per-section font multipliers."""
    return {"scales": dict(FONT_SCALES), "min": FONT_SCALE_MIN, "max": FONT_SCALE_MAX}

@app.post("/api/font-scales")
async def set_font_scales(request: Request):
    """Update one or more per-section font multipliers and persist them."""
    global FONT_SCALES
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    scales = body.get("scales") if isinstance(body, dict) else None
    if not isinstance(scales, dict):
        raise HTTPException(status_code=400, detail="Expected {'scales': {...}}")

    new_scales = dict(FONT_SCALES)
    for section, value in scales.items():
        if section in FONT_SCALE_SECTIONS:
            new_scales[section] = _clamp_font_scale(value)
    FONT_SCALES = new_scales

    cfg = load_config()
    cfg['font_scales'] = new_scales
    save_config(cfg)
    return {"status": "success", "scales": new_scales}

@app.get("/api/git-context")
async def api_git_context(request: Request):
    """Return git repo info for the active folder, if any."""
    folder_path = request.app.state.folder_path
    return get_git_context(folder_path)

@app.get("/api/commits")
async def api_commits(request: Request, limit: int = 30):
    """Recent commits in the active folder's git repo.

    Shells out to `git log` — keeps the implementation simple and works
    correctly with packed refs, signed commits, and any history shape we
    might encounter. If the folder isn't a git repo, returns an empty
    list rather than an error so the UI can render a friendly message.
    """
    folder_path = request.app.state.folder_path
    if not (folder_path / ".git").exists():
        return {"is_repo": False, "commits": []}
    try:
        import subprocess
        limit = max(1, min(int(limit), 200))
        # %x1f = unit separator, %x1e = record separator — avoids any
        # quoting headaches that would come from a JSON or pipe format.
        result = subprocess.run(
            ["git", "log", f"-{limit}",
             "--pretty=format:%h%x1f%an%x1f%ad%x1f%s%x1e",
             "--date=short"],
            cwd=str(folder_path),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"is_repo": True, "commits": [], "error": result.stderr.strip()[:300]}
        commits = []
        for record in result.stdout.split("\x1e"):
            record = record.strip()
            if not record:
                continue
            parts = record.split("\x1f")
            if len(parts) < 4:
                continue
            sha, author, date, subject = parts[0], parts[1], parts[2], parts[3]
            commits.append({
                "sha": sha,
                "author": author,
                "date": date,
                "subject": subject,
            })
        return {"is_repo": True, "commits": commits}
    except FileNotFoundError:
        return {"is_repo": True, "commits": [], "error": "git binary not on PATH"}
    except Exception as e:
        return {"is_repo": True, "commits": [], "error": str(e)[:300]}

@app.get("/api/search")
async def search_notes(request: Request, q: str = ""):
    """Search notes in the current folder for a substring (case-insensitive).

    Returns matching note indexes and short snippets. The frontend renders
    the results inline; this endpoint stays cheap by scanning in-memory
    notes rather than re-reading notes.md.
    """
    query = (q or "").strip()
    if not query:
        return {"query": "", "matches": []}
    needle = query.lower()
    matches = []
    for idx, note in enumerate(note_manager.notes):
        haystack = f"{note.title}\n{note.content}".lower()
        pos = haystack.find(needle)
        if pos < 0:
            continue
        # Build a snippet around the first match.
        body = f"{note.title}\n{note.content}"
        snippet_start = max(0, pos - 40)
        snippet_end = min(len(body), pos + len(needle) + 40)
        snippet = body[snippet_start:snippet_end].replace('\n', ' ')
        matches.append({
            "index": idx,
            "title": note.title or "(untitled)",
            "timestamp": note.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "snippet": snippet,
            "count": haystack.count(needle),
        })
    return {"query": query, "matches": matches}

###############################################################################
# Cross-folder routes (global tasks page, registry, global search)
###############################################################################
@app.get("/global-tasks", response_class=HTMLResponse)
async def global_tasks_page():
    return HTMLResponse(folders_module.GLOBAL_TASKS_HTML)

@app.get("/api/global-tasks")
async def api_global_tasks(include_done: int = 0):
    return folder_registry.get_all_tasks(include_done=bool(include_done))

@app.post("/api/global-tasks/{task_id}/toggle")
async def api_toggle_global_task(task_id: int):
    result = folder_registry.toggle_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@app.get("/api/global-folders")
async def api_global_folders():
    return folder_registry.list_active()

@app.post("/api/global-folders/add")
async def api_add_folder(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    path = (body or {}).get("path") if isinstance(body, dict) else None
    if not path:
        raise HTTPException(status_code=400, detail="Expected {'path': '...'}")
    p = Path(path).expanduser()
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder does not exist: {path}")
    return folder_registry.add_folder(p)

@app.post("/api/global-folders/{folder_id}/forget")
async def api_forget_folder(folder_id: int):
    if not folder_registry.forget_folder(folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"status": "success"}

@app.post("/api/global-folders/{folder_id}/sync")
async def api_sync_folder(folder_id: int):
    n = folder_registry.sync_folder(folder_id)
    return {"status": "success", "task_count": n}

@app.post("/api/global-sync")
async def api_sync_all():
    n = folder_registry.sync_all()
    return {"status": "success", "task_count": n}

@app.get("/api/search/global")
async def api_search_global(q: str = ""):
    return {"query": q, "results": folder_registry.search_all(q)}

###############################################################################
# AI assist routes
###############################################################################
@app.get("/api/ai/config")
async def api_ai_config_get():
    return ai_module.sanitized_view(AI_CONFIG)

@app.post("/api/ai/config")
async def api_ai_config_set(request: Request):
    global AI_CONFIG
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    AI_CONFIG = ai_module.apply_update(AI_CONFIG, body or {})
    cfg = load_config()
    cfg['ai'] = AI_CONFIG
    save_config(cfg)
    return ai_module.sanitized_view(AI_CONFIG)

@app.post("/api/ai/ask")
async def api_ai_ask(request: Request):
    from fastapi.responses import StreamingResponse
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    user_messages = body.get("messages") if isinstance(body, dict) else None
    if not isinstance(user_messages, list) or not user_messages:
        raise HTTPException(status_code=400, detail="Expected {'messages': [...]}")
    context = (body or {}).get("context") or AI_CONFIG.get("default_context", "all")
    folder_path = request.app.state.folder_path
    messages = ai_module.build_messages(user_messages, context, folder_path)
    return StreamingResponse(
        ai_module.stream_chat(AI_CONFIG, messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/ai/render")
async def api_ai_render(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    md = (body or {}).get("markdown", "")
    return {"html": parse_markdown(md)}

@app.get("/api/ai/history")
async def api_ai_history_list(request: Request):
    history = ai_module.AIHistory(request.app.state.folder_path)
    return history.list_entries()

@app.post("/api/ai/history")
async def api_ai_history_add(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(body, dict) or not body.get("question") or not body.get("response"):
        raise HTTPException(status_code=400, detail="Expected {'question': '...', 'response': '...'}")
    history = ai_module.AIHistory(request.app.state.folder_path)
    return history.append_entry(
        question=body["question"],
        response=body["response"],
        model=body.get("model", AI_CONFIG.get("model", "")),
        context=body.get("context", AI_CONFIG.get("default_context", "all")),
    )

@app.delete("/api/ai/history/{entry_id}")
async def api_ai_history_delete(entry_id: str, request: Request):
    history = ai_module.AIHistory(request.app.state.folder_path)
    if not history.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "success"}

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
            font-size: calc(0.7rem * var(--font-scale-links, 1));
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
            font-size: calc(0.9rem * var(--font-scale-notes, 1));
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
            font-size: calc(0.7rem * var(--font-scale-tasks, 1));
            color: {colors[text_color]} !important;
            text-decoration: none;
        }}
        /* Tasks rendered into #activeTasks come from updateActiveTasks() —
           they use <label> elements, not .task-text. Scale them too. */
        #activeTasks label {{
            font-size: calc(0.75rem * var(--font-scale-tasks, 1));
        }}
        #activeTasks .task-text:hover {{
            color: {colors[accent]} !important;
            text-decoration: underline;
        }}

        /* Task metadata chips — used by active tasks + global tasks page */
        .chip {{
            display: inline-block;
            padding: 0 5px;
            margin: 0 1px;
            font-family: 'space_monoregular', monospace;
            font-size: 0.62rem;
            line-height: 1.4;
            border-radius: 3px;
            vertical-align: baseline;
            white-space: nowrap;
        }}
        .chip-p1 {{ background: #c4423a; color: #fff; font-weight: bold; }}
        .chip-p2 {{ background: #d3863a; color: #fff; }}
        .chip-p3 {{ background: #5a7a8c; color: #fff; }}
        .chip-due {{ background: #2d4a5e; color: #9ecbe0; }}
        .chip-tag {{
            background: transparent;
            color: {colors[accent]};
            border: 1px solid {colors[accent]};
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
        /* ---- Right-edge tab strip + unified side panel ----------------- */
        /* Tabs anchored low-right (admin panel's old spot), stacked upward. */
        #rightTabs {{
            position: fixed; right: 0; bottom: 30px;
            display: flex; flex-direction: column-reverse; gap: 6px;
            z-index: 1001;
        }}
        #rightTabs button {{
            background: {colors[box_background]};
            color: {colors[accent]};
            border: 1px solid #555; border-right: none;
            padding: 10px 6px; cursor: pointer;
            writing-mode: vertical-rl;
            font-family: monospace; font-size: 0.72rem;
            letter-spacing: 1px; text-transform: lowercase;
            border-radius: 6px 0 0 6px;
            transition: background 0.15s ease, color 0.15s ease;
            min-height: 70px;
        }}
        #rightTabs button:hover {{ background: #3a3f47; }}
        #rightTabs button.active {{
            background: {colors[accent]};
            color: {colors[background]};
        }}
        /* Slide-in side panel. Display flex always (so children compute
           sizes), with transform pushing it off-screen when closed.
           Uses box_background (the same color as note/task/links cards)
           so the panel reads as a darker surface on every theme,
           including dark-blue where the page background is navy. */
        #sidePanel {{
            position: fixed; right: 0; top: 0; bottom: 0; width: 460px;
            background: {colors[box_background]};
            color: {colors[text_color]};
            box-shadow: -2px 0 14px rgba(0,0,0,0.5);
            border-left: 1px solid #555; z-index: 1000;
            font-family: 'space_monoregular', monospace;
            display: flex; flex-direction: column;
            transform: translateX(100%);
            transition: transform 0.22s ease-out;
            visibility: hidden;
        }}
        #sidePanel.open {{
            transform: translateX(0);
            visibility: visible;
        }}
        #sidePanel header {{
            padding: 10px 14px;
            background: {colors[label_background]};
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid #555;
        }}
        #sidePanel header h2 {{
            margin: 0; font-size: 0.9rem;
            color: {colors[accent]};
            text-transform: lowercase; font-weight: normal;
        }}
        #sidePanel .close {{
            cursor: pointer; opacity: 0.7; font-size: 1.2rem;
            padding: 0 4px;
        }}
        #sidePanel .close:hover {{ opacity: 1; }}
        #sidePanel .pane {{
            display: none; flex: 1; overflow-y: auto; padding: 16px;
            flex-direction: column;
        }}
        #sidePanel .pane.active {{ display: flex; }}
        #sidePanel .pane-help {{
            font-size: 0.7rem; opacity: 0.6; margin: 0 0 12px 0;
            line-height: 1.4;
        }}
        #sidePanel .pane-label {{
            display: block; font-size: 0.7rem; opacity: 0.7;
            margin: 8px 0 4px;
        }}
        #sidePanel select, #sidePanel input[type="text"], #sidePanel input[type="password"] {{
            background: {colors[input_background]};
            color: {colors[text_color]};
            border: 1px solid {colors[input_border]};
            padding: 6px 8px;
            font-family: inherit; font-size: 0.8rem;
            width: 100%; box-sizing: border-box;
            border-radius: 3px;
        }}
        .pane-button {{
            background: {colors[button_bg]};
            color: {colors[button_text]};
            border: 1px solid #555;
            padding: 6px 14px;
            font-family: inherit; font-size: 0.78rem;
            cursor: pointer; border-radius: 4px;
            margin-top: 8px;
        }}
        .pane-button:hover {{ background: {colors[button_hover]}; }}
        .pane-button.danger {{ color: #e08080; border-color: #663030; }}

        /* Commits panel */
        #commitsList {{ display: flex; flex-direction: column; gap: 8px; }}
        #commitsList .commits-empty {{
            opacity: 0.55; font-style: italic; text-align: center; padding: 20px 0;
        }}
        #commitsList .commit {{
            padding: 8px 10px;
            border-left: 2px solid {colors[accent]};
            background: rgba(255,255,255,0.025);
            border-radius: 0 4px 4px 0;
        }}
        #commitsList .commit-meta {{
            display: flex; gap: 8px; align-items: baseline;
            font-size: 0.65rem; opacity: 0.7;
            margin-bottom: 3px;
        }}
        #commitsList .commit-sha {{
            font-family: monospace; color: {colors[accent]};
            font-weight: bold;
        }}
        #commitsList .commit-date {{ opacity: 0.75; }}
        #commitsList .commit-author {{ margin-left: auto; opacity: 0.6; }}
        #commitsList .commit-subject {{
            font-size: 0.75rem; line-height: 1.35;
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
            cursor: pointer;
            transition: filter 0.15s ease;
        }}
        .directory-bar:hover {{
            filter: brightness(1.15);
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
        /* Per-section font scaling (admin panel adjusts these).
           The variables are applied at the *descendant* level where the
           original rules set explicit font-sizes; setting them only on
           the container has no effect because each child re-declares
           its own size. */
        :root {
            <!-- FONT_SCALE_VARS -->
        }
        /* Local search panel */
        .search-box {
            background: var(--box-bg, #26292c);
            padding: 4px;
            margin-bottom: 4px;
            border-radius: 4px;
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .search-box input {
            flex: 1;
            background: transparent;
            border: 1px solid #555;
            color: inherit;
            font-family: inherit;
            font-size: 0.7rem;
            padding: 2px 4px;
        }
        .search-results {
            background: var(--box-bg, #26292c);
            padding: 4px;
            margin-bottom: 4px;
            border-radius: 4px;
            font-size: 0.65rem;
            max-height: 220px;
            overflow-y: auto;
        }
        .search-results .hit {
            padding: 3px 4px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            cursor: pointer;
        }
        .search-results .hit:hover { background: rgba(255,255,255,0.05); }
        .search-results .hit .hit-title { font-weight: bold; }
        .search-results .hit .hit-snippet { opacity: 0.75; font-size: 0.6rem; }
        .search-results .hit mark {
            background: var(--accent, #df8a3e);
            color: #000;
            padding: 0 1px;
        }
        /* Git context badge — sits on the directory bar */
        .git-badge {
            font-family: monospace;
            font-size: 0.55rem;
            padding: 2px 6px;
            background: rgba(0,0,0,0.35);
            color: var(--accent, #df8a3e);
            border-radius: 3px;
            margin-left: auto;
            white-space: nowrap;
        }
        .git-badge.detached { background: rgba(180,40,40,0.4); }
        /* Font scale sliders in admin panel */
        .font-scales {
            display: flex; flex-direction: column; gap: 6px;
            margin: 4px 0; padding: 6px 0;
            border-top: 1px solid rgba(255,255,255,0.08);
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .font-scales .row {
            display: flex; align-items: center; gap: 6px;
            font-size: 0.7rem; color: inherit;
        }
        .font-scales .row .label {
            width: 42px;
            font-family: monospace;
            opacity: 0.8;
        }
        .font-scales .row input[type="range"] {
            flex: 1; min-width: 0;
            accent-color: var(--accent, #df8a3e);
        }
        .font-scales .row .val {
            width: 32px; text-align: right;
            font-family: monospace; font-size: 0.65rem;
            opacity: 0.7;
        }
        /* Live previews of each region's scaled size. The boxes pick up
           the same CSS variables as the real sections, so dragging a
           slider shows here even though the right column is hidden
           behind the open panel. */
        .font-preview {
            display: flex; flex-direction: column; gap: 14px;
            margin-top: 18px;
        }
        .font-preview-label {
            font-size: 0.6rem; opacity: 0.55;
            text-transform: uppercase; letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .font-preview-box {
            background: rgba(0,0,0,0.25);
            border-radius: 4px; padding: 10px 12px;
            min-height: 26px;
        }
        .font-preview-box code {
            background: rgba(255,255,255,0.08);
            padding: 1px 4px; border-radius: 3px;
            font-family: monospace;
        }
        .global-tasks-link {
            font-size: 0.7rem;
            text-align: right;
            margin: 4px 0 8px 0;
            padding-right: 4px;
        }
        .global-tasks-link a {
            color: var(--accent, #df8a3e);
            text-decoration: none;
            opacity: 0.75;
        }
        .global-tasks-link a:hover { opacity: 1; text-decoration: underline; }

        /* AI assist sub-pane (nested inside #sidePanel) */
        #sidePanel .ai-tabs {
            display: flex; border-bottom: 1px solid #555;
            margin: -16px -16px 12px -16px;
        }
        #sidePanel .ai-tabs button {
            flex: 1; background: transparent; color: inherit; border: none;
            padding: 8px; font-family: inherit; font-size: 0.75rem;
            cursor: pointer; border-bottom: 2px solid transparent;
            opacity: 0.7;
        }
        #sidePanel .ai-tabs button.active {
            border-bottom-color: var(--accent, #df8a3e);
            color: var(--accent, #df8a3e);
            opacity: 1;
        }
        #sidePanel .ai-subpane { display: none; flex: 1; flex-direction: column; overflow-y: auto; }
        #sidePanel .ai-subpane.active { display: flex; }
        /* Chat pane */
        #aiChatLog {
            flex: 1; overflow-y: auto; padding-bottom: 8px;
            font-size: 0.75rem; line-height: 1.45;
        }
        #aiChatLog .msg { margin-bottom: 10px; padding: 6px 8px; border-radius: 4px; }
        #aiChatLog .msg.user { background: #2a2e33; border-left: 3px solid var(--accent, #df8a3e); }
        #aiChatLog .msg.assistant { background: #1f2226; border-left: 3px solid #4a90e2; }
        #aiChatLog .msg.assistant .actions {
            margin-top: 6px; display: flex; gap: 6px; font-size: 0.65rem;
        }
        #aiChatLog .msg.assistant .actions button {
            background: #26292c; color: #ccc; border: 1px solid #555;
            padding: 2px 8px; cursor: pointer; border-radius: 3px;
            font-family: inherit; font-size: 0.65rem;
        }
        #aiChatLog .msg.assistant .actions button:hover { background: #3a3f47; }
        #aiChatLog .msg.error { background: rgba(180,40,40,0.18); border-left: 3px solid #c33; }
        /* Animated "thinking" pulse — gives the user a visual cue that
           the placeholder bubble is still live even when no tokens have
           arrived yet (Ollama loading a model, slow first byte, etc.) */
        .ai-thinking {
            display: inline-block;
            opacity: 0.55;
            font-style: italic;
            animation: ai-pulse 1.4s ease-in-out infinite;
        }
        .ai-thinking-dots {
            display: inline-block;
            min-width: 1.4em;
            text-align: left;
        }
        @keyframes ai-pulse {
            0%, 100% { opacity: 0.35; }
            50%      { opacity: 1; }
        }
        #aiInputRow { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
        #aiInputRow textarea {
            background: #26292c; color: #c0c0c0; border: 1px solid #555;
            padding: 6px; font-family: inherit; font-size: 0.75rem;
            resize: vertical; min-height: 60px;
        }
        #aiInputRow .controls { display: flex; gap: 6px; align-items: center; }
        #aiInputRow .controls select, #aiInputRow .controls button {
            background: #26292c; color: #ccc; border: 1px solid #555;
            padding: 4px 8px; font-family: inherit; font-size: 0.7rem; cursor: pointer;
        }
        #aiInputRow .controls button.send {
            color: var(--accent, #df8a3e); font-weight: bold;
        }
        /* Settings pane */
        #aiSettings label { display: block; margin: 8px 0 2px; font-size: 0.7rem; opacity: 0.75; }
        #aiSettings input, #aiSettings select {
            width: 100%; background: #26292c; color: #c0c0c0; border: 1px solid #555;
            padding: 4px 6px; font-family: inherit; font-size: 0.75rem;
            box-sizing: border-box;
        }
        #aiSettings .save {
            margin-top: 12px; background: #26292c; color: var(--accent, #df8a3e);
            border: 1px solid #555; padding: 6px 14px; cursor: pointer;
            font-family: inherit; font-size: 0.75rem;
        }
        #aiSettings .save:hover { background: #3a3f47; }
        #aiSettings .key-status { font-size: 0.65rem; opacity: 0.6; margin-top: 2px; }
        /* History pane */
        #aiHistoryList .entry {
            padding: 6px; border-bottom: 1px solid #2a2e33; font-size: 0.7rem;
        }
        #aiHistoryList .entry .meta {
            display: flex; justify-content: space-between; opacity: 0.7;
            font-size: 0.6rem; margin-bottom: 4px;
        }
        #aiHistoryList .entry .meta a {
            color: #c33; cursor: pointer; text-decoration: none;
        }
        #aiHistoryList .entry .q { font-weight: bold; margin-bottom: 4px; }
        #aiHistoryList .entry .body { opacity: 0.85; max-height: 200px; overflow-y: auto; }
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
            const content = document.getElementById('noteContent').value.trim();
            const editIndex = document.getElementById('noteContent').getAttribute('data-edit-index');

            if (!content) return;

            const hasArchiveLink = content.includes('+http');
            const overlay = document.querySelector('.loading-overlay');
            let timeoutId = null;
            let controller = null;

            if (hasArchiveLink) {
                overlay.style.display = 'flex';
                // Cap the request at 60s so the spinner can never hang
                // forever — the backend's own archive cap is ~30s, this is
                // a belt-and-suspenders for network weirdness.
                controller = new AbortController();
                timeoutId = setTimeout(() => controller.abort(), 60000);
            }

            try {
                const formData = new FormData();
                formData.append('title', title);
                formData.append('content', content);

                const url = editIndex !== null ? `/api/notes/${editIndex}` : '/api/notes';
                const method = editIndex !== null ? 'PUT' : 'POST';

                const resp = await fetch(url, {
                    method: method,
                    body: formData,
                    signal: controller ? controller.signal : undefined,
                });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);

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
                if (error.name === 'AbortError') {
                    alert('Archive took too long (60s). The page may still be archived — refresh to check.');
                } else {
                    alert('Failed to save note: ' + error.message);
                }
            } finally {
                if (timeoutId) clearTimeout(timeoutId);
                if (hasArchiveLink) {
                    overlay.style.display = 'none';
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

        // Render a task's text with inline metadata markers (!p1, @YYYY-MM-DD,
        // #tag) replaced by styled chips. Returns an HTML string.
        function renderTaskText(text) {
            // Tokenize on whitespace runs so we can swap individual tokens
            // without disturbing surrounding spaces.
            const out = [];
            let i = 0;
            const re = /(\\s+)/g;
            const parts = text.split(re);
            for (const tok of parts) {
                if (!tok) continue;
                if (/^\\s+$/.test(tok)) { out.push(escapeHtml(tok)); continue; }
                let m;
                if ((m = tok.match(/^!p([1-3])$/i))) {
                    out.push('<span class="chip chip-p chip-p' + m[1] + '">!p' + m[1] + '</span>');
                } else if ((m = tok.match(/^@(\\d{4}-\\d{2}-\\d{2})$/))) {
                    out.push('<span class="chip chip-due">@' + escapeHtml(m[1]) + '</span>');
                } else if ((m = tok.match(/^#([A-Za-z][A-Za-z0-9_\\-]*)$/))) {
                    out.push('<span class="chip chip-tag">#' + escapeHtml(m[1]) + '</span>');
                } else {
                    out.push(escapeHtml(tok));
                }
            }
            return out.join('');
        }

        async function updateActiveTasks() {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                const tasksContainer = document.getElementById('activeTasks');

                tasksContainer.innerHTML = tasks.length
                    ? ''
                    : '<div style="opacity:0.5;font-style:italic;">No active tasks</div>';

                tasks.forEach(task => {
                    const taskElement = document.createElement('div');
                    taskElement.className = 'task-item';
                    taskElement.innerHTML =
                        '<input type="checkbox" data-checkbox-index="' + task.index +
                        '" id="task_' + task.index + '_active">' +
                        '<label for="task_' + task.index + '_active">' +
                          renderTaskText(task.text) + '</label>';
                    tasksContainer.appendChild(taskElement);
                });

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

        // Collapse / expand a single note. Click anywhere on a collapsed
        // note to re-expand it without using the menu.
        function toggleNote(noteIndex) {
            const note = document.getElementById('note-' + noteIndex);
            if (!note) return;
            note.classList.toggle('collapsed');
        }

        // Collapse every note except the one at noteIndex (focus mode).
        function collapseOthers(noteIndex) {
            document.querySelectorAll('#notesContainer .notes-item').forEach((note) => {
                const isTarget = note.id === 'note-' + noteIndex;
                note.classList.toggle('collapsed', !isTarget);
            });
        }

        // ---- Local search ---------------------------------------------------
        let _searchTimer = null;
        function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, (c) => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            })[c]);
        }
        function highlight(text, query) {
            if (!query) return escapeHtml(text);
            // Note: this string lives inside a Python triple-quoted block,
            // so every backslash is doubled to survive Python's parser
            // before JS sees the intended single-backslash regex escapes.
            const escQ = query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const re = new RegExp(escQ, 'gi');
            return escapeHtml(text).replace(re, (m) => '<mark>' + m + '</mark>');
        }
        async function runSearch(query) {
            const resultsBox = document.getElementById('searchResults');
            if (!query) {
                resultsBox.style.display = 'none';
                resultsBox.innerHTML = '';
                document.getElementById('searchClear').style.display = 'none';
                return;
            }
            document.getElementById('searchClear').style.display = 'inline';
            try {
                const resp = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await resp.json();
                if (!data.matches.length) {
                    resultsBox.innerHTML = '<div class="hit"><em>No matches.</em></div>';
                } else {
                    resultsBox.innerHTML = data.matches.map((m) => (
                        '<div class="hit" data-index="' + m.index + '">' +
                        '<span class="hit-title">' + highlight(m.title || '(untitled)', query) + '</span>' +
                        ' <span style="opacity:0.5;">[' + m.timestamp + '] ×' + m.count + '</span>' +
                        '<div class="hit-snippet">' + highlight(m.snippet, query) + '</div>' +
                        '</div>'
                    )).join('');
                    resultsBox.querySelectorAll('.hit').forEach((row) => {
                        row.addEventListener('click', () => {
                            const idx = row.getAttribute('data-index');
                            const note = document.getElementById('note-' + idx);
                            if (note) {
                                note.classList.remove('collapsed');
                                note.scrollIntoView({behavior: 'smooth', block: 'start'});
                                note.style.outline = '2px solid var(--accent, #df8a3e)';
                                setTimeout(() => { note.style.outline = ''; }, 1200);
                            }
                        });
                    });
                }
                resultsBox.style.display = 'block';
            } catch (e) {
                console.error('Search failed:', e);
            }
        }

        // ---- Font scaling ---------------------------------------------------
        async function loadFontScales() {
            try {
                const resp = await fetch('/api/font-scales');
                const data = await resp.json();
                const container = document.getElementById('fontScales');
                if (!container) return;
                container.innerHTML = '';
                Object.entries(data.scales).forEach(([section, value]) => {
                    const row = document.createElement('div');
                    row.className = 'row';
                    row.innerHTML = (
                        '<span class="label">' + section + '</span>' +
                        '<input type="range" min="' + data.min + '" max="' + data.max + '"' +
                        ' step="0.05" value="' + value + '" data-section="' + section + '">' +
                        '<span class="val">' + Number(value).toFixed(2) + 'x</span>'
                    );
                    const slider = row.querySelector('input');
                    const valSpan = row.querySelector('.val');
                    slider.addEventListener('input', () => {
                        const v = parseFloat(slider.value);
                        document.documentElement.style.setProperty(
                            '--font-scale-' + section, v
                        );
                        valSpan.textContent = v.toFixed(2) + 'x';
                    });
                    slider.addEventListener('change', async () => {
                        await fetch('/api/font-scales', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({scales: {[section]: parseFloat(slider.value)}})
                        });
                    });
                    container.appendChild(row);
                });
            } catch (e) {
                console.error('Font scales load failed:', e);
            }
        }

        // ---- Git context badge ---------------------------------------------
        async function loadGitContext() {
            try {
                const resp = await fetch('/api/git-context');
                const data = await resp.json();
                const badge = document.getElementById('gitBadge');
                if (!badge || !data.is_repo) return;
                const label = data.branch
                    ? data.branch + (data.sha ? ' @ ' + data.sha : '')
                    : 'detached @ ' + (data.sha || '?');
                badge.textContent = label;
                badge.title = data.branch ? 'Branch: ' + data.branch : 'Detached HEAD';
                if (!data.branch) badge.classList.add('detached');
                badge.style.display = 'inline-block';
            } catch (e) {
                /* not in a git repo or other issue — silently hide */
            }
        }

        // ---- Right-edge tab system ----------------------------------------
        function togglePanel(name) {
            const panel = document.getElementById('sidePanel');
            const isCurrent = panel.dataset.active === name && panel.classList.contains('open');
            // Reset all tabs/panes
            document.querySelectorAll('#rightTabs button').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('#sidePanel .pane').forEach(p => p.classList.remove('active'));
            if (isCurrent) {
                panel.classList.remove('open');
                panel.dataset.active = '';
                return;
            }
            // Activate the requested panel
            const tabBtn = document.querySelector('#rightTabs button[data-panel="' + name + '"]');
            const pane = document.querySelector('#sidePanel .pane[data-panel="' + name + '"]');
            if (tabBtn) tabBtn.classList.add('active');
            if (pane) pane.classList.add('active');
            panel.classList.add('open');
            panel.dataset.active = name;
            document.getElementById('sidePanelTitle').textContent = name;

            // Lazy-load each pane's data the first time it's shown.
            if (name === 'fonts') loadFontScales();
            if (name === 'admin') initializeTheme();
            if (name === 'ai') {
                loadAISettings();
                loadAIHistory();
                const ai = document.getElementById('aiInput');
                if (ai) ai.focus();
            }
            if (name === 'commits') loadCommits();
        }

        function closeSidePanel() {
            const panel = document.getElementById('sidePanel');
            panel.classList.remove('open');
            panel.dataset.active = '';
            document.querySelectorAll('#rightTabs button').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('#sidePanel .pane').forEach(p => p.classList.remove('active'));
        }

        // ---- AI assist (now nested inside the side panel) ------------------
        let _aiMessages = [];   // [{role, content}] for the current conversation
        let _aiStreaming = false;

        function switchAITab(name) {
            document.querySelectorAll('#sidePanel .ai-tabs button').forEach((b) => {
                b.classList.toggle('active', b.dataset.aitab === name);
            });
            document.querySelectorAll('#sidePanel .ai-subpane').forEach((p) => {
                p.classList.remove('active');
            });
            const idMap = { chat: 'aiPaneChat', history: 'aiPaneHistory', settings: 'aiPaneSettings' };
            document.getElementById(idMap[name]).classList.add('active');
            if (name === 'history') loadAIHistory();
            if (name === 'settings') loadAISettings();
        }

        async function loadCommits() {
            const list = document.getElementById('commitsList');
            if (!list) return;
            list.innerHTML = '<div class="commits-empty">Loading…</div>';
            try {
                const resp = await fetch('/api/commits?limit=30');
                const data = await resp.json();
                if (!data.is_repo) {
                    list.innerHTML = '<div class="commits-empty">Current folder is not a git repository.</div>';
                    return;
                }
                if (data.error) {
                    list.innerHTML = '<div class="commits-empty" style="color:#c33;">' + escapeHtml(data.error) + '</div>';
                    return;
                }
                if (!data.commits.length) {
                    list.innerHTML = '<div class="commits-empty">No commits yet.</div>';
                    return;
                }
                list.innerHTML = data.commits.map(c => (
                    '<div class="commit">' +
                      '<div class="commit-meta">' +
                        '<span class="commit-sha">' + escapeHtml(c.sha) + '</span>' +
                        '<span class="commit-date">' + escapeHtml(c.date) + '</span>' +
                        '<span class="commit-author">' + escapeHtml(c.author) + '</span>' +
                      '</div>' +
                      '<div class="commit-subject">' + escapeHtml(c.subject) + '</div>' +
                    '</div>'
                )).join('');
            } catch (e) {
                list.innerHTML = '<div class="commits-empty" style="color:#c33;">' + escapeHtml(String(e)) + '</div>';
            }
        }

        async function loadAISettings() {
            try {
                const resp = await fetch('/api/ai/config');
                const cfg = await resp.json();
                document.getElementById('aiEndpoint').value = cfg.endpoint || '';
                document.getElementById('aiModel').value = cfg.model || '';
                document.getElementById('aiDefaultContext').value = cfg.default_context || 'all';
                document.getElementById('aiKeyStatus').textContent =
                    cfg.api_key_set ? 'An API key is currently set.' : 'No API key set yet.';
                document.getElementById('aiContext').value = cfg.default_context || 'all';
            } catch (e) { console.error('AI settings load:', e); }
        }

        async function aiSaveSettings() {
            const body = {
                endpoint: document.getElementById('aiEndpoint').value.trim(),
                model: document.getElementById('aiModel').value.trim(),
                api_key: document.getElementById('aiApiKey').value,
                default_context: document.getElementById('aiDefaultContext').value,
            };
            try {
                const resp = await fetch('/api/ai/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                if (resp.ok) {
                    document.getElementById('aiApiKey').value = '';
                    await loadAISettings();
                } else {
                    alert('Failed to save AI settings');
                }
            } catch (e) {
                console.error('AI save:', e);
            }
        }

        function aiAppendMessage(role, contentHtml) {
            const log = document.getElementById('aiChatLog');
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.innerHTML = contentHtml;
            log.appendChild(div);
            log.scrollTop = log.scrollHeight;
            return div;
        }

        async function aiRenderMarkdown(md) {
            try {
                const resp = await fetch('/api/ai/render', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({markdown: md}),
                });
                const data = await resp.json();
                return data.html;
            } catch (e) {
                return escapeHtml(md);
            }
        }

        function aiNewChat() {
            _aiMessages = [];
            document.getElementById('aiChatLog').innerHTML = '';
            document.getElementById('aiInput').focus();
        }

        // Live thinking indicator with a tiny in-place spinner so the
        // user knows the bubble is alive even before any tokens land.
        function aiThinkingMarkup(seconds) {
            const dots = '.'.repeat((seconds % 3) + 1);
            return '<b>AI</b> <span class="ai-thinking">thinking' +
                   '<span class="ai-thinking-dots">' + dots + '</span></span>' +
                   ' <span style="opacity:0.45;font-size:0.65rem;margin-left:6px;">' +
                     seconds + 's</span>';
        }

        // Module-level handles so aiStop() can interrupt an in-flight request.
        let _aiAbort = null;
        let _aiThinkingTimer = null;

        function aiStop() {
            if (_aiAbort) { try { _aiAbort.abort(); } catch (e) {} }
        }

        async function aiSend() {
            if (_aiStreaming) return;
            const input = document.getElementById('aiInput');
            const question = input.value.trim();
            if (!question) return;
            input.value = '';
            _aiMessages.push({role: 'user', content: question});
            aiAppendMessage('user', '<b>You</b><br>' + escapeHtml(question));

            const placeholder = aiAppendMessage('assistant', aiThinkingMarkup(0));
            const ctx = document.getElementById('aiContext').value;

            // Cycle the "thinking..." dots + seconds counter once per second
            // so the user can see the request hasn't stalled out.
            let elapsed = 0;
            _aiThinkingTimer = setInterval(() => {
                elapsed += 1;
                if (!_aiStreaming) return;
                // Only refresh while we're still waiting on the FIRST token —
                // once tokens arrive we replace the placeholder content anyway.
                if (placeholder.querySelector('.ai-thinking')) {
                    placeholder.innerHTML = aiThinkingMarkup(elapsed) +
                        ' <button onclick="aiStop()" style="margin-left:8px;background:#26292c;color:#c33;border:1px solid #555;padding:1px 8px;font-size:0.65rem;cursor:pointer;border-radius:3px;">stop</button>';
                }
            }, 1000);

            _aiStreaming = true;
            _aiAbort = new AbortController();
            let accumulated = '';
            try {
                const resp = await fetch('/api/ai/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({messages: _aiMessages, context: ctx}),
                    signal: _aiAbort.signal,
                });
                if (!resp.ok || !resp.body) {
                    placeholder.classList.add('error');
                    placeholder.innerHTML = '<b>AI</b> request failed (HTTP ' + resp.status + ')';
                    return;
                }
                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buf = '';
                let errored = false;
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    buf += decoder.decode(value, {stream: true});
                    const parts = buf.split('\\n\\n');
                    buf = parts.pop();
                    for (const part of parts) {
                        const trimmed = part.trim();
                        if (!trimmed.startsWith('data:')) continue;
                        let data;
                        try { data = JSON.parse(trimmed.slice(5).trim()); }
                        catch (e) { continue; }
                        if (data.error) {
                            errored = true;
                            placeholder.classList.add('error');
                            placeholder.innerHTML = '<b>AI</b><br>' + escapeHtml(data.error);
                        } else if (data.text) {
                            accumulated += data.text;
                            placeholder.innerHTML = '<b>AI</b><br><pre style="white-space:pre-wrap;font-family:inherit;margin:0;">' + escapeHtml(accumulated) + '</pre>';
                            placeholder.scrollIntoView({block: 'end'});
                        }
                    }
                }
                if (!errored && accumulated) {
                    // Re-render the final text as proper markdown + add save/copy actions.
                    const html = await aiRenderMarkdown(accumulated);
                    placeholder.innerHTML =
                        '<b>AI</b><div class="markdown-body">' + html + '</div>' +
                        '<div class="actions">' +
                            '<button onclick="aiSaveEntry(this, ' + JSON.stringify(question).replace(/"/g, '&quot;') +
                              ', ' + JSON.stringify(accumulated).replace(/"/g, '&quot;') + ')">Save to history</button>' +
                            '<button onclick="aiCopyText(this, ' + JSON.stringify(accumulated).replace(/"/g, '&quot;') + ')">Copy</button>' +
                        '</div>';
                    if (window.typeset) await typeset(placeholder);
                    _aiMessages.push({role: 'assistant', content: accumulated});
                } else if (!errored && !accumulated) {
                    placeholder.classList.add('error');
                    placeholder.innerHTML = '<b>AI</b> empty response — check endpoint and model settings.';
                }
            } catch (e) {
                placeholder.classList.add('error');
                if (e.name === 'AbortError') {
                    placeholder.innerHTML = '<b>AI</b> request cancelled.';
                } else {
                    placeholder.innerHTML = '<b>AI</b> error: ' + escapeHtml(String(e));
                }
            } finally {
                _aiStreaming = false;
                _aiAbort = null;
                if (_aiThinkingTimer) {
                    clearInterval(_aiThinkingTimer);
                    _aiThinkingTimer = null;
                }
            }
        }

        async function aiSaveEntry(btn, question, response) {
            // Optional first arg — older callers pass (question, response).
            if (typeof btn === 'string') {
                response = question;
                question = btn;
                btn = null;
            }
            const orig = btn ? btn.textContent : null;
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Saving…';
            }
            try {
                const resp = await fetch('/api/ai/history', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        question: question,
                        response: response,
                        context: document.getElementById('aiContext').value,
                    }),
                });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                if (btn) {
                    btn.textContent = 'Saved ✓';
                    btn.style.color = 'var(--accent, #df8a3e)';
                    setTimeout(() => {
                        if (!btn) return;
                        btn.textContent = orig;
                        btn.style.color = '';
                        btn.disabled = false;
                    }, 1400);
                }
                loadAIHistory();
            } catch (e) {
                console.error('AI save:', e);
                if (btn) {
                    btn.textContent = 'Save failed';
                    btn.style.color = '#c33';
                    setTimeout(() => {
                        if (!btn) return;
                        btn.textContent = orig;
                        btn.style.color = '';
                        btn.disabled = false;
                    }, 2000);
                }
            }
        }

        async function aiCopyText(btn, text) {
            await copyToClipboard(text, btn);
            const orig = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = orig; }, 900);
        }

        async function loadAIHistory() {
            try {
                const resp = await fetch('/api/ai/history');
                const entries = await resp.json();
                const list = document.getElementById('aiHistoryList');
                if (!entries.length) {
                    list.innerHTML = '<div class="entry" style="opacity:0.5;">No saved entries.</div>';
                    return;
                }
                const renderedBodies = await Promise.all(entries.map(e => aiRenderMarkdown(e.response)));
                list.innerHTML = entries.map((e, i) => (
                    '<div class="entry">' +
                      '<div class="meta">' +
                        '<span>' + escapeHtml(e.timestamp) + ' · ' + escapeHtml(e.model || 'unknown') + '</span>' +
                        '<a onclick="aiDeleteEntry(' + JSON.stringify(e.id).replace(/"/g, '&quot;') + ')">delete</a>' +
                      '</div>' +
                      '<div class="q">' + escapeHtml(e.question) + '</div>' +
                      '<div class="body markdown-body">' + renderedBodies[i] + '</div>' +
                    '</div>'
                )).join('');
            } catch (e) { console.error('AI history:', e); }
        }

        async function aiDeleteEntry(id) {
            if (!confirm('Delete this entry?')) return;
            try {
                await fetch('/api/ai/history/' + encodeURIComponent(id), {method: 'DELETE'});
                loadAIHistory();
            } catch (e) { console.error('AI delete:', e); }
        }

        // Copy text to clipboard with brief visual feedback on the element.
        async function copyToClipboard(text, element) {
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(text);
                } else {
                    const ta = document.createElement('textarea');
                    ta.value = text;
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                }
                if (element) {
                    const prev = element.style.color;
                    element.style.color = 'var(--accent, #df8a3e)';
                    setTimeout(() => { element.style.color = prev; }, 600);
                }
            } catch (err) {
                console.error('Copy failed:', err);
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
            await updateLinks();
            // Theme + font sliders are populated lazily when their tab opens;
            // the actual theme and font sizes are applied via server-rendered
            // CSS variables, so the page already looks correct.

            const notesContainer = document.getElementById('notesContainer');
            await typeset(notesContainer);

            // Global keyboard shortcuts.
            document.addEventListener('keydown', (e) => {
                // ESC closes the side panel from anywhere on the page.
                if (e.key === 'Escape') {
                    const panel = document.getElementById('sidePanel');
                    if (panel && panel.classList.contains('open')) {
                        if (document.activeElement && document.activeElement.id === 'searchInput') return;
                        closeSidePanel();
                    }
                }
                // `/` focuses the search box (skip when typing somewhere).
                if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
                    const tag = document.activeElement && document.activeElement.tagName;
                    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
                    const search = document.getElementById('searchInput');
                    if (search) {
                        e.preventDefault();
                        search.focus();
                        search.select();
                    }
                }
            });

            // Click a collapsed note anywhere on its body to re-expand.
            notesContainer.addEventListener('click', (e) => {
                const collapsed = e.target.closest('.notes-item.collapsed');
                if (!collapsed) return;
                // Don't fire when the click was on an interactive child element.
                if (e.target.closest('.section-label, button, a, input')) return;
                collapsed.classList.remove('collapsed');
            });

            // Directory bar: click anywhere on it to copy the folder path.
            const dirBar = document.getElementById('directoryBar');
            if (dirBar) {
                dirBar.addEventListener('click', (e) => {
                    // Let clicks on the git badge through (it's informational only).
                    if (e.target.closest('#gitBadge')) return;
                    const path = dirBar.querySelector('.directory-bar-content');
                    if (path) copyToClipboard(path.textContent.trim(), dirBar);
                });
            }

            // Local search: debounce input -> /api/search.
            const searchInput = document.getElementById('searchInput');
            const searchClear = document.getElementById('searchClear');
            if (searchInput) {
                searchInput.addEventListener('input', () => {
                    clearTimeout(_searchTimer);
                    const q = searchInput.value.trim();
                    _searchTimer = setTimeout(() => runSearch(q), 150);
                });
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        searchInput.value = '';
                        runSearch('');
                    }
                });
            }
            if (searchClear) {
                searchClear.addEventListener('click', () => {
                    searchInput.value = '';
                    runSearch('');
                    searchInput.focus();
                });
            }

            // Git context badge stays visible on the directory bar regardless
            // of the side panel state, so it loads on initial page mount.
            await loadGitContext();

            // AI assist Ctrl+Enter to send
            const aiInput = document.getElementById('aiInput');
            if (aiInput) {
                aiInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        aiSend();
                    }
                });
            }

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
Drag & Drop images/files to upload.

NoteFlow sigils (expanded at save time):
  +https://example.com         Archive the page locally as self-contained HTML
  +file:src/foo.py#10-25       Embed those lines as a fenced code block

Tasks (filterable via the `noteflow tasks` CLI and the global tasks page):
- [ ] Plain task
- [ ] !p1 @2026-05-31 #release    Priority (1-3), due date, and #tag tokens

Markdown basics:
- Headers: # H1 / ## H2 / ### H3
- **bold** / *italic* / ~~strikethrough~~ / inline code in backticks
- Lists: '- bullet' or '1. numbered'; indent two spaces for sub-items
- Links: [text](https://example.com)   Images: ![alt](image.jpg)
- Blockquotes: > like this
- Tables:
    | Column 1 | Column 2 |
    |----------|----------|
    | a        | b        |
- Code blocks: triple-backtick fences, optionally with a language hint
- Math: single dollar signs for inline, double dollar signs for block (MathJax)
- Press / anywhere to focus the search box."></textarea>
            </div>
            <div id="notesContainer" class="notes-container"></div>
        </div>
        <div class="right-column">
            <!-- Directory Bar -->
            <div id="directoryBar" class="directory-bar" title="Click to copy folder path">
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
                <span class="directory-bar-content">{folder_path}&nbsp;</span>
                <span id="gitBadge" class="git-badge" style="display:none;"></span>
            </div>

            <!-- Local Search -->
            <div class="search-box">
                <input type="text" id="searchInput"
                       placeholder="Search notes in this folder…"
                       autocomplete="off">
                <span id="searchClear"
                      style="cursor:pointer;display:none;font-size:0.65rem;opacity:0.7;"
                      title="Clear">&times;</span>
            </div>
            <div id="searchResults" class="search-results" style="display:none;"></div>

            <!-- Tasks Box -->
            <div id="activeTasks" class="task-box">
                <!-- Task items will be dynamically inserted here -->
            </div>
            <div class="global-tasks-link">
                <a href="/global-tasks" target="_blank">global tasks &rarr;</a>
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

    <!-- Right-edge tab strip + unified side panel -->
    <nav id="rightTabs" aria-label="Side panels">
        <button data-panel="fonts" onclick="togglePanel('fonts')">fonts</button>
        <button data-panel="admin" onclick="togglePanel('admin')">admin</button>
        <button data-panel="ai" onclick="togglePanel('ai')">ai</button>
        <button data-panel="commits" onclick="togglePanel('commits')">commits</button>
    </nav>
    <aside id="sidePanel" data-active="">
        <header>
            <h2 id="sidePanelTitle">fonts</h2>
            <span class="close" onclick="closeSidePanel()" title="Close (Esc)">&times;</span>
        </header>

        <div class="pane" data-panel="fonts">
            <p class="pane-help">
                Resize each region's text. The previews below scale in
                real time so you can see the effect even when the panel
                covers the actual sections.
            </p>
            <div class="font-scales" id="fontScales"></div>
            <div class="font-preview">
                <div class="font-preview-block">
                    <div class="font-preview-label">notes preview</div>
                    <div class="font-preview-box notes-preview">
                        <div class="markdown-body" style="font-size: calc(0.9rem * var(--font-scale-notes, 1));">
                            The quick brown fox jumps over the lazy dog.
                            <em>Italic</em>, <strong>bold</strong>, and <code>inline code</code>.
                        </div>
                    </div>
                </div>
                <div class="font-preview-block">
                    <div class="font-preview-label">tasks preview</div>
                    <div class="font-preview-box">
                        <div style="display:flex;gap:8px;align-items:flex-start;">
                            <input type="checkbox" disabled>
                            <label style="font-size: calc(0.75rem * var(--font-scale-tasks, 1));">
                                Sample active task line
                            </label>
                        </div>
                    </div>
                </div>
                <div class="font-preview-block">
                    <div class="font-preview-label">links preview</div>
                    <div class="font-preview-box" style="font-size: calc(0.7rem * var(--font-scale-links, 1));">
                        example.com — site archive [2026-05-24 08:00:00]
                    </div>
                </div>
            </div>
        </div>

        <div class="pane" data-panel="admin">
            <label class="pane-label">Theme</label>
            <select id="themeSelector"></select>
            <button class="pane-button" onclick="saveTheme()">Save theme</button>
            <div style="flex:1;"></div>
            <button class="pane-button danger" onclick="shutdownServer()">Shutdown server</button>
        </div>

        <div class="pane" data-panel="ai">
            <div class="ai-tabs">
                <button data-aitab="chat" class="active" onclick="switchAITab('chat')">Chat</button>
                <button data-aitab="history" onclick="switchAITab('history')">History</button>
                <button data-aitab="settings" onclick="switchAITab('settings')">Settings</button>
            </div>
            <div id="aiPaneChat" class="ai-subpane active">
                <div id="aiChatLog"></div>
                <div id="aiInputRow">
                    <textarea id="aiInput" placeholder="Ask anything about your notes…  [Ctrl+Enter to send]"></textarea>
                    <div class="controls">
                        <label style="font-size:0.65rem;opacity:0.7;">context:</label>
                        <select id="aiContext">
                            <option value="all">all notes</option>
                            <option value="200">last 200 lines</option>
                            <option value="100">last 100 lines</option>
                            <option value="50">last 50 lines</option>
                        </select>
                        <button onclick="aiNewChat()">New chat</button>
                        <button class="send" onclick="aiSend()">Send</button>
                    </div>
                </div>
            </div>
            <div id="aiPaneHistory" class="ai-subpane">
                <div id="aiHistoryList"></div>
            </div>
            <div id="aiPaneSettings" class="ai-subpane">
                <div id="aiSettings">
                    <label>Endpoint (OpenAI-compatible /v1/chat/completions)</label>
                    <input type="text" id="aiEndpoint" placeholder="https://api.openai.com/v1/chat/completions">
                    <label>Model</label>
                    <input type="text" id="aiModel" placeholder="gpt-4o-mini">
                    <label>API key</label>
                    <input type="password" id="aiApiKey" placeholder="Leave blank to keep existing">
                    <div class="key-status" id="aiKeyStatus"></div>
                    <label>Default context</label>
                    <select id="aiDefaultContext">
                        <option value="all">all notes</option>
                        <option value="200">last 200 lines</option>
                        <option value="100">last 100 lines</option>
                        <option value="50">last 50 lines</option>
                    </select>
                    <button class="pane-button" onclick="aiSaveSettings()">Save settings</button>
                </div>
            </div>
        </div>

        <div class="pane" data-panel="commits">
            <p class="pane-help">Recent commits in the current folder's git repo.</p>
            <div id="commitsList"><div class="commits-empty">Loading…</div></div>
        </div>
    </aside>
</body>
</html>
"""

###############################################################################
# Main Entry Point
###############################################################################
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noteflow",
        description=(
            "NoteFlow — a lightweight, Markdown-based note-taking application "
            "with task management. Run inside any folder; notes are stored in "
            "notes.md and archives under assets/sites/."
        ),
        epilog=(
            "Subcommands (run with --help for details):\n"
            "  noteflow append [--title TITLE] [BODY...]   Append a note from the CLI.\n"
            "  noteflow tasks  [filters / actions]         Query, filter, toggle tasks\n"
            "                                              across every registered folder."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help="Folder to use as the notes directory (defaults to the current working directory).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to. If omitted or in use, NoteFlow scans upward from 8000.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the browser when the server starts.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"noteflow {__version__}",
    )
    return parser


def _open_browser_when_ready(url: str, delay: float = 1.0):
    """Open `url` in the default browser shortly after server startup."""
    def _go():
        try:
            webbrowser.open(url, new=2)
        except Exception as e:
            print(f"Could not auto-open browser: {e}")
    threading.Timer(delay, _go).start()


def main():
    import uvicorn
    global note_manager, folder_registry

    # Subcommand dispatch — `noteflow append …` or `noteflow tasks …` run
    # the CLI handlers and exit; everything else (including a bare path)
    # boots the web server below.
    if len(sys.argv) > 1 and sys.argv[1] in {"append", "tasks"}:
        from . import cli
        sys.exit(cli.dispatch(sys.argv[1], sys.argv[2:]))

    args = _build_arg_parser().parse_args()

    try:
        working_dir = validate_folder_path(args.folder)
        print(f"Using folder: {working_dir}")

        create_directories(working_dir)
        mount_assets_directory(app, working_dir)

        note_manager = NoteManager(working_dir)
        app.state.folder_path = working_dir

        # Cross-folder registry: auto-register the active folder and start
        # the background sync ticker. Folders persist across runs in
        # ~/.config/noteflow/tasks.db.
        folder_registry = folders_module.FolderRegistry()
        folder_registry.add_folder(working_dir)
        folder_registry.start_background_sync()

        port = find_free_port(args.port) if args.port else find_free_port()
        set_app_port(port)

        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["loggers"]["uvicorn.access"]["level"] = "DEBUG"

        if not args.no_browser:
            _open_browser_when_ready(f"http://127.0.0.1:{port}/")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="debug",
            log_config=log_config,
            access_log=False,
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
