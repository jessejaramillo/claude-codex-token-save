# claude-token-efficient Integration

Source: https://github.com/drona23/claude-token-efficient

## What It Is
A set of CLAUDE.md instruction files that reduce output verbosity. Drop one file into
your project — no code changes, no dependencies.

## Profiles
| File | Use Case |
|---|---|
| `CLAUDE.md` | Base — concise reasoning, no sycophancy, no over-engineering |
| `profiles/CLAUDE.coding.md` | Coding tasks — code-first, minimal explanations |
| `profiles/CLAUDE.agents.md` | Multi-agent — structured output, no prose |
| `profiles/CLAUDE.analysis.md` | Analysis — bullets/tables, no filler |

## Setup
```bash
git clone https://github.com/drona23/claude-token-efficient /tmp/claude-token-efficient
# Pick the profile that matches your use case and append to your project CLAUDE.md:
cat /tmp/claude-token-efficient/profiles/CLAUDE.coding.md >> your-project/CLAUDE.md
```

## How It Layers With This Stack
- **claude-token-efficient** reduces *output* tokens (response verbosity)
- **token-savior / jCodeMunch** reduce *input* tokens (avoid reading full files)
- **RTK** reduces *tool output* tokens (shell command compression)
- **graphify + LightRAG** provide graph-indexed context instead of raw file reads

All four layers are complementary and can be active simultaneously.

## Key Rules from Base Profile
- Think before acting. Read existing files before writing code.
- No sycophantic openers or closing fluff.
- Prefer editing over rewriting whole files.
- User instructions always override this file.
