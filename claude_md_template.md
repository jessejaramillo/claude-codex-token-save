## Token-Saving Stack (always check these before reading files)

Priority order — use the cheapest source that answers the question:

| Question type | Tool | Cost | Command |
|---------------|------|------|---------|
| Where is X defined? | token-savior MCP | ~50 tok | `list_symbols` MCP tool |
| What does X do? | LightRAG | ~500 tok | `python ~/scripts/rag_pipeline.py . --query "..."` |
| What calls X? | graphify | ~200 tok | `/graphify query "..."` |
| Architecture overview | graphify-out/GRAPH_REPORT.md | ~300 tok | Read the report |
| Full context on X | Obsidian vault | ~800 tok | Read graphify-out/obsidian/entities/X.md |
| Raw file (last resort) | Read tool | ~5-50k tok | Only if above tools insufficient |

### LightRAG query modes
- `--query "question"` — hybrid mode (KG + vector), best for most questions
- `--query "question" --mode global` — whole-graph reasoning
- `--query "question" --mode local` — entity-focused, most token-efficient

### Rebuild after major code changes
    python ~/scripts/rag_pipeline.py . --rebuild
