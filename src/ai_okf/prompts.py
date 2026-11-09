from ai_okf.models.plan import OKFConceptPlan

NOTES_PROFILE = "notes"


def build_plan_prompt(profile: str, files_summary: str) -> str:
    if profile == NOTES_PROFILE:
        return (
            "We are building a personal knowledge wiki in OKF format from the "
            "notes below.\n"
            f"Here are the note files:\n{files_summary}\n\n"
            "Create at most 8 concept pages that group related notes (not one "
            "page per note). Use lowercase kebab-case concept IDs "
            "(e.g. t2-migration, kompamanager). Only reference files from the "
            "list above. Prefer projects, decisions and their rationale, people "
            "and organisations, recurring themes, open questions, and reference "
            "material. Provide a structured plan containing the list of concept "
            "files to create."
        )
    return (
        "We are generating a codebase documentation wiki matching the OKF "
        "specification.\n"
        f"Here is the codebase file list:\n{files_summary}\n\n"
        "Please identify key modules, classes, data models, entrypoints, "
        "configuration, or structural patterns. Provide a structured plan "
        "containing the list of concept files to create."
    )


def build_concept_prompt(
    profile: str,
    plan: OKFConceptPlan,
    sources: str | None = None,
) -> str:
    files = ", ".join(plan.files_to_read)
    if profile == NOTES_PROFILE:
        source_block = sources.strip() if sources else "(no note content available)"
        return (
            f"Write ONE OKF knowledge file of type '{plan.type}' for:\n"
            f"ID: {plan.concept_id}\nTitle: {plan.title}\n"
            f"Description: {plan.description}\n\n"
            "The complete text of the relevant notes is included below. "
            "Synthesize only from this text.\n\n"
            f"--- BEGIN NOTES ---\n{source_block}\n--- END NOTES ---\n\n"
            "Rules:\n"
            "- Use only facts present in the notes. If a fact is unknown, "
            'write "unknown".\n'
            "- Do not invent names, dates, numbers, events, or decisions.\n"
            "- Never mention tools, access, prompts, or that you are an AI.\n"
            "- Start the output with YAML frontmatter delimited by --- lines, "
            f"including type: {plan.type} and a title.\n"
            "- Then a markdown body with structural headings.\n"
            "- Return only the document: no commentary, no code fences.\n"
        )
    return (
        f"Generate a comprehensive OKF knowledge file of type '{plan.type}' "
        f"for the concept:\nID: {plan.concept_id}\nTitle: {plan.title}\n"
        f"Description: {plan.description}\n\n"
        "Inspect and extract structural knowledge from the following files: "
        f"{files}\n"
        "Use read_file_content tool as needed to construct rich, precise, and "
        "verified documentation."
    )


def build_update_prompt(profile: str, changes: str, output: str) -> str:
    if profile == NOTES_PROFILE:
        return (
            "The notes have changed since the last wiki generation.\n"
            f"Here are the modifications:\n{changes}\n\n"
            "Read the changed notes using read_file_content and identify which "
            f"existing OKF pages in '{output}' must be updated, or which new "
            "pages to author. Preserve decisions and flag anything that now "
            "contradicts an existing page.\nReturn a summary of actions taken."
        )
    return (
        "The codebase has evolved since the last documentation generation.\n"
        f"Here are the modifications:\n{changes}\n\n"
        "Inspect the changed files using read_file_content and identify which "
        f"existing OKF files in '{output}' must be rewritten to match the new "
        "codebase structure, or if new concepts must be authored.\n"
        "Return a summary of actions taken."
    )
