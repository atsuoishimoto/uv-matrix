# Configuration

All configuration lives under `[tool.uv-matrix]` in `pyproject.toml`, in three
kinds of table:

- `[tool.uv-matrix]` — top-level settings (`continue-on-error`, `max-jobs`,
  `vars`, `env`, `envfile`).
- `[tool.uv-matrix.matrix.<name>]` — a **matrix**: the axes to expand and the
  tasks to run for it.
- `[tool.uv-matrix.tasks.<name>]` — a **task**: a reusable command plus the
  environment it runs in.

A matrix names the tasks it runs; a task is defined once and can be reused by
several matrices. The example below has two matrices sharing one `test` task:

```toml
[tool.uv-matrix]
continue-on-error = false

# A matrix: axis arrays plus a reserved `tasks` list naming which tasks to run.
[tool.uv-matrix.matrix.test]
python-version = ["3.11", "3.12", "3.13"]
tasks = ["test"]

[tool.uv-matrix.matrix.checks]
python-version = ["3.13"]
tasks = ["lint", "typecheck"]

# Task definitions, referenced by name and reusable across matrices.
[tool.uv-matrix.tasks.test]
groups = ["test"]
run = "pytest"

[tool.uv-matrix.tasks.lint]
run = "ruff check ."

[tool.uv-matrix.tasks.typecheck]
run = "mypy src"
```

## Top-level settings

Keys set directly under `[tool.uv-matrix]`:

`continue-on-error`
: Global default for the per-task `continue-on-error` (see Tasks). `false` (the
  default) stops the run at the first failing job; `true` runs the rest. A
  failure always counts toward the exit code either way.

`max-jobs`
: Maximum number of jobs to run concurrently. Default `1` (sequential).
  Overridden by `--max-jobs N` on the command line. See {ref}`parallel`.

`vars`
: Global variables, exposed to every task's templates and expressions (see
  {ref}`variables`). Each **string value is evaluated as a Python expression**,
  with the same rules as `when` — so quote a literal string
  (`reports = "'.reports'"`), and non-string values (numbers, booleans, arrays)
  are used as-is. Expressions see the reserved variables, the matrix cell's
  axes, and every var defined earlier in the table, so a later var can build on
  an earlier one. Vars are resolved before `envfile`/`env` are applied, so
  `environ` inside a var expression is the plain process environment.

`envfile`
: Path(s) to `.env`-style files whose variables are added to **every** job's
  environment. Same form and rules as the per-task `envfile` (a template or a
  list of templates; a missing file is an error). A task's own `envfile`/`env`
  override a same-named variable for that task's jobs only. See
  {ref}`environment`.

`env`
: Environment variables applied to **every** job (keys literal, values Jinja2
  templates). Overrides the top-level `envfile`; overridden per task by the
  task's own `envfile`/`env`. See {ref}`environment`.

## Matrices

A matrix is a table under `[tool.uv-matrix.matrix.<name>]`. Its keys are of two
kinds:

- The reserved **`tasks`** key lists the names of the tasks
  (`[tool.uv-matrix.tasks.<name>]`) to run for this matrix. It selects *what*
  runs, not a parameter; its values are task names, not cell data.
- **Every other key is an axis**: an array of values to expand over. Axis values
  become the matrix cell — the data a task's templates and expressions read. An
  axis name may use any character except whitespace and `=` (the latter is the
  `KEY=VALUE` separator for `--filter`); an invalid name is a configuration error.

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.11", "3.12", "3.13"]  # an axis
tasks = ["test"]                           # the reserved task list
```

So the matrix above runs the `test` task once for each `python-version`.
Matrices are independent and expanded separately, so different task groups can
have completely different axes.

### Matrix exclusions

You can exclude specific combinations of matrix values using the `exclude` key (an array of tables matching axis values). Any expanded matrix cell that matches all keys of any exclusion rule will be skipped:

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.12", "3.13"]
mode = ["fast", "slow"]
tasks = ["test"]

[[tool.uv-matrix.matrix.test.exclude]]
python-version = "3.13"
mode = "slow"
```

In this case, the `(3.13, slow)` combination will not be generated.


### Matrix expansion

Each matrix is expanded on its own: its axes form a cartesian product, and each
resulting cell is paired with each name in `tasks`. For the two matrices at the
top of this page:

```text
test:test         python-version=3.11
test:test         python-version=3.12
test:test         python-version=3.13
checks:lint       python-version=3.13
checks:typecheck  python-version=3.13
```

Five jobs, nothing skipped. The same task can appear in more than one matrix; it
then runs in each of them. A matrix with only `tasks` (no axes) runs each of its
tasks exactly once.

