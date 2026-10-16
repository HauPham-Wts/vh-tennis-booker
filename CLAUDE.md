# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Last updated: 2026-10-16.

## Project

Python code on Windows that drives the **Vinhomes Resident** Android app (Flutter) inside
the **MuMu Player** emulator to book a tennis court. A learning project meant to be a
realistic, CV-worthy product; personal use only. The only product goal is to win the race
when bookings open at **06:00 every day**, unattended. Bypassing any app check and
on-device automation (AccessibilityService) are out of scope.

Read the matching doc before changing an area; these notes hold only the essentials:

| Doc | Holds |
|---|---|
| `docs/architecture.md` | Every module, route and UI layer in detail |
| `docs/field-notes.md` | App screens, labels, dialogs, MuMu facts, timings, verified runs |
| `docs/roadmap.md` | Product decisions, phases, situations table, ruled-out ideas |
| `docs/how-it-works.md` | How the flow reads the app (dumps, matching, navigation) |
| `docs/specs/0.5.0-desktop-app.md` | Desktop app design: backend, screens, parts of 0.5.0 and 0.6.0, packaging (last) |
| `CONTRIBUTING.md` | Setup, checks, branches, releasing, runner folder |

## Commands

The Python `Scripts` folder is not on PATH on the dev machine, so prefix tools with `python -m`.

