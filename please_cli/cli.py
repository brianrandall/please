from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .config import CONFIG_PATH, Config, config_template, load_config
from .executor import run_command, shell_syntax_is_valid
from .llm import OllamaClient, OllamaError
from .photo_organizer import apply_photo_organize_plan, build_photo_organize_plan
from .safety import SafetyLevel, assess

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
SUBCOMMANDS = {"doctor", "explain", "config-init", "organize-photos", "shell-init"}


def with_model(config: Config, model: str | None) -> Config:
    if not model:
        return config
    return Config(
        model=model,
        fallback_model=config.fallback_model,
        ollama_url=config.ollama_url,
        timeout_seconds=config.timeout_seconds,
    )


@app.callback()
def main() -> None:
    """Local-first terminal assistant powered by Ollama."""


def run_request(request: list[str], *, dry_run: bool, yes: bool, model: str | None) -> None:
    if not request:
        console.print("[red]Give me a shell request, or run `please --help`.[/red]")
        raise typer.Exit(2)

    config = with_model(load_config(), model)
    client = OllamaClient(config)
    text = " ".join(request)

    try:
        if not client.model_is_loaded(config.model):
            console.print(f"[dim]Loading {config.model} into memory (first request is slow)...[/dim]")
        with console.status(f"Asking Ollama ({config.model})...", spinner="dots"):
            proposal = client.propose_command(text, cwd=str(Path.cwd()))
    except KeyboardInterrupt as exc:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(130) from exc
    except OllamaError as exc:
        console.print(f"[bold red]Ollama error:[/bold red] {exc}")
        raise typer.Exit(2) from exc

    safety = assess(proposal.command)
    render_proposal(proposal.command, proposal.explanation, proposal.risk, proposal.notes, safety)

    if not safety.allowed:
        raise typer.Exit(3)

    if dry_run:
        return

    if not confirm_execution(safety.level, yes=yes, phrase=safety.confirmation_phrase):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    ok, error = shell_syntax_is_valid(proposal.command)
    if not ok:
        console.print("[bold red]Refusing to run: the command does not parse cleanly under zsh.[/bold red]")
        console.print(error, style="red")
        raise typer.Exit(2)

    result = run_command(proposal.command)
    if result.stdout:
        console.print(result.stdout, end="")
    if result.stderr:
        console.print(result.stderr, style="red", end="")
    raise typer.Exit(result.returncode)


@app.command()
def explain(command: Annotated[str, typer.Argument(help="Shell command to explain.")]) -> None:
    config = load_config()
    client = OllamaClient(config)
    try:
        if not client.model_is_loaded(config.model):
            console.print(f"[dim]Loading {config.model} into memory (first request is slow)...[/dim]")
        with console.status(f"Asking Ollama ({config.model})...", spinner="dots"):
            text = client.explain(command)
    except KeyboardInterrupt as exc:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(130) from exc
    except OllamaError as exc:
        console.print(f"[bold red]Ollama error:[/bold red] {exc}")
        raise typer.Exit(2) from exc
    console.print(Panel(text, title="Explanation", border_style="cyan"))


@app.command()
def doctor() -> None:
    config = load_config()
    console.print(f"[bold]Config:[/bold] {CONFIG_PATH}")
    console.print(f"[bold]Ollama URL:[/bold] {config.ollama_url}")
    console.print(f"[bold]Default model:[/bold] {config.model}")

    try:
        models = OllamaClient(config).available_models()
    except OllamaError as exc:
        console.print(f"[bold red]Ollama error:[/bold red] {exc}")
        raise typer.Exit(2) from exc

    if not models:
        console.print("[yellow]Ollama is running, but no models are installed yet.[/yellow]")
        console.print(f"Try: [bold]ollama pull {config.model}[/bold]")
        return

    table = Table(title="Installed Ollama Models")
    table.add_column("Model")
    table.add_column("Default")
    for name in models:
        table.add_row(name, "yes" if name == config.model else "")
    console.print(table)

    if config.model not in models:
        console.print(f"[yellow]Default model is not installed.[/yellow] Try: [bold]ollama pull {config.model}[/bold]")


