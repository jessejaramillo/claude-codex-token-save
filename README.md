# Claude/Codex Token Save

An 85–92% token reduction stack for Claude Code and OpenAI Codex CLI. Instead of reading raw source files into context, Claude queries pre-built knowledge graphs, structural indexes, and Obsidian notes — getting the same answer at a fraction of the cost.

## How It Works

Four tools work together in a priority chain:

```
Raw files (~50k tokens)
    ↓ replace with
token-savior  →  "Where is X?"        ~50 tokens   (structural, free)
LightRAG      →  "What does X do?"   ~500 tokens   (semantic KG, built once)
graphify      →  "What calls X?"     ~200 tokens   (visual graph, git-maintained)
Obsidian      →  "Details on X"      ~800 tokens   (pre-built notes)
```

Estimated savings per session: **85–92%** vs reading files directly.

## Requirements

- Python 3.10+
- Claude Code CLI (`claude`) installed
- `graphify` CLI available (`pip install graphifyy`)
- An [OpenRouter](https://openrouter.ai) API key (for LightRAG entity extraction — one-time per project, uses cheap open-source models)

## Installation

### Windows

```powershell
git clone https://github.com/jessejaramillo/claude-codex-token-save
cd claude-codex-token-save

.\install.ps1 `
  -Projects "C:\path\to\proj1,C:\path\to\proj2" `
  -OpenRouterKey "sk-or-your-key-here"
```

### macOS / Linux

```bash
git clone https://github.com/jessejaramillo/claude-codex-token-save
cd claude-codex-token-save

chmod +x install.sh
./install.sh \
  --projects "/path/to/proj1,/path/to/proj2" \
  --openrouter-key "sk-or-your-key-here"
```

## What the Installer Does

1. Installs Python packages: `lightrag-hku`, `sentence-transformers`, `token-savior`, `graphifyy`
2. Copies bridge scripts to `~/scripts/`
3. Stores your OpenRouter API key
4. Runs `graphify claude install` on each project (writes token-saving section to `CLAUDE.md`)
5. Installs `graphify` post-commit git hook (auto-rebuilds graph after every commit)
6. Registers `token-savior` as a global Claude Code MCP server pointing to all your projects

## First-Time Setup Per Project

Build the LightRAG knowledge graph once per project (uses OpenRouter, ~$0.01–0.05 per project):

```bash
python ~/scripts/rag_pipeline.py /path/to/project
```

This creates:
- `graphify-out/lightrag/` — semantic knowledge graph
- `graphify-out/obsidian/lightrag/` — 500–2000 Obsidian entity notes
- Updates `CLAUDE.md` with the token-saving lookup table

## Usage

### Query the KG instead of reading files

```bash
# Hybrid (recommended)
python ~/scripts/rag_pipeline.py /path/to/project --query "how does authentication work?"

# Entity-focused (cheapest)
python ~/scripts/rag_pipeline.py /path/to/project --query "what is UserService?" --mode local

# Whole-graph reasoning
python ~/scripts/rag_pipeline.py /path/to/project --query "what are the main architectural patterns?" --mode global
```

### Other bridge scripts

```bash
# token-savior index → graphify graph.json + HTML viz
python ~/scripts/token_savior_to_graphify.py /path/to/project --viz --obsidian

# token-savior index → Obsidian vault (symbol notes)
python ~/scripts/token_savior_to_obsidian.py /path/to/project
```

### Rebuild after major changes

```bash
python ~/scripts/rag_pipeline.py /path/to/project --rebuild
```

## Token Savings Reference

| Question | Tool used | Tokens | vs. reading files |
|----------|-----------|--------|-------------------|
| "Where is X defined?" | token-savior MCP | ~50 | saves ~2,000 |
| "What does X do?" | LightRAG | ~500 | saves ~15,000 |
| "What calls X?" | graphify | ~200 | saves ~5,000 |
| "Architecture overview" | GRAPH_REPORT.md | ~300 | saves ~30,000 |
| "Details on X" | Obsidian entity note | ~800 | saves ~8,000 |

## What Gets Created Per Project

```
project/
├── CLAUDE.md                          ← token-saving priority table added
├── graphify-out/
│   ├── graph.json                     ← graphify knowledge graph
│   ├── graph.html                     ← interactive browser viz
│   ├── GRAPH_REPORT.md               ← architecture report
│   ├── lightrag/                      ← LightRAG semantic KG
│   │   ├── graph_chunk_entity_relation.graphml
│   │   ├── kv_store_full_entities.json
│   │   └── ...
│   └── obsidian/
│       ├── lightrag/                  ← LightRAG entity notes
│       │   ├── entities/
│       │   └── INDEX.md
│       └── symbols/                   ← token-savior symbol notes
└── .git/hooks/post-commit             ← auto-rebuild graphify on commit
```

## Configuration

Edit `~/scripts/rag_pipeline.py` to change:
- `LLM_MODEL` — default `meta-llama/llama-3.1-8b-instruct` (cheapest). Use any OpenRouter model.
- `MAX_FILES` — max files per project for LightRAG ingestion (default 300)
- `MAX_FILE_BYTES` — skip files larger than this (default 80KB)

## Credits

Built on top of:
- [graphify](https://github.com/safishamsi/graphify) — knowledge graph for any codebase
- [token-savior](https://pypi.org/project/token-savior/) — structural code indexer with MCP
- [LightRAG](https://github.com/hkuds/lightrag) — fast graph-based RAG
- [sentence-transformers](https://www.sbert.net/) — free local embeddings

## Works Great With

### [rtk](https://github.com/rtk-ai/rtk) — Command Output Filter (Rust)
RTK compresses noisy CLI output (git, cargo, docker, pytest) by 60-90% before it hits Claude's context. Pair it with this stack for maximum savings:

| Layer | Tool | What it saves |
|-------|------|--------------|
| Command output | **rtk** | Filters verbose CLI noise |
| Symbol lookups | **token-savior** | Skips file reads for definitions |
| Semantic queries | **LightRAG** | Replaces reading whole files |
| Architecture | **graphify** | Pre-built graph vs. exploring code |
| Notes | **Obsidian vault** | Pre-built answers vs. re-reading |

Install rtk (Linux/macOS): `curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh`

### [jCodeMunch](https://j.gravelle.us/jCodeMunch) — Symbol-Level MCP (99.8% on FastAPI)
jCodeMunch is an MCP server for surgical symbol retrieval. Benchmarked 99.8% reduction on
FastAPI (214,312 → 480 tokens per query). Complements token-savior.

```bash
pip install git+https://github.com/jgravelle/jcodemunch-mcp.git
```

See `docs/rtk-install.md` for Claude Code + Codex registration steps.

### [claude-token-efficient](https://github.com/drona23/claude-token-efficient) — Output Verbosity Profiles
Drop-in CLAUDE.md profiles that reduce output verbosity. Layers with this stack:
- This repo reduces *input* tokens (avoid reading full files)
- claude-token-efficient reduces *output* tokens (response length)

```bash
git clone https://github.com/drona23/claude-token-efficient /tmp/claude-token-efficient
cat /tmp/claude-token-efficient/profiles/CLAUDE.coding.md >> your-project/CLAUDE.md
```

See `docs/claude-token-efficient.md` for full integration guide.

## Additional Techniques

### AGENTS.md Template
For Codex CLI and other agent tools, use the provided AGENTS.md template (`templates/AGENTS.md`)
in place of or alongside CLAUDE.md. It includes:
- Structured-output-only mode (no prose in agent responses)
- token-savior tool priority chain (find_symbol first, file reads last)
- Compact Serialization rules

### Compact Serialization (TOON)
Use Token-Oriented Object Notation in agent pipelines instead of JSON:
```
# JSON (verbose)
{"file": "src/auth.ts", "symbol": "verifyToken", "line": 42}

# TOON (compact)
file=src/auth.ts sym=verifyToken line=42
```
Add `templates/CLAUDE.md.append` to any project CLAUDE.md for these rules.

### Context Management
- Compact session history every ~40 messages via `/compact`
- CLAUDE.md is the only persistent context — don't repeat it in-session
- After compaction, re-read only active files

### Selective Loading
- Use token-savior `find_symbol` / `get_function_source` before any file read
- Never preload entire directories; use `list_files` with patterns
