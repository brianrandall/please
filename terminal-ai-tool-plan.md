# Terminal AI Tool Plan

Imported from ChatGPT shared conversation: "Local AI Shell Alternatives"

## Goal

Build a local-first terminal AI assistant for macOS that turns natural language into shell commands, asks for confirmation before running anything, and gradually grows into a lightweight local coding agent.

The working command name is `please`.

## Motivation

Warp moved natural-language terminal prompts behind a paywall. Instead of depending on another hosted tool or subscription, this project should run locally on the always-on Mac using Ollama.

## Core Stack

- Python
- Typer for the CLI
- Rich for terminal output
- Ollama API for local model inference
- subprocess for execution
- prompt_toolkit later if a richer prompt loop is useful

No Electron, no Node requirement, no cloud dependency, no telemetry.

## Phase 1: MVP

- Install and verify Ollama
- Pull and test a coding model
- Build `please`
- Convert English requests into one shell command
- Display the generated command with syntax highlighting
- Show a short explanation
- Ask before execution
- Run the command only after confirmation

Example:

```bash
please find every jpg over 20mb
```

Expected output:

```text
Command

find . -type f -iname "*.jpg" -size +20M

Explanation

Search recursively for JPG files larger than 20 MB.

Run? [Y/n]
```

## Safety

Safety should be a first-class feature.

- Flag destructive commands
- Require stronger confirmation for risky commands
- Refuse obviously catastrophic commands
- Avoid `sudo` unless explicitly necessary
- Prefer non-destructive defaults

Example:

```text
Potentially destructive command

rm -rf build

Execute?

Type DELETE to continue:
```

Commands like `sudo rm -rf /` should be refused outright.

## Phase 2: Shell Copilot

Add helpers beyond command generation:

- Explain commands
- Explain failures
- Suggest fixes
- Use recent stdout, stderr, and exit code where possible
- Maintain light conversational context

Example:

```bash
please why did that command fail
```

## Phase 3: Directory Awareness

Make the assistant inspect the current directory before suggesting commands.

Example:

```bash
please start this project
```

If it sees:

```text
package.json
docker-compose.yml
README.md
```

It can choose between:

```bash
docker compose up
```

or:

```bash
npm run dev
```

depending on project contents.

## Phase 4: Local Coding Agent

Eventually let it operate as a local coding assistant:

- Inspect the project
- Find routing and file structure
- Create or edit files
- Wire code together
- Run tests
- Iterate on failures
- Support multiple specialized local models

Example:

```bash
please make a new express endpoint for users
```

## Suggested Project Structure

```text
please/
├── please.py
├── llm.py
├── executor.py
├── prompts.py
├── safety.py
├── config.py
└── pyproject.toml
```

## Prompt Direction

The model should be guided with a strict shell-assistant prompt:

```text
You are an expert macOS terminal assistant.
Generate exactly one shell command.
Never wrap it in markdown.
Never explain unless asked.
Never use sudo unless required.
Prefer POSIX tools.
If destructive, state that clearly.
```

The actual MVP should likely request structured JSON instead of raw prose so the CLI can reliably parse:

```json
{
  "command": "find . -type f -iname \"*.pdf\" -size +100M",
  "explanation": "Search recursively for PDFs over 100 MB.",
  "risk": "low"
}
```

## Model Plan

Start with a small-to-medium local coding model. The earlier discussion suggested Qwen Coder, such as:

```bash
ollama pull qwen2.5-coder:7b
```

Before hardcoding anything, benchmark a few models on the actual machine for:

- Shell command accuracy
- Python ability
- JavaScript and TypeScript ability
- Speed
- RAM usage
- General coding behavior

The tool should be model-agnostic from day one.

Example config:

```yaml
default_model: qwen2.5-coder:7b
fallback_model: llama
```

## Ollama Install Notes

The original Homebrew install hit:

```text
Error: Failed to download resource "rust (1.97.1)"
Download failed: https://static.rust-lang.org/dist/rustc-1.97.1-src.tar.gz
curl: (92) HTTP/2 stream 1 was not closed cleanly before end of the underlying stream
```

Likely causes:

- Spotty internet
- Interrupted large download
- CDN issue between the Mac and `static.rust-lang.org`
- Homebrew compiling a dependency from source, especially if LLVM was using 100% CPU

Initial checks after install:

```bash
ollama --version
ollama list
ollama serve
```

If Homebrew is behaving strangely:

```bash
brew doctor
brew config
```

## Near-Term Next Step

Verify Ollama is installed and running, pull one model, then scaffold the Python CLI.
