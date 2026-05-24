"""AI assist — chat your notes via any OpenAI-compatible endpoint.

Mirrors the Go v1.7 feature: a slideout chat panel backed by a
configurable OpenAI-compatible /v1/chat/completions URL. Works with
OpenAI, Anthropic via a compatibility proxy, LiteLLM, Ollama, vLLM, etc.

Security notes:
  - API key is stored on disk in the same user-config JSON the rest of
    NoteFlow uses; only the server has it.
  - The browser never receives the key — GET /api/ai/config returns
    `api_key_set: bool` only.
  - All upstream traffic is proxied by the server; the browser only
    talks to the local server.

Streaming:
  - The server reads the upstream SSE stream line-by-line and re-emits
    each token as `data: {"text": "..."}` to the client.
  - End of stream is signaled with `data: {"done": true}`.
  - On error: `data: {"error": "message"}` followed by `data: {"done": true}`.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import requests

from . import folders as folders_module  # for shared note/header parsing


###############################################################################
# Config
###############################################################################
AI_CONFIG_KEYS = ("endpoint", "api_key", "model", "default_context")
DEFAULT_AI_CONFIG = {
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "api_key": "",
    "model": "gpt-4o-mini",
    "default_context": "all",
}
UPSTREAM_TIMEOUT = 300  # seconds — the AI may stream for a while


def merge_ai_config(loaded: Dict) -> Dict:
    """Fill in defaults for any missing AI keys."""
    raw = loaded.get("ai") if isinstance(loaded, dict) else None
    raw = raw if isinstance(raw, dict) else {}
    return {k: raw.get(k, DEFAULT_AI_CONFIG[k]) for k in AI_CONFIG_KEYS}


def sanitized_view(ai_cfg: Dict) -> Dict:
    """What the browser is allowed to see — never includes the api key."""
    return {
        "endpoint": ai_cfg.get("endpoint", ""),
        "model": ai_cfg.get("model", ""),
        "default_context": ai_cfg.get("default_context", "all"),
        "api_key_set": bool((ai_cfg.get("api_key") or "").strip()),
    }


def apply_update(ai_cfg: Dict, body: Dict) -> Dict:
    """Merge a partial update into the AI config. An empty/missing api_key
    in the update leaves the existing one in place — so the browser can
    edit endpoint/model without re-sending the key."""
    out = dict(ai_cfg)
    for k in AI_CONFIG_KEYS:
        if k in body and body[k] is not None:
            if k == "api_key" and not str(body[k]).strip():
                continue  # keep existing
            out[k] = body[k]
    return out


###############################################################################
# Prompt assembly
###############################################################################
def _read_notes_md(folder_path: Path) -> str:
    notes_md = folder_path / "notes.md"
    if not notes_md.exists():
        return ""
    try:
        content = notes_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = notes_md.read_text(encoding="utf-8", errors="replace")
    return content.replace("\r\n", "\n").replace("\r", "\n")


def build_messages(
    user_messages: List[Dict],
    context: str,
    folder_path: Path,
) -> List[Dict]:
    """Prepend a system prompt with the user's notes as context."""
    notes_text = _read_notes_md(folder_path)
    if not notes_text:
        system_body = (
            "You are NoteFlow's AI assistant. The user's notes.md is currently empty."
        )
    else:
        ctx = (context or "all").strip().lower()
        if ctx == "all":
            included = notes_text
        else:
            try:
                n = int(ctx)
                included = "\n".join(notes_text.splitlines()[: max(0, n)])
            except ValueError:
                included = notes_text
        system_body = (
            "You are NoteFlow's AI assistant. The user's notes (a markdown "
            "file split by `<!-- note -->` delimiters) are below. Answer "
            "concisely, cite specific notes by their title or timestamp "
            "when relevant, and format responses in markdown.\n\n"
            "----- BEGIN notes.md -----\n"
            f"{included}\n"
            "----- END notes.md -----\n"
        )
    msgs = [{"role": "system", "content": system_body}]
    for m in user_messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant", "system") and isinstance(content, str):
            msgs.append({"role": role, "content": content})
    return msgs


###############################################################################
# Streaming proxy
###############################################################################
def stream_chat(ai_cfg: Dict, messages: List[Dict]) -> Iterator[bytes]:
    """Yield SSE-formatted bytes for FastAPI's StreamingResponse.

    Runs synchronously; FastAPI/Starlette will iterate this in a thread,
    so blocking on requests.iter_lines is fine and doesn't stall the
    event loop.
    """
    endpoint = (ai_cfg.get("endpoint") or "").strip()
    api_key = (ai_cfg.get("api_key") or "").strip()
    model = (ai_cfg.get("model") or "").strip()
    if not endpoint or not api_key or not model:
        yield _sse_error("AI is not configured. Set endpoint, model, and API key first.")
        yield _sse_done()
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    try:
        with requests.post(
            endpoint,
            headers=headers,
            json=payload,
            stream=True,
            timeout=UPSTREAM_TIMEOUT,
        ) as resp:
            if not resp.ok:
                detail = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
                yield _sse_error(f"upstream error: {detail}")
                yield _sse_done()
                return
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content")
                if text:
                    yield _sse_text(text)
        yield _sse_done()
    except requests.Timeout:
        yield _sse_error("upstream request timed out")
        yield _sse_done()
    except Exception as e:
        yield _sse_error(f"upstream proxy error: {e}")
        yield _sse_done()


