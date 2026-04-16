#!/usr/bin/env bash
# Claude/Codex Token Save — macOS/Linux installer
# Usage: ./install.sh [--projects "/path/proj1,/path/proj2"] [--openrouter-key "sk-or-..."]

set -e

SCRIPTS_DIR="$HOME/scripts"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS=""
OPENROUTER_KEY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --projects) PROJECTS="$2"; shift 2 ;;
        --openrouter-key) OPENROUTER_KEY="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; shift ;;
    esac
done

echo "=== Claude/Codex Token Save Installer ==="

# 1. Python packages
echo "[1/5] Installing Python packages..."
pip install -r "$REPO_DIR/requirements.txt" -q
echo "  OK"

# 2. Scripts
echo "[2/5] Installing scripts to $SCRIPTS_DIR..."
mkdir -p "$SCRIPTS_DIR"
cp "$REPO_DIR/scripts/"*.py "$SCRIPTS_DIR/"
echo "  OK"

# 3. OpenRouter key
if [ -n "$OPENROUTER_KEY" ]; then
    echo "[3/5] Writing OPENROUTER_API_KEY to ~/.zshrc / ~/.bashrc..."
    for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc" ]; then
            grep -q "OPENROUTER_API_KEY" "$rc" || echo "export OPENROUTER_API_KEY=\"$OPENROUTER_KEY\"" >> "$rc"
        fi
    done
    export OPENROUTER_API_KEY="$OPENROUTER_KEY"
    echo "  OK"
else
    echo "[3/5] Skipping OPENROUTER_API_KEY (not provided)"
    echo "      Add to ~/.zshrc: export OPENROUTER_API_KEY=sk-or-..."
fi

# 4. Graphify hooks on all projects
if [ -n "$PROJECTS" ]; then
    echo "[4/5] Installing graphify on projects..."
    IFS=',' read -ra PROJ_LIST <<< "$PROJECTS"
    for proj in "${PROJ_LIST[@]}"; do
        proj="${proj// /}"
        if [ -d "$proj" ]; then
            cd "$proj"
            graphify claude install 2>&1 | tail -1
            graphify hook install 2>&1 | grep "post-commit:" || true
            echo "  $proj"
            cd - > /dev/null
        else
            echo "  SKIP (not found): $proj"
        fi
    done

    # 5. token-savior MCP
    echo "[5/5] Adding token-savior MCP server..."
    TS_EXE=$(which token-savior 2>/dev/null || echo "")
    if [ -n "$TS_EXE" ]; then
        python3 -c "
import json, os
from pathlib import Path
cfg_path = Path.home() / '.claude.json'
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
cfg.setdefault('mcpServers', {})['token-savior'] = {
    'command': '$TS_EXE',
    'args': [],
    'env': {'WORKSPACE_ROOTS': '$PROJECTS'}
}
cfg_path.write_text(json.dumps(cfg, indent=2))
print('  token-savior MCP registered')
"
    else
        echo "  token-savior not in PATH — run: pip install token-savior"
    fi
else
    echo "[4/5] No projects specified — skipping graphify/MCP setup"
    echo "      Re-run with: --projects '/path/proj1,/path/proj2'"
    echo "[5/5] Skipped"
fi

echo ""
echo "=== Install complete ==="
echo ""
echo "Next steps:"
echo "  1. Build LightRAG KG (one-time per project):"
echo "     python ~/scripts/rag_pipeline.py <project_path>"
echo "  2. Query:"
echo "     python ~/scripts/rag_pipeline.py <project_path> --query 'how does X work?'"
echo "  3. token-savior MCP is always-on in Claude Code"
echo "  4. graphify auto-rebuilds after every git commit"
