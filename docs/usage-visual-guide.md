# Visual Usage Guide

This guide shows how the `UserPromptSubmit` hook is used before the main Codex agent receives a user message.

<table>
  <tr>
    <td width="50%"><a href="#hook-flow"><img src="images/hook-flow.png" alt="Hook flow"></a></td>
    <td width="50%"><a href="#mode-selection"><img src="images/mode-selection.png" alt="Mode selection"></a></td>
  </tr>
  <tr>
    <td width="50%"><a href="#install-and-verify"><img src="images/install-verify.png" alt="Install and verify"></a></td>
    <td width="50%"><a href="#injected-context"><img src="images/injected-context.png" alt="Injected context"></a></td>
  </tr>
</table>

## Hook Flow

The user message reaches the `UserPromptSubmit` hook first. The hook keeps the original prompt intact, adds a `<prompt-enhance>` context block through `hookSpecificOutput.additionalContext`, and then lets the main Codex agent continue with the enriched request.

![Hook flow](images/hook-flow.png)

## Mode Selection

The hook chooses between two paths:

- `full`: runs the `prompt-enhance` agent with model `gpt-5.4` and reasoning effort `medium`.
- `fast-session-context`: skips the model call for short follow-up prompts when recent session context already exists.

![Mode selection](images/mode-selection.png)

## Install And Verify

Install the hook from the repository:

```bash
python3 scripts/install.py
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

Check the hook output without calling Codex:

```bash
printf '%s' '{"hook_event_name":"UserPromptSubmit","prompt":"new task","cwd":"'"$PWD"'"}' \
  | PROMPT_ENHANCE_DRY_RUN=1 python3 hooks/prompt_enhance_user_prompt.py
```

![Install and verify](images/install-verify.png)

## Injected Context

The injected context contains the current request, project context, relevant local memory lines, and the latest 3 completed user/assistant turns when a transcript is available.

![Injected context](images/injected-context.png)
