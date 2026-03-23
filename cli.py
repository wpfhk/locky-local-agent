"""호환용 진입점 — `python cli.py \"요구사항\"` 은 `locky run` 과 동일합니다."""

from __future__ import annotations

import sys

# 하위 호환: 서브커맨드 없이 첫 인자만 넘긴 경우 → locky run
_SUBCOMMANDS = frozenset(
    {
        "run",
        "develop",
        "dashboard",
        "web",
        "-h",
        "--help",
        "--version",
    }
)


def main() -> None:
    argv = sys.argv[:]
    if len(argv) >= 2 and argv[1] not in _SUBCOMMANDS and not argv[1].startswith("-"):
        argv.insert(1, "run")
        sys.argv = argv
    from locky_cli.main import cli

    cli()


if __name__ == "__main__":
    main()