@app.command("organize-photos")
def organize_photos(
    directory: Annotated[
        Path, typer.Argument(help="Directory to organize. Defaults to the current directory.")
    ] = Path("."),
    destination: Annotated[
        Path | None, typer.Option("--destination", "-d", help="Base folder for YYYY/MM_YY folders.")
    ] = None,
    parent: Annotated[
        bool, typer.Option("--parent", help="Create YYYY/MM_YY folders next to the source directory.")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview moves without changing files.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    if destination and parent:
        console.print("[red]Use either --destination or --parent, not both.[/red]")
        raise typer.Exit(2)

    source_root = directory.expanduser().resolve()
    destination_root = destination or (source_root.parent if parent else source_root)
    plan = build_photo_organize_plan(source_root, destination_root=destination_root)

    if not plan.moves:
        console.print("[yellow]No photo/video files with dates found to move.[/yellow]")
        if plan.skipped:
            console.print(f"[dim]Skipped {len(plan.skipped)} file(s) without a detectable date.[/dim]")
        return

    table = Table(title=f"Photo Moves: {plan.source_root} -> {plan.destination_root}")
    table.add_column("Date")
    table.add_column("From")
    table.add_column("To")
    for move in plan.moves:
        table.add_row(
            f"{move.taken_date:%Y-%m-%d}",
            move.source.name,
            str(move.destination.relative_to(plan.destination_root)),
        )
    console.print(table)

    if plan.skipped:
        console.print(f"[dim]Skipped {len(plan.skipped)} file(s) without a detectable date.[/dim]")

    if dry_run:
        return

    console.print(f"[bold]Source:[/bold] {plan.source_root}")
    console.print(f"[bold]Destination base:[/bold] {plan.destination_root}")
    if not yes and not typer.confirm("Move these files to this destination?", default=False):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    apply_photo_organize_plan(plan)
    console.print(f"[green]Moved {len(plan.moves)} file(s).[/green]")


@app.command("config-init")
def config_init(force: Annotated[bool, typer.Option("--force", help="Overwrite existing config.")] = False) -> None:
    if CONFIG_PATH.exists() and not force:
        console.print(f"[yellow]Config already exists:[/yellow] {CONFIG_PATH}")
        return

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}: {value}\n" for key, value in config_template().items()]
    CONFIG_PATH.write_text("".join(lines))
    console.print(f"[green]Wrote config:[/green] {CONFIG_PATH}")


@app.command("shell-init")
def shell_init(apply: Annotated[bool, typer.Option("--apply", help="Append the line to ~/.zshrc.")] = False) -> None:
    snippet = (
        "# zsh fails on unquoted request words containing ? * [ ] (e.g. `please what is on port 8188?`).\n"
        "setopt nonomatch"
    )
    if not apply:
        console.print(Panel(snippet, title="Add to ~/.zshrc", border_style="cyan"))
        return

    rc = Path.home() / ".zshrc"
    existing = rc.read_text() if rc.exists() else ""
    if "setopt nonomatch" in existing:
        console.print(f"[green]Already present in[/green] {rc}")
        return
    rc.write_text(existing.rstrip() + "\n\n" + snippet + "\n")
    console.print(f"[green]Added to[/green] {rc}. New terminals get it automatically; run `source {rc}` to apply now.")


def render_proposal(command: str, explanation: str, model_risk: str, notes: list[str], safety) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Risk", f"model={model_risk}, local={safety.level.value}")
    if safety.reasons:
        table.add_row("Why", "; ".join(safety.reasons))

    console.print(Panel(Syntax(command, "zsh", word_wrap=True), title="Command", border_style="cyan"))
    console.print(Panel(explanation, title="Explanation", border_style="green"))
    console.print(table)

    for note in notes:
        console.print(f"[dim]- {note}[/dim]")

    if safety.level is SafetyLevel.REFUSE:
        console.print("[bold red]Refused. I will not run this command.[/bold red]")


def confirm_execution(level: SafetyLevel, *, yes: bool, phrase: str | None) -> bool:
    if yes and level in {SafetyLevel.LOW, SafetyLevel.MEDIUM}:
        return True

    if phrase:
        console.print(f"[bold red]Potentially destructive command.[/bold red] Type {phrase} to continue.")
        return typer.prompt("Confirm") == phrase

    return typer.confirm("Run?", default=False)


def parse_request_args(args: list[str]) -> tuple[list[str], bool, bool, str | None]:
    """Split request words from global flags, regardless of position in args."""
    dry_run = False
    yes = False
    model: str | None = None
    request: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--dry-run":
            dry_run = True
        elif arg in {"--yes", "-y"}:
            yes = True
        elif arg == "--model":
            i += 1
            if i >= len(args):
                console.print("[red]--model requires a value.[/red]")
                raise typer.Exit(2)
            model = args[i]
        elif arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        else:
            request.append(arg)
        i += 1
    return request, dry_run, yes, model


def entrypoint() -> None:
    try:
        _entrypoint()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise SystemExit(130) from None
    except typer.exceptions.Abort:
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise SystemExit(130) from None
    except typer.Exit as exc:
        raise SystemExit(exc.exit_code) from None


def _entrypoint() -> None:
    args = sys.argv[1:]
    if not args or args[0] in SUBCOMMANDS or args[0] in {"--help", "-h"}:
        if args and args[0] == "explain" and len(args) != 2:
            console.print('[red]`please explain` takes a single command in quotes.[/red]')
            console.print('[dim]e.g. [bold]please explain "lsof -i :8188"[/bold][/dim]')
            raise SystemExit(2)
        app()
        return

    request, dry_run, yes, model = parse_request_args(args)
    run_request(request, dry_run=dry_run, yes=yes, model=model)
