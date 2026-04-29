#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def load_hooks(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    value.setdefault("hooks", {})
    if not isinstance(value["hooks"], dict):
        raise ValueError(f"{path}: hooks must be a JSON object")
    return value


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(path, path.with_name(f"{path.name}.bak-{stamp}"))


def merge_user_prompt_hook(data: dict[str, Any], command: str) -> dict[str, Any]:
    event_hooks = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    if not isinstance(event_hooks, list):
        raise ValueError("hooks.UserPromptSubmit must be a list")

    for matcher_entry in event_hooks:
        if not isinstance(matcher_entry, dict):
            continue
        hooks = matcher_entry.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hook in hooks:
            if isinstance(hook, dict) and hook.get("command") == command:
                return data

    event_hooks.append({"hooks": [{"type": "command", "command": command}]})
    return data


def copy_file(src: Path, dst: Path, executable: bool = False) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if executable:
        mode = dst.stat().st_mode
        dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Codex prompt-enhance hook.")
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--python", default=sys.executable or "python3")
    args = parser.parse_args()

    codex_home = args.codex_home.expanduser().resolve()
    hook_script = codex_home / "hooks" / "prompt_enhance_user_prompt.py"
    agent_file = codex_home / "agents" / "prompt-enhance.toml"
    prompt_file = codex_home / "prompts" / "prompt-rewriter.md"
    hooks_json = codex_home / "hooks.json"

    copy_file(ROOT / "hooks" / "prompt_enhance_user_prompt.py", hook_script, executable=True)
    copy_file(ROOT / "agents" / "prompt-enhance.toml", agent_file)
    copy_file(ROOT / "prompts" / "prompt-rewriter.md", prompt_file)

    data = load_hooks(hooks_json)
    command = f"{args.python} {hook_script}"
    merged = merge_user_prompt_hook(data, command)
    backup(hooks_json)
    hooks_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Installed hook script: {hook_script}")
    print(f"Installed agent: {agent_file}")
    print(f"Installed prompt rules: {prompt_file}")
    print(f"Updated hooks: {hooks_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