### Axis names

Axis names follow Python's variable rules, **plus** `-` (hyphen): a name is valid
when, with hyphens turned into underscores, it is a Python identifier. So
`python-version`, `django-version`, and `webui` are fine, while `os.name`,
`py3.13`, `ns:axis`, and `bad name` are rejected as configuration errors. The same
rule applies to matrix names and `[tool.uv-matrix.vars]` keys. (How a task reads a
hyphenated name in a template is covered under {ref}`templates`.)

```toml
[tool.uv-matrix.matrix.compat]
django-version = ["Django>=4.2,<4.3", "Django>=5.0,<5.1"]
tasks = ["test"]
```

One axis name is special: **`python-version`**. A task inherits it as the Python
version to run on when it does not set its own, so the common case — run a task
across several interpreters — needs no template at all. See
{ref}`python-version`.

## Tasks

A task, under `[tool.uv-matrix.tasks.<name>]`, defines what to run for a matrix
cell and the environment it runs in.

Each field below notes whether it is required and how its value is computed. The
kind is fixed per field, never inferred from the contents:

- a **template** is rendered with Jinja2,
- an **expression** is evaluated as Python,
- a **literal** is used as-is, never evaluated.

A task's templates and expressions are evaluated **only at `run` time**, when
jobs are actually built and executed. `list` merely enumerates the jobs and
evaluates nothing — no template is rendered and no `when` expression is run.

`run` — required, template (string) or list of templates (array)
: The command to run for the job. A string is executed through the platform's
  shell; an array is executed directly, one rendered element per argument. See
  {ref}`run-forms`.

`python-version` — optional, template
: The Python version the job runs on. Inherited from the `python-version`
  matrix axis when omitted, falling back to uv's default; see
  {ref}`python-version`.

`groups` — optional, list of templates
: Dependency groups to include in the job's environment. An element that renders
  to an empty or whitespace-only string is ignored (see {ref}`templates`).

`extras` — optional, list of templates
: Optional extras to include in the job's environment. An element that renders
  to an empty or whitespace-only string is ignored (see {ref}`templates`).

`uv-args` — optional, list of templates
: Extra options passed to `uv run` for the job (e.g. `--with`), for uv features
  uv-matrix does not model directly. An element that renders to an empty or
  whitespace-only string is ignored (see {ref}`templates`).

`envfile` — optional, template or list of templates
: Path(s) to `.env`-style files whose variables are added to the job's
  environment. Each path is a template (so it may read `matrix`/`vars`/`environ`).
  With a list, a later file overrides an earlier one on a shared key, and `env`
  (below) overrides them all. A path that names no existing file is an error.
  Layered on top of the top-level `[tool.uv-matrix]` `envfile`/`env`, so it
  overrides a same-named variable for this task's jobs only. See
  {ref}`environment`.

`env` — optional, map of templates
: Environment variables for the job (keys literal, values templated). Override
  any same-named variable from `envfile` and from the top-level
  `[tool.uv-matrix]` `envfile`/`env`. See {ref}`environment`.

`cwd` — optional, template
: The working directory the command runs in.

`when` — optional, expression
: Condition deciding whether the job runs.

`continue-on-error` — optional, expression or bool
: What to do when this job's command fails. `false` (the default) stops the run;
  `true` continues with the remaining jobs. Either way the failure counts toward
  the exit code (a failing job never makes the run exit 0). Defaults to the
  global `[tool.uv-matrix] continue-on-error`.

(run-forms)=
### Shell form and exec form

`run` accepts two forms, told apart by the TOML type:

```toml
run = "pytest {{ posargs }}"        # shell form: one string
run = ["pytest", "{{ posargs }}"]   # exec form: an argv array
```

**Shell form** (a string): the whole string is rendered as one template and
executed by the platform's shell (`sh -c` on POSIX, `cmd /c` on Windows) inside
the uv environment, so pipes, `&&`, redirects, and variable expansion all work.
`{{ posargs }}` renders as a single shell-quoted string (see {ref}`posargs`).

**Exec form** (an array): the array is the command's argv, executed directly
with no shell. Each element is rendered as a Jinja2 template and becomes
exactly one argument, so an argument containing spaces or shell metacharacters
needs no quoting. Two rules differ from the other list fields
(`groups`/`extras`/`uv-args`):

- An element that is exactly `{{ posargs }}` expands in place to the arguments
  given after `--`, one argv element each — and to nothing when none were
  given, so `["pytest", "{{ posargs }}"]` runs plain `pytest`. (A
  `{{ posargs }}` embedded inside a larger element renders normally, as the
  quoted joined string.)
- An element that renders to an empty string is kept as an empty argument
  rather than dropped, so argument positions never shift.

