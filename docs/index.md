# uv-matrix

A small matrix task runner for Python projects using [Astral uv](https://docs.astral.sh/uv/).

:::{warning}
Status: early development
:::

`uv-matrix` runs the same project tasks across Python versions, dependency variants, extras, dependency groups, and arbitrary task variants defined in `pyproject.toml`.

## Why uv-matrix?

Many Python projects need to run checks like this:

- run tests on Python 3.12 and 3.13
- run tests with different optional dependencies
- run lint, docs, and test tasks from one project configuration
- pass the same matrix setup to local development and CI

## How it relates to tox

tox is a mature test environment manager.

`uv-matrix` is intentionally smaller. It delegates interpreter discovery, environment creation, and dependency resolution to uv, then focuses on one job: expanding matrix definitions into commands.

Instead of encoding combinations into environment names, `uv-matrix` keeps matrix axes explicit in `pyproject.toml`.

## Where to next

- {doc}`installation` — install uv-matrix into a uv project.
- {doc}`quickstart` — set up pytest and ruff matrices and run them.
- {doc}`usage` — the `run` and `list` commands and their flags.
- {doc}`configuration` — the full `[tool.uv-matrix]` reference.

```{toctree}
:hidden:
:maxdepth: 2

installation
quickstart
usage
configuration
changelog
```
