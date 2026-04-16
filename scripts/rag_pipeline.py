"""
Unified token-saving pipeline: token-savior + LightRAG + graphify + Obsidian

Architecture (reads cheapest-first):
  token-savior  → structural index  (free, AST-based)
  LightRAG      → semantic KG       (built once with Haiku, queried cheaply after)
  graphify      → visual graph      (community map, git-hook maintained)
  Obsidian      → pre-built notes   (Claude reads notes, not raw files)

Token savings vs. reading raw files:
  "What does X do?"        LightRAG query  ~500 tok  vs. 3 files ~15,000 tok
  "What calls X?"          graphify query  ~200 tok  vs. grep    ~5,000 tok
  "Where is X defined?"    token-savior    ~50 tok   vs. search  ~2,000 tok

Usage:
    python rag_pipeline.py <project_root> [--query "your question"] [--rebuild]

    First run builds the KG (takes a few minutes, uses Haiku).
    Subsequent runs are instant — just query the cached KG.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

# ── env ──────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path("C:/Users/JesseJaramillo/ClaudeBot/.env"), override=True)
load_dotenv(Path("C:/Users/JesseJaramillo/Claude-NetSuite/.env"), override=True)

# Get OpenRouter key from registry (stored there, not in .env)
import winreg as _wr
try:
    _rk = _wr.OpenKey(_wr.HKEY_CURRENT_USER, "Environment")
    OPENROUTER_API_KEY, _ = _wr.QueryValueEx(_rk, "OPENROUTER_API_KEY")
except Exception:
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
# Cheapest capable model for entity extraction
LLM_MODEL = "meta-llama/llama-3.1-8b-instruct"

# ── LightRAG imports ──────────────────────────────────────────────────────────
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache

# ── Embedding: local sentence-transformers (free, no API cost) ────────────────
import numpy as np

_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model

async def local_embedding(texts: list[str]) -> np.ndarray:
    model = get_embed_model()
    return model.encode(texts, normalize_embeddings=True)  # returns np.ndarray

# ── LLM: cheap OpenRouter model (entity extraction, built once) ───────────────
async def openrouter_llm(prompt, system_prompt=None, history_messages=[], **kwargs):
    kwargs.pop("hashing_kv", None)
    kwargs.pop("keyword_extraction", None)
    return await openai_complete_if_cache(
        LLM_MODEL,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE,
        **kwargs,
    )

# ── File collection ───────────────────────────────────────────────────────────
CODE_EXTS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".md", ".txt",
             ".yaml", ".yml", ".json", ".toml", ".html", ".css"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv",
             "graphify-out", ".pydeps", "dist", "build", ".pytest_cache"}
MAX_FILE_BYTES = 80_000   # skip huge files
MAX_FILES = 300           # cap to control LLM cost on first build

def collect_texts(root: Path) -> list[tuple[str, str]]:
    """Return list of (rel_path, content) for all readable files."""
    results = []
    for f in root.rglob("*"):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if f.suffix.lower() not in CODE_EXTS:
            continue
        if not f.is_file() or f.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
        if len(text) < 30:
            continue
        results.append((str(f.relative_to(root)), text))
        if len(results) >= MAX_FILES:
            break
    return results

# ── LightRAG setup ────────────────────────────────────────────────────────────
def make_rag(working_dir: str) -> LightRAG:
    os.makedirs(working_dir, exist_ok=True)
    return LightRAG(
        working_dir=working_dir,
        llm_model_func=openrouter_llm,
        llm_model_name=LLM_MODEL,
        embedding_func=EmbeddingFunc(
            embedding_dim=384,          # all-MiniLM-L6-v2 output dim
            max_token_size=512,
            func=local_embedding,
        ),
        embedding_batch_num=16,
        max_extract_input_tokens=4096,
        chunk_token_size=800,
        chunk_overlap_token_size=100,
        enable_llm_cache=True,                 # never pay twice for same chunk
        enable_llm_cache_for_entity_extract=True,
    )

# ── Obsidian export ───────────────────────────────────────────────────────────
def export_to_obsidian(rag_dir: Path, obsidian_dir: Path):
    """Export LightRAG entities + relations to Obsidian markdown notes."""
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    (obsidian_dir / "entities").mkdir(exist_ok=True)
    (obsidian_dir / "relations").mkdir(exist_ok=True)

    # LightRAG stores KG in graph_chunk_entity_relation.graphml or JSON
    entity_file   = rag_dir / "kv_store_full_entities.json"
    relation_file = rag_dir / "kv_store_full_relations.json"
    graph_file    = rag_dir / "graph_chunk_entity_relation.graphml"

    # Collect entity names and relation pairs from KV stores
    all_entity_names: set[str] = set()
    entity_outgoing: dict[str, set[str]] = {}
    entity_incoming: dict[str, set[str]] = {}
    entities_written = 0

    if entity_file.exists():
        edata = json.loads(entity_file.read_text(encoding="utf-8"))
        for doc_val in edata.values():
            for name in doc_val.get("entity_names", []):
                all_entity_names.add(name)

    if relation_file.exists():
        rdata = json.loads(relation_file.read_text(encoding="utf-8"))
        for doc_val in rdata.values():
            for pair in doc_val.get("relation_pairs", []):
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    src, tgt = str(pair[0]), str(pair[1])
                    entity_outgoing.setdefault(src, set()).add(tgt)
                    entity_incoming.setdefault(tgt, set()).add(src)

    # Write one Obsidian note per entity
    for ename in all_entity_names:
        safe = re.sub(r'[\\/*?:"<>|]', "_", ename[:80])
        out_links = sorted(entity_outgoing.get(ename, set()))
        in_links  = sorted(entity_incoming.get(ename, set()))
        lines = [f"# {ename}", ""]
        if out_links:
            lines += ["## Related To", ""] + [f"- [[entities/{re.sub(r'[\\\\/*?:\"<>|]', '_', t[:80])}|{t}]]" for t in out_links[:30]] + [""]
        if in_links:
            lines += ["## Referenced By", ""] + [f"- [[entities/{re.sub(r'[\\\\/*?:\"<>|]', '_', t[:80])}|{t}]]" for t in in_links[:30]] + [""]
        (obsidian_dir / "entities" / f"{safe}.md").write_text("\n".join(lines), encoding="utf-8")
        entities_written += 1

    # Parse graphml for entity nodes
    nodes_written = 0
    if graph_file.exists():
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(graph_file)
            ns = {"g": "http://graphml.graphdrawing.org/graphml"}
            nodes = {}
            edges = []
            for node in tree.findall(".//g:node", ns):
                nid = node.get("id", "")
                data = {d.get("key", ""): d.text for d in node.findall("g:data", ns)}
                nodes[nid] = data
            for edge in tree.findall(".//g:edge", ns):
                src = edge.get("source", "")
                tgt = edge.get("target", "")
                data = {d.get("key", ""): d.text for d in edge.findall("g:data", ns)}
                edges.append((src, tgt, data))

            for nid, data in list(nodes.items())[:2000]:
                safe = re.sub(r'[\\/*?:"<>|]', "_", nid[:80])
                desc = data.get("d1", data.get("description", ""))
                etype = data.get("d0", data.get("entity_type", "UNKNOWN"))
                note_lines = [f"# {nid}", "", f"- **Type:** {etype}",
                              f"- **Description:** {desc}", "", "## Relations", ""]
                for src, tgt, ed in edges:
                    if src == nid or tgt == nid:
                        rel = ed.get("d2", ed.get("relation", "related"))
                        other = tgt if src == nid else src
                        arrow = "-->" if src == nid else "<--"
                        safe_other = re.sub(r'[\\/*?:"<>|]', "_", other[:80])
                        note_lines.append(f"- {arrow} [[{safe_other}]] `{rel}`")
                (obsidian_dir / "entities" / f"{safe}.md").write_text(
                    "\n".join(note_lines), encoding="utf-8")
                nodes_written += 1

            # Write relations index
            rel_lines = ["# Relations Index", ""]
            for src, tgt, data in edges[:500]:
                rel = data.get("d2", data.get("relation", "related"))
                s = re.sub(r'[\\/*?:"<>|]', "_", src[:60])
                t = re.sub(r'[\\/*?:"<>|]', "_", tgt[:60])
                rel_lines.append(f"- [[entities/{s}]] --{rel}--> [[entities/{t}]]")
            (obsidian_dir / "relations" / "INDEX.md").write_text(
                "\n".join(rel_lines), encoding="utf-8")
        except Exception as e:
            print(f"  graphml parse warning: {e}")

    # INDEX.md
    idx = [f"# LightRAG Knowledge Base", "",
           f"- **Chunk notes:** {entities_written}",
           f"- **Entity notes:** {nodes_written}",
           "", "## Query this vault (token-efficient)",
           "", "Instead of reading source files, ask LightRAG:",
           "```", "python ~/scripts/rag_pipeline.py <project> --query 'your question'", "```",
           "", "## Browse", "",
           "- [[entities/]] — entity notes (one per concept)",
           "- [[relations/INDEX]] — all extracted relations",
           ]
    (obsidian_dir / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")
    print(f"  Obsidian: {nodes_written} entity notes, {entities_written} chunk notes -> {obsidian_dir}")

# ── CLAUDE.md integration section ────────────────────────────────────────────
CLAUDE_SECTION = """
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
"""

def update_claude_md(project_root: Path):
    claude_md = project_root / "CLAUDE.md"
    marker = "## Token-Saving Stack"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if marker in content:
            return  # already present
        content += "\n" + CLAUDE_SECTION
    else:
        content = CLAUDE_SECTION
    claude_md.write_text(content, encoding="utf-8")
    print(f"  CLAUDE.md updated with token-saving instructions")

# ── Main ──────────────────────────────────────────────────────────────────────
async def build(project_root: Path, rebuild: bool = False):
    rag_dir = project_root / "graphify-out" / "lightrag"
    if rebuild and rag_dir.exists():
        import shutil
        shutil.rmtree(rag_dir)
        print(f"Cleared existing KG at {rag_dir}")
    print(f"Collecting files from {project_root} ...")
    texts = collect_texts(project_root)
    print(f"  {len(texts)} files collected")

    rag = make_rag(str(rag_dir))
    await rag.initialize_storages()
    print(f"Inserting into LightRAG (Haiku + local embeddings) ...")
    docs = [f"# File: {path}\n\n{content}" for path, content in texts]
    await rag.ainsert(docs)
    print(f"  Running entity extraction pipeline ...")
    await rag.apipeline_process_enqueue_documents()
    await rag.finalize_storages()
    print(f"  KG built -> {rag_dir}")

    obsidian_dir = project_root / "graphify-out" / "obsidian" / "lightrag"
    print(f"Exporting to Obsidian ...")
    export_to_obsidian(rag_dir, obsidian_dir)

    update_claude_md(project_root)
    print(f"Done. Run queries with: python rag_pipeline.py {project_root} --query '...'")


async def query(project_root: Path, question: str, mode: str = "hybrid"):
    rag_dir = project_root / "graphify-out" / "lightrag"
    if not rag_dir.exists():
        print("No KG found. Run without --query first to build it.")
        sys.exit(1)
    rag = make_rag(str(rag_dir))
    await rag.initialize_storages()
    result = await rag.aquery(question, param=QueryParam(mode=mode))
    print(f"\n[LightRAG/{mode}] {question}\n")
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--query", "-q", default=None, help="Question to ask the KG")
    parser.add_argument("--mode", default="hybrid",
                        choices=["hybrid", "global", "local", "naive"])
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild KG")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    rag_dir = root / "graphify-out" / "lightrag"

    if args.query:
        asyncio.run(query(root, args.query, args.mode))
    elif args.rebuild or not rag_dir.exists():
        asyncio.run(build(root, rebuild=args.rebuild))
    else:
        print(f"KG already built at {rag_dir}. Use --query to ask questions or --rebuild to refresh.")
