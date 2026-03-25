"""locky_cli/context.py — .locky/profile.json 기반 프로젝트 컨텍스트 캐시."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCKY_DIR = ".locky"
_PROFILE_FILE = "profile.json"
_SCHEMA_VERSION = "1"


def _locky_dir(root: Path) -> Path:
    return root / _LOCKY_DIR


def _profile_path(root: Path) -> Path:
    return _locky_dir(root) / _PROFILE_FILE


def load_profile(root: Path) -> dict[str, Any]:
    """.locky/profile.json 읽기. 없거나 파손되면 {} 반환."""
    path = _profile_path(root)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_profile(root: Path, data: dict[str, Any]) -> None:
    """.locky/profile.json 저장. 디렉토리 자동 생성."""
    try:
        _locky_dir(root).mkdir(parents=True, exist_ok=True)
        _profile_path(root).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # 쓰기 권한 없음 등 — 경고 없이 skip


def update_last_run(root: Path, command: str, status: str) -> None:
    """last_run 필드만 갱신. 프로파일이 없으면 생성하지 않음."""
    profile = load_profile(root)
    if not profile:
        return
    profile["last_run"] = {
        "command": command,
        "at": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    save_profile(root, profile)


def _detect_commit_style(root: Path) -> dict[str, Any]:
    """최근 커밋 메시지에서 스타일 패턴을 감지합니다."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", "-20"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        messages = [m.strip() for m in result.stdout.splitlines() if m.strip()]
        if not messages:
            return {"type": "unknown", "lang": "unknown", "examples": []}

        conventional = sum(
            1
            for m in messages
            if ":" in m
            and m.split(":")[0].strip().lower()
            in ("feat", "fix", "refactor", "docs", "style", "test", "chore", "perf")
        )
        style_type = "conventional" if conventional > len(messages) / 2 else "free"

        # 언어 감지: 한글 포함 여부
        has_korean = any(any("\uac00" <= c <= "\ud7a3" for c in m) for m in messages)
        lang = "ko" if has_korean else "en"

        return {
            "type": style_type,
            "lang": lang,
            "examples": messages[:3],
        }
    except Exception:
        return {"type": "unknown", "lang": "unknown", "examples": []}


def detect_and_save(root: Path) -> dict[str, Any]:
    """언어·커밋 스타일 감지 후 profile.json 저장. 기존 프로파일이 있으면 병합."""
    existing = load_profile(root)

    try:
        from locky_cli.lang_detect import detect as _detect_lang

        lang_info = _detect_lang(root)
    except Exception:
        lang_info = existing.get("language", {"primary": "unknown", "all": []})

    profile: dict[str, Any] = {
        "version": _SCHEMA_VERSION,
        "project": {
            "name": root.name,
            "root": str(root),
        },
        "language": {
            **lang_info,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        },
        "commit_style": existing.get("commit_style") or _detect_commit_style(root),
        "last_run": existing.get("last_run"),
    }

    save_profile(root, profile)
    return profile