def _sse_text(text: str) -> bytes:
    return ("data: " + json.dumps({"text": text}) + "\n\n").encode("utf-8")


def _sse_done() -> bytes:
    return b'data: {"done": true}\n\n'


def _sse_error(message: str) -> bytes:
    return ("data: " + json.dumps({"error": message}) + "\n\n").encode("utf-8")


###############################################################################
# ai_history.md
###############################################################################
HISTORY_SEPARATOR = "\n<!-- ai -->\n"
HEADER_RE = re.compile(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\s+-\s+(.*))?$')


class AIHistory:
    """Append-only log of AI Q+A entries stored in basePath/ai_history.md.

    Each entry is one note-like block:
        ## YYYY-MM-DD HH:MM:SS - <question>

        > Model: <model> | Context: <ctx>

        ### Question
        <question body>

        ### Response
        <response markdown>

        <!-- ai -->

    Entries are referenced by their timestamp string, which is unique to
    second-precision and URL-safe enough for our purposes.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.file_path = base_path / "ai_history.md"
        if not self.file_path.exists():
            self.file_path.write_text("", encoding="utf-8")

    # -- read -----------------------------------------------------------
    def list_entries(self) -> List[Dict]:
        content = self.file_path.read_text(encoding="utf-8")
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        entries: List[Dict] = []
        for raw in content.split(HISTORY_SEPARATOR):
            block = raw.strip()
            if not block:
                continue
            entries.append(self._parse(block))
        # Newest first.
        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return entries

    @staticmethod
    def _parse(block: str) -> Dict:
        lines = block.split("\n")
        header = lines[0] if lines else ""
        m = HEADER_RE.match(header)
        timestamp = m.group(1) if m else ""
        title = (m.group(2) if m and m.group(2) else "").strip()

        body = "\n".join(lines[1:]).strip()
        model = ""
        context = ""
        meta_match = re.search(
            r'>\s*Model:\s*([^|]+?)\s*\|\s*Context:\s*([^\n]+)', body
        )
        if meta_match:
            model = meta_match.group(1).strip()
            context = meta_match.group(2).strip()

        # Split out question and response sections.
        question = ""
        response = ""
        q_idx = body.find("### Question")
        r_idx = body.find("### Response")
        if q_idx >= 0 and r_idx > q_idx:
            question = body[q_idx + len("### Question"): r_idx].strip()
            response = body[r_idx + len("### Response"):].strip()
        else:
            response = body
            question = title

        return {
            "id": timestamp,
            "timestamp": timestamp,
            "title": title or question[:80],
            "model": model,
            "context": context,
            "question": question,
            "response": response,
        }

    # -- write ----------------------------------------------------------
    def append_entry(
        self,
        question: str,
        response: str,
        model: str = "",
        context: str = "",
    ) -> Dict:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        short_q = question.strip().split("\n", 1)[0]
        if len(short_q) > 80:
            short_q = short_q[:77] + "..."

        block = (
            f"## {ts} - {short_q}\n"
            f"\n"
            f"> Model: {model or 'unknown'} | Context: {context or 'all'}\n"
            f"\n"
            f"### Question\n{question.strip()}\n"
            f"\n"
            f"### Response\n{response.strip()}\n"
        )

        existing = self.file_path.read_text(encoding="utf-8")
        if existing.strip():
            new = existing.rstrip("\n") + HISTORY_SEPARATOR + block
        else:
            new = block
        if not new.endswith("\n"):
            new += "\n"
        self.file_path.write_text(new, encoding="utf-8")
        return {
            "id": ts,
            "timestamp": ts,
            "title": short_q,
            "model": model,
            "context": context,
            "question": question,
            "response": response,
        }

    def delete_entry(self, entry_id: str) -> bool:
        content = self.file_path.read_text(encoding="utf-8")
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        blocks = [b.strip() for b in content.split(HISTORY_SEPARATOR) if b.strip()]
        kept = []
        removed = False
        for b in blocks:
            first_line = b.split("\n", 1)[0]
            m = HEADER_RE.match(first_line)
            if m and m.group(1) == entry_id:
                removed = True
                continue
            kept.append(b)
        if not removed:
            return False
        if kept:
            new = HISTORY_SEPARATOR.join(kept) + "\n"
        else:
            new = ""
        self.file_path.write_text(new, encoding="utf-8")
        return True
