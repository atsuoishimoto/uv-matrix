# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Write all project deliverables (code comments, docstrings, README, CLI output, error messages, commit messages) in English. (The design memo `.memo/memo.md` is in Japanese and stays as-is — it is an internal note, not a deliverable.)

## Project status

MVP implemented. Package modules: `config.py` (load + `find_pyproject` + `expand_matrix` + `iter_plan`), `evaluate.py` (template/expression evaluation), `runner.py` (`resolve_job` + `Job`), `cli.py` (`run`/`list`), `__init__.py` re-exports `main`. Tests in `tests/`. `.memo/memo.md` (Japanese) is design history and may describe superseded shapes — **this file and `README.md` are authoritative for the current model.**

## What this tool is

`uv-matrix` is a thin **matrix runner for uv-based Python projects**. It expands named matrices, maps each (cell, task) to a `uv run ...` invocation, runs them, and summarizes failures. It deliberately delegates Python install, venv creation, dependency resolution, and lockfile sync to `uv` — do not reimplement those. (Unrelated to UV coordinate transforms in graphics.)

Scope is intentionally narrow: read config → expand matrices → map task to `uv run` → aggregate results. Anything beyond that (installer/virtualenv backends, conda, tox/nox compat, plugins) is explicitly out of scope.

## Commands

This is a uv project — use `uv`, not bare `pip`/`python`.

- `uv sync` — create/sync the environment from the lockfile
- `uv run uv-matrix` — run the console entry point (`uv_matrix:main`)
- `uv build` — build with the `uv_build` backend

- `uv run pytest` — run the test suite (`tests/`)

No lint/type setup exists yet; add one when needed.

## Design constraints to honor when implementing

These come from `.memo/memo.md` and shape the public config contract:

- **Config: two namespaces under `[tool.uv-matrix]`**: top-level `continue-on-error`/`max-jobs` (+ optional `[tool.uv-matrix.vars]`); **named matrices** `[tool.uv-matrix.matrix.<name>]` (axis arrays + a reserved `tasks` list of task names); **task definitions** `[tool.uv-matrix.task.<name>]` (singular). Tasks are reusable across matrices. There is no unnamed default matrix and no `task` axis — that older model is gone. (`fail-fast` was removed; its role folded into `continue-on-error`.)
- **Expansion (`config.iter_plan`)**: for each named matrix, every key except the reserved `tasks` is an axis; cartesian-product the axes (`expand_matrix`) and pair each cell with each name in `tasks`, yielding `(matrix_name, cell, task_name)`. Matrices are independent (a task in two matrices runs in each; a matrix with only `tasks` runs each task once). `resolve_job(config, matrix_name, cell, task_name, task_defs)` builds the `Job`; a false `when` → skipped (`None`). `expand_matrix` rejects `include`/`exclude` keys with an error pointing to `when`.
- **Matrix keys are arbitrary strings** (may contain hyphens, non-ASCII). Never inject them as bare variables. Always reference via dict lookup in templates/expressions: `matrix['python-version']`, never `matrix.python` or `{python_version}`.
- **Per-field evaluation kind is fixed**, not inferred from the string:
  - template (Python f-string): `python-version`, `run`, `groups`/`extras`/`uv-args` (each list item), `env` (values), `cwd`
  - expression (Python `eval`): `when`, and `continue-on-error` when it's a string (a bool is used literally)
  - literal (never evaluated): `vars`, `matrix`
- **List-field element dropping (`groups`/`extras`/`uv-args`)**: `runner._rendered_list` drops an element that renders to native `None`/`False` or to an empty/whitespace string. The drop is decided by `evaluate.render_native` (a `NativeEnvironment`), so `"{{ cond and 'web' }}"` yields a real `False` and is omitted with no `or ''` needed. The kept element's text comes from the normal string `render_string` — never from the native render, because `NativeEnvironment` runs output through `literal_eval` and would mangle version-like values (`"3.10"` → `3.1`). Scalar fields (`python-version`, `run`, `cwd`, `env`) only ever use `render_string`.
- **Failure handling (`continue-on-error`)**: effective value per job = task's own `continue-on-error` if set, else global `[tool.uv-matrix] continue-on-error`, else `false`. A failing job whose effective value is `false` stops the run (sequential: break; parallel: cancel not-yet-started jobs, let running ones finish); `true` continues with the rest. Either way a non-zero exit always counts toward the final exit code — there is no exit-code suppression / "allowed failure" concept (removed along with `fail-fast`).
- **Evaluation context** exposes exactly: `matrix` (the matrix cell dict), `matrix_name`, `vars` (global `[tool.uv-matrix.vars]` merged with task-local `vars`), `task` (name), `task_config` (the task's dict).
- **Reserved `python-version` axis**: `python-version` is a reserved matrix axis name. A task with no `python-version` of its own inherits the matrix cell's `python-version` value (used literally, not as a template); a task that sets `python-version` overrides it (rendered as a template). When neither supplies one, `python_version` is `None` and the command omits `--python` so uv picks its default interpreter. (Other axes are arbitrary strings read only via template/`when` dict lookup.)
- **Task → command mapping**: `python-version` → `uv run --python`, each `groups` entry → `--group`, each `extras` entry → `--extra`, each `uv-args` entry inserted verbatim as a `uv run` flag (for `--with`, `--no-default-groups`, etc.), `run` → wrapped as `sh -c <run>` after the uv flags (so `run` is shell-interpreted inside the uv environment; the parent process never uses `shell=True`).
- **Per-job environment isolation (always on)**: each job runs with `UV_PROJECT_ENVIRONMENT` set to `<project-root>/.uv-matrix/<env_key>`, where `runner._env_key` hashes (python-version, groups, extras, uv-args). This keeps `.venv` untouched and stops jobs sharing env state (uv does not prune a reused `.venv`). `cli._job_env` layers it under the task's own `env` (explicit task env wins). There is no toggle — isolation is unconditional. `.uv-matrix/` is gitignored.
- **Object form** (`{ template = ... }` / `{ expr = ... }`) and parallel execution (jobs currently run sequentially) are deferred — don't build them yet.

## Security boundary

`run` executes arbitrary commands and templates/`when` are evaluated as Python. This is a trusted-repo developer tool, not a safe sandbox — keep that boundary explicit (and documented in the README) rather than trying to sandbox.
