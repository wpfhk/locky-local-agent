"""locky CLI -- Click 진입점 (v4.0.0). REPL만 제공."""

from __future__ import annotations

from pathlib import Path

import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="4.0.0", prog_name="locky")
@click.option(
    "--workspace",
    "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Workspace root (default: current directory).",
)
def cli(workspace_dir: Path | None) -> None:
    """Locky -- Natural Language to Shell Command."""
    from locky_cli.repl import run_interactive_session

    run_interactive_session(start_dir=workspace_dir)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
