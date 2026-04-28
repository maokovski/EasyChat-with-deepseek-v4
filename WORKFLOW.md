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

- `deepseek_api_client.py` owns application behavior.
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

## 5. Verify

Choose verification based on the change:

- For Python source changes, run:

```powershell
python -m py_compile deepseek_api_client.py ds_v4.py
```

- For packaging changes, run:

```powershell
.\build_exe.ps1
```

- For documentation-only changes, inspect the edited Markdown and run
  `git status --short`.

If a command cannot be run, record why in the final response.

## 6. Update Agent Notes

After changing behavior or project structure:

- Update `AGENTS.md` "Current Features" if functionality changed.
- Add a dated entry to `AGENTS.md` "Modification Log".
- Update `PACKAGING.md` if the build output or build command changed.
- Update `README.md` if the user-facing setup or usage changed.

## 7. Final Response Checklist

When reporting back:

- Summarize the files changed.
- Mention the verification performed.
- Mention any verification that could not be run.
- Keep the response brief and specific.
