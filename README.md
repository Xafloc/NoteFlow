# NoteFlow

NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It provides a clean interface for creating, viewing, and managing notes with support for tasks, images, and code snippets.

## Features

![Main View](/screenshot_1.png)

![Local Site Copy](/screenshot_2.png)

## Features

- **📝 Continuous Flow**: All notes stream into a single Markdown file, creating a natural timeline
- **✅ Active Tasks Tracking**: Active tasks automatically surface to a dedicated panel
- **🔍 Pure Markdown**: Write in plain Markdown and use checkboxes for task management
- **💾 Zero Database**: Your entire note history lives in one portable Markdown file
- **🚀 Instant Start**: Zero configuration required - just launch and start writing
- **🔒 Privacy First**: Runs entirely local - your notes never leave your machine
- **✨ Modern Interface**: Clean, responsive design built with FastAPI

## Quick Start

To quickly get started with Noteflow, follow these steps:

1. **Install Noteflow**: Use pip to install the package:

   ```bash
   pip install noteflow
   ```

2. **Run Noteflow**: After installation, you can run Noteflow using the command line from any folder you'd like to take notes in:

   ```bash
   noteflow
   ```

3. **Access the Application**: Your web browser should open automatically, else open your web browser and navigate to `http://localhost:8000` to start using Noteflow.

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
