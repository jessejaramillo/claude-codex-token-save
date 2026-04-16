# RTK (Rust Token Killer) Installation

RTK wraps shell commands and compresses output 60-90% before the LLM sees it. No MCP
registration needed — aliases make compression transparent.

## Install

### Windows (binary)
```bash
# Download v0.36.0 Windows binary
curl -L -o rtk.zip "https://github.com/rtk-ai/rtk/releases/download/v0.36.0/rtk-x86_64-pc-windows-msvc.zip"
mkdir -p "$LOCALAPPDATA/Programs/rtk"
unzip rtk.zip -d /tmp/rtk_extracted
cp /tmp/rtk_extracted/rtk.exe "$LOCALAPPDATA/Programs/rtk/rtk.exe"
```

### Linux/macOS
```bash
cargo install --git https://github.com/rtk-ai/rtk
```

## Shell Aliases (~/.bashrc)
```bash
export PATH="$PATH:$LOCALAPPDATA/Programs/rtk"   # Windows only
alias ls='rtk ls'
alias cat='rtk cat'
alias grep='rtk grep'
alias git='rtk git'
alias pytest='rtk pytest'
alias npm='rtk npm'
```

## Claude Code Integration
RTK is transparent via aliases. All Bash tool output is automatically compressed.
Config auto-created at `%APPDATA%\rtk\config.toml` on first run.

## Verification
```bash
rtk git status   # should show compressed git output
rtk --version    # should print rtk 0.36.0
```
