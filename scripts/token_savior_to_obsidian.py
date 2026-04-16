"""
token-savior → Obsidian bridge
Exports a token-savior project index as Markdown notes into an Obsidian vault.

Usage:
    python token_savior_to_obsidian.py <project_root> [--vault <vault_dir>]

Defaults:
    vault = <project_root>/graphify-out/obsidian
"""

import argparse
from pathlib import Path

from token_savior.project_indexer import ProjectIndexer
from token_savior.community import compute_communities
from token_savior.entry_points import score_entry_points


def safe_filename(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_")


def symbol_note(sym_name: str, file_path: str, community: str,
                outgoing: list, incoming: list, is_entry: bool) -> str:
    short = sym_name.split(".")[-1]
    tags = ["entry-point"] if is_entry else []
    lines = []
    if tags:
        lines += [f"---", f"tags: [{', '.join(tags)}]", f"---", ""]
    lines += [f"# {short}", ""]
    lines += [
        f"- **Full name:** `{sym_name}`",
        f"- **File:** `{file_path}`",
        f"- **Community:** [[communities/{safe_filename(community)}|{community.split('.')[-1]}]]",
        "",
    ]
    if outgoing:
        lines.append("## Calls / Uses")
        for dep in sorted(outgoing)[:30]:
            lines.append(f"- [[{safe_filename(dep)}]]")
        if len(outgoing) > 30:
            lines.append(f"- _(+{len(outgoing)-30} more)_")
        lines.append("")
    if incoming:
        lines.append("## Called By")
        for dep in sorted(incoming)[:30]:
            lines.append(f"- [[{safe_filename(dep)}]]")
        if len(incoming) > 30:
            lines.append(f"- _(+{len(incoming)-30} more)_")
        lines.append("")
    return "\n".join(lines)


def community_note(comm_id: str, members: list) -> str:
    short = comm_id.split(".")[-1]
    lines = [f"# Community: {short}", "", f"**ID:** `{comm_id}`",
             f"**Members:** {len(members)}", "", "## Symbols", ""]
    for m in sorted(members)[:100]:
        lines.append(f"- [[{safe_filename(m)}|{m.split('.')[-1]}]]")
    if len(members) > 100:
        lines.append(f"- _(+{len(members)-100} more)_")
    return "\n".join(lines)


def export(project_root: str, vault_dir: str):
    root = Path(project_root)
    vault = Path(vault_dir)
    (vault / "symbols").mkdir(parents=True, exist_ok=True)
    (vault / "communities").mkdir(parents=True, exist_ok=True)

    print(f"Indexing {root} ...")
    indexer = ProjectIndexer(str(root))
    idx = indexer.index()
    print(f"  {len(idx.symbol_table)} symbols, {idx.total_files} files")

    communities = compute_communities(idx)
    entry_pts = {e["name"] for e in score_entry_points(idx, max_results=50)}
    dep_graph = idx.global_dependency_graph        # sym -> set(deps)

    # Build incoming map
    incoming: dict[str, list] = {}
    for src, deps in dep_graph.items():
        for tgt in deps:
            incoming.setdefault(tgt, []).append(src)

    # Community member lists
    community_members: dict[str, list] = {}
    for sym, comm in communities.items():
        community_members.setdefault(comm, []).append(sym)

    # Write symbol notes
    written = 0
    for sym_name, file_path in idx.symbol_table.items():
        comm = communities.get(sym_name, "unknown")
        outgoing = list(dep_graph.get(sym_name, set()))
        note = symbol_note(sym_name, str(file_path), comm, outgoing,
                           incoming.get(sym_name, []), sym_name in entry_pts)
        (vault / "symbols" / f"{safe_filename(sym_name)}.md").write_text(note, encoding="utf-8")
        written += 1

    # Write community notes
    for comm_id, members in community_members.items():
        note = community_note(comm_id, members)
        (vault / "communities" / f"{safe_filename(comm_id)}.md").write_text(note, encoding="utf-8")

    # Write INDEX.md
    index_lines = [
        f"# {root.name} — Token Savior Index", "",
        f"- **Symbols:** {len(idx.symbol_table)}",
        f"- **Files:** {idx.total_files}",
        f"- **Functions:** {idx.total_functions}",
        f"- **Classes:** {idx.total_classes}",
        f"- **Communities:** {len(community_members)}",
        f"- **Entry Points:** {len(entry_pts)}",
        "", "## Communities", "",
    ]
    for comm_id in sorted(community_members):
        n = len(community_members[comm_id])
        index_lines.append(f"- [[communities/{safe_filename(comm_id)}|{comm_id.split('.')[-1]}]] ({n} symbols)")
    (vault / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    print(f"Vault: {written} symbol notes + {len(community_members)} community notes -> {vault}")
    print(f"Open {vault}/ as a vault in Obsidian.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--vault", default=None)
    args = parser.parse_args()
    vault = args.vault or str(Path(args.project_root) / "graphify-out" / "obsidian")
    export(args.project_root, vault)
