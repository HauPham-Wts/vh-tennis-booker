# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
It is also the shared project guidance for Codex, whose entry point is `AGENTS.md`.

Last updated: 2026-10-30.

## Project

Python code on Windows that drives the **Vinhomes Resident** Android app (Flutter) inside
the **MuMu Player** emulator to book a tennis court. A learning project meant to be a
realistic, CV-worthy product; personal use only. The only product goal is to win the race
when bookings open at **06:00 every day**, unattended.

Read the matching doc before changing an area; these notes hold only the essentials:

| Doc | Holds |
|---|---|
| `docs/architecture.md` | What each module, route and UI part does; what must stay true |
| `docs/field-notes.md` | Facts about the app and MuMu the code relies on: screens, labels, dialogs, timings |
| `docs/roadmap.md` | Goal, what is left, situations table, ruled-out ideas |
| `docs/how-it-works.md` | How the flow reads the app (dumps, matching, navigation) |
| `docs/specs/0.5.0-desktop-app.md` | Desktop app product decisions and the packaging plan (last) |
| `CONTRIBUTING.md` | Setup, checks, branches, releasing, runner folder |

Docs hold only what is true of the current code; history is in `CHANGELOG.md` and git.
Each fact has one home, the doc above that holds its kind; other files link to it rather
than restate it, so a change is made in one place.

## Commands

The Python `Scripts` folder is not on PATH on the dev machine, so prefix tools with `python -m`.

```bash
python -m pip install -e ".[dev,app]"                # package + tests/lint tools + backend
python -m pytest                                     # all tests (no emulator needed)
python -m pytest tests/test_flow.py -k slot          # single file / single test
python -m ruff check . && python -m ruff format .    # CI runs `ruff format --check .`
python -m court_booker --dry-run --verbose           # real run against the emulator
python -m court_booker --at 06:00 --dry-run          # timed run
python tools/release.py X.Y.Z                        # release commit on its branch (CONTRIBUTING)
python tools/setup_runner.py vX.Y.Z --schedule       # runner folder + daily task (CONTRIBUTING)
python -m court_booker schedule status               # task details (install, remove)
python -m court_booker setup                         # device setup checks (--auto fixes)
python -m court_booker serve --config config.toml    # backend on 127.0.0.1:8765 (/api/docs)
python tools/inspect_screen.py --near "Tôi đã hiểu"  # dump nodes level with a label
```

