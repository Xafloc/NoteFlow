# NoteFlow

NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It provides a clean interface for creating, viewing, and managing notes with support for tasks, images, and code snippets.

## Features

![Main View](/screenshot_1.png)

## Features

- **📝 Continuous Flow**: All notes stream into a single Markdown file, creating a natural timeline
- **✅ Active Tasks Tracking**: Active tasks automatically surface to a dedicated panel
- **🔍 Pure Markdown**: Write in plain Markdown and use checkboxes for task management
- **💾 Zero Database**: Your entire note history lives in one portable Markdown file
- **🚀 Instant Start**: Zero configuration required - just launch and start writing
- **🔒 Privacy First**: Runs entirely local - your notes never leave your machine
- **✨ Modern Interface**: Clean, responsive design built with FastAPI

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Xafloc/NoteFlow.git
cd NoteFlow

# Install dependencies
pip install -r requirements.txt

# Run NoteFlow
python noteflow.py
```

Your default browser will automatically open to `http://localhost:8000` (or another available port if 8000 is in use).

## Requirements

- Python 3.7+
- FastAPI
- uvicorn
- markdown-it-py
- Other dependencies listed in `requirements.txt`

## Installation

1. Ensure you have Python 3.7 or newer installed
2. Clone this repository
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
```bash
python noteflow.py
```

2. Your default web browser will automatically open to the application (typically at http://localhost:8000)

3. Create notes using Markdown syntax and give your note a title:
   - Use `- [ ]` for tasks
   - Drag and drop images directly into the editor
   - Use standard Markdown syntax for formatting
   - Press Ctrl+Enter to save notes

## Directory Structure

```
current_directory/
├── assets/
│   ├── images/    # Uploaded images
│   └── sites/     # Site-related assets
├── notes.md       # Notes storage file
```

## Markdown Support

- Headers (`# H1`, `## H2`, etc.)
- Lists (ordered and unordered)
- Task lists (`- [ ]` and `- [x]`)
- Code blocks with syntax highlighting
- Images
- Bold and italic text
- Links

## Development

The application is built with:
- FastAPI for the backend
- Pure JavaScript for frontend interactions
- Markdown-it for Markdown parsing
- Highlight.js for code syntax highlighting

## License

[MIT License](LICENSE)

<div align="center">
Made with ❤️ for note-taking enthusiasts
</div>
