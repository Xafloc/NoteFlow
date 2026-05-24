"""Save-time content sigils.

A sigil is a tiny markdown extension that the user types into a note
and gets expanded into normal markdown when the note is saved. The
expansion happens once and is stored in notes.md verbatim — so the
final file stays diff-friendly and the content survives even if the
referenced source disappears.

Currently implemented:
  +file:path               — embed an entire file
  +file:path#10            — embed just line 10
  +file:path#10-25         — embed an inclusive range

Resolution is sandboxed to the note's folder. Absolute paths, escape
attempts via "..", and symlinks pointing outside the folder are
refused — the sigil is left in place with a small error comment so
the user can see what went wrong rather than silently failing.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple


# +file:relative/path[#start[-end]]
# Path captures anything that's not whitespace or '#'; line range is optional.
_FILE_SIGIL_RE = re.compile(r'\+file:([^\s#]+)(?:#(\d+)(?:-(\d+))?)?')

# Filename-extension → fenced-code-block language hint. Conservative list;
# anything unknown gets no language hint (still renders as a code block).
_LANG_BY_EXT = {
    "py": "python", "pyi": "python",
    "js": "javascript", "mjs": "javascript", "cjs": "javascript",
    "ts": "typescript", "tsx": "tsx", "jsx": "jsx",
    "go": "go", "rs": "rust", "rb": "ruby", "php": "php",
    "java": "java", "kt": "kotlin", "swift": "swift",
    "c": "c", "h": "c", "cpp": "cpp", "hpp": "cpp", "cc": "cpp",
    "cs": "csharp", "m": "objective-c", "mm": "objective-c",
    "sh": "bash", "bash": "bash", "zsh": "bash", "fish": "fish",
    "ps1": "powershell",
    "md": "markdown", "rst": "rst",
    "json": "json", "yaml": "yaml", "yml": "yaml", "toml": "toml",
    "xml": "xml", "html": "html", "htm": "html", "css": "css",
    "scss": "scss", "sass": "sass", "less": "less",
    "sql": "sql", "graphql": "graphql", "gql": "graphql",
    "dockerfile": "dockerfile",
    "tf": "hcl", "hcl": "hcl",
    "lua": "lua", "r": "r", "jl": "julia",
    "ini": "ini", "conf": "ini", "cfg": "ini",
    "env": "bash",
}


def _lang_for(path: Path) -> str:
    """Best-effort language hint based on the filename."""
    name = path.name.lower()
    if name == "dockerfile" or name.endswith(".dockerfile"):
        return "dockerfile"
    if name in ("makefile", "rakefile", "gemfile"):
        return "makefile" if name == "makefile" else "ruby"
    ext = path.suffix.lstrip(".").lower()
    return _LANG_BY_EXT.get(ext, "")


def _resolve_safely(folder_path: Path, raw_path: str) -> Tuple[Path | None, str | None]:
    """Resolve `raw_path` relative to `folder_path` without escaping it.

    Returns (resolved_path, None) on success, or (None, error_message)
    on any sandbox violation. We reject absolute paths up front so
    `/etc/passwd` can't accidentally make it into a note, and call
    .resolve() after joining so symlinks get followed and verified
    against the base folder.
    """
    rp = Path(raw_path)
    if rp.is_absolute():
        return None, f"absolute path refused: {raw_path}"
    try:
        base = folder_path.resolve()
        target = (folder_path / rp).resolve()
    except (OSError, RuntimeError) as e:
        return None, f"resolve failed: {e}"
    # Path.is_relative_to() requires 3.9+, which the project already mandates.
    if not target.is_relative_to(base):
        return None, f"path escapes project folder: {raw_path}"
    if not target.exists():
        return None, f"file not found: {raw_path}"
    if not target.is_file():
        return None, f"not a regular file: {raw_path}"
    return target, None


def _slice_lines(text: str, start: int | None, end: int | None) -> str:
    """Return a 1-based, inclusive line slice. `end` may be None."""
    lines = text.split("\n")
    if start is None:
        return text
    s = max(1, start) - 1
    e = end if end is not None else start
    e = max(s + 1, e)
    return "\n".join(lines[s:e])


def _format_block(path_str: str, start: int | None, end: int | None,
                  lang: str, body: str) -> str:
    """Produce the fenced code block that replaces the sigil."""
    if start is not None and end is not None and end != start:
        header = f"// {path_str}#{start}-{end}"
    elif start is not None:
        header = f"// {path_str}#{start}"
    else:
        header = f"// {path_str}"
    # Pick a fence long enough to never collide with backticks inside body.
    fence = "```"
    while fence in body:
        fence += "`"
    return f"{fence}{lang}\n{header}\n{body.rstrip()}\n{fence}"


def expand_file_sigils(content: str, folder_path: Path) -> str:
    """Expand every +file: sigil in `content` into a fenced code block.

    The result is what gets stored in notes.md — sigils are a one-shot
    syntactic shortcut, not a live template that re-reads on every render.
    """
    if "+file:" not in content:
        return content

    def replace(match: re.Match) -> str:
        raw_path = match.group(1)
        start = int(match.group(2)) if match.group(2) else None
        end = int(match.group(3)) if match.group(3) else None

        target, err = _resolve_safely(folder_path, raw_path)
        if err:
            print(f"+file sigil rejected: {err}")
            return f"{match.group(0)}  <!-- +file rejected: {err} -->"

        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"{match.group(0)}  <!-- +file rejected: binary file -->"
        except OSError as e:
            return f"{match.group(0)}  <!-- +file rejected: read failed: {e} -->"

        body = _slice_lines(text, start, end)
        return _format_block(raw_path, start, end, _lang_for(target), body)

    return _FILE_SIGIL_RE.sub(replace, content)
