## 2026-05-24 09:00:00 - Welcome to NoteFlow

If you just `pip install`'d NoteFlow and ran `noteflow .` in this folder, this note is what you're reading right now in your browser. Every other note in this file is here to show off what NoteFlow can do — scroll down for the tour.

**Core idea.** `notes.md` lives in your project folder, version-controlled with your code. NoteFlow renders it as a web UI, parses tasks into a shared SQLite index across all your folders, archives linked web pages locally, and stays out of the way. One Python package, no cloud, no account.

### Try this right now

- [ ] !p1 @2026-05-31 #onboarding Read through the rest of the notes in this file
- [ ] !p2 #onboarding Press `/` to focus the search box; try searching for `Schrödinger`
- [ ] !p2 #onboarding Click the `fonts` tab on the right edge — bump notes up to `1.4x` and watch the previews
- [ ] !p3 #onboarding Click the `commits` tab — see this repo's recent git history
- [ ] !p3 #onboarding Click `global tasks →` below the active-tasks box; register a second folder
- [x] Read this welcome note

You can complete a task two ways: tick the checkbox in the web UI, or run `noteflow tasks --toggle <hash>` from the terminal. Both write back to this file *and* to the global task DB.

### Inline task metadata

The token grammar above (`!p1`, `@2026-05-20`, `#onboarding`) drives the `noteflow tasks` CLI filters and renders as colored chips in the active-tasks panel. From any folder with NoteFlow on your PATH:

```bash
noteflow tasks --due today           # today's planning surface
noteflow tasks --priority 1          # everything urgent
noteflow tasks --tag onboarding      # this onboarding list
noteflow tasks --status              # one-liner for shell prompts
noteflow tasks --json                # machine-readable for shell pipelines
```

See `noteflow --help`, `noteflow tasks --help`, and `noteflow append --help` for the full surface.

<!-- note -->
## 2026-05-24 08:00:00 - Sprint planning example

A realistic-looking task list using the inline-metadata grammar. The priorities, due dates, and tags are real tokens — they show up in the global tasks page and the `noteflow tasks` CLI.

### This week

- [ ] !p1 @2026-05-27 #release Cut the v0.4.0 release tarball and update the pip package
- [ ] !p1 @2026-05-27 #release Verify install works cleanly on a fresh Python venv
- [ ] !p2 @2026-05-29 #docs Fill out the "Configuring AI assist" section of the README
- [ ] !p2 #refactor Pull the markdown renderer out of `noteflow.py` into its own module
- [ ] !p3 #cleanup Remove the old `internal/archived/` venvs that no longer work

### Backlog

- [ ] !p3 #ideas Status-bar app for macOS that calls `noteflow tasks --status` every 60s
- [ ] !p3 #ideas Cross-folder AI history view (currently per-folder only)
- [ ] !p3 #ideas Export selection of notes as a single self-contained HTML

### Recently shipped

- [x] !p1 #release Stable task IDs across syncs (upsert on `(folder_id, task_hash)`)
- [x] !p1 #release `noteflow tasks` CLI with the full filter surface
- [x] !p1 #release Search — press `/` to try it
- [x] !p1 #release AI assist slideout — chat your notes via any OpenAI-compatible endpoint

<!-- note -->
## 2026-05-24 07:00:00 - Tables, formatting, and the small stuff

