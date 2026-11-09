# AI-OKF

**OKF Knowledge Base Agent** — scans codebases and generates structured OKF knowledge bundles via LLM.

## Setup

```bash
uv venv
source .venv/bin/activate && uv pip install -e ".[dev]"
```

Env uses [Varlock](https://varlock.dev). Generate `.env.local` from schema:
```bash
varlock load --format env > .env.local   # then edit to add API key(s)
```

Run any command through `varlock run --` (injects validated env). The `env.py` module is auto-generated from `.env.schema` — do not edit directly.

## Commands

```bash
okf init [PATH]                    # full codebase scan → OKF bundle
okf init [PATH] -o <dir>           # custom output dir (default: .okf-bundle)
okf init [PATH] -m <provider/model> # pick LLM (default: opencode-zen/nemotron-3-ultra-free)
okf init [PATH] -f                 # overwrite existing bundle
okf update [PATH]                  # incremental update from git changes
okf config show                    # effective config + parsed config paths
```

Privacy is local-only by default: non-loopback `--api-base` values are refused
unless `--cloud` is passed. Secret/credential files, binaries, and files over
`MAX_FILE_BYTES` are excluded from scans.

Providers: `opencode-zen` (free), `opencode-go`, `openrouter`. API key requirement follows from `-m` prefix — set `OPENCODE_API_KEY` or `OPENROUTER_API_KEY`.

## Quality commands

All via `uv run`:

| Task | Command |
|---|---|
| Tests | `uv run pytest` |
| Single test | `uv run pytest tests/test_foo.py -k test_bar -v` |
| Lint | `uv run ruff check src/ tests/` |
| Format check | `uv run black --check src/ tests/` |
| Type check | `uv run mypy src/` |

`ruff` selects `E,F,W,I`. `mypy` is strict. `black` line-length 88.

## Package layout

```
src/ai_okf/
├── cli.py              # Typer entrypoint (okf)
├── config.py           # Defaults, provider URLs, API key env mapping
├── commands/           # init_cmd.py, update_cmd.py
├── core/               # scanner.py, git_scanner.py, okf_bundle.py
├── models/             # okf.py, plan.py (pydantic models)
└── agent/              # pydantic-ai agent builder + LLM capabilities
tests/                  # pytest, tmp_path fixtures, no integration deps
```

## Architecture notes

- Scanner (`core/scanner.py`) walks `root.rglob("*")`, skips `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `*.pyc` dirs + `.okf-bundle`. Language map covers 20+ extensions.
- `CodebaseAnalysisCapability` equips the agent with three tools:
  - `read_file_content`: Reads up to 100KB of file text safely, preventing context limit saturation.
  - `find_files_matching`: Locates specific paths based on wildcard globs or substring matches.
  - `search_text_in_files`: Performs rapid, case-insensitive substring searches across non-excluded text files, highlighting file paths and line numbers.
- `okf init` pipeline: scan → LLM plans concepts (typed `list[OKFConceptPlan]`) → LLM drafts each concept → writes `.md` files with YAML frontmatter to output dir → writes `index.md` + `.okf-metadata.json`.
- `okf update` reads `last_ingested_commit` from `.okf-metadata.json`, runs `git diff` since that ref, asks LLM to update bundle. Updates `last_ingested_commit` on success.
- LLM fallback: if `output_type` structured response fails, extracts JSON from text with regex.
- Output follows [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — markdown with YAML frontmatter, hierarchical `index.md`, cross-linking.
