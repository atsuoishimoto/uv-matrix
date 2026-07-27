# Changelog

## 0.0.5 2026/07/27

- Parallel runs now execute every job fully in parallel: each parallel slot
  gets its own environment directory (`.uv-matrix/slot-<n>`), so concurrent
  jobs never share an environment and no longer wait on each other to sync.
- The `list` command now rejects an unknown task name instead of silently
  printing nothing, and gained the same `-m`/`--matrix` filter as `run`.
- Unknown keys in a task table or directly under `[tool.uv-matrix]` are now
  rejected with a config error naming the offending and known keys, so a typo
  like `group` for `groups` can no longer silently drop a setting.
- A malformed config shape (a non-table `[tool.uv-matrix]`, `matrix`, `tasks`,
  `vars`, or `env`) now fails with a clean error message and exit code 1
  instead of escaping as a raw traceback.
- An `exclude` rule value that matches no value of its axis is now a config
  error instead of a silent no-op, matching how `--filter` treats an unknown
  value.
- A non-string value in an `env` table or `envfile` array now fails with an
  error naming the owning table and key (e.g. `task 't': env value for 'PORT'
  must be a string, got int`).
- Fixed stop-on-failure in parallel runs: jobs cancelled by a failure are now
  counted in the run summary, a race that let workers start new jobs after the
  failure is closed, and "(stopping)" is printed only once.
- Fixed argument quoting on Windows: quoted `posargs` (e.g. `-- "a b c"`) now
  reach the command intact through `cmd.exe` instead of being split into
  separate arguments with stray quote characters.

## 0.0.4 2026/07/04

- Added top-level `env` and `envfile` settings under `[tool.uv-matrix]` that
  apply to every job; a task's own `env`/`envfile` layer on top and override
  same-named variables for that task's jobs only.
- Top-level `[tool.uv-matrix.vars]` string values are now evaluated as Python
  expressions (like `when`): a literal string must be quoted, and each var is
  evaluated in definition order so a later one can build on an earlier one.

## 0.0.3 2026/06/29

- Added matrix-level `exclude` support: a matrix table may list `exclude` rules
  (tables of axis/value pairs) to drop matching cells from the expanded product.
- Matrix `tasks` entries must now be strings; a non-string entry raises a config error.

## 0.0.2 2026/06/27

- Various small changes.

## 0.0.1 2026/06/26

- Initial release.

