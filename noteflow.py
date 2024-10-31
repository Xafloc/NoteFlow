from fastapi import FastAPI, HTTPException, Path
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

app = FastAPI()

# Mount the local directories
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/fonts", StaticFiles(directory=Path(__file__).parent / "fonts"), name="fonts")

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
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {}
            },
            daisyui: {
                themes: ["light", "dark"],
            },
        }
    </script>
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
            font-family: 'space_monoregular', Arial, sans-serif;
        }

        .note-content img { max-width: 100%; }
        .note-content { scroll-margin-top: 100px; }
        
        .markdown-body {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        /* First level bullets */
        .markdown-body ul li::before {
            content: "*";
            display: inline-block;
            width: 1em;
            margin-left: -1em;
        }
        /* Second level bullets */
        .markdown-body ul ul li::before {
            content: "›";
            margin-left: -1em;
}
        /* Third level bullets */
        .markdown-body ul ul ul li::before {
            content: "»";
            margin-left: -1em;
        }
        .markdown-body ul,
        .markdown-body ol {
            list-style-position: outside;
            padding-left: 1.5rem;
            margin-top: 0.15rem;
            margin-bottom: 0.15rem;
        }
        .markdown-body li {
            margin-bottom: 0.15rem;
        }
        .markdown-body input[type="checkbox"] {
            margin-right: 0.5rem;
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
        .note-timestamp {
            display: block;
            font-size: 0.75rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }

        /* Adjust header and layout styles */
        .fixed-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            z-index: 10;
            padding-bottom: 1rem;
        }

        body {
            margin-top: 150px;
        }

        .notes-container {
            max-width: 64rem;
            margin-left: auto;
            margin-right: auto;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Adjust the layout proportions */
        #noteForm {
            width: 100%;
        }
        .flex-1 {
            flex: 1 1 0%;
            min-width: 0;
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
            word-break: break-word;
            white-space: pre-wrap; /* Maintain line breaks for long tasks */
        }

        /* Adjust the "Add Note" button size */
        #noteForm button {
            width: 100px;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }
    </style>
</head>
<body class="min-h-screen bg-base-200" data-theme="light">
    <div class="fixed-header bg-base-100">
        <div class="w-full py-2 px-4">
            <div class="flex w-full">
                <!-- Left side: Form (65%) -->
                <div class="w-2/3 pr-4">
                    <form id="noteForm" class="w-full">
                        <div class="flex w-full mb-2">
                            <label for="noteTitle" class="w-32 flex-shrink-0 label">Note Title:</label>
                            <div class="flex-1">
                                <input 
                                    type="text" 
                                    id="noteTitle" 
                                    name="noteTitle"
                                    class="input input-bordered w-full" 
                                    placeholder="Enter note title..."
                                >
                            </div>
                        </div>
                        <div class="flex w-full">
                            <div class="w-32 flex-shrink-0 flex flex-col justify-between">
                                <label for="noteInput" class="label">New Note:</label>
                                <button 
                                    type="submit" 
                                    class="btn btn-primary"
                                >
                                    Add Note
                                </button>
                            </div>
                            <div class="flex-1">
                                <textarea 
                                    id="noteInput" 
                                    name="noteInput"
                                    class="textarea textarea-bordered w-full" 
                                    rows="5"
                                    placeholder="Enter your note in Markdown format..."
                                ></textarea>
                            </div>
                        </div>
                    </form>
                </div>
                
                <!-- Right side: Active Tasks (35%) -->
                <div class="w-1/3 border-l pl-4">
                    <h3 class="text-lg font-semibold mb-2">Active Tasks</h3>
                    <div id="activeTasks" class="space-y-1 overflow-y-auto">
                        <!-- Tasks will be populated here -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="notes-container" id="notesContainer">
        <div id="notes" class="space-y-6"></div>
    </div>

    <script>
        async function loadNotes() {
            const response = await fetch('/api/notes');
            const html = await response.text();
            document.getElementById('notes').innerHTML = html;
            await updateActiveTasks();
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

        loadNotes();
    </script>
</body>
</html>
    """

@app.get("/api/notes")
async def get_notes():
    notes_file = init_notes_file()
    content = notes_file.read_text()
    
    # Split content by note separator and filter out empty strings
    notes = [note.strip() for note in content.split("===NOTE===") if note.strip()]
    
    html_notes = []
    # Initialize global checkbox_index
    global_checkbox_index = 0
    
    for note_index, note in enumerate(notes):
        lines = note.split('\n')
        timestamp = lines[0]
        note_content = '\n'.join(lines[1:])
        
        # Initialize MarkdownIt and use the custom task list plugin
        md = MarkdownIt()
        task_list_plugin(md)
        
        # Prepare env with note_index and current global_checkbox_index
        env = {'note_index': note_index, 'checkbox_index': global_checkbox_index}
        
        # Render the note content to HTML
        rendered_content = md.render(note_content, env)
        
        # Update the global_checkbox_index with the count of checkboxes in this note
        global_checkbox_index = env.get('checkbox_index')
        
        # Wrap the timestamp and content in HTML
        html_note = f'''
        <div class="markdown-body">
            <span class="note-timestamp">{timestamp}</span>
            {rendered_content}
        </div>
        '''
        html_notes.append(html_note)
    
    # Join all formatted notes
    html_content = '\n<div class="my-4"></div>\n'.join(html_notes)
    return HTMLResponse(html_content)

@app.post("/api/notes")
async def add_note(note: Note):
    notes_file = init_notes_file()
    current_content = notes_file.read_text()
    
    # Format new note with separators
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f" - {note.title}" if note.title else ""
    formatted_note = f"===NOTE===\n## {timestamp}{title}\n\n{note.content}\n"
    
    # Prepend to file (add to top)
    with notes_file.open('w') as f:
        f.write(formatted_note + current_content)
    
    return {"status": "success"}

class UpdateNoteRequest(BaseModel):
    checked: bool
    checkbox_index: int

@app.patch("/api/update-checkbox")
async def update_checkbox(request: UpdateNoteRequest):
    notes_file = init_notes_file()
    content = notes_file.read_text()
    notes = [note.strip() for note in content.split("===NOTE===") if note.strip()]
    
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
                    updated_content = "\n===NOTE===\n".join(notes)
                    notes_file.write_text(updated_content)
                    return {"status": "success"}
                current_index += 1
    
    return {"status": "success"}

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