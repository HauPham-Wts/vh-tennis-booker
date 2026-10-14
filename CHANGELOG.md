# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- The `ui/` project for the app's screens: React, TypeScript (strict) and Vite, built with
  `npm run build` and served for development with `npm run dev`.
- `npm run lint` checks the UI code with ESLint (type-aware TypeScript rules, React hooks
  rules); `npm run format` and `npm run format:check` format it with Prettier.
- `npm test` runs the UI tests with Vitest and Testing Library in a jsdom page;
  `npm run typecheck` checks the types without building.
- CI type-checks, lints, tests and builds the UI in its own job; Dependabot updates the
  UI's npm packages monthly.
- The UI ships its fonts (Bricolage Grotesque, IBM Plex Mono, with Vietnamese) instead of
  loading them from the internet, so it works offline.
- Design tokens of the "Vé giấy" design (colors, type, spacing, shapes) and base page
  styles with a visible keyboard focus ring and reduced motion when Windows asks for it.
  A test holds every text color pair to WCAG AA contrast; the "failed" color is a little
  darker than in the mockups to pass it.
- Every screen has its own address (`/`, `/schedule`, `/history`, `/activity`,
  `/settings/booking`, `/settings/device`, `/guide`, `/welcome`) and names the window; an
  unknown address or a screen that fails shows a page with a way back.
- The page shell of the mockups: the "court booker." name over an ink rule, the navigation
  with the current screen as a filled ink tab (hidden on the welcome screen), one centred
  column that narrows with the window, and a skip link for keyboard users.
- Vietnamese and English: a VI/EN switch in the header changes every text, the window title
  and the page language at once, and the choice is remembered on this machine. Vietnamese
  is the default. Both language files must hold the same keys, and a mistyped key fails
  the type check.
- `tools/export_openapi.py` writes the backend's OpenAPI schema to `ui/openapi.json`, the
  source of the UI's types; the backend tests fail while it is out of date.
- `npm run api:types` generates the UI's TypeScript types from `ui/openapi.json`; CI fails
  while they are out of date.
- A typed API client with one function per backend endpoint. Every failure becomes an
  error with a stable code and a message in Vietnamese or English, also when the
  backend is not running. In development Vite forwards `/api` to `court-booker serve`.
- The screens share backend data through a TanStack Query cache: one hook per kind of
  data and per action. Reads retry only while the backend is out of reach; actions
  never repeat on their own and refresh the data they change.
- The UI follows the live feed: one connection for the whole app brings each new step as
  runs write it and refreshes the data it changes. After a drop, or a socket that never
  opens, it reconnects and resumes after the last step seen, so no step is lost or
  repeated (checked with the backend stopped and restarted).
- Dates, times, durations, slots and courts are formatted per language ("Thứ Tư 14/10",
  "Wed 14 Oct", "7,0 giây", "18:00–19:00", "S6"). The backend's local times are read as
  written, never shifted by a time zone, and a value that cannot be read is shown as it is.
- Shared building blocks of the paper design for the screens: buttons, an on/off switch
  that writes out its state, pill filters, paper cards, a ticket with a torn-off stub, the
  "ĐÃ ĐẶT" stamp, a dotted ledger table that scrolls when narrow, small capital labels, the
  page header, and loading, error (with "Thử lại") and empty states.
