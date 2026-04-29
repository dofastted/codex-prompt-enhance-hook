#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove the prompt-enhance hook entry from hooks.json.")
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--python", default=sys.executable or "python3")
    parser.add_argument("--remove-files", action="store_true")
    args = parser.parse_args()

    codex_home = args.codex_home.expanduser().resolve()
    hook_script = codex_home / "hooks" / "prompt_enhance_user_prompt.py"
    hooks_json = codex_home / "hooks.json"
    command = f"{args.python} {hook_script}"

    if hooks_json.exists():
        data: dict[str, Any] = json.loads(hooks_json.read_text(encoding="utf-8"))
        event_hooks = data.get("hooks", {}).get("UserPromptSubmit", [])
        kept = []
        for matcher_entry in event_hooks:
            hooks = matcher_entry.get("hooks") if isinstance(matcher_entry, dict) else None
            if not isinstance(hooks, list):
                kept.append(matcher_entry)
                continue
            filtered_hooks = [
                hook for hook in hooks if not (isinstance(hook, dict) and hook.get("command") == command)
            ]
            if filtered_hooks:
                new_entry = dict(matcher_entry)
                new_entry["hooks"] = filtered_hooks
                kept.append(new_entry)
        data.setdefault("hooks", {})["UserPromptSubmit"] = kept
        hooks_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated hooks: {hooks_json}")

    if args.remove_files:
        for path in (
            hook_script,
            codex_home / "agents" / "prompt-enhance.toml",
            codex_home / "prompts" / "prompt-rewriter.md",
        ):
            if path.exists():
                path.unlink()
                print(f"Removed: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

