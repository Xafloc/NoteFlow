# NoteFlow — CLAUDE.md

## Project overview

NoteFlow is a local-first, Markdown-based note-taking app. Python/FastAPI backend serving a vanilla JS frontend — all in a single file (`noteflow/noteflow.py`). No framework, no bundler. Notes live in `notes.md` per folder; user config in `~/.config/noteflow-py/noteflow.json`.

## Architecture

- **Single-file app**: `noteflow/noteflow.py` (~5k lines) — FastAPI routes, HTML template, CSS, and JS are all embedded. Supporting modules live beside it: `ai.py`, `folders.py`, `archiver.py`, `cli.py`, `sigils.py`.
- **Entry point**: `noteflow.noteflow:main` (registered in both `setup.py` and `pyproject.toml`).
- **Config**: JSON file managed by `load_config()` / `save_config()`. Globals (`CURRENT_THEME`, `FONT_SCALES`, `AUTOSAVE`, `AI_CONFIG`) loaded at startup, mutated in-memory by API endpoints, persisted on change. `load_config()` only rewrites disk when normalization actually changes values.
- **Frontend**: Vanilla JS embedded in a Python triple-quoted string. Config values are injected via string concatenation at template render time (e.g. `""" + CURRENT_THEME + """`).
- **Notes I/O**: `NoteManager` keeps notes in memory; `save()` writes atomically (`.tmp` + `os.replace`). `reload_if_changed()` reloads when `notes.md` mtime advances (skipped while dirty).
- **Rendering**: Module-level MarkdownIt instance + per-note HTML cache; task checkbox indices resolved via a lookup map. Checkbox toggles return `active_tasks` so the client avoids a full notes re-render.
- **Bind**: Defaults to `127.0.0.1`; `--host` / `--port` flags in `main()`.

## Version strings

There are **four files** that must stay in sync when bumping the version:

1. `noteflow/noteflow.py` — `__version__ = "X.Y.Z"`
2. `noteflow/__init__.py` — `__version__ = 'X.Y.Z'`
3. `pyproject.toml` — `version = "X.Y.Z"`
4. `setup.py` — `version='X.Y.Z'`

Always update all four together.

## Build and release

### Prerequisites

```bash
pip install build twine
```

### Full release checklist

1. **Bump version** in all four files listed above.
2. **Commit and tag**:
   ```bash
   git add noteflow/noteflow.py noteflow/__init__.py pyproject.toml setup.py
   git commit -m "feat: <description> (vX.Y.Z)"
   git tag vX.Y.Z
   git push origin main --tags
   ```
3. **Build PyPI packages**:
   ```bash
   rm -rf dist/*
   python -m build
   ```
4. **Upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```
   Credentials are in `~/.pypirc`.
5. **Create GitHub release**:
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z — <title>" --notes "<release notes>"
   ```
6. **Update Homebrew formula** (separate repo: `Xafloc/homebrew-NoteFlow`):
   ```bash
   # Get the sha256 of the new tag tarball
   curl -sL https://github.com/Xafloc/NoteFlow/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256

   # Edit homebrew-NoteFlow/noteflow-py.rb:
   #   - Update url to new tag
   #   - Update sha256
   #   - Update assert_match version in test block
   cd /path/to/homebrew-NoteFlow
   git add noteflow-py.rb
   git commit -m "bump noteflow-py to vX.Y.Z"
   git push
   ```

### Homebrew tap location

The formula lives at `/Users/darren/Documents/Projects/homebrew-NoteFlow/noteflow-py.rb` (repo: `Xafloc/homebrew-NoteFlow`). It uses `virtualenv_install_with_resources` — resource blocks list pinned PyPI dependency tarballs. These may need updating when dependencies change.

## Development

```bash
# Run locally (auto-opens browser; localhost only)
noteflow --port 8765

# Run without opening browser
noteflow --port 8765 --no-browser

# LAN bind (no auth — only for intentional multi-device use)
noteflow --host 0.0.0.0 --port 8765

# Verify import without starting server
python -c "import noteflow.noteflow"

# Unit tests
python -m unittest tests.test_core -v
```

Editable install (so `noteflow` on PATH tracks this checkout):

```bash
pip install -e .
```

## Adding a new config setting

Follow the pattern used by `autosave` or `font_scales`:

1. Add a default factory function (e.g. `_default_autosave()`).
2. Add the key to `default_config` in `load_config()`.
3. Add normalization logic in the config-load path.
4. Add a module-level global (e.g. `AUTOSAVE = config.get(...)`).
5. Add `GET`/`POST` API endpoints.
6. Inject initial values into the JS template via string concatenation.
7. Add UI controls in the admin panel (`<div class="pane" data-panel="admin">`).

## Adding a new side panel tab

1. Add a `<button>` in the `#rightTabs` nav.
2. Add a `<div class="pane" data-panel="name">` inside `#sidePanel`.
3. The `togglePanel()` JS function handles show/hide automatically.

## Testing

Unit tests live under `tests/` (stdlib `unittest`; no pytest required):

```bash
python -m unittest tests.test_core -v
```

Coverage includes atomic save, task reindex, external reload, AI context selection, upload sanitization, folders task extract, and checkbox lookup.

Also verify manually by:
- Importing the module: `python -c "import noteflow.noteflow"`
- Starting the server and testing in-browser (checkbox toggle should not full-refresh notes)
- Hitting API endpoints with curl (`/api/notes/status`, `/api/tasks/{i}`)
