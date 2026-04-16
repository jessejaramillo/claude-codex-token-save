"""
token-savior → graphify bridge
Converts a token-savior project index into graphify-compatible graph.json,
then optionally runs graphify clustering + HTML viz on it.

Usage:
    python token_savior_to_graphify.py <project_root> [--viz] [--obsidian]

Outputs:
    <project_root>/graphify-out/graph.json   (graphify-compatible)
    <project_root>/graphify-out/graph.html   (if --viz)
    <project_root>/graphify-out/obsidian/    (if --obsidian)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from token_savior.project_indexer import ProjectIndexer
from token_savior.community import compute_communities
from token_savior.entry_points import score_entry_points


def build_graphify_json(idx, root_name: str) -> dict:
    """Convert token-savior ProjectIndex → graphify node-link format."""
    communities = compute_communities(idx)
    entry_pts = {e["name"] for e in score_entry_points(idx, max_results=50)}

    symbol_table = idx.symbol_table          # {symbol_name: file_path}
    dep_graph = idx.global_dependency_graph  # {symbol_name: set(deps)}

    # Build nodes — one per symbol
    nodes = []
    for sym_name, file_path in symbol_table.items():
        nodes.append({
            "id": sym_name,
            "label": sym_name.split(".")[-1],   # short name for display
            "file_type": "code",
            "source_file": str(file_path),
            "source_location": None,
            "community": communities.get(sym_name, "0"),
            "is_entry_point": sym_name in entry_pts,
        })

    known = set(symbol_table.keys())

    # Build edges from dependency graph
    links = []
    for source, deps in dep_graph.items():
        if source not in known:
            continue
        for target in deps:
            if target not in known:
                continue
            links.append({
                "source": source,
                "target": target,
                "relation": "calls",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "weight": 1.0,
            })

    return {"directed": True, "multigraph": False, "nodes": nodes, "links": links}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--viz", action="store_true", help="Generate graph.html via graphify")
    parser.add_argument("--obsidian", action="store_true", help="Also export Obsidian vault")
    args = parser.parse_args()

    root = Path(args.project_root)
    out_dir = root / "graphify-out"
    out_dir.mkdir(exist_ok=True)

    print(f"Indexing {root} with token-savior...")
    indexer = ProjectIndexer(str(root))
    idx = indexer.index()
    print(f"  {len(idx.symbol_table)} symbols, {idx.total_files} files")

    graph = build_graphify_json(idx, root.name)
    out_path = out_dir / "graph.json"
    out_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"graph.json -> {out_path}  ({len(graph['nodes'])} nodes, {len(graph['links'])} edges)")

    if args.viz:
        print("Running graphify HTML viz...")
        subprocess.run([sys.executable, "-c", f"""
import json
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_html
from pathlib import Path
G = build_from_json(json.loads(Path(r'{out_path}').read_text()))
communities = cluster(G)
to_html(G, communities, r'{out_dir / "graph.html"}')
print('graph.html written')
"""], check=False)

    if args.obsidian:
        obsidian_script = Path(__file__).parent / "token_savior_to_obsidian.py"
        subprocess.run([sys.executable, str(obsidian_script), str(root)], check=False)

    print(f"\nDone. Outputs in {out_dir}/")


if __name__ == "__main__":
    main()
