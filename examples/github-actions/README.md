# github-actions

Run a uv-matrix Python-version matrix as **parallel GitHub Actions jobs**, one
job per interpreter.

uv-matrix expands a matrix and runs the cells itself. By default that happens on
a single runner (sequentially, or up to `--max-jobs` at once). To spread the
matrix across runners instead — so Python 3.10 through 3.14 build at the same
time — you let GitHub Actions own the fan-out and hand each job a single
interpreter with `--filter`.

## How it works

The matrix is declared once in [`pyproject.toml`](pyproject.toml):

```toml
[tool.uv-matrix.matrix.test]
python-version = ["3.10", "3.11", "3.12", "3.13", "3.14"]
tasks = ["test"]

[tool.uv-matrix.tasks.test]
run = "pytest -q"
```

The workflow in [`.github/workflows/test.yml`](.github/workflows/test.yml)
declares a GitHub Actions matrix over the *same* versions and, in each job, runs
only that job's cell:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]
steps:
  - run: uv run uv-matrix run --matrix test --filter python-version=${{ matrix.python-version }}
```

`--filter python-version=X` keeps only the matrix cells whose `python-version`
axis equals `X`, so each runner tests exactly one interpreter and the five
versions run in parallel.

## Things to keep in mind

- **The two version lists must match.** `--filter` rejects a value that is not
  one of the axis's values (a typo is an error, not a silent no-op), so the
  GitHub Actions `matrix.python-version` and the `pyproject.toml`
  `python-version` axis are kept in sync by hand.
- **No interpreter install step.** uv-matrix delegates interpreter management to
  uv, and `uv run --python X` downloads a missing interpreter on demand, so the
  job needs no separate `uv python install`.
- **Multiple cells per version still run on one runner.** If the matrix had a
  second axis (say `webui = ["", "django", "flask"]`), filtering by
  `python-version` would leave several cells for that job; add `--max-jobs N` to
  run them concurrently within the runner.
- **`fail-fast: false`** lets every version finish even if one fails. This is the
  GitHub Actions setting, separate from uv-matrix's own `continue-on-error`.

## Try it locally

```bash
uv run uv-matrix list                                            # see every cell
uv run uv-matrix run --matrix test --filter python-version=3.12  # one version
```
