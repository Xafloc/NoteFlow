from fastapi import FastAPI, HTTPException, Path, UploadFile, File
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
from urllib.parse import quote, unquote
import os
from bs4 import BeautifulSoup
import requests
import base64
import mimetypes
import hashlib
from urllib.parse import urljoin, urlparse

app = FastAPI()

# Mount the local directories
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/fonts", StaticFiles(directory=Path(__file__).parent / "fonts"), name="fonts")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Define the new separator
NOTE_SEPARATOR = "\n---\n"

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
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Notes</title>
    <style>
        @font-face {
            font-family: 'space_monoregular';
            src: url('/fonts/spacemono-regular-webfont.woff2') format('woff2'),
                 url('/fonts/spacemono-regular-webfont.woff') format('woff'),
                 url('/fonts/spacemono-regular-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap; /* This helps prevent invisible text during loading */
        }
        @font-face {
            font-family: 'space_monobold';
            src: url('/fonts/spacemono-bold-webfont.woff2') format('woff2'),
                 url('/fonts/spacemono-bold-webfont.woff') format('woff'),
                 url('/fonts/spacemono-bold-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'space_monobold_italic';
            src: url('/fonts/spacemono-bolditalic-webfont.woff2') format('woff2'),
                 url('/fonts/spacemono-bolditalic-webfont.woff') format('woff'),
                 url('/fonts/spacemono-bolditalic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'space_monoitalic';
            src: url('/fonts/spacemono-italic-webfont.woff2') format('woff2'),
                 url('/fonts/spacemono-italic-webfont.woff') format('woff'),
                 url('/fonts/spacemono-italic-webfont.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }

        body {
            margin: 0;
            padding: 0;
            background-color: #1e3c72;
            color: #000;
            font-family: 'space_monoregular', Arial, sans-serif;
        }

        .container {
            display: flex;
            max-width: 100%;
            margin: 0 auto;
            padding: 15px;
            gap: 15px;
        }

        .site-title {
            background-color: #000;
            color: #ff8c00;
            padding: 1px 10px;
            font-family: monospace;
            font-size: 12px;
            display: flex;
            align-items: center;
        }

        .site-title a {
            color: #ff8c00;
            text-decoration: none;
        }

        .site-path {
            margin-left: 10px;
            color: #666;
        }

        .left-column, .right-column {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .left-column {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 15px;
            width: 100%;
        }

        .right-column {
            flex: 0 0 325px;
            width: 325px;
        }

        .input-box {
            background: white;
            margin-top: -15px;
            padding: 5px;
            border: 1px solid #000;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px; 
            box-sizing: border-box;
        }

        .task-box {
            background: white;
            margin-top: -15px;
            padding: 5px;
            border: 1px solid #000;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px; 
            box-sizing: border-box;
        }

        .links-box {
            background: white;
            padding: 5px;
            border: 1px solid #000;
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px; 
        }

        .input-box textarea {
            width: 100%;
            box-sizing: border-box;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
            padding: 8px;
            border: 1px solid #ccc;
        }

        .section-container {
            position: relative;
            margin-bottom: 5px;
            margin-top: 5px;
            margin-left: 2px;
        }

        .section-label {
            position: absolute;
            top: 0;
            left: -18px;
            background: #000;
            color: #ff8c00;
            padding: 2px 2px 2px 2px;
            font-family: monospace;
            font-size: 10px;
            display: inline-flex;
            flex-direction: column;
            line-height: 1;
            text-transform: lowercase;
            width: 15px;
            border-radius: 7px 0 0 7px;
        }

        .section-label span {
            display: block;
            text-align: center;
            padding: 1px 1px 0.5px 1px;
        }

        .notes-item {
            background: white;
            padding-left: 5px;
            padding-top: 15px;
            padding-right: 5px;
            padding-bottom: 5px;
            margin-right: 15px;
            border: 1px solid #000;
            border-top-left-radius: 0px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-bottom-left-radius: 7px; 
        }

        .post-header {
            font-weight: normal;
            font-size: 10px;
            margin-top: -10px;
            margin-bottom: 10px;
            color: #666;
        }

        .links-box a {
            color: blue;
            text-decoration: none;
            display: block;
            padding: 2px 0;
        }

        .note-content img { max-width: 100%; }
        .note-content { scroll-margin-top: 100px; }
        
        .markdown-body {
            font-size: 0.9rem;  /* Make all markdown content slightly smaller */
        }
        /* First level bullets */
        .markdown-body ul {
            list-style-type: disc;  /* First level bullets */
        }
        /* Second level bullets */
        .markdown-body ul ul {
            list-style-type: circle;  /* Second level bullets */
        }
        /* Third level bullets */
        .markdown-body ul ul ul {
            list-style-type: square;  /* Third level bullets */
        }
        .markdown-body ul,
        .markdown-body ol {
            list-style-position: outside;
            padding-left: 1.5em;  /* Reduced from 2em */
            margin-top: 0.1rem;   /* Reduced from 0.15rem */
            margin-bottom: 0.1rem;
        }
        .markdown-body li {
            margin-bottom: 0.1rem;  /* Reduced from 0.15rem */
        }
        .markdown-body input[type="checkbox"] {
            margin-right: 0.5rem;
        }
        .markdown-body h4 {
            margin-top: 5px;
            margin-bottom: 5px;
        }
        .markdown-body h2 {
            font-size: 1.5rem;
            font-weight: bold;
            margin: 1rem 0;
            color: #2563eb;
        }
        .markdown-body p {
            margin: 1rem 0;
        }

        .notes-container {
            width: 100%;
            margin-left: 15px;
            margin-right: 0;
            padding-left: 0;
            padding-right: 0;
        }

        /* Adjust the layout proportions */
        #noteForm {
            width: 100%;
        }

        /* Styles for Active Tasks */
        #activeTasks {
            word-wrap: break-word;
            overflow-wrap: break-word;
            max-height: 300px;
        }

        #activeTasks .task-item {
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            padding: 0.1rem 0;
        }

        #activeTasks .task-text {
            flex: 1;
            min-width: 0;
            padding-top: 2px;
            word-break: break-word;
            white-space: pre-wrap; /* Maintain line breaks for long tasks */
            font-size: 0.7rem;  /* Make task text smaller */
        }

        /* Adjust the "Add Note" button size */
        #noteForm button {
            width: 100px;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }

        /***********************************
        *        Code Block Styles         *
        ***********************************/
        pre {
            background-color: #fdf6e3; /* Soft pastel blue background */
            margin: 0 0;
            padding: 0 0;
        }
        pre code {
            background-color: #fdf6e3; /* Soft pastel blue background */
            padding: 0.2em;  /* Reduced from 1em */
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.7rem;  /* Make code slightly smaller */
        }  
        .markdown-body pre code.hljs {
            background-color: #fdf6e3; /* Soft pastel blue background */
            padding: 0.3em !important;  /* Using !important as a fallback */
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }
        .notes-item pre code {
            background-color: #fdf6e3; /* Soft pastel blue background */
            padding: 0.3em;
            border-radius: 0.3em;
            display: block;
            overflow-x: auto;
            font-size: 0.75rem;
        }
        /**********************************
        *   END Code Block Styles         *
        **********************************/

        .input-box input[type="text"] {
            width: 100%;
            box-sizing: border-box;
            font-family: inherit;
            padding: 4px 8px;
            border: 1px solid #ccc;
            margin-bottom: 5px;
            height: 18px;
        }

        .input-box textarea::placeholder {
            font-size: 10px;  /* Adjust size as needed */
            color: #999;      /* Optional: customize color */
        }

        .input-box input::placeholder {
            font-size: 10px;  /* Adjust size as needed */
            color: #999;      /* Optional: customize color */
        }

        /*=============================================
        =            List and Checkbox Styles         =
        =============================================*/


    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/default.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
</head>
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
            <div id="activeTasks"class="task-box">
            </div>
        </div>
    </div>

    <script>
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
                await submitNoteForm();
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
    </script>
</body>
</html>
    """

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
        
        # Use the render_markdown function
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
                <div class="post-header">Posted: {timestamp}</div>
                {rendered_content}
            </div>
        </div>
        '''
        html_notes.append(html_note)
    
    html_content = ''.join(html_notes)
    return HTMLResponse(html_content)

@app.post("/api/notes")
async def add_note(note: Note):
    notes_file = init_notes_file()
    current_content = notes_file.read_text().strip()
    
    # Process +https:// links in the content
    processed_content = process_plus_links(note.content)
    
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
    
    return {"status": "success"}

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
    return md.render(content, env)

def create_directories():
    # Define the directories to be created
    directories = [
        Path("assets"),
        Path("assets/images"),
        Path("assets/sites")
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Call this function at the start of your application
create_directories()

def archive_website(url):
    """Archive a website to a single HTML file with embedded resources."""
    try:
        # Generate a filename based on just the domain
        domain = urlparse(url).netloc
        filename = f"{domain}.html"
        filepath = Path("assets/sites") / filename

        # If already archived, return existing path
        if filepath.exists():
            return str(filepath)

        # Fetch the main page
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Handle CSS
        for css_tag in soup.find_all('link', rel='stylesheet'):
            try:
                css_url = urljoin(url, css_tag['href'])
                css_content = requests.get(css_url).text
                # Create data URI for CSS
                css_b64 = base64.b64encode(css_content.encode()).decode()
                css_tag['href'] = f'data:text/css;charset=utf-8;base64,{css_b64}'
            except Exception as e:
                print(f"Error processing CSS {css_url}: {e}")

        # Handle JavaScript
        for script in soup.find_all('script', src=True):
            try:
                js_url = urljoin(url, script['src'])
                js_content = requests.get(js_url).text
                # Create data URI for JavaScript
                js_b64 = base64.b64encode(js_content.encode()).decode()
                script['src'] = f'data:text/javascript;charset=utf-8;base64,{js_b64}'
            except Exception as e:
                print(f"Error processing JavaScript {js_url}: {e}")

        # Handle images
        for img in soup.find_all('img', src=True):
            try:
                img_url = urljoin(url, img['src'])
                img_response = requests.get(img_url)
                content_type = img_response.headers.get('content-type', 'image/jpeg')
                # Create data URI for image
                img_b64 = base64.b64encode(img_response.content).decode()
                img['src'] = f'data:{content_type};base64,{img_b64}'
            except Exception as e:
                print(f"Error processing image {img_url}: {e}")

        # Save the consolidated file
        filepath.write_text(str(soup))
        return str(filepath)

    except Exception as e:
        print(f"Error archiving website {url}: {e}")
        return None

def process_plus_links(content):
    """Process +https:// links in the content and create local copies."""
    def replace_link(match):
        url = match.group(1)
        local_path = archive_website(url)
        if local_path:
            return f'[{url}]({url}) ([local copy](/assets/sites/{Path(local_path).name}))'
        return url

    # Find +https:// links and process them
    pattern = r'\+((https?://)[^\s]+)'
    return re.sub(pattern, replace_link, content)

def main():
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