The UI lives in `ui/` (run these there; CI's `ui` job runs the same scripts):

```bash
npm ci                                               # install from package-lock.json
npm run dev                                          # Vite dev server, http://localhost:5173
npm run typecheck && npm run lint                    # tsc -b; ESLint (type-aware)
npm run format                                       # Prettier (format:check in CI)
npm test                                             # Vitest + Testing Library (jsdom)
npm run build                                        # type-check and build to ui/dist
npm run api:types                                    # src/api/schema.d.ts from openapi.json
```

## Rules

- **Booking flow changes** are tested with a real booking to the ticket, timed with `--at`
  a few minutes ahead like the 06:00 run, never with `--dry-run` (it stops before
  "Xác nhận"): book two consecutive free slots on today + 2
  (`python -m court_booker --verbose --config config.toml --slots "<a>" "<b>" --at <time>`);
  the user cancels them. CI cannot do this.
- The scheduled task has no `--dry-run`; it books for real. For a scheduled test, add
  `--dry-run` to the task arguments by hand (`schedule install` overwrites it).
- Never switch the schedule on from a development backend (`PUT /api/schedule`): the task
  would run the development Python instead of the runner folder.
- After a backend route, model or `catalog.py` change: `python tools/export_openapi.py`
  (writes `ui/openapi.json` and `ui/src/catalog.json`), then `npm run api:types` (backend
  tests and CI fail until they match).
- Every change (a feature, a rule, a constraint, anything) updates, in the same branch,
  every place that holds what it changes, so all stays in sync: the doc that is the fact's
  home (this file for rules and commands, README for what a user does), `config.example.toml`,
  CHANGELOG, generated files, tests, the UI texts in both languages and the session notes.
  Grep for the names touched first; a fact found restated outside its home becomes a link
  there instead of a second copy to update.
- To try the UI against a real backend, use a scratch folder:
  `COURT_BOOKER_HOME=<scratch>/data python -m court_booker serve --config <scratch>/config.toml`,
  then `npm run dev` (Vite forwards `/api` to 127.0.0.1:8765). Headless Edge `--dump-dom`
  captures the page before any request answers; read the DOM over the DevTools protocol
  after a real wait instead.
- Never commit `config.toml`, UI dumps, or screenshots of the Vinhomes app or of real data
  (they may hold personal data; the repo is public). The only images in the repo are the
  README's screenshots of this project's UI with made-up data, in `docs/img/` (English
  UI, 1280 wide, under 200 KB each).
- All code, comments, logs, commits and docs in English; app labels stay in the app's
  language (Vietnamese in the config, English built into `app_language.py`). Docs are
  written for a newcomer (CONTRIBUTING, "Writing"). Type hints, short imperative
  docstrings, comments explain why, module loggers, `BookingError` subclasses, named
  constants, Ruff line length 100.
- Git: `develop` (protected) is the development line; `main` (protected) holds releases
  only, every commit on it tagged `vX.Y.Z`. `feat/`, `fix/`, `docs/`, `chore/` branches are
  cut from `develop` and PR'd into it (merge commit, never squash); a branch stacked on
  another still targets `develop`, merged in order. Only finished, tested work is merged (a
  booking flow change: a real booking first), so `develop` can be released any time. A
  release (CONTRIBUTING, "Releasing") moves the 06:00 run to new code, so it is cut when that
  run needs a change (the engine, or a config key the backend writes), at once for a fix it
  needs, else about weekly: the UI and the backend run from the development folder.
  `python tools/release.py X.Y.Z` on a clean, up-to-date `develop` commits on
  `chore/release-X.Y.Z`; a PR into `develop`, then a PR from `develop` into `main`, whose
  merge commit the `Tag` workflow tags `vX.Y.Z` (by hand only if it failed); an urgent fix
  takes the same way. No `release/X.Y.Z` branches. Conventional Commits, Semantic
  Versioning, CHANGELOG (Keep a Changelog; each PR adds its entries under "Unreleased", one
  short entry per change a user or developer notices; small UI touches share one, without
  sizes or colours). The user opens and
  merges PRs on GitHub: give a compare link (`compare/develop...<branch>`, or
  `compare/main...develop` for a release), title and description. `gh` is for reading
  GitHub state only.
- Write code only when the user asks for it.

## Code map

`src/court_booker`; what each part does and keeps true is in `docs/architecture.md`:

- `cli.py` run entry (overrides, log file, NTP offset, keep awake, run lock), exit codes
  (`RequestError` 2, `DeviceError` 3, `AppNotReadyError` 4, `LockHeldError` 5, Ctrl+C 130).
  Each `[[instances]]` table (another MuMu instance and account) runs as its own
  `--instance N` process.
- `runner.py` connects the device (`emulator.py`, `adb.py`, `driver.py` with uiautomator2 as
  fallback) and runs the rounds; `watchdog.py` limits every device call to 60 s.
- `driver.py` talks to the instrumentation APK built from `android/` by
  `tools/build_driver.py` (committed in `src/court_booker/assets/`).
- `flow.py` `Booker`: the booking flow; device use only through `snapshot()`, `tap()`,
  `tap_point()`, `press_back()`, `_scroll()`, each counted in `commands`. Pure:
  `screen.py` (one dump, matched locally), `app_language.py` (labels per language),
  `catalog.py` (subdivisions → sports → venues → courts, the only copy; the UI gets it as
  `ui/src/catalog.json`), `geometry.py`, most of `clock.py`.
- `lock.py` + `processes.py` (run lock, quiet time), `events.py` (event kinds are stable
  strings), `history.py` + `history_read.py` (`booker.db`), `config.py`, `paths.py` (data
  folder `%LOCALAPPDATA%\CourtBooker`, `COURT_BOOKER_HOME`), `device_setup.py`,
  `schedule.py` (Task Scheduler), `power.py`, `notify.py`.
- `api/`: FastAPI backend (`court-booker serve`, 127.0.0.1:8765); errors become `Problem`
  JSON with an `error` code.

`ui/src` (React 19, strict TypeScript, Vite): `pages/`, `components/`, `styles/` (tokens),
`i18n/` (Vietnamese default, English), `api/` (generated types, client, React Query hooks,
live feed), `booking.ts` (slots, and the choices read from the generated `catalog.json`).

Invariants that tests and reviews rely on:

- External effects are injectable; nothing in the test suite touches a device, adb, the
  network or Task Scheduler. `tests/conftest.py` points `COURT_BOOKER_HOME` at a temporary
  folder, so tests never write the real history.
- A full round in `tests/test_flow.py` (`FakeApp`) costs 16 device commands.
- Reporting and history never cost a booking: sink and database errors are swallowed and
  logged.
- Loading the config never validates it, so an existing config never stops the 06:00 run.
  New config fields go into the dataclass and `config.example.toml`.
- Route modules in `api/` skip `from __future__ import annotations` and use `Optional`
  (Python 3.9 evaluates the annotations at run time). `cli.serve` imports the backend
  lazily, so a run never loads FastAPI.

## App facts that shape the code

Flow: Home ("Tiện ích") → Utilities list ("Sân Tennis") → Calendar (date, slot,
"Tiếp tục") → optional venue ("Chọn phân khu") → Court list → Booking details
("Tiếp tục") → Confirmation (consent checkbox, "Xác nhận") → Ticket; one Back returns to the
Utilities list. Details, labels and their dates are in `docs/field-notes.md`.

- Flutter exposes text via `content-desc`, not `text`, and builds lazily (off-screen
  elements are absent from the dump). MuMu runs at 540x1600, 220 DPI. Locate elements from
  the current dump, never from stored coordinates (the consent checkbox moves).
- The app may be in Vietnamese or English, the same screens with other labels; court and
  venue names stay Vietnamese in both. Each subdivision's account sees its own utilities,
  venues and courts (`catalog.py`; Origami and BS surveyed).
- Success is the ticket's title showing after "Xác nhận"; a "Thông báo" dialog fails the
  round (the quota one, 2 slots a day and 8 a month, also skips the rounds left). A frame
  without labels shows before either, so a page going away proves nothing; neither within
  `timeout` fails the round as "Outcome unknown".
- MuMu can freeze; a device call then never returns, so the watchdog ends the run after
  60 s (no restart, no retry).

## Environment

- Windows 11, Python 3.14 (`python` is the install manager's launcher: the pid
  `Start-Process python` returns is not the pid in `run.lock`), Git.
- CI (GitHub Actions): `lint` (ruff check + format), `test` (Python 3.9, 3.11, 3.12, 3.13,
  3.14), `driver` (build the Android sources with JDK 21 and SDK 35), and `ui` (Node 22:
  `npm ci`, generated API type check, typecheck, lint, format check, test, build); the `Tag`
  workflow tags each push to `main` with its version. Ruff's version is pinned once, in
  `pyproject.toml` (CI reads it; pre-commit must match, a test checks). Tooling:
  pre-commit (ruff, basic hooks), `.editorconfig`, `.gitattributes` (LF), Dependabot, PR and
  issue templates.
- Node.js 22.19, npm 10.9 for `ui/`. Node 22.22 would allow jsdom 30 and React Router 8,
  which Dependabot skips until then.
- MuMu in `C:\Program Files\Netease\MuMuPlayer` (instance 0 serves ADB on
  `127.0.0.1:16384`, its clone instance 1 on `127.0.0.1:16416` with a second account,
  renderer Vulkan); adb is found and connected automatically
  (`device = "auto"`).
- The daily task (wake 05:50 on this machine, start 06:00) runs the runner folder
  `D:\VH-Booker\runner` (git worktree at the last release tag, own `.venv`, its
  `pythonw.exe`) with the development `config.toml` and `logs/`; `Start In` is the
  development folder, which the src layout keeps from being imported. Move the runner with
  `tools/setup_runner.py` after each release; the development folder may stay on any
  branch.
- Repo `github.com/servedbyhau/vh-tennis-booker` is **public**; local path
  `D:\VH-Booker\vh-tennis-booker`. GitHub CLI `gh` is installed and logged in.

## Current state

- The released version is the newest section of `CHANGELOG.md`; what is left is in
  `docs/roadmap.md`.
- Session notes live outside the repo, in Vietnamese, in `D:\VH-Booker\notes\`:
  `progress.md` (current state: release, runner, open branches, last 06:00 run, decisions in
  force), `next.md` (the plan of the next task) and `issues.md` (open bugs). Read
  `progress.md` and `next.md` at the start of a session and keep all three short and current;
  nothing else goes there. Local test tools are in `D:\VH-Booker\dev-tools\`.
- A separate local branch, `feat/android-on-device`, holds an Android compatibility lab using
  the instrumentation driver through Shizuku; it is not part of any release. Read that
  branch's `android/mobile/README.md` when working on it.
