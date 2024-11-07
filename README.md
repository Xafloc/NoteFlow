# NoteFlow

NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It provides a clean interface for creating, viewing, and managing notes with support for tasks, images, and code snippets.

## Features

![Main View](/screenshot_1.png)

![Local Site Copy](/screenshot_2.png)

![Site Link Example](/screenshot_3.png)

## Features

- **📝 Continuous Flow**: All notes stream into a single Markdown file, creating a natural timeline
- **✅ Active Tasks Tracking**: Active tasks automatically surface to a dedicated panel
- **🔍 Pure Markdown**: Write in plain Markdown and use checkboxes for task management
- **💾 Zero Database**: Your entire note history lives in one portable Markdown file
- **🚀 Instant Start**: Zero configuration required - just launch and start writing
- **🔒 Privacy First**: Runs entirely local - your notes never leave your machine
- **✨ Modern Interface**: Clean, responsive design built with FastAPI
- **📚 Site Links and Archival**: Save site links, and generate a static HTML archive version of linked sites

## Quick Start

To quickly get started with Noteflow, follow these steps:

1. **Install Noteflow**: Use pip to install the package:

   ```bash
   pip install noteflow
   ```

2. **Install Noteflow**: Use Homebrew to install the package:

   ```bash
   brew tap Xafloc/noteflow
   brew install noteflow
   ```

3. **Run Noteflow**: After installation, you can run Noteflow using the command line from any folder you'd like to take notes in:

   ```bash
   noteflow
   ```

4. **Access the Application**: Your web browser should open automatically, else open your web browser and navigate to `http://localhost:8000` to start using Noteflow.

That's it! You're now ready to start using Noteflow for your note-taking needs.

## Requirements

- Python 3.7+
- FastAPI
- uvicorn
- markdown-it-py
- Other dependencies listed in `requirements.txt`

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

### Attaching Images

- Drag and drop images into the Noteflow input box to attach them to your note
- Images are automatically embedded in the note and saved locally within the assets/images folder

### Saving Site Links and Archiving

- Create a link in your note by typing + followed by the URL (e.g., `+https://www.google.com`)
- Site link will be saved and archived locally within the assets/sites folder

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
## 2024-10-30 12:34:56 - Optional Title

Your note content here...

---

## 2024-10-30 12:33:45

Another note...
```

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
