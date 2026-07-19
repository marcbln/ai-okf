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

# Generate .env.local from schema (then edit to add your API key)
varlock load --format env > .env.local

# Run via varlock to inject env vars securely
varlock run -- okf init /path/to/project --output ./knowledge-base
```

### Provider and model

Specify a model with `--model` / `-m` in `provider/model` format:

| Example                                      | Provider       | Model                        |
|----------------------------------------------|----------------|------------------------------|
| `-m opencode-zen/deepseek-v4-flash-free`     | Opencode Zen   | `deepseek-v4-flash-free`     |
| `-m opencode-go/deepseek-v4-pro`             | Opencode Go    | `deepseek-v4-pro`            |
| `-m openrouter/openai/gpt-5.2`               | OpenRouter     | `openai/gpt-5.2`             |

Default: `opencode-zen/deepseek-v4-flash-free` (free tier, no subscription needed).

The API base URL is hardcoded per provider. You only need to set the matching API key in `.env.local`:

| Key                  | Required for               |
|----------------------|----------------------------|
| `OPENCODE_API_KEY`   | Opencode Zen / Go          |
| `OPENROUTER_API_KEY` | OpenRouter                 |

## Usage

- `okf init [PATH]` — Full codebase scan, generates complete OKF bundle
- `okf update [PATH]` — Incremental update based on git changes
- `--model, -m` — LLM model in `provider/model` format (default: opencode-zen/deepseek-v4-flash-free)
- `--api-base` — Override API base URL (normally inferred from model provider)
- `--output, -o` — Output directory (default: .okf-bundle)

### Env management (Varlock)

This project uses [Varlock](https://varlock.dev) for environment variable validation and secure injection.

```bash
# Generate .env.local from schema defaults + your current env (edit to fill in secrets)
varlock load --format env > .env.local

# Validate your config
varlock load

# Run any command with validated env vars
varlock run -- okf init /path/to/project
```

## Output Format

The generated bundle follows [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md):
- Hierarchical markdown with YAML frontmatter
- `index.md` for each directory level
- Cross-linking between concepts
- Every concept has a REQUIRED `type` field
