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
ollama pull qwen3:8b
ollama pull llama3.2   # optional fast fallback
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

Flags like `--dry-run`, `--yes`, and `--model` work before or after the request:

```bash
please find every jpg over 20mb --dry-run
please --model llama3.2:latest list files modified today
```

### Question marks and glob characters

zsh treats `?`, `*`, and `[` in unquoted words as glob patterns, so a request like
`please what is on port 8188?` dies with `zsh: no matches found` before `please` runs.
Let `zsh` ignore unmatched patterns:

```bash
please shell-init --apply   # appends `setopt nonomatch` to ~/.zshrc
```

...or just quote the request: `please "what is on port 8188?"`.

## Deterministic recipes

Some requests never call the model — they map straight to a known shell loop, so they are fast and always format the pattern exactly right:

```bash
please make 25 new txt files here        # numbered 01.txt..25.txt
please rename all txt files to md in this folder
```

## Safety

Every command passes a local safety scan before it can run:

| Level   | Behavior                                                |
| ------- | ------------------------------------------------------- |
| low     | runs with a plain `Run? [y/N]` prompt                   |
| medium  | runs with a plain `Run? [y/N]` prompt                   |
| high    | requires typing `DELETE`                                |
| refuse  | never runs                                              |

Commands are scored on destructive file verbs (`rm`, `mv`, `cp`, ...), recursive/force flags, `find -exec`/`-delete`, package installers, sudo, downloaded-script pipes, and more. A couple of things to know:

- **Refused outright** — recursive force-deletes aimed at `/` or your home directory, no matter how they are spelled (`rm -rf /`, `rm -r -f ~/Downloads/x`, `rm -rf $HOME/*`, literal `/Users/you/...` paths, even inside `find -exec`); `dd` to a raw disk; fork bombs; `chmod -R 777 /`; `chown -R /`.
- **Not a false positive** — quoted mentions like `grep 'rm'` and read-only commands like `ps -ef` are scored low/medium.
- **Never executes** — the model's proposal must also parse cleanly under `zsh -n`; a proposal that does not parse is refused with exit code 2.

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
default_model: qwen3:8b
fallback_model: llama3.2:latest
ollama_url: http://127.0.0.1:11434
timeout_seconds: 120.0
```

Override the model for one command:

```bash
please --model llama3.2:latest list files modified today
```

## Development

```bash
.venv/bin/python -m pytest -q    # run the test suite
.venv/bin/ruff check .           # lint
```

## Roadmap

- Explain failed commands using recent stdout, stderr, and exit status
- Inspect the current directory before proposing commands
- Detect common project types like npm, Docker, Python, and Git repos
- Grow into a local coding agent that can edit files and run tests
