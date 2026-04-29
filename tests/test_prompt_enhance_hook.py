from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "hooks" / "prompt_enhance_user_prompt.py"


def load_hook_module():
    spec = importlib.util.spec_from_file_location("prompt_enhance_user_prompt", HOOK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_hook_module_from(path: Path, module_name: str = "prompt_enhance_user_prompt_installed"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def message(role: str, text: str) -> dict:
    content_type = "input_text" if role == "user" else "output_text"
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "content": [{"type": content_type, "text": text}],
        },
    }


class PromptEnhanceHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.codex_home = self.tmp_path / ".codex"
        (self.codex_home / "memories").mkdir(parents=True)
        (self.codex_home / "prompts").mkdir(parents=True)
        (self.codex_home / "memories" / "memory_summary.md").write_text(
            "project memory line for hook tests\n", encoding="utf-8"
        )
        (self.codex_home / "memories" / "MEMORY.md").write_text("", encoding="utf-8")
        (self.codex_home / "prompts" / "prompt-rewriter.md").write_text(
            "Rewrite to English.\n", encoding="utf-8"
        )
        os.environ["CODEX_HOME"] = str(self.codex_home)
        os.environ["PROMPT_ENHANCE_RULES"] = str(self.codex_home / "prompts" / "prompt-rewriter.md")
        self.hook = load_hook_module()

    def tearDown(self) -> None:
        os.environ.pop("CODEX_HOME", None)
        os.environ.pop("PROMPT_ENHANCE_RULES", None)
        os.environ.pop("PROMPT_ENHANCE_FORCE_FULL", None)
        self.tmp.cleanup()

    def write_transcript(self, turns: int) -> Path:
        path = self.tmp_path / "rollout.jsonl"
        lines = [message("user", "# AGENTS.md instructions for /tmp/project\nignored")]
        for idx in range(turns):
            lines.append(message("user", f"user request {idx}"))
            lines.append(message("assistant", f"assistant reply {idx}"))
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        return path

    def test_no_session_turns_requires_full_mode(self) -> None:
        needs_full, reason = self.hook.needs_full_enhancement("continue", [])
        self.assertTrue(needs_full)
        self.assertIn("no completed session turns", reason)

    def test_default_codex_home_uses_installed_codex_parent(self) -> None:
        installed_hook = self.tmp_path / "installed" / ".codex" / "hooks" / "prompt_enhance_user_prompt.py"
        installed_hook.parent.mkdir(parents=True)
        shutil.copy2(HOOK_PATH, installed_hook)

        os.environ.pop("CODEX_HOME", None)
        try:
            module = load_hook_module_from(installed_hook)
            self.assertEqual(module.CODEX_HOME, installed_hook.parents[1])
        finally:
            os.environ["CODEX_HOME"] = str(self.codex_home)

    def test_short_followup_uses_fast_mode_when_session_exists(self) -> None:
        transcript = self.write_transcript(2)
        payload = {"transcript_path": str(transcript), "cwd": str(self.tmp_path)}
        turns = self.hook.collect_session_turns(payload, "continue")
        needs_full, reason = self.hook.needs_full_enhancement("continue", turns)
        self.assertFalse(needs_full)
        self.assertIn("short", reason)

    def test_collect_session_turns_keeps_latest_three_with_assistant_reply(self) -> None:
        transcript = self.write_transcript(5)
        payload = {"transcript_path": str(transcript), "cwd": str(self.tmp_path)}
        turns = self.hook.collect_session_turns(payload, "continue")
        self.assertEqual([turn["user"] for turn in turns], ["user request 2", "user request 3", "user request 4"])
        self.assertEqual(
            [turn["assistant"] for turn in turns],
            ["assistant reply 2", "assistant reply 3", "assistant reply 4"],
        )

    def test_session_context_keeps_full_user_message_and_summarizes_agent_reply(self) -> None:
        path = self.tmp_path / "rollout-long.jsonl"
        full_user_message = "user line 1\nuser line 2\nuser line 3\nuser line 4"
        long_agent_reply = "reply line 1\nreply line 2\nreply line 3\nreply line 4\nreply line 5"
        lines = [
            message("user", full_user_message),
            message("assistant", long_agent_reply),
        ]
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        payload = {"transcript_path": str(path), "cwd": str(self.tmp_path)}

        turns = self.hook.collect_session_turns(payload, "continue")
        session_context = self.hook.format_session_turns(turns)

        self.assertIn(full_user_message, session_context)
        self.assertIn("reply line 1\nreply line 2\nreply line 3", session_context)
        self.assertNotIn("reply line 4", session_context)
        self.assertNotIn("reply line 5", session_context)

    def test_fast_context_contains_user_and_assistant_sections(self) -> None:
        transcript = self.write_transcript(1)
        payload = {"transcript_path": str(transcript), "cwd": str(self.tmp_path)}
        turns = self.hook.collect_session_turns(payload, "continue")
        context_bundle = self.hook.build_context_bundle(payload, "continue", turns)
        context = self.hook.build_fast_context(context_bundle, "continue", "test")
        self.assertIn("Mode: fast-session-context", context)
        self.assertIn("user_message:", context)
        self.assertIn("agent_reply_summary:", context)


if __name__ == "__main__":
    unittest.main()
