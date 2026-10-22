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

The driver that runs install on the emulator lives in `android/` (Java, the usual Gradle
folder layout, built without Gradle). Its APK is committed
(`src/court_booker/assets/court-driver.apk`), so only a change to `android/` needs the
build tools: a JDK 17 or later and the Android SDK. Unpack the
[command-line tools](https://developer.android.com/studio#command-line-tools-only) into
`<sdk>/cmdline-tools/latest`, set `ANDROID_HOME` to `<sdk>` (the build tool falls back to
`D:\Tools\android-sdk`), then install the two packages it uses and build:

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.0"
python tools/build_driver.py     # writes the APK and court-driver.json; commit both
```

In PowerShell, pass the package names after `--%` (`sdkmanager --% "platforms;android-35"
"build-tools;35.0.0"`): `sdkmanager.bat` splits its arguments at `;` otherwise. The APK is
signed with the Android debug key (`~/.android/debug.keystore`, created on the first build);
a run replaces a driver signed with another key. A test fails while the committed APK was
not built from the current sources; CI's `driver` job builds them.

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
  Accessibility labels stay in the target app's language: Vietnamese in `config.toml`,
  English in `src/court_booker/app_language.py`. The booker detects the app's language.
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
- **Branches:** `develop` is the development line; `main` holds releases only, so every
  commit on `main` is a released version with its `vX.Y.Z` tag. Work happens on
  `feat/<topic>`, `fix/<topic>` or `docs/<topic>` branches cut from `develop` and merged back
  into it via pull request, one PR per branch; tooling and CI changes use `chore/<topic>` and
  `ci/<topic>`. A branch that builds on another one still open is cut from it and also
  targets `develop`; they are merged in order. Only finished and tested work is merged (a
  booking flow change is tested with a real booking first), so `develop` can be released at
  any time. Nothing reaches `main` but a release (below); an urgent fix takes the same way
  and is released at once as a patch. Both branches take changes by pull request only.
- **Merging:** use "Create a merge commit"; do not squash or rebase, so commits keep their
  identity across branches.
- **Versioning:** [Semantic Versioning](https://semver.org/). Record changes in
  `CHANGELOG.md` under "Unreleased" and move them to a version section when releasing.
- **Privacy:** never commit `config.toml`, UI dumps, or screenshots of the Vinhomes app or
  of real data. The README's screenshots in `docs/img/` show this project's UI with
  made-up data only.

## Releasing

1. On `chore/release-X.Y.Z`, cut from `develop`, update `__version__` in
   `src/court_booker/__init__.py` (`pyproject.toml` reads it from there), run
   `python tools/export_openapi.py` (the schema carries the version), move the
   "Unreleased" entries in `CHANGELOG.md` to a new version section, and commit with
   `chore: release vX.Y.Z`. Open a pull request into `develop` and merge it.
2. Open a pull request from `develop` into `main`, titled `Release vX.Y.Z`, and merge it
   with a merge commit.
3. Tag that merge commit on `main`:
   ```bash
   git switch main && git pull --ff-only
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
python tools/setup_runner.py v0.9.0 --schedule   # first time: create it and point the task at it
python tools/setup_runner.py vX.Y.Z              # after a release: move it to the new tag
python tools/setup_runner.py <previous-tag>      # roll back to the last working release
```

The log of each run names the Python and code folder it used. A fix that must reach the
06:00 run before the next release goes out as a patch release (`vX.Y.Z+1`) and then moves
the runner.
