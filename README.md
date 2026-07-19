# AI-OKF

OKF Knowledge Base Agent — automatically explores codebases and generates structured **OKF (Open Knowledge Format)** knowledge bundles.

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Set your API endpoint (defaults to opencode.ai free tier)
export OKF_MODEL="deepseek-v4-flash-free"
export OKF_API_BASE="https://opencode.ai/zen/v1"

# Initialize a knowledge bundle from a codebase
okf init /path/to/project --output ./knowledge-base

# Update it after changes
okf update /path/to/project --output ./knowledge-base
```

## Usage

- `okf init [PATH]` — Full codebase scan, generates complete OKF bundle
- `okf update [PATH]` — Incremental update based on git changes
- `--model, -m` — Choose LLM model (default: deepseek-v4-flash-free)
- `--api-base` — Custom OpenAI-compatible API base URL
- `--output, -o` — Output directory (default: .okf-bundle)

## Output Format

The generated bundle follows [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md):
- Hierarchical markdown with YAML frontmatter
- `index.md` for each directory level
- Cross-linking between concepts
- Every concept has a REQUIRED `type` field