```bash
python -m pip install -e ".[dev,app]"                # package + tests/lint tools + backend
python -m pytest                                     # all tests (no emulator needed)
python -m pytest tests/test_flow.py -k slot          # single file / single test
python -m ruff check . && python -m ruff format .    # CI runs `ruff format --check .`
python -m court_booker --dry-run --verbose           # real run against the emulator
python -m court_booker --at 06:00 --dry-run          # timed run
python tools/setup_runner.py v0.4.0 --schedule       # runner folder + daily task (CONTRIBUTING)
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
- After a backend route or model change: `python tools/export_openapi.py`, then
  `npm run api:types` (a backend test and CI fail until both match).
- To try the UI against a real backend, use a scratch folder:
  `COURT_BOOKER_HOME=<scratch>/data python -m court_booker serve --config <scratch>/config.toml`,
  then `npm run dev` (Vite forwards `/api` to 127.0.0.1:8765). Headless Edge `--dump-dom`
  captures the page before any request answers; read the DOM over the DevTools protocol
  after a real wait instead.
- Never commit `config.toml`, UI dumps, or screenshots of the Vinhomes app or of real data
  (they may hold personal data; the repo is public). The only images in the repo are the
  README's screenshots of this project's UI with made-up data, in `docs/images/` (English
  UI, 1280 wide, under 200 KB each).
- All code, comments, logs, commits and docs in English; app labels stay Vietnamese in the
  config. Type hints, short imperative docstrings, comments explain why, module loggers,
  `BookingError` subclasses, named constants, Ruff line length 100.
- Git: `main` (protected) is the development line. `feat/`, `fix/`, `docs/`, `chore/`
  branches are cut from `main` and PR'd into it (merge commit, never squash); a branch
  stacked on another still targets `main`, merged in order. Only finished, tested work is
  merged (a booking flow change: a real booking first), so `main` can be released any time.
  `stable` is the latest release and only moves forward: a release is a
  `chore/release-X.Y.Z` PR into `main`, then `stable` moves to that commit, tagged `vX.Y.Z`.
  No `release/X.Y.Z` branches. Conventional Commits, Semantic Versioning, CHANGELOG (Keep a
  Changelog; each PR adds its line under "Unreleased"). The user opens and merges PRs on
  GitHub: give a compare link (`compare/main...<branch>`), title and description. `gh` is
  for reading GitHub state only.
- Write code only when the user asks for it.

## Code map

`src/court_booker` (details in `docs/architecture.md`):

- `cli.py` run entry: overrides, log file, NTP offset, keep awake, run lock, exit codes
  (`RequestError` 2, `DeviceError` 3, `AppNotReadyError` 4, `LockHeldError` 5, Ctrl+C 130).
- `runner.py` connects the device (`emulator.py` MuMuManager, `adb.py`, uiautomator2) and
  runs the rounds: prepare, warm up `warm_up_seconds` before the start, one round per slot.
  `watchdog.py` limits every device call to 60 s (a frozen MuMu ends the run, exit 3).
- `flow.py` `Booker`: the booking flow; device use only through `snapshot()`, `tap()`,
  `press_back()`, `_scroll()`, each counted in `commands`. `screen.py` (one dump parsed into
  nodes, matched locally), `geometry.py` and most of `clock.py` are pure.
- `lock.py` + `processes.py`: the run lock and the quiet time (no dry run or auto setup
  from `wake_at` to start + 5 min).
- `events.py` (event kinds are stable strings), `history.py` (`booker.db` writer, an event
  sink), `history_read.py` (read-only queries for the app).
- `config.py`, `paths.py` (data folder `%LOCALAPPDATA%\CourtBooker`, `COURT_BOOKER_HOME`),
  `device_setup.py`, `schedule.py` (Task Scheduler), `power.py`, `notify.py`.
- `api/`: FastAPI backend (`court-booker serve`, 127.0.0.1:8765); errors become `Problem`
  JSON with an `error` code.

`ui/src` (React 19, strict TypeScript, Vite): `pages/`, `components/`, `styles/` (tokens),
`i18n/` (Vietnamese default, English), `api/` (generated types, client, React Query hooks,
live feed).

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
"Tiếp tục") → optional venue ("Origami…") → Court list → Booking details ("Tiếp tục") →
Confirmation (consent checkbox, "Xác nhận") → Ticket; one Back returns to the Utilities
list. Details in `docs/field-notes.md`.

- Flutter exposes text via `content-desc`, not `text`, and builds lazily (off-screen
  elements are absent from the dump).
- MuMu runs at 540x1600, 220 DPI. Never use hard-coded coordinates: positions come from
  the dump of the screen being tapped (the consent checkbox moves).
- Success is the ticket's title showing after "Xác nhận"; a "Thông báo" dialog (closed
  hours, monthly quota of 8 slots, refused booking) fails the round. A frame without labels
  shows before either, so the confirmation page going away proves nothing; neither within
  `timeout` fails the round as "Outcome unknown".
- MuMu can freeze (seen 2026-10-13); a device call then never returns, so the watchdog
  ends the run after 60 s (no restart, no retry).

## Environment

- Windows 11, Python 3.14 (`python` is the install manager's launcher: the pid
  `Start-Process python` returns is not the pid in `run.lock`), Git.
- CI (GitHub Actions): `lint` (ruff check + format), `test` (Python 3.9, 3.11, 3.12, 3.13,
  3.14) and `ui` (Node 22: `npm ci`, typecheck, lint, format check, test, build). Tooling:
  pre-commit (ruff, basic hooks), `.editorconfig`, `.gitattributes` (LF), Dependabot, PR and
  issue templates.
- Node.js 22.19, npm 10.9 for `ui/`. Node 22.22 would allow jsdom 30 and React Router 8,
  which Dependabot skips until then.
- MuMu in `C:\Program Files\Netease\MuMuPlayer` (instance 0 serves ADB on
  `127.0.0.1:16384`, renderer Vulkan); adb is found and connected automatically
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

- Released: 0.6.3 (`stable`, tag `v0.6.3`); the runner is at v0.6.2 (0.6.3 changed only
  the UI and a read route). A booking fix is merged into `main` once tested and released
  as the next 0.6.x patch.
- Now: 0.6.x fixes and docs. Packaging the desktop app (Tauri, PyInstaller, installer;
  "Packaging" in `docs/specs/0.5.0-desktop-app.md`) is the last step before 1.0.0, after the
  speed work; it is not planned yet and has no version number yet (it was 0.7.0).
- Progress and the plan for the next part are kept outside the repo, in
  `D:\VH-Booker\notes\` (`progress.md`, `next.md`): read both at the start of a session and
  update them when a part ends. Local test tools (scratch backend, screenshots, a stand-in
  run) are in `D:\VH-Booker\dev-tools\`.