- Every step of a run or of the app has plain words in Vietnamese and English ("Đặt được
  15:00–16:00", "Chạy thử tới bước xác nhận: 10:00–11:00"), with a ✓/✕ tone, the time a
  slot took and the engine's own reason kept for the technical details.

### Changed
- The OpenAPI schema describes every error response as a `Problem` (also 422, which it
  listed as FastAPI's own validation error) and names the `/api/status` model `Overview`.
- The UI keeps a read fresh for 30 seconds, so returning to the window no longer reads
  everything again; the live feed still refreshes what each step changes at once.
- The OpenAPI schema lists every step kind (`EventKind`) and category, so a step the UI
  has no words for fails its type check.

## [0.5.3] - 2026-10-14

### Changed
- A timed run waits on the app's home screen instead of the utilities list, and opens the
  list `warm_up_seconds` before the start time (new setting, default 60 s), so the app has
  just loaded it when the booking starts. If the list does not open then, it is tried again
  two seconds before the start.

## [0.5.2] - 2026-10-14

### Added
- The debug log lists every new screen a run reads, as one entry each and without extra
  device commands, and every tap (with the element's label and position), Back press and
  swipe. Any failure can then be followed screen by screen; a one-slot run writes about
  400 log lines.

### Changed
- The screen after a confirmation is part of that screen log instead of its own entry.

## [0.5.1] - 2026-10-14

### Fixed
- A booking the app refused right after "Xác nhận" was reported as booked: the notice
  dialog (for example a slot someone else took a moment earlier) hides the confirmation
  page just as the ticket does. Such a round now fails with the app's message, which also
  reaches the history. Seen on 2026-10-14, when 18:00 - 19:00 was logged as booked but was
  not.

### Added
- The debug log lists the screen shown after each confirmation, and warns about any notice
  closed on the way back to the utilities list.
- Config label `notice` ("Thông báo"), the title of the app's message dialogs.

## [0.5.0] - 2026-10-13

### Added
- `tools/setup_runner.py` sets up the runner folder: a git worktree at a release tag with its
  own virtual environment, which the daily scheduled task runs, so work in progress never
  books. Configuration and logs stay in the development folder.
- The debug log names the Python and the code folder each run uses.
- Run events: besides its log lines, the engine reports each step as an event with fixed
  fields (run started with its trigger, device and app ready, waiting, each slot's steps and
  result, run finished with its status). For now they appear in the debug log; they are the
  base for the history database and the live view of the app.
- The app's data folder, `%LOCALAPPDATA%\CourtBooker` (or `COURT_BOOKER_HOME`), for its
  config, history database, logs and run lock.
- The config can be saved: it is checked first (slot format, court, day, wake time before
  start time, timeouts) and written safely, so a bad edit never reaches the file a run
  reads. A default config is created when none exists. New dependency: `tomli-w`.
- History database: every run (scheduled, dry run or manual) is recorded in `booker.db` in
  the data folder: the run with its trigger, play date, court and status, the result of each
  slot, every step, and the technical log lines. A database error only turns history off
  for that run; the booking goes on. Writing takes about 0.13 ms per row.
- The booking started event names the court.
- Run lock: only one run drives the emulator at a time. A second dry run or manual run is
  refused with exit code 5. The scheduled run waits for another run and, if it still holds
  the lock 2 minutes before the start time, stops it and goes on. A lock left by a run that
  is gone is removed, and that run is marked as interrupted in the history.
- No dry run may start from the wake time to 5 minutes after the start time (exit code 2).
- `court-booker setup` checks the PC and the emulator: MuMu installed, its screen at
  540x1600 and 220 DPI, wake timers allowed plugged in and on battery, the Vinhomes app
  installed. `setup --auto` fixes what it can (saves the MuMu path, sets the screen,
  restarting a running MuMu only with `--restart-mumu`, allows wake timers) and records each
  item in the history. It takes the run lock and does not start around the scheduled run.
- Each run turns off Android animations before opening the app.
- The desktop app's backend: `court-booker serve` runs a FastAPI app on 127.0.0.1 (port
  8765) with a health route, its OpenAPI schema at `/api/openapi.json` and engine errors
  answered as JSON with a stable code. It needs the new `app` extra
  (`pip install -e ".[app]"`); scheduled runs do not load it.
- Backend history routes, read-only: `GET /api/runs` (newest first, filters by play month
  and trigger, paging), `GET /api/runs/{id}` (slots, steps and log lines) and
  `GET /api/events` (the activity log by category).
- Backend settings routes: `GET /api/settings` and `PUT /api/settings`. Saving checks
  every value first and lists each problem; the Telegram keys are neither shown nor
  changed; a save is recorded in the activity log. Invalid requests answer with the list
  of invalid values.
- Backend setup routes: `GET /api/setup` (the device checks) and `POST /api/setup/auto`
  (auto setup, with the same lock, quiet time and activity log as `setup --auto`).
- Backend schedule routes: `GET /api/schedule` (on or off, the next booking and its play
  date) and `PUT /api/schedule`, which switches the daily task on only once a dry run has
  passed, and records each switch in the activity log.
- `POST /api/runs/dry-run` starts a dry run of the saved settings in its own process, as
  the scheduled task does; it is refused around the scheduled run and while another run
  (or the dry run started just before) is going.
- `GET /api/status`: the Overview in one call (the run going on, the schedule and next
  booking, the last run, the last auto setup).
- `WS /api/live`: the live feed pushes each new step of a run or of the app as it is
  written; a client can resume after the last step it saw. New dependency in the `app`
  extra: `websockets`.

### Fixed
- `tools/inspect_screen.py` connects to MuMu 12 instance 0 (`127.0.0.1:16384`) by default
  instead of the MuMu 6 port.

## [0.4.0] - 2026-10-12

### Added
- When a round or the preparation fails, the debug log lists every labelled or clickable
  element of the last screen read, with its bounds, so a failure seen once at 06:00 can be
  fixed from the log alone.
- While the target date is missing from the calendar, the debug log shows the first day
  listed, which tells whether the month switch went the right way.

## [0.3.0] - 2026-10-09

### Changed
- Each screen is read with one hierarchy dump; waiting for a screen and locating its
  elements is the same read, and taps use the coordinates from it. A round now costs about
  16 device commands instead of about 50; a timed dry run reached the accepted terms in
  5.9 s instead of 8.7 s.
- The utilities list is read again two seconds before the start time, so the first
  command at the start time is the tap on the utility.
- Waits poll from the client every 20 ms; no device-side waits or fixed sleeps.
- A slot is scrolled to only when it is not shown; the recommended MuMu resolution of
  540x1600 shows the whole slot list.

### Added
- A court labelled as fully booked fails the round with a clear message.
- The debug log counts device commands per round.

### Fixed
- The screen size is read from the hierarchy dump; `window_size()` reported (960, 540)
  when MuMu ran a tablet resolution, which made scrolling use a 540 px tall screen.

## [0.2.0] - 2026-10-08

### Changed
- Project text, logs and errors are now in English.
- Logging uses the standard `logging` module; added `--verbose`.
- Errors are raised as `BookingError` subclasses.
- Config label `full` renamed to `fully_booked`.
- Default `device` is now `"auto"`.
- The summary is logged instead of printed, so it also reaches the log file.

### Added
- Unattended booking: `court-booker schedule install` registers a daily Windows scheduled
  task (default 05:45) that wakes the PC and runs `court-booker --scheduled`.
- Emulator start: MuMu is launched through `MuMuManager.exe` when Android is not running.
- ADB auto-connect: adb is found on `adb_path`, `PATH` or in the MuMu folder, a running server
  is reused, and the emulator's own serial is connected; no manual `adb connect`.
- App preparation: the app is restarted (`restart_app`) and the run waits on the utilities
  list; a logged-out app fails early with exit code 4.
- Timed start: `--at HH:MM[:SS]` and `--scheduled` (`start_at`, default 06:00) wait for the
  exact time, corrected against an NTP server, and keep Windows awake during the run.
- Opening retry: the calendar is reloaded for up to `open_retry_seconds` while the new date
  or slot is not listed yet.
- Daily log file in `logs/`; optional Telegram summary (`telegram_token`, `telegram_chat_id`).
- Exit codes: 1 round failed, 2 bad arguments or config, 3 emulator or ADB error, 4 app not
  ready, 130 interrupted (finished rounds are still summarized).
- Pre-commit hooks, EditorConfig, Dependabot, issue and pull request templates,
  contribution guide; CI runs lint and format checks separately from tests.

## [0.1.0] - 2026-10-02

First release.

### Added
- Label-based UI automation of the tennis-court booking flow: every button is located
  at runtime by its accessibility label, with no hard-coded coordinates.
- Consent checkbox located as the small clickable node beside and level with its caption.
- Lag-tolerant navigation: tap as soon as a button appears, retry if the next screen
  does not show.
- Scroll-into-view for time slots below the fold; a slot is tapped only when fully
  visible and not covered by the sticky bottom button.
- Multiple booking rounds; each round after the first starts from the utilities list.
- Success verified by leaving the confirmation screen.
- Step logger with millisecond timing.
- `config.toml` for all settings and UI labels; command-line overrides.
- `tools/inspect_screen.py` to dump and inspect the UI tree.
- Unit tests with a fake device and GitHub Actions CI.
