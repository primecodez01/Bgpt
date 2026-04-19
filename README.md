# Bgpt

Bgpt is a customizable AI-powered shell assistant. It converts natural-language requests into shell commands, applies safety checks, and executes commands with confirmation and timeout controls.

## What You Get

- Multi-provider AI: `gemini`, `openai`, `anthropic`, `local` (Ollama)
- Safety pipeline with risk scoring, blocking rules, warnings, and confirmation
- Redesigned terminal UX with profile-based customization
- Agentic decision mode (auto decides run vs confirm based on risk)
- Interactive chat mode and one-shot mode
- Command history with execution metadata
- Setup wizard and diagnostics command

## Installation

### From source (recommended for this repository)

```bash
git clone https://github.com/primecodez01/Bgpt.git
cd Bgpt
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Optional dependencies

If you need all providers and extras:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1) Run setup wizard

```bash
bgpt --setup
```

### 2) Ask in one-shot mode

```bash
bgpt "find all python files larger than 50MB"
```

### 3) Enter chat mode

```bash
bgpt --chat
```

### 4) Explain an existing command

```bash
bgpt --explain "ls -la | grep py"
```

## Provider Setup

Bgpt reads API keys from either:

- Environment variables
- System keyring (when saved by setup wizard)

Supported environment variables:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Optional model overrides:

- `BGPT_GEMINI_MODEL`
- `BGPT_OPENAI_MODEL`
- `BGPT_ANTHROPIC_MODEL`
- `BGPT_LOCAL_MODEL`

Preferred workflow: use `bgpt --setup` to pick provider + model and persist it in config.

## Terminal Redesign And Full Customization

Bgpt now supports user-level terminal customization persisted in `~/.bgpt/config.json`.

### Profiles

- `default`
- `sunset`
- `matrix`
- `midnight`
- `minimal`

### Prompt styles

- `arrow` (default)
- `classic`
- `minimal`

### UX toggles

- Compact mode on/off
- Timestamp display on/off
- Tips on/off
- Command preview lines (3-30)

### Configure from CLI

```bash
bgpt config set --profile matrix --prompt-style classic
bgpt config set --compact --timestamps --tips
bgpt config set --preview-lines 20
bgpt config set --timeout 120
bgpt config set --provider openai --safety-level high
bgpt config set --model-provider openai --model gpt-4o-mini
bgpt config set --theme hacker
bgpt config set --agentic --hide-details --agentic-risk low
bgpt config show
```

### Configure live inside chat

```text
/profile matrix
/style classic
/theme hacker
/compact on
/timestamps off
/tips off
/preview 18
/provider gemini
/model gemini-2.5-flash
/model openai gpt-4o-mini
/agentic on
/details off
/agentic-risk low
/safety medium
/timeout 90
/config
```

## Safety Model

Before execution, Bgpt performs:

1. Syntax validation
2. Command parsing and operation classification
3. Safety scoring (low/medium/high)
4. Hard-block checks for dangerous patterns
5. Confirmation flow for risky commands

Commands can be blocked outright if they match critical destructive patterns.

## Configuration Reference

Config file path:

```text
~/.bgpt/config.json
```

Example:

```json
{
  "provider": "gemini",
  "theme": "default",
  "safety_level": "medium",
  "auto_execute": false,
  "agentic_mode": false,
  "show_command_details": true,
  "agentic_auto_execute_max_risk": "low",
  "save_history": true,
  "command_timeout": 60,
  "enabled_plugins": ["git", "mcp"],
  "models": {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "local": "tinyllama"
  },
  "ui": {
    "profile": "default",
    "prompt_style": "arrow",
    "compact_mode": false,
    "show_timestamps": true,
    "show_tips": true,
    "command_preview_lines": 12
  }
}
```

## Common Commands

```bash
# Chat mode
bgpt --chat

# One-shot generation and execution flow
bgpt "show top 10 processes by memory"

# Diagnostics
bgpt --doctor

# Show history
bgpt --history

# Setup local Ollama model
bgpt setup-local
```

## Plugin Commands

Current plugin registry includes:

- `git`
- `docker`
- `system`
- `mcp`

Manage plugins:

```bash
bgpt plugins list
bgpt plugins install git
bgpt plugins enable git
bgpt plugins disable git
bgpt plugins uninstall git
```

## Local Provider (Ollama)

To prepare local/offline usage:

```bash
bgpt setup-local
```

This checks Ollama availability and attempts to set up a lightweight model.

## Troubleshooting

### No command generated

- Run `bgpt --doctor`
- Verify API keys are configured
- Switch provider: `bgpt config set --provider gemini`

### Command times out

- Increase timeout: `bgpt config set --timeout 180`

### Provider initializes but returns nothing

- Set explicit model override (`BGPT_*_MODEL`)
- Try another provider

### TUI mode unavailable

- Install textual dependency:

```bash
pip install textual>=0.50.0
```

## Development

Run editable install and checks:

```bash
pip install -e .
python -m bgpt.main --help
```

## License

MIT
