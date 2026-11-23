# CLAUDE.md

NetBox plugin `netbox_mirror_session`: port mirror sessions with a mandatory expiry. Config automation reads
the sessions over GraphQL and renders them as PyAVD `monitor_sessions`.

## Commands

```
./tests/run.sh                       # tests + migration check in the official NetBox image (docker compose)
ruff check . && ruff format --check .
```

`tests/run.sh` passes `-f` to docker compose, because a host `COMPOSE_FILE` would otherwise override it.

## Rules

- The plugin version is the git tag (setuptools-scm); never write a version number in `pyproject.toml`.
- Supported NetBox range lives in `netbox_mirror_session/__init__.py` (`min_version`/`max_version`) and
  `COMPATIBILITY.md`. Change both together.
- After a model change, run `./tests/makemigrations.sh` and commit the migration; `tests/run.sh` fails on
  missing migrations.
- Migrations are tied to one NetBox minor version: 4.7 adds `related_name='+'` to `PrimaryModel.owner`, so a
  migration made on 4.6 shows drift on 4.7. Support one minor version per plugin release; moving to 4.7
  means a new migration and a new release.
- Commits follow Conventional Commits (`feat:`, `fix:`, `chore:` …): commitlint runs on push, and
  semantic-release tags releases from `main`.
- Never commit to `main`; every change goes through a branch and a PR.
- Form lists that depend on another field (device → interfaces/VRFs/addresses, session → interfaces) re-render
  the form on change (`RERENDER_FORM_ON_CHANGE` in `forms.py`) and get fixed filters in `__init__`. NetBox
  narrows every dropdown to the user's view permissions, so view tests must grant those.
- Business rules (expiry limit, warning thresholds) are constants in one place, `constants.py`. UI text that
  mentions them is built from those constants.
- Detail pages use NetBox's declarative layouts (`netbox.ui`, panels in `ui/panels.py`). The only template is
  the session page's alert block; templates get booleans from the view, never choice-value literals.
