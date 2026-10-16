# Contributing

## Setup

```bash
pip install -e ".[dev,app]"
pre-commit install
```

`pre-commit` runs Ruff (lint and format) and basic file checks on every commit. The `app`
extra (FastAPI, Uvicorn) is the backend of the web UI; without it the backend tests are
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

If the booking flow changed, also book for real against the emulator, timed like the 06:00
run, and cancel the bookings in the app afterwards: a dry run stops before "Xác nhận", so it
cannot test the end of the flow.

```bash
court-booker --verbose --slots "<slot>" "<next slot>" --at <a few minutes from now>
```

If the UI changed, run its checks in `ui/` (CI runs the same scripts):

```bash
npm run typecheck
npm run lint
npm run format       # or format:check to only report
npm test
npm run build
```

After changing a backend route or model, regenerate the UI's copy of the API (the backend
tests and CI fail until both files match the backend):

```bash
python tools/export_openapi.py   # writes ui/openapi.json
cd ui && npm run api:types       # writes ui/src/api/schema.d.ts
```

## Conventions

- **Where things are:** [docs/architecture.md](docs/architecture.md) describes every module,
  backend route and UI layer; [docs/field-notes.md](docs/field-notes.md) holds what the app
  and the emulator were seen to do. Update them with the code they describe.
- **Language:** code, comments, logs, commit messages and documentation are in English.
  Accessibility labels of the target app stay in Vietnamese and live in `config.toml`.
- **Style:** enforced by Ruff (line length 100). Public functions have type hints and a
  one-line docstring in the imperative mood. Comments explain *why*, not *what*. UI code
  is strict TypeScript, linted by ESLint and formatted by Prettier (also 100 columns).
- **UI:** every visible text has a key in `ui/src/i18n/locales/vi.json` and `en.json`
  (tests check both hold the same keys; TypeScript checks the keys used). Styles are CSS
  Modules beside their component and take values from `ui/src/styles/tokens.css`, never raw
  colors or sizes. Addresses come from `ui/src/paths.ts`. Tests sit beside the code and find
  elements by role and accessible name, as a screen reader would.
- **Errors:** raise a subclass of `BookingError` for failures that should abort one round.
- **Logging:** use the module logger (`logging.getLogger(__name__)`), never `print`, except
  for the final summary in the CLI.
- **Commits:** follow [Conventional Commits](https://www.conventionalcommits.org/),
  e.g. `feat: add retry when a slot is not yet open`, `fix: wait for ticket screen`.
- **Branches:** `main` is the development line. Work happens on `feat/<topic>`,
  `fix/<topic>` or `docs/<topic>` branches cut from `main` and merged back into it via pull
  request, one PR per branch; tooling and CI changes use `chore/<topic>` and `ci/<topic>`.
  A branch that builds on another one still open is cut from it and also targets `main`;
  they are merged in order. Only finished and tested work is merged (a booking flow change
  is tested with a real booking first), so `main` can be released at any time. `stable`
  points at the latest release: nobody commits on it, it only moves forward to the next
  release commit.
- **Merging:** use "Create a merge commit"; do not squash or rebase, so commits keep their
  identity across branches.
- **Versioning:** [Semantic Versioning](https://semver.org/). Record changes in
  `CHANGELOG.md` under "Unreleased" and move them to a version section when releasing.
- **Privacy:** never commit `config.toml`, UI dumps, or screenshots of the Vinhomes app or
  of real data. The README's screenshots in `docs/images/` show this project's UI with
  made-up data only.

## Releasing

1. On `chore/release-X.Y.Z`, cut from `main`, update `__version__` in
   `src/court_booker/__init__.py` (`pyproject.toml` reads it from there), run
   `python tools/export_openapi.py` (the schema carries the version), move the
   "Unreleased" entries in `CHANGELOG.md` to a new version section, and commit with
   `chore: release vX.Y.Z`.
2. Open a pull request into `main` and merge it with a merge commit.
3. Move `stable` to that merge commit and tag it (git refuses to move `stable` backwards
   or sideways without `--force`):
   ```bash
   git switch main && git pull --ff-only
   git push origin <merge-commit>:stable
   git tag -a vX.Y.Z -m "vX.Y.Z" <merge-commit>
   git push origin vX.Y.Z
   ```
4. Create a GitHub release from the tag using the changelog entry, then delete the
   `chore/release-X.Y.Z` branch.
5. Once a dry run of the release passes on the emulator, move the runner folder to the new
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
