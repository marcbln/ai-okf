I need an agent which creates (and later maintains) a knowledge base by exploring a codebase (and git history if it helps).
OKF spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
Not sure if 1 command is enough or if we better create 2 commands (`init` and `update`). 
It should use PydanticAI 2.0
- https://pydantic.dev/docs/ai/core-concepts/capabilities/
- check /home/marc/devel/git-digest/repos/orbit-support-agent for PydanticAI 2.0 based example).
It should use deepseek v4 flash free, but other LLMs should be possible too.
```
> curl -s https://opencode.ai/zen/v1/models | jq    | grep -i free -C 10
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "big-pickle",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "deepseek-v4-flash-free",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "mimo-v2.5-free",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "hy3-free",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "nemotron-3-ultra-free",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    },
    {
      "id": "north-mini-code-free",
      "object": "model",
      "created": 1784402501,
      "owned_by": "opencode"
    }
  ]
}
```




<instruction>
Create a **detailed** multi phased implementation plan in markdown format. 

## Plan Structure
- Include YAML frontmatter with the following fields:
```yaml
---
filename: "_ai/backlog/active/{YYMMDD_HHmm}__IMPLEMENTATION_PLAN__{name-of-the-plan}.md"
title: "Descriptive title of the plan"
createdAt: YYYY-MM-DD HH:mm
updatedAt: YYYY-MM-DD HH:mm
status: draft|in-progress|completed
priority: low|medium|high|critical
tags: [tag1, tag2, tag3]
estimatedComplexity: simple|moderate|complex
documentType: IMPLEMENTATION_PLAN
---
```
- The first section of the plan briefly describes the problem to be solved.

- The second section is an executive summary of the solution that this plan provides.

- The third section contains project environment details:
```
- Project Name: Python Project
- Frontend root: frontend
- Backend root: src




```
- The plan will be implemented by an AI coding agent.
- Include source code in the plan, mark each code block as [NEW FILE], [MODIFY], or [DELETE] to show the type of change.
- The plan should also include an update of the user documentation, if needed.
- Please follow SOLID principles.
- The final phase of the plan should handle project housekeeping: update `.gitignore` (if new file types/directories/build artifacts are introduced) and `README.md` (if setup, usage, or structure changes).




## Project Conventions & Reference Material
Include the relevant conventions below when drafting the plan so the AI has direct access to the latest standards.

    



### Python Conventions
---
name: "Python Conventions"
description: "PYTHON CONVENTIONS"
createdAt: 2025-12-14
createdBy: Cascade
tags: [python, conventions, code-style, pep8, nicegui, streamlit, textual, tui]
documentType: CONVENTIONS
---
# Python Coding Conventions

## General

