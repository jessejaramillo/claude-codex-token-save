# Claude/Codex Token Save — Windows installer
# Usage: .\install.ps1 -Projects "C:\path\proj1,C:\path\proj2" [-OpenRouterKey "sk-or-..."]

param(
    [string]$Projects = "",
    [string]$OpenRouterKey = ""
)

$ErrorActionPreference = "Stop"
$SCRIPTS_DIR = "$HOME\scripts"
$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Claude/Codex Token Save Installer ===" -ForegroundColor Cyan

# 1. Install Python packages
Write-Host "`n[1/5] Installing Python packages..." -ForegroundColor Yellow
pip install -r "$REPO_DIR\requirements.txt" -q
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# 2. Copy scripts
Write-Host "`n[2/5] Installing scripts to $SCRIPTS_DIR..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $SCRIPTS_DIR | Out-Null
Copy-Item "$REPO_DIR\scripts\*.py" $SCRIPTS_DIR -Force
Write-Host "  OK" -ForegroundColor Green

# 3. Store OpenRouter key if provided
if ($OpenRouterKey -ne "") {
    Write-Host "`n[3/5] Storing OPENROUTER_API_KEY in user registry..." -ForegroundColor Yellow
    [System.Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", $OpenRouterKey, "User")
    Write-Host "  OK" -ForegroundColor Green
} else {
    Write-Host "`n[3/5] Skipping OPENROUTER_API_KEY (not provided)" -ForegroundColor Gray
    Write-Host "      Set it later: [System.Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY','sk-or-...','User')"
}

# 4. Add token-savior MCP + graphify to all projects
if ($Projects -ne "") {
    Write-Host "`n[4/5] Installing graphify hooks on projects..." -ForegroundColor Yellow
    $projectList = $Projects -split ","
    $roots = $projectList -join ","

    foreach ($proj in $projectList) {
        $proj = $proj.Trim()
        if (Test-Path $proj) {
            Push-Location $proj
            graphify claude install 2>&1 | Select-Object -Last 1
            graphify hook install 2>&1 | Select-String "post-commit:"
            Pop-Location
            Write-Host "  $proj" -ForegroundColor Green
        } else {
            Write-Host "  SKIP (not found): $proj" -ForegroundColor Gray
        }
    }

    # Add token-savior MCP globally
    Write-Host "`n[5/5] Adding token-savior MCP server..." -ForegroundColor Yellow
    $exe = (Get-Command token-savior -ErrorAction SilentlyContinue)?.Source
    if (-not $exe) {
        $exe = "$env:APPDATA\Python\Python314\Scripts\token-savior.exe"
    }
    if (Test-Path $exe) {
        $claudeJson = "$HOME\.claude.json"
        $cfg = Get-Content $claudeJson | ConvertFrom-Json
        if (-not $cfg.mcpServers) { $cfg | Add-Member -MemberType NoteProperty -Name mcpServers -Value @{} }
        $cfg.mcpServers | Add-Member -MemberType NoteProperty -Name "token-savior" -Value @{
            command = $exe.Replace("\","/")
            args = @()
            env = @{ WORKSPACE_ROOTS = $roots }
        } -Force
        $cfg | ConvertTo-Json -Depth 10 | Set-Content $claudeJson
        Write-Host "  token-savior MCP registered for $($projectList.Count) projects" -ForegroundColor Green
    } else {
        Write-Host "  token-savior.exe not found at $exe — install manually" -ForegroundColor Red
    }
} else {
    Write-Host "`n[4/5] No projects specified — skipping graphify/MCP setup" -ForegroundColor Gray
    Write-Host "      Re-run with: -Projects 'C:\path\proj1,C:\path\proj2'"
    Write-Host "`n[5/5] Skipped (no projects)" -ForegroundColor Gray
}

Write-Host "`n=== Install complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Build LightRAG KG for a project (one-time):"
Write-Host "     python ~/scripts/rag_pipeline.py <project_path>"
Write-Host "  2. Query it:"
Write-Host "     python ~/scripts/rag_pipeline.py <project_path> --query 'how does auth work?'"
Write-Host "  3. Token-savior MCP is always-on in Claude Code"
Write-Host "  4. graphify rebuilds after every git commit automatically"
