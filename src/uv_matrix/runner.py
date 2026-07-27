"""Resolve matrix jobs into uv commands and execute them."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .config import CONFIG_TABLE
from .evaluate import build_context, eval_expr, render_string, render_template


def _shell_command(run: str) -> list[str]:
    """Wrap ``run`` for the platform's default shell.

    Mirrors how :mod:`subprocess` resolves ``shell=True``: on Windows it
    invokes ``%COMSPEC%`` (``cmd.exe`` when unset) with ``/c``; everywhere
    else it uses ``sh -c``. The shell is run inside the uv environment by
    ``uv run``, so ``run`` keeps full shell syntax (pipes, ``&&``,
    redirects, variable expansion) on each OS.
    """
    if sys.platform == "win32":
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", run]
    return ["sh", "-c", run]


def spawn_args(command: list[str]) -> list[str] | str:
    """Turn a job command into the argument subprocess.run should get.

    On POSIX the list is passed through: execve hands argv to "sh -c" as a
    real array, so the trailing run string arrives byte-for-byte intact.

    On Windows a list would be joined by subprocess.list2cmdline, which
    escapes the quotes inside the run string as \\". uv parses its own
    command line back correctly, but re-escapes the string the same way when
    spawning cmd.exe -- and cmd.exe forwards its /c tail to the child raw,
    so those escapes leak into the child's command line and split quoted
    arguments ("a b c" arrives as three pieces with literal quotes). Passing
    a single pre-built string instead leaves the run part unescaped: uv's
    argv parsing (CommandLineToArgvW rules, the exact inverse of the
    list2cmdline used for posargs) consumes its quotes and re-quotes each
    token cleanly for cmd.exe.

    command[-1] is the run string: resolve_job appends the _shell_command
    triple last and the CLI splices verbosity flags right after "uv run",
    so the invariant holds for every job command. Only the argv prefix goes
    through list2cmdline; the run string is appended verbatim.
    """
    if sys.platform != "win32":
        return command
    return f"{subprocess.list2cmdline(command[:-1])} {command[-1]}"


class TaskError(Exception):
    """Raised when a job cannot be resolved: an undefined or invalid task, or
    invalid environment settings (``env``/``envfile``) at either level."""


@dataclass
class Job:
    """A single resolved job (a matrix cell paired with a task)."""

    matrix_name: str
    task: str
    matrix: dict[str, Any]
    python_version: str | None
    command: list[str]
    env: dict[str, str]
    cwd: str | None
    continue_on_error: bool

    @property
    def label(self) -> str:
        """Human-readable ``matrix:task key=value ...`` description."""
        cells = " ".join(f"{key}={value}" for key, value in self.matrix.items())
        return f"{self.matrix_name}:{self.task} {cells}".rstrip()

    @property
    def command_str(self) -> str:
        return " ".join(shlex.quote(part) for part in self.command)


def _str_list(value: Any, task_name: str, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise TaskError(f"task {task_name!r}: {field!r} must be an array")
    return value


def _rendered_list(
    task_config: dict[str, Any], field: str, task_name: str, ctx: dict[str, Any]
) -> list[str]:
    """Render a list field and drop elements that are empty after stripping.

    A template such as ``"{{ matrix['django'] or '' }}"`` evaluates to an empty
    string when the value is absent. Emitting it verbatim would build a bogus
    flag (e.g. ``--group ""``), so each rendered element is stripped and skipped
    when it has no remaining content. This lets a template conditionally omit an
    element by evaluating to ``""``.
    """
    rendered = render_template(_str_list(task_config.get(field, []), task_name, field), ctx)
    result = []
    for item in rendered:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _load_envfiles(raw: Any, owner: str, ctx: dict[str, Any]) -> dict[str, str]:
    """Load ``envfile`` paths into a flat ``{name: value}`` mapping.

    ``raw`` is the ``envfile`` value from ``owner`` — the top-level
    ``[tool.uv-matrix]`` table or a task; ``owner`` labels error messages. It is
    either a single path or a list of paths, each rendered as a Jinja2 template
    (so a path may use ``matrix``/``vars``/``environ``). Files are parsed in
    order with ``.env`` semantics; a later file overrides an earlier one on a
    shared key, so the same level's ``env`` (applied on top by the caller)
    always wins last.

    A path that does not name an existing file is an error rather than a silent
    skip — ``dotenv_values`` returns ``{}`` for a missing file, so the existence
    check is made here. A value with no ``=`` right-hand side parses to ``None``
    and is normalized to the empty string.

    Relative paths resolve from the current working directory, which the CLI sets
    to the project root, so an ``envfile`` resolves the same as ``run``/``cwd``.
    """
    if raw is None:
        return {}
    if isinstance(raw, str):
        paths = [raw]
    elif isinstance(raw, list):
        paths = raw
    else:
        raise TaskError(f"{owner}: 'envfile' must be a string or an array")

    result: dict[str, str] = {}
    for entry in paths:
        if not isinstance(entry, str):
            raise TaskError(
                f"{owner}: envfile entry must be a string, got {type(entry).__name__}"
            )
        path = render_string(entry, ctx)
        if not Path(path).is_file():
            raise TaskError(f"{owner}: envfile {path!r} not found")
        for key, value in dotenv_values(path).items():
            result[key] = value if value is not None else ""
    return result


def _rendered_env(raw: Any, owner: str, ctx: dict[str, Any]) -> dict[str, str]:
    """Render an ``env`` table's values as templates (keys stay literal).

    Each value must be a string; anything else (e.g. ``PORT = 8080``) is
    rejected here with the owning table and key named, rather than letting
    ``render_string`` raise a context-free type error (issue #18).
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TaskError(f"{owner}: 'env' must be a table")
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            raise TaskError(
                f"{owner}: env value for {str(key)!r} must be a string, "
                f"got {type(value).__name__}"
            )
        result[str(key)] = render_string(value, ctx)
    return result


def resolve_job(
    config: dict[str, Any],
    matrix_name: str,
    cell: dict[str, Any],
    task_name: str,
    task_defs: dict[str, Any],
    posargs: list[str] | None = None,
) -> Job | None:
    """Resolve a (matrix cell, task) pair into a :class:`Job`.

    Returns ``None`` when the task's ``when`` expression is false.

    ``posargs`` are the command-line arguments after ``--``, exposed to
    templates as ``{{ posargs }}``.
    """
    try:
        task_config = task_defs[task_name]
    except (KeyError, TypeError):
        raise TaskError(f"undefined task {task_name!r}")

    ctx = build_context(config, matrix_name, cell, task_name, task_config, posargs)

    # Environment is settled first, before any other field is evaluated. Two
    # levels apply: the top-level [tool.uv-matrix] `envfile`/`env` (shared by
    # every job), then the task's own `envfile`/`env` layered on top, so a task
    # overrides a same-named variable for its own jobs only. Within each level
    # the file(s) load first and `env` overrides them. After every step the
    # result is folded into the `environ` namespace, so each later step — and
    # every field below, `when` included — reads the post-override values
    # through `{{ environ['X'] }}`. Precedence low→high:
    # os.environ < top-level envfile < top-level env < task envfile < task env.
    env: dict[str, str] = {}
    levels = ((config, f"[tool.{CONFIG_TABLE}]"), (task_config, f"task {task_name!r}"))
    for table, owner in levels:
        env.update(_load_envfiles(table.get("envfile"), owner, ctx))
        ctx["environ"] = {**os.environ, **env}  # so `env` can read envfile values
        env.update(_rendered_env(table.get("env"), owner, ctx))
        ctx["environ"] = {**os.environ, **env}

    if "when" in task_config and not eval_expr(task_config["when"], ctx):
        return None

    # `python-version` is a reserved matrix axis name. A task uses its own
    # `python-version` when set (rendered as a template); otherwise it inherits
    # the value from the matrix cell's `python-version` axis. When neither
    # supplies one, the job runs without `--python` and uv picks its default.
    if "python-version" in task_config:
        python_version = render_string(task_config["python-version"], ctx)
    elif "python-version" in cell:
        python_version = str(cell["python-version"])
    else:
        python_version = None

    if "run" not in task_config:
        raise TaskError(f"task {task_name!r}: missing 'run'")
    run = render_string(task_config["run"], ctx)

    groups = _rendered_list(task_config, "groups", task_name, ctx)
    extras = _rendered_list(task_config, "extras", task_name, ctx)
    uv_args = _rendered_list(task_config, "uv-args", task_name, ctx)

    command = ["uv", "run"]
    if python_version is not None:
        command += ["--python", python_version]
    for group in groups:
        command += ["--group", group]
    for extra in extras:
        command += ["--extra", extra]
    # Arbitrary uv flags (e.g. --with, --no-default-groups) passed through verbatim.
    command += uv_args
    # `run` is executed by a shell inside the uv environment, so shell syntax
    # (pipes, &&, redirects, variable expansion) all apply with the env's tools.
    # The shell is chosen per-OS (sh on POSIX, cmd.exe on Windows).
    command += _shell_command(run)

    cwd = render_string(task_config["cwd"], ctx) if "cwd" in task_config else None
    # The task's own `continue-on-error` wins; otherwise the global
    # [tool.uv-matrix] default applies; otherwise false (stop on this failure).
    coe = task_config.get("continue-on-error", config.get("continue-on-error", False))
    continue_on_error = bool(eval_expr(coe, ctx))

    return Job(
        matrix_name=matrix_name,
        task=task_name,
        matrix=cell,
        python_version=python_version,
        command=command,
        env=env,
        cwd=cwd,
        continue_on_error=continue_on_error,
    )