- **Python version**: 3.12+
- **Type hints**: Mandatory for functions and class methods
- **Style**: Follow [PEP8](https://peps.python.org/pep-0008/) and [PEP257](https://peps.python.org/pep-0257/)
- **Documentation**: Use docstrings for modules, classes, and functions
- **Naming**:
  - `snake_case` for functions/variables/modules
  - `PascalCase` for classes
  - `UPPERCASE` for constants
- **F-strings**: Preferred for string formatting
- **Imports**: Group imports in the following order with a blank line between groups:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports

## Development Workflow & `uv` Usage

This project uses **`uv`** as the all-in-one tool for managing the virtual environment and dependencies. It is the required replacement for `pip`, `venv`, and `requirements.txt`.

### 1. Initial Project Setup

Run these commands only once after cloning the repository.

1.  **Create the Virtual Environment:** `uv` will create a `.venv` directory in the project root.
    ```bash
    uv venv
    ```

2.  **Activate the Environment:**
    ```bash
    source .venv/bin/activate
    ```

3.  **Install All Dependencies:** This installs the project in editable mode (`-e`) along with all development dependencies (`[dev]`) defined in `pyproject.toml`.
    ```bash
    uv pip install -e ".[dev]"
    ```
    *(Note: Do not run `uv init`. The project is already initialized.)*

**Alternatively (Recommended One-Liner):**

After creating the environment with `uv venv`, you can activate and install in a single step:
```bash
source .venv/bin/activate && uv pip install -e ".[dev]"
```

### 2. Common `uv` Commands (Daily Workflow)

Use these commands for day-to-day development.

| Task                                 | Command                               | Description                                                                 |
| ------------------------------------ | ------------------------------------- | --------------------------------------------------------------------------- |
| **Run a quality check or test**      | `uv run pytest`                       | Executes a command using the virtual environment's tools.                   |
|                                      | `uv run black .`                      |                                                                             |
| **Add a new dependency**             | `uv add <package-name>`               | Adds a package and updates `pyproject.toml`.                                |
| **Add a new dev dependency**         | `uv add --dev <package-name>`         | Adds a package to `[project.optional-dependencies.dev]`.                    |
| **Remove a dependency**              | `uv remove <package-name>`            | Removes a package and updates `pyproject.toml`.                             |
| **Sync after pulling changes**       | `uv pip sync pyproject.toml --all-extras` | Updates your environment to exactly match `pyproject.toml`.                 |
| **Create a lockfile (optional)**     | `uv lock`                             | Creates a `uv.lock` file for fully reproducible builds.                     |


## Project Structure

- Organize code in a modular structure with clear separation of concerns.
- Use a package layout with properly defined `__init__.py` files.
- Follow the structure:
  ```
  project_name/
  ├── .venv/            # Virtual environment (managed by uv)
  ├── __init__.py
  ├── cli.py            # Command-line interface
  ├── core/             # Core business logic
  ├── utils/            # Utility functions
  ├── commands/         # Subcommands for CLI applications, each in files ending with _cmd.py
  └── config.py         # Configuration handling
  ```
- Avoid placing all code into a single file; organize into multiple modules.
- Avoid writing code into a `__init__.py` file.

## Testing and Quality

- **Unit tests**: Required for all new functionality.
- **Test framework**: `pytest`.
- **Coverage**: Aim for at least 80% test coverage.
- **Code quality**: Use `black` for formatting, `ruff` or `flake8` for linting, and `mypy` for type checking. These are installed as development dependencies and run with `uv run`.

## Dependencies

- All dependencies are defined in **`pyproject.toml`**. Do not use `requirements.txt`.
- Use `uv add <package>` to manage application dependencies in `[project.dependencies]`.
- Use `uv add --dev <package>` to manage development dependencies in `[project.optional-dependencies.dev]`.
- Keep dependencies minimal and justified. Use the specified libraries where appropriate:
    - **Typer**: CLI interface with type hints (as used in project).
    - **Rich**: Terminal output formatting (as used in project).
    - **Textual**: Modern framework for full TUI applications.
    - **Trogon**: Auto-generate TUIs for Typer CLIs (`typer myapp utils trogon`).
    - **Inquirer**: Interactive CLI prompts (as used in project).
    - **PyYAML**: Configuration file handling (as used in project).
    - **FastAPI**: For web APIs (if needed).
    - **NiceGUI / Streamlit**: For web UI development.
    - **Pydantic**: Data validation (recommended for OpenAI API interactions).
    - **SQLAlchemy**: For database interactions (if needed).
    - **LiteLLM**: For LLM interactions (if needed).

## CLI Development

- Use Typer for all CLI functionality.
- CLI subcommands should be placed in separate files under the `commands/` directory with filenames ending in `_cmd.py` (e.g., `generate_cmd.py`, `list_cmd.py`).
- Implement comprehensive `--help` documentation.
- **Add `-h` as a short option for `--help` for all commands.** This is achieved by passing `context_settings` to the `typer.Typer` constructor. It's best practice to define these settings in a central location (e.g., `config.py`) and import them.
- **Show help by default:** CLI applications should show the help menu when run without arguments by setting `no_args_is_help=True` in the `Typer` constructor.

  ```python
  # In config.py
  CLI_CONTEXT_SETTINGS = {
      "help_option_names": ["-h", "--help"],
  }

  # In cli.py or command modules
  import typer
  from .config import CLI_CONTEXT_SETTINGS

  app = typer.Typer(
      context_settings=CLI_CONTEXT_SETTINGS,
      no_args_is_help=True,
  )
  ```
- Provide meaningful error messages.
- Support configuration via both CLI arguments and config files.
- Follow the pattern established in `cli.py` with the app object.

## UI Development

### NiceGUI Conventions

- **Structure**:
    - Use `ui.run()` only in `main.py` inside `if __name__ in {"__main__", "__mp_main__"}:`.
    - Prefer decorators `@ui.page('/')` for routing over implicit routes.
- **Styling**:
    - Use Tailwind CSS utility classes via the `.classes()` method (e.g., `ui.label('Text').classes('text-lg font-bold')`) rather than raw CSS where possible.
- **State Management**:
    - Use `app.storage` for persistent state and standard Python classes/variables for memory state.
    - Utilizing `.bind_value()` or `.bind_text()` is preferred for reactive UI updates.
- **Async**:
    - NiceGUI is inherently async. Define handlers with `async def` and use `await` for I/O operations (DB calls, API requests) to prevent blocking the UI loop.
- **Dynamic UI**:
    - Use the `@ui.refreshable` decorator for UI sections that need to be dynamically rebuilt based on state changes.

### Streamlit Conventions

- **Execution Model**:
    - Streamlit scripts run from top to bottom on every interaction. Avoid side effects in the main body unless intended to run every time.
- **State Management**:
    - **ALWAYS** use `st.session_state` to persist variables across reruns.
    - Initialize state variables at the top of the script using the pattern:
      ```python
      if 'key' not in st.session_state:
          st.session_state.key = default_value
      ```
- **Caching**:
    - Use `@st.cache_data` for data computations and loading (serializable objects).
    - Use `@st.cache_resource` for global resources (database connections, ML models).
- **Callbacks**:
    - Prefer using `on_change` or `on_click` callbacks in widgets to handle logic *before* the script reruns.
- **Layout**:
    - Use `st.sidebar` for navigation and controls.
    - Use `st.columns` or `st.tabs` for organizing the main content area.

### Textual (TUI) Conventions

- **Framework**: Use **Textual** for complex TUI applications.
- **Structure**:
    - Subclass `App` (from `textual.app`).
    - Use the `compose()` method to yield widgets (Header, Footer, Static, etc.).
- **Styling**:
    - Use **TCSS** (Textual CSS) for styling. Prefer external `.tcss` files for larger apps, or the `CSS` class variable for small components.
    - Stick to standard CSS-like property names provided by Textual.
- **Interactivity**:
    - Use message handlers (e.g., `def on_button_pressed(self, event):`) or the `@on` decorator for event handling.
- **Async**:
    - Textual is async-native. All event handlers and I/O bound methods should be `async def`.
- **Typer Integration**:
    - For existing Typer CLIs, use **Trogon** (`uv add trogon`) to auto-generate a TUI:
      ```python
      from trogon import Trogon
      from typer.main import get_command
      # ... inside your CLI setup
      @app.command()
      def tui(ctx: typer.Context):
          Trogon(get_command(app), click_context=ctx).run()
      ```

## API Interactions

- Isolate API client code into dedicated modules.
- Use environment variables for API keys and configuration (e.g., via `.env` files loaded with `python-dotenv`).
- Implement proper error handling and rate limiting awareness.
- Cache results where appropriate to reduce API calls.

## Configuration

- Use YAML for configuration files.
- Support both global (`~/.config/your_app/config.yml`) and local (`./config.yml`) configuration.
- Implement fallbacks for missing configuration values.

## Example `pyproject.toml`

A modern `pyproject.toml` reflecting these conventions.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "git-summarize"
version = "0.1.0"
description = "A tool to summarize git commits using AI"
requires-python = ">=3.12"
license = "MIT"
authors = [
    { name = "Your Name", email = "you@example.com" },
]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.7.0",
    "inquirerpy>=0.3.4",
    "textual>=0.50.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
git-summarize = "git_summarize.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "mypy>=1.8.0",
    "ruff>=0.3.0", # Can replace black, flake8, and more
]