NoteFlow uses [markdown-it-py](https://github.com/executablebooks/markdown-it-py) under the hood with the `dollarmath` plugin for MathJax, so it supports CommonMark + the usual extensions cleanly.

### Tables

| Feature                  | Status   | Where to find it                              |
|--------------------------|----------|-----------------------------------------------|
| Markdown + MathJax       | shipped  | Just write — every note renders               |
| Task inline metadata     | shipped  | `!p1 @YYYY-MM-DD #tag` in any `- [ ]` line    |
| Cross-folder task search | shipped  | `noteflow tasks` CLI + global tasks page      |
| `/` search shortcut      | shipped  | Press `/` anywhere on the page                |
| `+http://` archiving     | shipped  | Prefix any URL with `+` to archive on save    |
| `+file:` snippet sigil   | shipped  | Embed code by file path + line range          |
| AI assist slideout       | shipped  | `ai` tab on the right edge                    |
| Git context in UI        | shipped  | Branch badge + commits panel on the right     |
| Per-section font scaling | shipped  | `fonts` tab — sliders for notes/tasks/links   |

### Blockquotes

> Project notes that *reference* code are everywhere. Notes that *contain* the right information embedded next to your thinking are rare.

### Lists

1. Numbered lists work
2. With sub-items:
   - Like this one
   - Indented two spaces
3. And formatting inside: **bold**, *italic*, `inline code`, ~~strikethrough~~

### Inline code & fenced blocks

You can quote a function name like `parse_markdown()` mid-sentence, or block-quote a snippet:

```python
# strip_checkbox removes the "- [ ] " prefix when displaying tasks.
def strip_checkbox(line: str) -> str:
    line = line.lstrip()
    if line.startswith("- "):
        line = line[2:]
    return line
```

Checkbox markers inside fenced code blocks are *not* parsed as tasks — try writing `- [ ] something` inside ``` fences and confirm it doesn't show in active tasks.

<!-- note -->
## 2026-05-24 06:00:00 - MathJax showcase

NoteFlow ships with MathJax pre-wired: wrap an expression in **single dollar signs for inline math** or **double dollar signs for block math**, and it renders as proper LaTeX. Useful for research notebooks, lecture notes, and any project where the README isn't enough.

### Inline math

Probability of two independent events: $P(A \cap B) = P(A) \cdot P(B)$. The relativistic energy of a body at rest: $E = mc^2$. Both render inline with your prose.

### Block math — Fourier series

The Fourier series of a periodic function $f(x)$ with period $2\pi$:

$$
f(x) = \frac{a_0}{2} + \sum_{n=1}^{\infty} \left( a_n \cos(nx) + b_n \sin(nx) \right)
$$

Coefficients:

- $a_0 = \frac{1}{\pi} \int_{-\pi}^{\pi} f(x) \, dx$
- $a_n = \frac{1}{\pi} \int_{-\pi}^{\pi} f(x) \cos(nx) \, dx$
- $b_n = \frac{1}{\pi} \int_{-\pi}^{\pi} f(x) \sin(nx) \, dx$

### Matrices and eigenvalues

The characteristic polynomial of matrix $\mathbf{A}$:

$$
\det(\mathbf{A} - \lambda \mathbf{I}) = 0
$$

For a $2 \times 2$ matrix $\mathbf{A} = \begin{pmatrix} a & b \\ c & d \end{pmatrix}$, the eigenvalues are:

$$
\lambda_{1,2} = \frac{(a+d) \pm \sqrt{(a+d)^2 - 4(ad-bc)}}{2}
$$

### Statistics

The Central Limit Theorem — for i.i.d. random variables $X_1, X_2, \ldots, X_n$ with mean $\mu$ and variance $\sigma^2$:

$$
\frac{\bar{X}_n - \mu}{\sigma/\sqrt{n}} \xrightarrow{d} \mathcal{N}(0,1) \text{ as } n \to \infty
$$

Bayes' theorem:

$$
P(H \mid E) = \frac{P(E \mid H) \cdot P(H)}{P(E)}
$$

<!-- note -->
## 2026-05-24 05:00:00 - Working notes — complex analysis & quantum mechanics

A long-form example: real working notes that lean on MathJax. Realistic for anyone using NoteFlow as a research notebook.

### Cauchy-Riemann equations

For a complex function $f(z) = u(x, y) + i v(x, y)$ to be differentiable at $z_0$, the partial derivatives must satisfy:

$$
\frac{\partial u}{\partial x} = \frac{\partial v}{\partial y}, \quad \frac{\partial u}{\partial y} = -\frac{\partial v}{\partial x}
$$

If these hold *and* the partial derivatives are continuous, $f$ is **holomorphic** in the neighborhood of $z_0$.

### Residue theorem

For a function $f(z)$ meromorphic on and inside a simple closed contour $C$, with isolated singularities $z_1, z_2, \ldots, z_k$ inside $C$:

$$
\oint_C f(z) \, dz = 2\pi i \sum_{k} \operatorname{Res}(f, z_k)
$$

### Schrödinger equation

Time-independent form:

$$
-\frac{\hbar^2}{2m} \nabla^2 \Psi(\mathbf{r}) + V(\mathbf{r}) \Psi(\mathbf{r}) = E \Psi(\mathbf{r})
$$

Heisenberg uncertainty:

$$
\Delta x \cdot \Delta p \geq \frac{\hbar}{2}
$$

where $\Delta x = \sqrt{\langle x^2 \rangle - \langle x \rangle^2}$ and similarly for $\Delta p$.

### Practice problems

- [ ] !p2 @2026-05-30 #math Verify Fourier convergence for $f(x) = |x|$ on $[-\pi, \pi]$
- [ ] !p2 @2026-06-01 #math Calculate eigenvalues of $\begin{pmatrix} 3 & 1 \\ 1 & 3 \end{pmatrix}$ — sanity-check against the closed form above
- [ ] !p3 #math Sketch a proof of the residue theorem from Cauchy's integral formula
- [ ] !p3 #math Solve the harmonic oscillator using the Schrödinger equation above; compare $\langle x^2 \rangle$ to the classical RMS

<!-- note -->
## 2026-05-24 04:30:00 - Code-aware notes — the `+file:` sigil

NoteFlow ships a markdown sigil that embeds code straight from your repo. When you save a note containing `+file:path/to/file.py#10-25`, it expands at save time into a fenced code block with the language detected from the extension and a `// path#range` header so you can find the source.

Try writing a new note containing exactly this line:

```
The save flow lives at +file:noteflow/noteflow.py#883-897
```

When saved, that single line becomes a real code block referencing the `add_note` route at those exact lines. The sigil supports:

- `+file:path` — entire file
- `+file:path#10` — just line 10
- `+file:path#10-25` — inclusive range

**Security.** Path resolution is sandboxed to the project folder. Absolute paths, `..` escape attempts, and symlinks pointing outside the repo are rejected with a small `<!-- +file rejected: ... -->` comment left next to the sigil so you can see what went wrong.

**Archiver upgrade.** If [`monolith`](https://github.com/Y2Z/monolith) (`brew install monolith`) or [`obelisk`](https://github.com/go-shiori/obelisk) is on your PATH, NoteFlow uses it for `+http://` archives — better fidelity on JS-heavy modern pages. Without either, it falls back to the built-in BeautifulSoup-based inliner.

<!-- note -->
## 2026-05-24 04:00:00 - Web archiving (the `+http://` sigil)

Prefix any URL with `+` and NoteFlow will fetch the page, inline every CSS/JS/image/font as a data URI, and store the result locally so the page survives even if the original gets deleted.

Example you can write in a new note:

```
Saw this technique today: +https://example.com/some-article
```

When saved, that line becomes a regular markdown link pointing to `assets/sites/<timestamp>_<title>-<host>.html` — the locally-archived copy. The archive is fully self-contained: open it in any browser, no network needed.

Useful for:

- **Reference material that might rot** — blog posts and personal sites disappear constantly
- **Citation snapshots** — record the exact state of a source you're quoting
- **Reading offline later** — archive on your laptop, read on a flight

The archive is just an HTML file. It's diff-friendly enough (each archive is one self-contained file referenced from `notes.md`) and you can delete archives you no longer want from the right-column links section.

**Under the hood:** the archiver prefetches up to 32 top-level assets in parallel (12 workers), respects a 30s total deadline so it can't hang the UI, and skips resources larger than 8 MiB. If it runs out of time it writes whatever it managed to inline as a partial archive rather than failing entirely.

<!-- note -->
## 2026-05-24 03:00:00 - AI assist — chat your notes

Click the `ai` tab on the right edge to open the chat slideout. Three sub-tabs: Chat, History, Settings.

**Setup (Settings tab):**

- **Endpoint** — any OpenAI-compatible `/v1/chat/completions` URL. Works with:
  - OpenAI: `https://api.openai.com/v1/chat/completions`
  - Anthropic native: `https://api.anthropic.com/v1/messages` (handled via auto-fallback)
  - Ollama local: `http://localhost:11434/v1/chat/completions`
  - LM Studio local: `http://localhost:1234/v1/chat/completions`
  - LiteLLM proxy / OpenRouter / Groq / Together / etc.
- **API key** — stored in `~/.config/noteflow-py/noteflow.json` (or the macOS equivalent). Never sent to the browser.
- **Model** — whatever your endpoint expects (e.g. `gpt-4o-mini`, `claude-sonnet-4-5`, `llama3.2`).
- **Default context** — "all notes" sends every byte of `notes.md` as the system prompt; "last N lines" trims it.

**What gets sent:** the full contents of *this folder's* `notes.md` as a system prompt, plus your conversation. So the AI's answers are grounded in your actual notes.

**History** lives at `ai_history.md` in this folder. Click "Save to history" on any answer to keep it. The format is human-readable markdown with `<!-- ai -->` separators — grep-friendly, openable in NoteFlow itself.

**Scope split:** API key is global (one key serves all folders), conversation history is per-folder.

- [ ] !p3 #ideas Cross-folder AI history view — aggregate `ai_history.md` from every registered folder
