"""Evaluate uv-matrix template and expression fields.

Template fields are rendered as Jinja2 templates; expression fields as plain
Python expressions. Both run with the job's context as the namespace. This is
deliberately not a sandbox -- uv-matrix evaluates configuration from trusted
repositories only.
"""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any

import jinja2


class EvalError(Exception):
    """Raised when a template or expression fails to evaluate."""


def _finalize(value: Any) -> Any:
    """Render ``None`` and ``False`` as an empty string.

    Uses ``is`` rather than ``in (None, False)`` so that ``0`` and ``0.0``
    (which compare equal to ``False``) are left untouched.
    """
    if value is None or value is False:
        return ""
    return value


# Jinja2 environment shared by every template render. ``StrictUndefined`` turns
# a reference to a missing name (e.g. ``{{ matrix['missing'] }}``) into an error
# instead of silently rendering an empty string, so typos surface immediately.
# Autoescaping is off: templates produce shell command fragments, not HTML.
_JINJA = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    autoescape=False,
    keep_trailing_newline=True,
    finalize=_finalize,
)


def build_context(
    config: dict[str, Any],
    matrix_name: str,
    cell: dict[str, Any],
    task_name: str,
    task_config: dict[str, Any],
    posargs: list[str] | None = None,
) -> dict[str, Any]:
    """Build the variable namespace exposed to templates and expressions.

    ``posargs`` are the arguments collected after ``--`` on the command line
    (``uv-matrix run -- -k foo``). They are exposed as ``{{ posargs }}``: a
    single shell-quoted, space-joined string suitable for splicing into a
    ``run`` command. When no ``--`` arguments are given it is the empty string,
    so ``run = "pytest {{ posargs }}"`` renders to plain ``pytest``.

    ``environ`` is a copy of the process environment (``os.environ``), so a
    template can read a variable with ``{{ environ['HOME'] }}``. It is a copy:
    mutating it from an expression does not leak into the real environment.

    ``platform`` is ``sys.platform`` of the running interpreter (e.g.
    ``"linux"``, ``"darwin"``, ``"win32"``), so a ``when`` expression can gate a
    job by OS (``when = "platform == 'win32'"``).

    Each ``[tool.uv-matrix.vars]`` string value is evaluated as a **Python
    expression** with the same rules as ``when`` (:func:`eval_expr`): a
    non-string value (number, boolean, array) is used as-is, and a literal
    string must be quoted inside the expression (``reports = "'.reports'"``).
    Values are evaluated in definition order, each one seeing the reserved
    names below, the matrix cell's axes, and every var defined before it — so
    a later var can build on an earlier one. Because vars are resolved when
    the context is built, ``environ`` inside a var expression is the plain
    process environment, before any ``envfile``/``env`` settings are applied.

    Each matrix axis and each ``vars`` key is also exposed as a **top-level
    variable** with ``-`` replaced by ``_``, so a hyphenated name is usable as a
    plain name in a template or expression (``python_version`` for the
    ``python-version`` axis, ``{{ reports }}`` for ``vars['reports']``). The
    ``matrix`` and ``vars`` dicts themselves are left unchanged, so the original
    ``matrix['python-version']`` / ``vars['reports']`` lookups keep working.
    Precedence on a name clash is reserved name > matrix axis > vars: a reserved
    key below overrides an alias of the same name (so an axis named ``platform``
    cannot shadow the builtin), and a matrix axis overrides a ``vars`` key (the
    cell is the more specific, per-job value).
    """
    base = {
        "matrix": cell,
        "matrix_name": matrix_name,
        "task": task_name,
        "task_config": task_config,
        "posargs": shlex.join(posargs or []),
        "environ": dict(os.environ),
        "platform": sys.platform,
    }
    cell_alias = {key.replace("-", "_"): value for key, value in cell.items()}
    vars_dict: dict[str, Any] = {}
    vars_alias: dict[str, Any] = {}
    for key, raw in config.get("vars", {}).items():
        # The namespace mirrors the final context's precedence (reserved names
        # and axes shadow var aliases) and grows as each var is defined.
        namespace = {**vars_alias, **cell_alias, **base, "vars": vars_dict}
        try:
            value = eval_expr(raw, namespace)
        except EvalError as exc:
            raise EvalError(f"vars[{key!r}]: {exc}") from exc
        vars_dict[key] = value
        vars_alias[key.replace("-", "_")] = value
    return {**vars_alias, **cell_alias, **base, "vars": vars_dict}


def render_string(template: str, ctx: dict[str, Any]) -> str:
    """Render a single string as a Jinja2 template."""
    if not isinstance(template, str):
        raise EvalError(f"expected a string template, got {type(template).__name__}")
    try:
        return _JINJA.from_string(template).render(ctx)
    except Exception as exc:
        raise EvalError(f"failed to render template {template!r}: {exc}") from exc


def render_template(value: Any, ctx: dict[str, Any]) -> Any:
    """Recursively render a template value (string, list, or map)."""
    if isinstance(value, str):
        return render_string(value, ctx)
    if isinstance(value, list):
        return [render_template(item, ctx) for item in value]
    if isinstance(value, dict):
        return {key: render_template(item, ctx) for key, item in value.items()}
    return value


def eval_expr(value: Any, ctx: dict[str, Any]) -> Any:
    """Evaluate a Python expression; a bool is returned as-is."""
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return value
    try:
        return eval(value, {}, ctx)
    except Exception as exc:
        raise EvalError(f"failed to evaluate expression {value!r}: {exc}") from exc
