# Changelog

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

