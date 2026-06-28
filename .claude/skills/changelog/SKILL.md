---
name: changelog
description: Record functional changes in docs/changelog.md from the diff since the last release tag. Use when the user asks to update/create the changelog or write release notes for uv-matrix.
---

# Changelog

Add a new entry to `docs/changelog.md` covering changes since the last release.

## Steps

1. **Find the diff range.** Get the last release tag with `git describe --tags --abbrev=0`, then review the range with `git log <tag>..HEAD --oneline` and `git diff <tag>..HEAD --stat`.

2. **Select items.** Record functional additions and changes only — things that affect `src/uv_matrix/` or the tool's observable behavior. Exclude documentation (`docs/`, `README`), examples (`examples/`), and CI / lint / dependency-bot changes (`.github/`, `renovate.json`, ruff-only formatting commits).

3. **Write concisely.** Each item is 1–2 sentences, no more. Describe it from the user's point of view, not as a restatement of an internal refactor.

4. **Version heading.** Use the version from `pyproject.toml`, but confirm it with the user (the tag may not exist yet). Format the heading as `## <version> YYYY/MM/DD`.

5. **Insert.** Place the new section above the current top entry in `docs/changelog.md`. Do not modify existing entries.

6. **Nothing to record.** If there are no functional changes, tell the user and stop — do not pad the entry with filler like "Various small changes."