[tool.ruff]
# Example Ruff config to replace flake8 and isort
line-length = 88
select = ["E", "F", "W", "I"] # Standard flake8 and isort checks

[tool.mypy]
strict = true

[tool.black]
line-length = 88
```







## Report Structure
The last phase of the plan should be to write a report to `_ai/backlog/reports/{YYMMDD_HHmm}__IMPLEMENTATION_REPORT__{name-of-the-plan}.md`

Include YAML frontmatter with the following fields:
```yaml
---
filename: "_ai/backlog/reports/{YYMMDD_HHmm}__IMPLEMENTATION_REPORT__{name-of-the-plan}.md"
title: "Report: {plan title}"
createdAt: YYYY-MM-DD HH:mm
updatedAt: YYYY-MM-DD HH:mm
planFile: "_ai/backlog/active/{YYMMDD_HHmm}__IMPLEMENTATION_PLAN__{name-of-the-plan}.md"
project: "{project-name}"
status: completed|partial|blocked
filesCreated: 0
filesModified: 0
filesDeleted: 0
tags: [tag1, tag2, tag3]
documentType: IMPLEMENTATION_REPORT
---
```

The report content should include:
1. **Summary**: Brief overview of what was accomplished (2-3 sentences)
2. **Files Changed**:
    - List of new files created with brief descriptions
    - List of modified files with summary of changes
    - List of deleted files (if any)
3. **Key Changes**: Bullet points of the main technical changes made
4. **Deviations from Plan**: What broke, what performance issues were hit, and why a different approach was taken
5. **Technical Decisions**: Important design decisions or trade-offs made during implementation
6. **Testing Notes**: How the changes can be verified or tested
7. **Usage Examples** (if applicable): Provide specific CLI commands, arguments, and example outputs if the implementation involved command-line interfaces
8. **Documentation Updates**: Summary of any documentation changes made
9. **Next Steps** (optional): Any follow-up work or improvements that could be made
</instruction>

