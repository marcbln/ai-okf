# AI-OKF

OKF Knowledge Base Agent — automatically explores codebases and generates structured **OKF (Open Knowledge Format)** knowledge bundles.

## Karpathy LLM Wiki Architecture

Unlike standard chunk-and-search vector RAG models which are stateless, `ai-okf` generates a persistent, compounding, structured knowledge base directly written in Git-versioned Markdown.

1. **Planning Phase:** A deep analysis mapping codebase structures to discrete OKF Concepts.
2. **Modular Compilation:** The agent reads focused file bundles and authors isolated concept sheets with standard frontmatter.
3. **Diff-Driven Evolution:** Updates run iteratively over code changes, keeping documentation fresh without full codebase rebuilds.

## Quick Start

```bash
uv venv
source .venv/bin/activate && uv pip install -e ".[dev]"

# Set your API endpoint and model (defaults to opencode.ai free tier)
export OKF_MODEL="deepseek-v4-flash-free"
export OKF_API_BASE="https://opencode.ai/zen/v1"

# Initialize a knowledge bundle from a codebase
okf init /path/to/project --output ./knowledge-base

# Update it incrementally after making changes
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
