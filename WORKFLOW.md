# AI Agent Workflow

This workflow is for AI coding agents working in this repository.

## 1. Start Here

Before changing files:

- Read `AGENTS.md`.
- Read `README.md` for user-facing setup and run instructions.
- Skim `PACKAGING.md` if the request may affect executable packaging.
- Check the relevant source file before assuming behavior.

## 2. Inspect The Workspace

Before editing:

- Run `git status --short`.
- Treat uncommitted changes as user work unless you made them in this session.
- Do not revert, overwrite, or delete unrelated changes.
- If a file has user changes that overlap with your task, read it carefully and
  work with the existing edits.

## 3. Understand The Code Boundaries

Current source layout:

- `deepseek_api_client.py` owns the Tkinter application behavior and keeps the
  public compatibility exports.
- `deepseek_client.py` owns the DeepSeek/OpenAI-compatible API wrapper.
- `config_store.py` owns runtime paths, config loading/saving, prompt loading,
  and session file paths.
- `ui_text.py` owns runtime UI language text.
- `ds_v4.py` is the stable compatibility entrypoint.
- `config.example.json` is a template only.
- `prompts.txt` is runtime prompt content.
- `build_exe.ps1` owns the portable Windows build flow.

Keep changes scoped to the files that actually need them.

## 4. Make Changes

When implementing:

- Preserve the `python ds_v4.py` run path unless the user explicitly asks to
  change it.
- Keep API keys and local secrets out of tracked files.
- Keep runtime data such as `conversations/` intact.
- Prefer existing patterns in the app over new abstractions.
- Add comments only when they clarify non-obvious behavior.
- Be careful with UTF-8 and Chinese UI text.

For GUI changes:

- Keep theme colors centralized in `apply_theme()` when possible.
- Keep repeated visual behavior, such as button hover handling, behind helper
  methods instead of duplicating bindings for each widget.
- Maintain clear surface contrast between sidebar, chat display, and input
  composer in both light and dark modes.
- For Chinese chat readability, prefer compact line spacing and avoid inserting
  extra blank lines in formatted model replies.
- Preserve Markdown structure in model replies. Headings, separators, lists,
  tables, quotes, fenced code, and inline code examples should not be treated as
  ordinary prose paragraphs.
- When users expect Markdown display, remember that Tkinter `Text` does not
  render Markdown automatically. Use text tags for supported visual styles and
  keep raw transcript text readable. Markdown links, autolinks, and bare URLs
  should use tag bindings and open in the default browser. Source-style bare
  domains such as `example.com/path` should also be clickable.
- For conversation context, preserve summary-memory behavior: long chats should
  send the system prompt, saved summary, and recent full messages. Persist
  summary state in sessions when changing conversation storage.
- When changing session/history management, handle active-session indexes and
  persisted `sessions.json` together. Deleting the active session should reset
  messages, transcript, display entries, and summary-memory state.
- History actions that operate on one session should live on the corresponding
  history row when practical, instead of relying only on a global sidebar
  action.
- DeepSeek V4 Pro and Flash both support thinking and non-thinking modes.
  Preserve per-model thinking settings and avoid temperature/top_p style
  sampling parameters when thinking is enabled.
- Preserve Unicode display. Emoji should use a font/tag path that can render
  them without breaking regular Chinese text styling.
- For Markdown tables, collect the whole table block before rendering. Align
  columns by display width so Chinese text and emoji do not immediately break
  table readability.
- Preserve keyboard behavior: Enter sends, Shift+Enter inserts a newline.

## 5. Verify

Choose verification based on the change:

- For Python source changes, run:

```powershell
python -m py_compile deepseek_api_client.py ds_v4.py config_store.py deepseek_client.py ui_text.py
```

- For packaging changes, run:

```powershell
.\build_exe.ps1
```

- For documentation-only changes, inspect the edited Markdown and run
  `git status --short`.

- For GUI changes, at minimum run the Python compile check. If the change
  affects visible layout or interaction, also launch the app locally when
  practical and inspect both light and dark modes.

If a command cannot be run, record why in the final response.

## 6. Update Agent Notes

After changing behavior or project structure:

- Update `AGENTS.md` "Current Features" if functionality changed.
- Add a dated entry to `AGENTS.md` "Modification Log".
- Update `WORKFLOW.md` if a repeated project convention or verification habit
  becomes clear during the work.
- Update `PACKAGING.md` if the build output or build command changed.
- Update `README.md` if the user-facing setup or usage changed.

## 7. Final Response Checklist

When reporting back:

- Summarize the files changed.
- Mention the verification performed.
- Mention any verification that could not be run.
- Keep the response brief and specific.
