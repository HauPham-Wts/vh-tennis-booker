# Contributing

## Setup

```bash
pip install -e ".[dev,app]"
pre-commit install
```

`pre-commit` runs Ruff (lint and format) and basic file checks on every commit. The `app`
extra (FastAPI, Uvicorn) is the desktop app's backend; without it the backend tests are
skipped. The runner folder installs the package without it.

The app's screens live in `ui/` (React, TypeScript, Vite) and need Node.js 22.12 or later:

```bash
cd ui
npm ci            # install the exact versions from package-lock.json
npm run dev       # development server with hot reload
```

## Before opening a pull request

```bash
ruff check .
ruff format .
pytest
```

If the booking flow changed, also run `court-booker --dry-run --verbose` against the emulator.

If the UI changed, run its checks in `ui/` (CI runs the same scripts):

```bash
npm run typecheck
npm run lint
npm run format       # or format:check to only report
npm test
npm run build
```

## Conventions

- **Language:** code, comments, logs, commit messages and documentation are in English.
  Accessibility labels of the target app stay in Vietnamese and live in `config.toml`.
- **Style:** enforced by Ruff (line length 100). Public functions have type hints and a
  one-line docstring in the imperative mood. Comments explain *why*, not *what*. UI code
  is strict TypeScript, linted by ESLint and formatted by Prettier (also 100 columns).
- **Errors:** raise a subclass of `BookingError` for failures that should abort one round.
- **Logging:** use the module logger (`logging.getLogger(__name__)`), never `print`, except
  for the final summary in the CLI.
- **Commits:** follow [Conventional Commits](https://www.conventionalcommits.org/),
  e.g. `feat: add retry when a slot is not yet open`, `fix: wait for ticket screen`.
- **Branches:** each version is prepared on `release/X.Y.Z`, cut from `main`. Work happens
  on `feat/<topic>`, `fix/<topic>` or `docs/<topic>` branches cut from the release branch
  and merged back into it via pull request, one PR per branch. `main` only receives the
  release branch when everything in it is stable. Tooling and CI changes use `chore/<topic>`
  and `ci/<topic>`.
- **Merging:** use "Create a merge commit"; do not squash or rebase, so commits keep their
  identity across branches.
- **Versioning:** [Semantic Versioning](https://semver.org/). Record changes in
  `CHANGELOG.md` under "Unreleased" and move them to a version section when releasing.
- **Privacy:** never commit screenshots, UI dumps or `config.toml`.

## Releasing

1. Start the version from `main`:
   ```bash
   git switch -c release/X.Y.Z main
   git push -u origin release/X.Y.Z
   ```
2. For each change, branch from `release/X.Y.Z` and open a pull request into it.
3. When the release branch is stable, on a branch from it update `__version__` in
   `src/court_booker/__init__.py` (`pyproject.toml` reads it from there), move the
   "Unreleased" entries in `CHANGELOG.md` to a new version section, and commit with
   `chore: release vX.Y.Z`; merge it into the release branch.
4. Open one pull request `release/X.Y.Z` → `main` and merge it with a merge commit.
5. Tag the merge commit on `main` and push the tag:
   ```bash
   git switch main && git pull
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
6. Create a GitHub release from the tag using the changelog entry, then delete the
   release branch.
7. Once a dry run of the release passes on the emulator, move the runner folder to the new
   tag (see below); until then the daily task keeps the previous release:
   ```bash
   python tools/setup_runner.py vX.Y.Z
   ```

## Runner folder

The daily scheduled task books for real, so it never runs the development checkout. It runs
`../runner`, a git worktree checked out at a release tag, with its own virtual environment;
it still reads `config.toml` and writes `logs/` in the development folder.

```bash
python tools/setup_runner.py v0.4.0 --schedule   # first time: create it and point the task at it
python tools/setup_runner.py vX.Y.Z              # after a release: move it to the new tag
python tools/setup_runner.py v0.4.0              # move it back if the new release fails
```

The log of each run names the Python and code folder it used. A fix that must reach the
06:00 run before the next release goes out as a patch release (`vX.Y.Z+1`) and then moves
the runner.
