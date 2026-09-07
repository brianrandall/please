# please

Local-first terminal assistant for macOS.

`please` turns a plain-English request into one shell command, explains it, and asks before execution. The MVP talks to Ollama on your machine and runs commands only after a local safety pass.

## Setup

```bash
cd ~/Dropbox/PROJECTS/CLIAI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Install and start Ollama if you have not already:

```bash
brew install ollama
ollama serve
```

Pull the default model:

```bash
ollama pull llama3.2
```

Check local status:

```bash
please doctor
```

## Use

```bash
please find every jpg over 20mb
please --dry-run delete node_modules
please explain 'find . -type f -size +20M'
please organize-photos --dry-run
```

Quote requests that include shell punctuation such as parentheses:

```bash
please "move the files out of this directory into appropriate subdirectories (some are already there)"
```

For Camera Uploads-style cleanup, use the built-in organizer from inside the folder:

```bash
please organize-photos --dry-run
please organize-photos
```

It moves top-level photo/video files into `YYYY/MM_YY/` folders inside the source folder based on filename dates or macOS metadata, creates missing folders, and asks before moving. Use `--parent` if you explicitly want the `YYYY/MM_YY/` folders created next to the source folder instead.

Low and medium risk commands ask `Run? [y/N]`. High-risk commands require typing `DELETE`. Obviously catastrophic commands are refused.

## Configuration

Create the default config:

```bash
please config-init
```

Configuration lives at `~/.config/please/config.yaml`:

```yaml
default_model: llama3.2:latest
fallback_model: qwen3:8b
ollama_url: http://127.0.0.1:11434
timeout_seconds: 60.0
```

Override the model for one command:

```bash
please --model llama3.2:latest list files modified today
```

## Roadmap

- Explain failed commands using recent stdout, stderr, and exit status
- Inspect the current directory before proposing commands
- Detect common project types like npm, Docker, Python, and Git repos
- Grow into a local coding agent that can edit files and run tests