(python-version)=
### Choosing the Python version

A job's Python version comes from one of three places, in order:

1. **The task's own `python-version`.** When set, it takes precedence and is
   rendered as a Jinja2 template — useful to pin a version or derive it:

   ```toml
   [tool.uv-matrix.tasks.lint]
   python-version = "3.13"
   run = "ruff check ."
   ```

2. **The `python-version` matrix axis.** When a task sets no `python-version`,
   it inherits the value from the matrix cell. This is the usual way to run a
   task across several interpreters:

   ```toml
   [tool.uv-matrix.matrix.test]
   python-version = ["3.11", "3.12", "3.13"]
   tasks = ["test"]

   [tool.uv-matrix.tasks.test]
   run = "pytest"
   ```

3. **uv's default.** When neither supplies a version, the job runs without
   `--python` and uv selects the interpreter itself.

(environment)=
### The job environment

A job's environment variables come from five layers, lowest precedence first:

1. **The process environment** (`os.environ`) uv-matrix inherited.
2. **Top-level `envfile`** — file(s) named by `[tool.uv-matrix] envfile`, shared
   by every job.
3. **Top-level `env`** — the `[tool.uv-matrix] env` map, shared by every job.
4. **The task's `envfile`** — file(s) the task names.
5. **The task's `env`** — the task's own map.

A later layer overrides an earlier one on a shared key: within each level `env`
wins over `envfile`, and the whole task level sits above the top level, so a
task's `envfile`/`env` override the shared settings for that task's jobs only.

These layers are resolved **first, before any other task field is evaluated**, and
the result is folded into the `environ` namespace after each step. So a task's
`envfile` path or `env` value can read the top-level values, and every later
field — `run`, `cwd`, `groups`, and even `when` — reads the final,
post-override values through `{{ environ['X'] }}`:

```toml
[tool.uv-matrix]
env = { DATABASE_URL = "sqlite:///base.db" }   # shared by every job

[tool.uv-matrix.tasks.test]
envfile = ".env"                    # e.g. DATABASE_URL=sqlite:///file.db
env = { DATABASE_URL = "sqlite:///test.db" }   # overrides the file and the top level
# environ['DATABASE_URL'] is now "sqlite:///test.db" for run too:
run = "pytest --db {{ environ['DATABASE_URL'] }}"
```

The same merged set is also exported to the subprocess, so the command sees the
variables both as real environment variables (`$DATABASE_URL`) and through the
template namespace.

(templates)=
## Templates

Template fields are Jinja2, so expressions and method calls work inside them:

```toml
run = "pytest --junitxml=.reports/py{{ python_version.replace('.', '') }}/pytest.xml"
```

Every matrix axis is exposed two ways: as a key in the `matrix` dict
(`matrix['django-version']`) **and** as a top-level variable with `-` replaced by
`_` (`django_version`). The top-level form is the convenient one for a hyphenated
name, since `matrix.django-version` parses as a subtraction in Jinja2:

```toml
[tool.uv-matrix.tasks.test]
# both of these render the same value:
uv-args = ["--with", "{{ django_version }}"]
uv-args = ["--with", "{{ matrix['django-version'] }}"]
run = "pytest"
```

`[tool.uv-matrix.vars]` keys are exposed the same way — `vars['db-url']` and the
top-level `db_url` both work. On a name clash a reserved variable (see
{ref}`variables`) wins over an axis alias, and an axis wins over a `vars` key.

In the list fields `groups`, `extras`, and `uv-args`, an element that renders to
an empty string (or only whitespace) is dropped instead of producing a bogus
flag such as `--group ""`. This lets a template conditionally omit an element:

```toml
# --group is added only for the rows where matrix['django'] is set.
groups = ["{{ matrix['django'] or '' }}"]

# --extra web is added only when the ui axis is 'cli'.
extras = ["{{ ui == 'cli' and 'web' or '' }}"]
```

Dropping is by empty string, not by falsiness, so a conditional element must
end in `or ''`: a bare `{{ cond and 'web' }}` renders the falsy branch as the
literal text `False`, which would be passed through as `--extra False` rather
than dropped.

The exec-form `run` array is different: its elements are kept even when they
render empty, so argument positions never shift. See {ref}`run-forms`.

(variables)=
## Variables

Templates and expressions evaluate with the names below in scope. The example
values are for one concrete job — the `lint` task of the `os = "ubuntu"` cell of
this config:

```toml
[tool.uv-matrix.vars]
reports = "'.reports'"

[tool.uv-matrix.matrix.checks]
python-version = ["3.13"]
os = ["ubuntu", "macos"]
tasks = ["lint"]

[tool.uv-matrix.tasks.lint]
run = "ruff check ."
```

