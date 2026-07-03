# uv-matrix

A small matrix task runner for Python projects using [Astral uv](https://docs.astral.sh/uv/).

> **Status:** early development.

`uv-matrix` runs the same project tasks across Python versions, dependency variants, extras, dependency groups, and arbitrary task variants defined in `pyproject.toml`.

**Documentation:** https://uv-matrix.readthedocs.io/

## Why uv-matrix?

Many Python projects need to run checks like this:

- run tests on Python 3.12 and 3.13
- run tests with different optional dependencies
- run lint, docs, and test tasks from one project configuration
- pass the same matrix setup to local development and CI

`uv-matrix` keeps that configuration explicit and close to the rest of the project:

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.12", "3.13"]
tasks = ["test"]

[tool.uv-matrix.tasks.test]
run = "pytest"
```

Running the matrix executes each job with `uv run`.

```bash
uv-matrix run
```

## How it relates to tox

tox is a mature test environment manager.

`uv-matrix` is intentionally smaller. It delegates interpreter discovery, environment creation, and dependency resolution to uv, then focuses on one job: expanding matrix definitions into commands.

Instead of encoding combinations into environment names, `uv-matrix` keeps matrix axes explicit in `pyproject.toml`.

## Installation

`uv-matrix` requires Python 3.10+ and a working uv installation.

Add it to a project:

```bash
uv add --dev uv-matrix
uv run uv-matrix --help
```

Or run it directly:

```bash
uvx uv-matrix --help
```

## Quick start

Add a matrix and a task to `pyproject.toml`:

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.12", "3.13"] # 
tasks = ["test"]

[tool.uv-matrix.tasks.test]
run = "pytest"
```

Run all jobs:

```bash
uv-matrix run
```

List the jobs without running them:

```bash
uv-matrix list
```

The matrix above expands to:

```text
test:test  python-version=3.12
test:test  python-version=3.13
```

Each job is executed through `uv run`. For example, the first job runs roughly like this:

```bash
uv run --python 3.12 sh -c "pytest"
```

### Matrices

Inside a matrix, every key except `tasks` and `exclude` defines an axis.

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.12", "3.13"]
webui = ["", "django", "flask"]
tasks = ["test"]
```

Axes are combined as a cartesian product. In the example above, `python-version` has 2 values and `webui` has 3 values, so the `test` matrix creates 6 jobs.

`python-version` is a reserved axis. It is inherited by tasks that do not set their own Python version and is passed to `uv run --python`.

### Tasks

Tasks are reusable command definitions.

```toml
[tool.uv-matrix.tasks.test]
run = "pytest {{ posargs }}"
extras = ["{{ webui }}"]
when = "platform != 'win32'"
```

Common task fields include:

* `run`: command to execute
* `extras`: optional project extras to include
* `groups`: dependency groups to include
* `cwd`: working directory for the command
* `when`: condition that decides whether the job should run

Task fields can use Jinja2 templates such as `{{ webui }}` and `{{ posargs }}`.

`{{ posargs }}` expands to arguments passed after `--`:

```bash
uv-matrix run --task test -- -k slow
```

### Conditions

`when` is evaluated with Python's `eval` against the context provided by `uv-matrix`.

Treat `pyproject.toml` configuration as trusted project code.

Templates and `when` expressions are evaluated only when running jobs. Commands that only enumerate jobs, such as `list`, expand the matrix without rendering templates or evaluating `when`.

See the documentation for the full template and condition reference:

* [https://uv-matrix.readthedocs.io/en/latest/configuration.html#templates](https://uv-matrix.readthedocs.io/en/latest/configuration.html#templates)
* [https://uv-matrix.readthedocs.io/en/latest/configuration.html#variables](https://uv-matrix.readthedocs.io/en/latest/configuration.html#variables)

## Usage

```bash
uv-matrix run                          # run every job from every matrix
uv-matrix run --matrix test            # run one matrix
uv-matrix run --filter webui=django    # select jobs by axis value
uv-matrix run --task lint              # run one task wherever it appears
uv-matrix run --max-jobs 4             # run up to 4 jobs at once
uv-matrix run --dry-run                # print commands without running them
uv-matrix run --task test -- -k slow   # pass extra args as {{ posargs }}
uv-matrix list                         # list selectable jobs
```

By default, `uv-matrix` finds `pyproject.toml` by walking up from the current directory, then runs from the project root.

Use `--config PATH` to point to a specific config file, or `--project DIR` to set the project directory.

## License

MIT License. See [LICENSE](LICENSE) for details.
