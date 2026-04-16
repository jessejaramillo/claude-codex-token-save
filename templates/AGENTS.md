# AGENTS.md

## Output
Structured only (JSON, bullets, tables). No prose unless human reader present.
Execute without narration or status updates. No confirmation requests.
No decorative Unicode. JSON-safe strings. Cap parallel subagents at 3.
Never invent paths, endpoints, or field names — use null or UNKNOWN.

## Tool Priority Chain (token-savior)
1. find_symbol / get_function_source / get_dependents FIRST
2. smart_search / smart_outline before full file reads
3. Only read files when symbol tools return insufficient context
4. Never glob entire directories; use list_files with patterns

## Compact Serialization
Prefer compact key=value or TOON over full JSON objects in inter-agent payloads.
Pass minimal identifiers (file path + symbol name) between steps — not full source.

## Selective Loading
Load only files strictly necessary for the current task.
Use token-savior lookups before any file read. Never preload directories.

## Context Management
Compact every ~40 messages. AGENTS.md is the only persistent context — do not repeat it in-session.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