`matrix`
: The matrix cell for this job: a dict mapping each axis name to its value for
  this combination (the reserved `tasks` key is not included). Read an axis with
  dict lookup.
  Example value `{'python-version': '3.13', 'os': 'ubuntu'}`, so
  `{{ matrix['os'] }}` renders to `ubuntu`. Each axis is also a top-level name
  with `-` replaced by `_`, so `{{ python_version }}` and `{{ os }}` render the
  same values.

`matrix_name`
: The name of the matrix table this job came from — useful to branch in a `when`
  or to label output.
  Example value `'checks'`, so `{{ matrix_name }}` renders to `checks`.

`vars`
: The global `[tool.uv-matrix.vars]` table, shared by every job. String values
  are Python expressions (evaluated like `when`, in definition order); other
  values are used literally.
  Example value `{'reports': '.reports'}` (the expression `"'.reports'"`
  evaluated), so `{{ vars['reports'] }}` renders to `.reports`. Each key is also
  a top-level name (`-` → `_`), so `{{ reports }}` renders to `.reports` as well.

`task`
: The name of the task being run.
  Example value `'lint'`, so `{{ task }}` renders to `lint`.

`task_config`
: The task's own definition table, as an unevaluated dict — for introspection;
  rarely needed directly.
  Example value `{'run': 'ruff check .'}`.

`posargs`
: The command-line arguments after `--`, shell-quoted into a single string
  (empty when none were given). See {ref}`posargs`.
  Example: `uv-matrix run -- -k slow` makes `posargs` `'-k slow'`; with no `--`
  it is `''`.

`environ`
: The process environment (`os.environ`) as a dict, overlaid with the top-level
  and task `envfile`/`env` values (which are resolved before any other field; see
  {ref}`environment`), for reading variables the command will run with. It is a
  copy, so a `when` expression cannot mutate the real environment through it.
  Example: `{{ environ['HOME'] }}` renders to the caller's home directory, and
  `when = "environ.get('CI')"` runs the task only under CI.

`platform`
: `sys.platform` of the running interpreter — a string identifying the OS (e.g.
  `'linux'`, `'darwin'`, `'win32'`). Useful to gate a job by OS in a `when`
  expression.
  Example value `'linux'`, so `when = "platform == 'win32'"` skips the job
  except on Windows.

Used together in a `run` template:

```toml
run = "ruff check . --output-file {{ vars['reports'] }}/{{ matrix_name }}-{{ matrix['os'] }}.txt"
# for the ubuntu cell, renders to:
# ruff check . --output-file .reports/checks-ubuntu.txt
```

(posargs)=
## Posargs

Arguments after `--` on the command line are exposed to templates as
`{{ posargs }}`, mirroring tox's `tox -- -k foo`. This is the standard way to
re-run a matrix with extra arguments without editing `pyproject.toml`:

```toml
[tool.uv-matrix.tasks.test]
run = "pytest {{ posargs }}"
```

```console
$ uv-matrix run --task test -- -k slow -x
```

Every selected job then runs `pytest -k slow -x`.

`{{ posargs }}` is a single string, not a list: the arguments are joined with
spaces and shell-quoted, so values containing spaces or shell metacharacters
survive intact when the `run` command is executed by the shell. For example,
`-- -k "slow and fast"` expands to `-k 'slow and fast'`.

An exec-form `run` (an array) is the exception: an element that is exactly
`{{ posargs }}` expands to the raw arguments, one argv element each, instead
of the joined string. See {ref}`run-forms`.

When no `--` arguments are given, `{{ posargs }}` is the **empty string**, so
`run = "pytest {{ posargs }}"` runs plain `pytest` and a task that does not
reference it is unaffected. Because `posargs` apply to every selected job,
combine `--` with `--matrix` or `--task` to target a specific subset.

## Recipes

### Testing against multiple dependency versions

`uv-args` passes extra options through to `uv run` for the job, so you can reach
uv features that `uv-matrix` does not model directly. A common case is testing
against several versions of a dependency with `--with`, which layers a version
on top of the project environment. Pair a `python-version` axis (inherited) with
a custom axis read through a template:

```toml
[tool.uv-matrix.matrix.django]
python-version = ["3.12", "3.13"]
django = ["Django>=4.2,<4.3", "Django>=5.0,<5.1"]
tasks = ["test"]

[tool.uv-matrix.tasks.test]
uv-args = ["--with", "{{ matrix['django'] }}"]
groups = ["test"]
run = "pytest"
```

Each job tests against the version you list, while your project's own Django
stays in place, so everyday work is unaffected.
