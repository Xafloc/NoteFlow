# NoteFlow

![NoteFlow Banner](https://img.shields.io/badge/NoteFlow-A%20Natural%20Way%20to%20Take%20Notes-blue?style=for-the-badge)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

NoteFlow transforms a single Markdown file into a modern web interface where notes and tasks coexist seamlessly. Let your thoughts flow naturally while keeping your tasks in check.

![Screenshot placeholder - replace with actual app screenshot](/docs/screenshot.png)

## Features

- **📝 Continuous Flow**: All notes stream into a single Markdown file, creating a natural timeline
- **✅ Live Task Dashboard**: Active tasks automatically surface to a dedicated panel
- **🔍 Pure Markdown**: Write in plain Markdown with live preview and checkbox support
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

### Running NoteFlow

```bash
python noteflow.py
```

### Taking Notes

- Type your note in the content area
- Optionally add a title
- Click "Add Note" or press Ctrl+Enter to save

### Creating Tasks

- Use Markdown checkboxes:
  ```markdown
  - [ ] New task
  - [x] Completed task
  ```
- Tasks automatically appear in the Active Tasks panel
- Click checkboxes to mark tasks as complete

### Markdown Support

NoteFlow supports standard Markdown syntax including:
- Headers
- Lists (bulleted and numbered)
- Checkboxes
- Bold/Italic text
- Code blocks
- And more!

## File Structure

Your notes are stored in `notes.md` in your working directory. The file format is simple:

```markdown
===NOTE===
## 2024-10-30 12:34:56 - Optional Title

Your note content here...

===NOTE===
## 2024-10-30 12:33:45

Another note...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Note that by contributing to this project, you agree to license your contributions under the GNU General Public License v3.0.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details. This license ensures that:

- You can freely use, modify, and distribute this software
- Any modifications or derivative works must also be licensed under GPL-3.0
- The source code must be made available when distributing the software
- Changes made to the code must be documented

For more information, see the [full license text](https://www.gnu.org/licenses/gpl-3.0.en.html).

<div align="center">
Made with ❤️ for note-taking enthusiasts
</div>