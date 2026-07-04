"""Obsidian vault summarizer skill definition."""

from otto_agent.agents.skill import AgentSkill, FinalDetailField

OBSIDIAN_VAULT_SUMMARIZER_SKILL = AgentSkill(
    name="obsidian_vault_summarizer",
    goal="Summarize the knowledge contained in a local collection of notes.",
    instructions=(
        "Use the available tools to list the files in the vault and read the "
        "notes that are relevant to the summary. "
        "Internal note references may use the Wikilink format, such as "
        "[[Name]] or [[Name.md]], to refer to another note. "
        "Use these references only to understand relationships between the "
        "ideas in the notes. "
        "Do not include Obsidian, Markdown, Wikilinks, file formats, note "
        "mechanics, or the existence of links in the final knowledge summary "
        "unless those are themselves the subject matter of the notes. "
        "Do not invent notes, relationships, facts, or conclusions that are "
        "not supported by the file contents. "
        "If a tool result says a note or file was blocked, inaccessible, "
        "hidden, filtered, unreadable, or unavailable, treat it as outside "
        "the accessible knowledge. Do not mention that note, file, or access "
        "restriction in the final summary, topics, or relationships. "
        "Prefer reading all available files when the vault is small. "
        "When finished, provide a concise subject-matter summary of what the "
        "notes say, including the main topics and how the concepts relate to "
        "each other."
    ),
    fact_types={
        "vault_file_list": "The list of files discovered in the Obsidian vault.",
        "note_content": "The content read from one note.",
        "note_reference": "A relationship found through a reference between notes.",
        "knowledge_topic": "A topic or concept supported by the vault notes.",
    },
    output_types={
        "knowledge_summary": (
            "A concise subject-matter summary of the knowledge in the vault."
        ),
        "concept_relationships": (
            "A structured description of how concepts in the notes relate."
        ),
    },
    final_detail_fields={
        "summary": FinalDetailField(
            description=(
                "The final concise subject-matter summary of the vault's "
                "knowledge. Do not mention Obsidian, Markdown, Wikilinks, "
                "files, links, blocked files, inaccessible files, hidden "
                "files, filtered files, unreadable files, or unavailable "
                "files unless they are the subject matter."
            ),
        ),
        "main_topics": FinalDetailField(
            description=(
                "The main subject-matter topics or concepts found in the "
                "vault, written as a brief comma-separated list. Include only "
                "topics supported by accessible note content."
            ),
        ),
        "note_relationships": FinalDetailField(
            description=(
                "A brief explanation of the important subject-matter "
                "relationships between concepts. Do not describe note-linking "
                "mechanics, blocked notes, inaccessible notes, hidden notes, "
                "filtered notes, unreadable notes, or unavailable notes."
            ),
        ),
        "files_read": FinalDetailField(
            description=(
                "The vault files that were read to create the summary, written "
                "as a brief comma-separated list."
            ),
        ),
        "reason_code": FinalDetailField(
            description="The structured reason for the final result.",
            allowed_values={
                "summary_created": "A vault knowledge summary was created.",
                "missing_vault_files": "No vault files could be discovered.",
                "missing_note_content": (
                    "The agent could not read enough note content to summarize "
                    "the vault."
                ),
            },
        ),
    },
)
