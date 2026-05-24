# NoteFlow

> **FORMAT CHANGE NOTICE**: As of version 0.3.0, the note separator changed from `---` to `<!-- note -->`. If you're upgrading from an older version, please update your `notes.md` accordingly.

NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It runs locally, stores everything in a single `notes.md` file per folder, and stays out of your way. One Python package, no cloud, no account.

## What's new in 0.4.0

A major release that backports the feature surface from [noteflow-go](https://github.com/Xafloc/NoteFlow-Go):

- **AI assist slideout** — chat your notes via any OpenAI-compatible endpoint (OpenAI, Anthropic-direct, Ollama, LM Studio, LiteLLM, OpenRouter, Groq, Together, etc.). Streaming + automatic non-streaming fallback. Per-folder `ai_history.md` log.
- **Cross-folder global tasks** — register multiple folders; their tasks aggregate to a global page at `/global-tasks`. SQLite-backed with stable task IDs and a 30s background sync.
- **Planning CLI** — `noteflow tasks` (filter by priority/due/tag/project, save views, toggle by hash), `noteflow append` (write a note from stdin or args).
- **Inline task metadata** — `!p1` `!p2` `!p3` priorities, `@YYYY-MM-DD` due dates, `#tag` tags, rendered as colored chips and filterable from the CLI.
- **`+file:` snippet sigil** — `+file:path#10-25` in a note expands at save time into a fenced code block with the file's content at those lines.
- **External archiver autodetect** — if `monolith` or `obelisk` is on your PATH, NoteFlow uses it for higher-fidelity `+http://` archives; otherwise falls back to the built-in BeautifulSoup pipeline.
- **Right-edge tab UI** — four slideout panels (fonts / admin / ai / commits) replace the old hover-to-expand admin menu.
- **Per-section font scaling** — sliders for notes/tasks/links sections with live previews.
- **Local + global search** — press `/` anywhere to focus search; results jump to matching notes.
- **Git context** — branch + short SHA badge in the directory bar, plus a commits panel showing recent `git log`.
- **Code-region-aware task parsing** — checkboxes inside fenced or inline code blocks are no longer mis-parsed as real tasks.
- **CLI flags** — `--help`, `--version`, `--port`, `--no-browser`.

## Screenshots

#### Initial View
![Initial View](/screenshot_1.png)
#### Markdown Editor
![Markdown Editor](/screenshot_2.png)
#### Upload Images and Files
![Upload Images and Files](/screenshot_3.png)
#### Point in Time Site Copy / Bookmark
![Point in Time Site Copy/Bookmark](/screenshot_4.png)
#### Multiple Themes
![Multiple Themes](/screenshot_5.png)
#### Math Rendering
![Math Rendering](/screenshot_6.png)

## Features

- **📝 One big Markdown file** — all notes stream into a single `notes.md`, version-controllable with your code
- **✅ Active task tracking** — checkboxes in any note surface to a dedicated panel
- **🔖 Inline task metadata** — `!p1` priorities, `@YYYY-MM-DD` due dates, `#tag` tags, rendered as colored chips
- **🌐 Cross-folder global tasks** — register multiple project folders, see every open task in one place
- **🤖 AI assist** — chat your notes via any OpenAI-compatible endpoint
- **🔍 Search** — instant local search; `/` shortcut to focus from anywhere
- **🔗 Web archiving** — prefix any URL with `+` to save a self-contained local copy
- **📎 File embed sigil** — `+file:path#10-25` embeds source code at save time
- **🚀 CLI** — `noteflow append`, `noteflow tasks` with filters / saved views / JSON output
- **💾 Zero database for notes** — your note history lives in one portable Markdown file (cross-folder task index uses SQLite for speed)
- **🔒 Privacy first** — runs entirely local; AI key never sent to the browser; no cloud or account
- **🎨 Multiple themes** — dark-orange, dark-blue, light-blue
- **🔢 Math** — MathJax inline (`$...$`) and block (`$$...$$`)
- **🖥️ Multiple instances** — run NoteFlow in any number of folders concurrently

## Installation

### pip (all platforms)

```bash
pip install noteflow
```

### Homebrew (macOS / Linux)

```bash
brew tap Xafloc/noteflow
brew install noteflow
```

### Optional: better-fidelity archiving

`monolith` produces higher-quality `+http://` archives on JS-heavy pages. If installed, NoteFlow uses it automatically; otherwise it falls back to the built-in archiver.

```bash
brew install monolith         # macOS / Linux
# or: cargo install monolith
# or: download binary from https://github.com/Y2Z/monolith/releases
```

## Quick start

```bash
# Run in the current folder
noteflow

# Or point at a specific folder
noteflow /path/to/notes

# Or, for the demo content
noteflow --help
```

Your browser opens automatically at `http://localhost:8000` (or the next free port). Use `--no-browser` to suppress, `--port 8765` to pin a specific port.

## Daily use

### Taking notes

Type in the content area, optionally add a title, hit `Ctrl+Enter` (or `Cmd+Enter` on Mac) or click **Save Note**. Notes save to `notes.md` in the current folder.

### Tasks

Any Markdown checkbox becomes a tracked task:

```markdown
- [ ] Open task
- [x] Completed task
- [ ] !p1 @2026-06-15 #urgent Priority 1, due date, and tag tokens
```

The inline metadata tokens (`!p1` / `!p2` / `!p3`, `@YYYY-MM-DD`, `#tag`) render as colored chips and are filterable from the CLI. Checkboxes inside fenced code blocks (```` ``` ````) or inline backticks aren't parsed as real tasks — write task syntax in documentation without polluting your active-tasks list.

### Cross-folder global tasks

Click **global tasks →** below the active-tasks box (or visit `/global-tasks`) to see every open task across every registered folder. Add a new folder from that page; NoteFlow rescans them every 30 seconds.

### Web archiving — the `+http://` sigil

Prefix any URL with `+` and NoteFlow archives the page locally on save:

```
Saw this technique today: +https://example.com/some-article
```

The line is replaced with a markdown link to a self-contained HTML archive in `assets/sites/`. Useful for citation snapshots, reference material that might rot, and reading offline.

### Code embedding — the `+file:` sigil

```
The save flow lives at +file:noteflow/noteflow.py#883-900
```

On save, the sigil expands into a fenced code block with the file's lines 883–900 and a language hint detected from the extension. Variants:

- `+file:path` — entire file
- `+file:path#10` — just line 10
- `+file:path#10-25` — inclusive range

Path resolution is sandboxed to the project folder; `../escape` attempts and absolute paths are refused.

### AI assist

Click the **ai** tab on the right edge → **Settings**. Fill in:

- **Endpoint** — any OpenAI-compatible `/v1/chat/completions` URL, e.g.:
  - OpenAI: `https://api.openai.com/v1/chat/completions`
  - Anthropic native: `https://api.anthropic.com/v1/messages` (auto-detected)
  - Ollama local: `http://localhost:11434/v1/chat/completions`
  - LM Studio local: `http://localhost:1234/v1/chat/completions`
- **API key** — stored in `~/.config/noteflow-py/noteflow.json` (or the macOS equivalent). Never sent to the browser.
- **Model** — e.g. `gpt-4o-mini`, `claude-sonnet-4-5`, `llama3.2`.
- **Default context** — "all notes" sends every byte of `notes.md` as the system prompt; "last N lines" trims it.

The AI sees *this folder's* `notes.md` as a system prompt, plus your conversation. Click **Save to history** on any answer to keep it in `ai_history.md`.

### Keyboard shortcuts

- `Ctrl+Enter` / `Cmd+Enter` — save the current note
- `/` — focus the search box (anywhere on the page)
- `Esc` — close the active side panel (or clear the search box)

### CLI

```bash
noteflow append --title "from cli" "Some body text"
echo "- [ ] !p1 #release ship 0.4.0" | noteflow append

noteflow tasks                    # human-readable table of open tasks
noteflow tasks --status           # one-liner for shell prompts
noteflow tasks --priority 1       # urgent only
noteflow tasks --due today
noteflow tasks --tag release --json
noteflow tasks --toggle <hash>    # flip a task by task_hash prefix

noteflow tasks --priority 1 --save-view urgent
noteflow tasks --view urgent      # apply a saved filter
```

See `noteflow --help`, `noteflow tasks --help`, and `noteflow append --help` for the full surface.

## File structure

Per folder you point NoteFlow at:

```
your-folder/
├── notes.md            # your notes (the source of truth)
├── ai_history.md       # saved AI conversations (per-folder)
└── assets/
    ├── images/         # drag-and-dropped images
    ├── files/          # drag-and-dropped files
    └── sites/          # +http archives + sidecar .tags metadata
```

Per user (shared across all folders):

```
~/.config/noteflow-py/        # Linux; on macOS: ~/Library/Application Support/noteflow-py/
├── noteflow.json             # theme, font scales, AI config (key, endpoint, model)
├── tasks.db                  # SQLite cache for cross-folder global tasks
└── task_views.json           # saved CLI filter combinations
```

The `noteflow-py` dir name avoids collision with [noteflow-go](https://github.com/Xafloc/NoteFlow-Go) if both are installed.

## Requirements

- Python 3.9+
- Dependencies installed automatically by pip: `fastapi`, `uvicorn`, `markdown-it-py`, `mdit-py-plugins`, `python-multipart`, `pydantic`, `requests`, `beautifulsoup4`, `platformdirs`, `psutil`
- Optional: `monolith` or `obelisk` on PATH for higher-fidelity web archiving

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details. In short:

- You can freely use, modify, and distribute this software
- Modifications and derivative works must also be licensed under GPL-3.0
- Source code must be made available when distributing the software
- Changes must be documented

For more, see the [full license text](https://www.gnu.org/licenses/gpl-3.0.en.html).

<div align="center">
Made with ❤️ for note-taking enthusiasts
</div>
