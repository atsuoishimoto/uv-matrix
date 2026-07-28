# uv-matrix

A small matrix task runner for Python projects using [Astral uv](https://docs.astral.sh/uv/).

**Documentation:** https://uv-matrix.readthedocs.io/

`uv-matrix` runs the same project tasks across Python versions, dependency variants, extras, dependency groups, and arbitrary task variants defined in `pyproject.toml`:

```toml
[tool.uv-matrix.matrix.test]        # a matrix named "test"
python-version = ["3.12", "3.13"]   # run the job on Python 3.12 and 3.13
tasks = ["run_test"]                # run the "run_test" task in every cell

[tool.uv-matrix.tasks.run_test]     # a task named "run_test"
run = "pytest"                      # command run through `uv run`
```


## Why uv-matrix?

Many Python projects need to run checks like this:

- run tests against multiple Python versions
- run tests with different optional dependencies
- run lint, docs, and test tasks from one project configuration
- pass the same matrix setup to local development and CI


## Installation

`uv-matrix` requires Python 3.10+ and a working uv installation.

Run it directly:

```bash
uvx uv-matrix --help
```


Or add it to a project:

```bash
uv add --dev uv-matrix
uv run uv-matrix --help
```

## Matrices

In this matrix, `python-version` and `webui` are axes.

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.12", "3.13"]   # reserved axis -> uv run --python
webui = ["django", "flask"]         # a custom axis (any name)
tasks = ["test"]                    # 2 x 2 = 4 jobs
```

Axes are combined as a cartesian product. In the example above, `python-version` has 2 values and `webui` has 2 values, so the `test` matrix creates 4 jobs.

`python-version` is a reserved axis. It is inherited by tasks that do not set their own Python version and is passed to `uv run --python`.

## Tasks

Tasks are reusable command definitions.

```toml
[tool.uv-matrix.tasks.run_test]
run = "pytest {{ posargs }}"        # {{ posargs }}: args after `--`
extras = ["{{ webui }}"]            # include the current webui extra. ignored if webui is blank.
when = "platform != 'win32'"        # skip this task on Windows
```

Common task fields include:

* `run`: command to execute (shell form or exec form, see below)
* `extras`: optional project extras to include
* `groups`: dependency groups to include
* `cwd`: working directory for the command
* `when`: condition that decides whether the job should run

The full set of task fields is `run`, `groups`, `extras`, `uv-args`, `env`, `envfile`, `cwd`, `when`, `python-version`, and `continue-on-error`. An unknown key in a task table (or at the top level of `[tool.uv-matrix]`) is an error, so a typo such as `group` for `groups` fails immediately instead of silently running the job without the intended settings.

Task fields can use [Jinja2](https://jinja.palletsprojects.com/en/stable/) templates such as `{{ webui }}` and `{{ posargs }}`.

`{{ posargs }}` expands to arguments passed after `--`:

```bash
uv-matrix run --task run_test -- -k slow
```

### Shell form and exec form

`run` accepts two forms:

```toml
run = "pytest {{ posargs }}"        # shell form: one string
run = ["pytest", "{{ posargs }}"]   # exec form: an argv array
```

A string is run through the platform's shell (`sh -c` on POSIX, `cmd /c` on Windows) inside the uv environment, so pipes, `&&`, redirects, and variable expansion all work; `{{ posargs }}` renders as a single shell-quoted string.

An array is executed directly, with no shell. Each element is rendered as a Jinja2 template and becomes exactly one argument, so arguments containing spaces or shell metacharacters need no quoting. Two rules differ from the other array fields (`groups`/`extras`/`uv-args`):

* An element that is exactly `{{ posargs }}` expands in place to the arguments given after `--`, one argv element each — and to nothing when none were given, so `["pytest", "{{ posargs }}"]` runs plain `pytest`.
* An element that renders to an empty string is kept as an empty argument rather than dropped.

## Conditions

`when` specifies a Python expression. If it evaluates to `False`, the task is skipped.

Templates and `when` expressions are evaluated only when running jobs. Commands that only enumerate jobs, such as `list`, expand the matrix without rendering templates or evaluating `when`.

## Usage

```bash
uv-matrix run                            # run every job from every matrix
uv-matrix run --matrix test              # run one matrix
uv-matrix run --filter webui=django      # select jobs by axis value
uv-matrix run --task lint                # run one task wherever it appears
uv-matrix run --max-jobs 4               # run up to 4 jobs at once
uv-matrix run --dry-run                  # print commands without running them
uv-matrix run --task run_test -- -k slow # pass extra args as {{ posargs }}
uv-matrix list                           # list selectable jobs
uv-matrix list --matrix test             # list only one matrix's jobs
```

By default, `uv-matrix` finds `pyproject.toml` by walking up from the current directory, then runs from the project root.

Use `--config PATH` to point to a specific config file, or `--project DIR` to set the project directory.

## How it relates to tox

tox is a mature test environment manager.

`uv-matrix` is intentionally smaller. It delegates interpreter discovery, environment creation, and dependency resolution to uv, then focuses on one job: expanding matrix definitions into commands.

Instead of encoding combinations into environment names, `uv-matrix` keeps matrix axes explicit in `pyproject.toml`.


## License

MIT License. See [LICENSE](LICENSE) for details.


## Status

Early development.
