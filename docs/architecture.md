# Architecture

The code has three parts: the **engine** (`python -m court_booker`), which books a court in
one run of its own; the **backend** (`court_booker.api`, FastAPI), which the app's screens
talk to; and the **UI** (`ui/`, React), the screens themselves. The engine never needs the
backend: the 06:00 task runs it alone. The design behind the backend and the UI is in
[specs/0.5.0-desktop-app.md](specs/0.5.0-desktop-app.md); "spec part N" below refers to it.
How the booking flow reads the app is described in [how-it-works.md](how-it-works.md).

## Engine: one run

- `cli.py` parses args (or dispatches `schedule ...` to `schedule.main`), applies overrides
  onto `Config`, adds the log file (and logs the Python and code folder it runs from),
  resolves the start time, measures the NTP offset, and inside `power.keep_awake()` takes
  the run lock, then calls `runner.connect_device` and `runner.run_booking`. Errors map to
  exit codes (`RequestError` 2, `DeviceError` 3, `AppNotReadyError` 4, `LockHeldError` 5,
  Ctrl+C 130); the summary is logged and optionally sent with `notify.send_telegram` on
  every path. A dry run is refused (exit 2) from `wake_at` to 5 minutes after `start_at`.
  After the summary, while still holding the lock, `cli.close_emulator` shuts MuMu down
  (`emulator.MuMu.shutdown`, MuMuManager `control shutdown`) when `mumu_manager` is set,
  the run is not a dry run and ran at least one round, and neither Ctrl+C nor a frozen
  device ended it; a failure only logs a warning (exit code and history unchanged). Tests
  replace it (`closed_mumu` fixture in `tests/conftest.py`), since the default
  `mumu_manager` is the real one.
- `lock.py`: the run lock `run.lock` in the data folder (spec part 5), a JSON `Holder` (pid,
  process start time, trigger, since) published with `os.link` so it is created atomically
  and never read half-written. `RunLock.acquire` raises `LockHeldError` while a running
  process holds it; `acquire_for_schedule` (scheduled runs) waits and, at
  `start - TAKE_OVER_AHEAD` (2 min), stops the holder and takes the lock. A lock whose
  holder is gone (or unreadable) is removed and logged; a lock file that cannot be written
  lets the run go on without it. Events `lock_cleared`, `lock_waiting`, `lock_taken_over`.
  After taking the lock the CLI calls `History.interrupt_stale_runs`, so runs left
  `running` become `interrupted`. `lock.check_quiet_time` refuses a dry run or auto setup
  from `wake_at` to start + 5 min.
- `processes.py` names a process by pid and start time (`GetProcessTimes` via ctypes on
  Windows), so a later process that reuses a pid is never taken for the holder or stopped.
- `runner.connect_device`: `emulator.MuMu.ensure_started` (MuMuManager `info`/`control
  launch`), `adb.find_adb` + `adb.resolve_device` (prefers the serial MuMu reports), then
  the driver (`driver.connect_driver`, see "Driver (`android/`)"); when it fails to start,
  for any reason but a frozen MuMu, a warning, `am force-stop` of the driver (it would hold
  UiAutomation) and `uiautomator2.connect` (imported lazily so tests do not need it).
  `--driver instrumentation|uiautomator2` asks for one only (`auto` by default; not a
  config field, so an older runner reads a newer config). The device's `driver` names the
  one used (log line, `device_ready` event), and the CLI calls its `close()` after the run
  (not after a freeze): the driver stops, uiautomator2's server stays. `runner.QuickTap` wraps
  the device: `click(x, y)` sends `touch.down(x, y).up(x, y)` instead of uiautomator2's
  `click`, which holds the touch about 100 ms; every other attribute passes through. The
  connection and every call on the device it returns (`watchdog.GuardedDevice`, around
  `QuickTap`, so a tap's two events are one limited call) run on one daemon worker
  thread (`watchdog.Watchdog`, about 0.04 ms per call) and end with
  `DeviceNotRespondingError` (a `DeviceError`) after `COMMAND_TIMEOUT` (60 s); later calls
  then fail at once. `run_booking` reports the round as failed and re-raises, so no later
  round runs; the CLI logs it, records the run, releases the lock and then exits with
  `end_process` (`os._exit`, code 3), since the exit hook of uiautomator2 could wait for
  the stuck thread.
- `runner.run_booking`: `Booker.prepare()` (ends on the home screen),
  `wait_until(start - warm_up_seconds)`, `Booker.locate_entry()` (taps "Tiện ích", loads
  the utilities list; a failure is logged and retried by the next call),
  `wait_until(start - LOCATE_AHEAD)`, `locate_entry()` again (read only),
  `wait_until(start)`, then one round per slot; a `BookingError` (or any exception) fails
  that round only, except `DeviceNotRespondingError`, which ends the run after it. Results are appended to a caller-owned list; the debug log counts
  device commands per round. When a round, `prepare()` or `locate_entry()` fails,
  `log_last_screen` writes `Booker.last_screen` to the debug log, so a failure seen once at
  06:00 can be fixed from the log alone.

## Engine: the booking flow

- `screen.Screen` parses one `dump_hierarchy` into `Node`s (label, visible bounds,
  clickable); `screen.Match` (desc / prefix / contains / full-match pattern / clickable) is
  applied locally. `Screen.describe()` gives one log line per labelled or clickable node
  (bounds, label).
- `flow.Booker` builds `Match`es from `config.labels` in `__init__`. The device is only used
  through `snapshot()` (one dump), `tap()`/`tap_point()` (`device.click(x, y)`),
  `press_back()` and `_scroll()`; each increments `commands` and logs itself at debug level
  (taps with the element's label and position). `snapshot()` logs a screen that differs
  from the previous read as one record (`log_screen`), so the debug log and the history's
  log lines hold every screen a run went through (about 400 lines for one slot, no extra
  device commands).
- `wait_for(find, timeout, screen=None)` reads the screen every 20 ms until a finder returns
  something; the found node carries the coordinates to tap. Every transition goes through
  `tap_and_advance(screen, target, name, find_next)`: tap `target` from `screen`, wait for
  `find_next`, re-tap while `target` is still shown. The court goes through
  `select_court(screen)` instead: the court list can move under the tap (field notes), so
  the booking details page must name the configured court (`opened_court`); another court
  is left with `go_back()` and the court tapped again where the list shows it, and a list
  still shown 0.6 s after the tap with the court moved (`_MOVED_COURT_WAIT`) gets the tap
  again at once. Five taps in all, then `NavigationError`.
- `Booker.prepare()` first turns off Android animations (`ANIMATION_SCALES` set to 0 in one
  `shell` command, as Accessibility > Remove animations; a failure is logged and ignored),
  then restarts the app and ends on the home screen (`return_to_home()`, never Back on
  home: that leaves the app).
- `locate_entry()` opens the utilities list, then reads it again just before the start, so
  the first command at the start is the tap. `return_to_utilities()` presses Back until the
  utilities list or home appears (home: taps "Tiện ích") and returns that screen;
  `return_to_home()` likewise stops on home. Each Back goes through `go_back()`, which
  returns as soon as the next screen shows: the destination, or a screen with controls
  (clickable elements smaller than the screen) that lacks a control of the one left. The
  status bar's labels and a screen that only gains controls do not count, nor does the
  frame without controls read while a screen is built; nothing new in 2 s presses Back
  again.
  `open_slot()` re-enters the calendar while the date or slot is missing.
- `accept_and_confirm` reads the screen after "Xác nhận" until the ticket's title (booked)
  or a notice dialog (`BookingRejectedError` with the message, `Booker.notice_text`) shows;
  frames without either, such as the empty one while the next screen is built, are read
  again. Neither within `timeout` fails the round with `BookingUnconfirmedError`
  ("Outcome unknown ... check the app").
- `book()` returns a `Booked`, read from screens the round reads anyway (no extra
  command): `read_confirmation` takes the date, slot and court from the confirmation page
  (`Screen.line_after` the `booked_time` and `booked_place` captions) and only warns when
  they differ from the target, the round still confirms; `read_ticket` notes the ticket's
  status in the read that showed the ticket, if it shows already.
- `clock.ntp_offset` asks the configured `ntp_server`, then `NTP_FALLBACKS`
  (time.google.com, time.windows.com, pool.ntp.org), twice each with a 1 s timeout, and
  takes the first valid reply (a server's, stratum 1-15); with none it logs a warning and
  the run uses the PC clock.
- `geometry.py`, `screen.py` and most of `clock.py` are pure; logic testable without a
  device belongs there.

## Events and history

- `events.py`: progress events beside the log lines (spec part 2). `EventKind` values are
  stable strings (database values and message keys); `Reporter` stamps the time and hands an
  `Event` to a sink, swallowing sink errors so reporting never costs a booking. Sinks:
  `LogSink` (one debug line `Event <kind> key=value ...`), `MemorySink` (tests),
  `MultiSink`, `NullSink`. The CLI emits `run_started` (trigger `scheduled`/`dry_run`/
  `manual`), `device_ready` and `run_finished` (status `ok`/`partial`/`failed`/
  `interrupted`) on every path; `run_booking` emits `app_ready`, `waiting`,
  `booking_started`, `slot_started`, `slot_booked`/`slot_failed` (`slot_booked` adds the
  `Booked` details found: `shown_date`, `shown_slot`, `shown_court`, `ticket_status`);
  `Booker` emits `calendar_opened`, `date_selected`, `slot_selected`,
  `court_selected`, `terms_accepted`.
  Reporting sends no device command.
- `history.py`: the history database `booker.db` in the data folder (spec part 4; stdlib
  `sqlite3`, `MIGRATIONS` counted in `PRAGMA user_version`, WAL, 0.5 s busy timeout).
  `History` is an event sink: `run_started` inserts a `runs` row (`running`),
  `booking_started` adds the play date and court, `slot_booked`/`slot_failed` insert
  `run_slots`, `run_finished` sets the status; every event is also an `events` row
  (category `step`, `slot` or `error`, kind, JSON data). `History.handler` copies log
  records into `log_lines`, holding lines logged before `run_started` until the run exists.
  The first `sqlite3.Error` turns history off for the process (logged once), so the
  database never costs a booking. The CLI opens it after the log file (`open_history`) and
  closes it last; `History: N writes in X ms` is logged on close (about 0.13 ms per write).
- `history_read.py` reads the history for the app through `open_read_only` (`mode=ro` URI,
  `check_same_thread=False`, creates an empty database first): `list_runs` (newest first,
  `booked`/`total` slot counts, `month` on the play date, `trigger`, `before` id paging),
  `get_run` (slots, steps with parsed JSON `data`, log lines), `list_events` (newest first,
  `category`, `before`), `events_after` (the live feed), `dry_run_passed` and
  `last_setup`.

## Configuration and data folder

- `config.load_config` rejects unknown keys (`ConfigError`); the TOML key `continue` maps
  to `Labels.continue_`; keys ending in `_xy` become tuples. New config fields must be added
  to the dataclass and `config.example.toml`. A relative `log_dir` resolves against the
  config file. Loading does not validate, so an existing config never stops the 06:00 run.
- `config_from_dict` builds a config from parsed TOML; `validate_config` lists problems
  (slot format and duplicates, empty court, `days_ahead` 0-2, `wake_at` before `start_at`,
  positive timeouts, `_xy` ratios); `save_config` validates, then writes with `tomli-w`
  through a temporary file and `os.replace` (comments are not kept), with only the labels
  that differ from the defaults (an older runner refuses a label it does not know);
  `ensure_config` writes the defaults once.
- `paths.data_folder()`: the app's data folder, `%LOCALAPPDATA%\CourtBooker` (override with
  `COURT_BOOKER_HOME`), holding `config.toml`, `booker.db`, `logs/` and `run.lock`. The CLI
  writes only `booker.db` there; its config and logs stay beside `--config` until the app.

## Device setup

`device_setup.py` (spec part 6, the "Thiết lập máy" tab): `run_checks` returns one `Check`
(item, `Status`, detail) per item:

- `mumu_installed`: config path, uninstall registry (key `MuMuPlayerGlobal`), usual
  folders.
- `mumu_screen`: `MuMu.settings`, readable while MuMu is off.
- `wake_timers`: `powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE`, AC and DC hex values
  read by position.
- `app_installed`: `adb shell pm path`, `unknown` while MuMu is off.

Statuses are `ok`, `fixed`, `fixable`, `user` (install or log in by hand) and `unknown`;
item keys and statuses are stable message keys. `auto_setup` fixes `fixable` items: saves
the MuMu path (`save_config`, drops comments), writes `SCREEN_SETTINGS` (a running MuMu
only with `restart_mumu`, then `control restart`), enables wake timers
(`powercfg /set...valueindex`, `/setactive`). Being logged in is shown by the dry run
(exit 4), not checked here.

`run_auto_setup` is auto setup as one task: quiet time, run lock (trigger `setup`), and
`setup_started`, one `setup_item` per item and `setup_finished` as history events of
category `setup` without a run. `court-booker setup` prints the checks; `--auto` and
`POST /api/setup/auto` both call `run_auto_setup`.

## Backend (`court_booker.api`)

- `create_app(AppContext)` builds the backend (needs the `app` extra: FastAPI, Uvicorn,
  websockets); `AppContext` holds the config path and the `DataFolder`, and routes receive
  it as a `Context` parameter (`Annotated` with `Depends(get_context)`).
  `court-booker serve` (`api/server.py`) listens on 127.0.0.1 only (no login yet), default
  port 8765, config from `--config` or the data folder (created with defaults). `cli.serve`
  imports the backend lazily, so a run never loads FastAPI. OpenAPI at `/api/openapi.json`,
  docs at `/api/docs`.
- Route modules skip `from __future__ import annotations` and use `Optional`: FastAPI and
  Pydantic evaluate annotations at run time, where Python 3.9 has no `X | None`.
- Errors: `CourtBookerError`s become `Problem` JSON (`error` code, `detail`):
  `LockHeldError` 409 `lock_held`, `RequestError` 400 `bad_request`, `DeviceError` 503
  `device`, `AppNotReadyError` 503 `app_not_ready`, others 500 `engine`. Invalid request
  values answer 422 `invalid_request` with `problems` (one line per value). Every router
  lists `422` and `default` responses as `Problem` (`api.app.ERROR_RESPONSES`).
- The backend opens the history with `open_store` (no log capture: its log lines would mix
  requests). `api/activity.record` writes app events (no run) to the history; a database
  error is only logged.

| Route | Module | Behaviour |
|---|---|---|
| `GET /api/status` | `status.py` | The Overview in one call (model `Overview`): `version`, `running` (lock holder, or the dry run the backend just started), `schedule`, `last_run`, `setup` (`last_setup`: time and items left by the last auto setup; empty until it ran). Never calls MuMu |
| `GET /api/runs`, `GET /api/runs/{id}` | `history.py` | Runs newest first, each with its `slots` (read for the whole page in one query; `month`, `trigger`, `dry_run` from the run's flag, not its trigger, `before`, `days`: every run of the newest 1-60 days that have runs, by start day, `limit`); one run with slots, steps and log lines (404 `not_found` via `api.errors.NotFoundError`) |
| `GET /api/runs/months` | `history.py` | Months of real bookings by play date, newest first, with `runs` and `booked` slots; declared before `/runs/{run_id}`, which would take "months" for an id |
| `GET /api/events` | `history.py` | Activity steps newest first (`category`, `before`, `limit`). A `Step`'s `kind` is the `EventKind` enum and its `category` the `Category` literal in the schema; a row with a kind the backend does not know fails the response, so the engine and the backend must be the same version or the backend newer |
| `GET`/`PUT /api/settings` | `settings.py` | `settings_of(config)` (TOML keys, labels with `continue`, without the `HIDDEN` Telegram keys). `PUT` takes the full `Settings` (extra keys refused), merges it, runs `validate_config` (422 `invalid_settings` with `problems`, file untouched), and only when something changed saves it (comments are lost) and records `settings_saved` with the changed keys |
| `GET /api/setup`, `POST /api/setup/auto` | `setup.py` | The checks as `SetupItem`s (item, status, detail); auto setup with `{"restart_mumu": bool}` (400 in the quiet time, 409 while a run holds the lock) |
| `GET`/`PUT /api/schedule` | `schedule.py` | `enabled` (`schedule.installed`), wake and start time, `next_start`, `next_play_date`, `dry_run_passed`. `PUT {"enabled": bool}` installs the task again on every switch-on (needs a passed dry run: 409 `dry_run_required`; wake before start: 400) or removes it, recording `schedule_enabled` / `schedule_disabled` (category `schedule`). `ScheduleError` answers 503 `schedule` |
| `POST /api/runs/dry-run` | `runs.py` | 202 `{pid, started_at}`; starts `python -m court_booker --dry-run --config <config>` with `launch` (own process, no window, output discarded: the run writes its history and log file). 400 in the quiet time; 409 while `RunLock.running_holder()` (a peek that never clears) names a running holder or the process it started last (`app.state.dry_run`) still runs, as a fresh dry run does not hold the lock for its first milliseconds. A `threading.Lock` keeps two requests from both starting one |
| `WS /api/live` | `live.py` | Pushes each new step as `{"type": "step", "step": ...}`, reading `history_read.events_after` every `POLL_SECONDS` (0.25 s) from a cursor fixed before `accept` (the newest step, or `?after=<id>` to resume); a task awaiting `websocket.receive` ends the loop when the client closes. Uvicorn needs `websockets` to serve it; `TestClient` does not, so only a real server shows a missing one |

The schedule task runs the backend's Python, so switching it on from a development backend
would move the task away from the runner folder.

## UI (`ui/`)

- Vite 8, React 19, strict TypeScript (two projects: `tsconfig.app.json` for `src/`,
  `tsconfig.node.json` for `vite.config.ts`, which also holds the Vitest settings).
  TypeScript is held at `~6.0.3` because typescript-eslint supports below 6.1, jsdom at 29
  because jsdom 30 needs Node 22.22, and React Router at 7 (8 needs Node 22.22);
  Dependabot skips them. ESLint 10 flat config (`recommendedTypeChecked`, react-hooks,
  react-refresh, then eslint-config-prettier); Prettier at 100 columns.
- Tests sit beside the code (`*.test.tsx`) and run in jsdom with Vitest globals off, so
  `src/test/setup.ts` adds the jest-dom matchers, calls `cleanup` and resets the language
  and the storage (`localStorage`, `sessionStorage`) after each test. Helpers in `src/test/`: `stubBackend`/`reply`/
  `requestsTo`, `createTestQueryClient`/`withQueryClient`, `FakeSocket`/
  `fakeConnection`/`step`.
- `main.tsx` loads `i18n`, the styles and `createBrowserRouter(routes)`.
  `styles/fonts.css`: Fontsource Bricolage Grotesque variable with `opsz` and IBM Plex Mono
  400/500/600, offline, with Vietnamese, as `--font-sans`/`--font-mono`;
  `styles/tokens.css`: role-named tokens; `styles/base.css`: page defaults,
  `:focus-visible` ring, reduced motion, `.visually-hidden`. Styles are CSS Modules on the
  tokens. `tokens.test.ts` reads `tokens.css?raw` (Vitest `css.include` lists it, as Vitest
  blanks CSS imports) and holds text pairs to 4.5:1 and markers to 3:1; `--color-failed` is
  `#b53c0b`, darker than the mockups' `#c2410c` (4.14:1 on the ground).
- `paths.ts` names every address once (English paths); `routes.tsx` maps them to `pages/*`
  under `App` (errorElement `ErrorPage`, `*` `NotFoundPage`, `/settings` redirects to
  `/settings/booking`, `/history` to `/history/bookings` and the old `/activity` to
  `/history/activity`, the last two through `components/Redirect`, which keeps `?month=`
  and `?run=`) and is shared by the tests through `createMemoryRouter`. `App` lays
  out the skip link, `components/SiteHeader` (brand, `MainNav` with `NavLink`
  `aria-current="page"`, hidden on `/welcome` via `useMatch`, and `LanguageSwitch`) and
  `<main id="main">`. Pages set the window title with `components/PageTitle` (React 19
  hoists `<title>` above the static one of `index.html`).
- `src/i18n`: i18next with `locales/vi.json` and `en.json` (same keys, checked by
  `locales.test.ts`), Vietnamese default and fallback; `i18next.d.ts` types the keys
  against `vi.json`. The choice is stored under `court-booker.language` in `localStorage`
  (blocked storage falls back to Vietnamese) and sets `<html lang>`. `LanguageSwitch`
  buttons are named "VI Tiếng Việt" / "EN English" with `aria-label` (a hidden span lost
  the space). Language files use the same `{{placeholders}}` in both languages and no
  i18next plurals (Vietnamese has only `_other`, so the keys would differ).
- `src/format.ts`: pure formatting of backend values. `parseLocal` reads the backend's
  local times (no zone) from the text, never through `new Date(text)`, which reads a date
  alone as UTC; weekday and month names come from `Intl` on a UTC date, and Vietnamese
  day/month is built by hand (`Intl` writes "14-10"). Unreadable values are returned as
  they are. `useFormat()` binds the functions to the current language and adds the words
  of `format.*` in the language files; `Formatter` is its type.
- `src/components`: the shared pieces of the paper design, each with a CSS Module on the
  tokens and a behaviour test. `Button` (`primary`/`secondary`, `normal`/`large`, never
  submits unless `type` says so), `Switch` (`role="switch"`, state also written out),
  `PillGroup` (one choice, `aria-pressed`), `Card` and `Ticket` (`as` picks the element;
  the ticket's stub sits behind a dashed perforation with two notches, `notch="small"` for
  rows), `Stamp` (`booked`/`failed`, upright), `Ledger` (a named, focusable scroll area
  around a dotted table), `Overline` (capitals set by CSS, so the language files stay in
  normal case), `PageHeader` (h1, lead, controls, window title), and `Loading`,
  `ErrorNotice`, `EmptyState`. `QueryView` shows a read's data first, so data already shown
  stays when a later refresh fails, then its error with a retry, then loading.
- `src/steps.ts`: `stepMessage(t, f, step)` gives a step its words (`steps.*` in the
  language files), a `tone` (`booked`, `failed`, `moment` for the start time, `plain`), an
  `extra` (the time a slot took) and a `detail` (the engine's English reason or error,
  for the technical details). `MESSAGES` is a `Record<StepKind, ...>`, so a new kind fails
  the type check; a missing value gives a sentence without it (`.plain` keys), and an
  unknown kind at run time reads "Bước khác (kind)". Trigger, setup item and status names
  are `triggers.*` and `setup.items.*`/`setup.statuses.*`, shared with the screens.
- `src/runs.ts`: `runStamp` (the run's stamp, blue only when every slot went through; a
  dry run says "CHẠY THỬ ĐẠT"), `runResult` (✓/✕ mark for lists), `triggerName`.
  `src/days.ts`: `newestDays` keeps every item of the newest `DAYS_SHOWN` (10) days that
  have items, `playDay` (play date, else start day) and `runDay` (start day).
- Screens (`src/pages`): `HistoryPage` and `SettingsPage` are `components/TabbedPage`s:
  the title and the tabs as `NavLink`s (`aria-current`) above the `Outlet`; the window
  keeps the screen's name. `ActivityPage` (second tab of History, `/history/activity`)
  lists the runs of the newest ten days beside `RunDetail` (header, stamp, step lines from
  `stepMessage`, `<details>` technical log). `useRunDays` is a `useInfiniteQuery` over
  `GET /api/runs?days=10&limit=500` (`select` flattens the pages); "Xem thêm" reads the
  ten days before (`before=` the last run), and a page with fewer days (`nextRunDays`)
  ends the list. A `?run=` older than the pages read still shows, unmarked in the list. Tests render the whole app with
  `test/app.tsx` `renderApp(path, replies)`: test cache, live feed on fake sockets and
  `stubBackend`.
- `BookingsPage` (first tab of History, `/history/bookings`) shows the real bookings of
  one month (`?month=`, else the newest from `useRunMonths`), read in one request
  (`limit=200`), as small `Ticket`s with `runStamp`: those of the newest ten days of play,
  and ten days more per "Xem thêm" without a request; another month starts again.
- `OverviewPage` reads three things: `/api/status` (`StatusLine`: no setup, setup items
  left, schedule off, or ready; `NextBooking` ticket), the settings (court and slots on
  the stub) and the newest real run (`LastBooking`, hidden before one). `useFormat().when`
  says "sáng mai"; `reasons.ts` `failureReason` turns the engine's known English reasons
  into a few words and points to the activity log for the rest.
- While `running` names a booking or a dry run, `OverviewPage` shows `RunningBanner` and
  `LiveRun` instead: the run holding the lock is the newest run if it started after the
  lock's `since` (it may have just ended), else "Đang chuẩn bị". `progress.ts`
  `progressOf(steps)` reads the slots, the current one, each slot's state and the progress
  from the steps alone. `useOverview` polls every 2 s (`settlingInterval`) only while a run
  holds the lock without a running row, or during auto setup: a run gives the lock back
  after its last step, and no step marks that moment.
- `SettingsPage` holds "Đặt sân" and "Thiết lập máy" as tabs. `booking.ts` keeps the choices the
  developer maintains with the Vinhomes app: `SLOTS` (13), `COURTS` (S6, S8, S9, S10),
  `DAYS_AHEAD`; `slotChoices` and `courtChoices` also offer a value the config holds outside
  them, and `toggleSlot` appends, so the list order is the booking order.
  `BookingSettingsPage` edits only `slots`, `court` and `days_ahead` on a draft and saves
  them merged into the settings it read (`useSaveSettings`), so the developer's fields go
  back unchanged; the form is keyed on the saved choice, so a save or another change
  starts the draft again from it.
- `DeviceSetupPage` reads the Overview and `useSetupChecks(enabled)`, enabled only once the
  Overview says no run holds the lock (the checks ask MuMu and adb). `setup/ManualSteps`
  derives the three user steps: MuMu and the app from the checks (`fixable` MuMu counts as
  installed), the login from the runs (`reasons.ts` `isLoggedOut` on the last run's error,
  else `dry_run_passed`); the backend's English `detail` is never shown. `setup/AutoSetup`
  is a `Ticket`: the auto items and their status, the button, and the restart question,
  shown when a run without `restart_mumu` leaves `mumu_screen` fixable. `quiet.ts`
  `quietEnd` (start + 5 min, `format.ts` `addMinutes`) gives the end of the quiet time.
- `SchedulePage` reads the Overview (the lock and the times). `schedule/DryRunStep` starts a
  dry run (`useStartDryRun`) and reads the newest dry run (`dry_run=true`, `limit=1`); it
  follows nothing itself and links to the Overview while a run goes on.
  `schedule/ScheduleStep` reads `useSchedule` and switches it (`useSwitchSchedule`, which
  writes the answer to the cache); the switch is off until `dry_run_passed`. A run's
  `run_finished` step also marks the schedule stale, for `dry_run_passed`. Tests stand in
  for the backend: a real `PUT /api/schedule` rewrites the Windows task, so it is never
  sent from a development backend.
- `GuidePage` is static and sends no request: the four start steps (`Link` cards), the
  screens as a `dl` and the problems as `<details>`. The labels it quotes (buttons, tabs,
  reasons, "Cài đặt › Đặt sân") are passed in from the screens' own keys, so a renamed
  label changes the guide too. `components/ButtonLink` is a `Link` with the `Button`
  classes, for moves to another screen.
- `welcome.ts` `isFirstOpen(overview)` (no dry run passed, schedule off, no run holding the
  lock) is read from `/api/status`, never from a stored flag. `OverviewPage` then renders
  `<Navigate to="/welcome" replace>` unless `welcomeShown()`: `WelcomePage` sets
  `court-booker.welcomed` in `sessionStorage` when it mounts, so the redirect happens once
  per opening, and storage that cannot be read counts as shown (no loop back).
- `WelcomePage` keeps the step in `?step=1..4` (`welcome/steps.ts`, anything else is 1).
  `welcome/StepBar` links every step (`aria-current="step"`) and moves focus to the new one
  when the step changes, which scrolls the page back up. Step 1 is `welcome/Intro` (times
  from the Overview's schedule); steps 2 to 4 render `DeviceSetupPage`,
  `BookingSettingsPage` and `schedule/ScheduleSteps` (also the body of `SchedulePage`)
  under their own `h1`; the window title stays "Chào mừng". `BookingSettingsPage`'s
  `onUnsavedChange` reports a draft not saved (and `false` when the form goes away), and
  the step's "Tiếp" becomes a disabled button with a note while it is.

### Backend connection (`ui/src/api`)

- `openapi.json` is written by `tools/export_openapi.py` from
  `court_booker.api.schema.openapi_json` (no server needed); `tests/api/test_api_schema.py`
  fails while it differs (skipped on Python 3.9, which gets FastAPI 0.128 and words the
  schema differently). The `/api/status` model is `Overview` (it clashed with
  `device_setup.Status`, the setup status enum, named `Status` in the schema).
- `schema.d.ts` comes from openapi-typescript 7 (peer TypeScript 5; an npm override lets it
  use TS 6) and is ignored by ESLint and Prettier; CI regenerates it and fails on a diff.
  `types.ts` names the schema types (`SetupStatus` is the enum); `types.test.ts` pins
  shapes with `expectTypeOf` (run by the type check).
- `client.ts`: openapi-fetch on the page's origin, `fetch` looked up per call (tests stub
  it); `call` turns failures into `ApiError` (`code`: the Problem's, `unreachable` for no
  answer or a proxy 5xx without a Problem, `http` otherwise). `endpoints.ts`: one function
  per route with its schema return type (the settings are cast: openapi-fetch widens the
  `[x, y]` tuples to `number[]`). `errors.ts`: `ERROR_CODES` and `errorMessage(t, error)`
  from `errors.*` in the locales.
- `queryClient.ts` retries reads only while `unreachable` (3 times), never mutations, and
  keeps reads fresh for `FRESH_MS` (30 s): invalidation still refetches at once;
  `queries.ts` (`queryKeys`, one hook per read) and `mutations.ts` (save settings, auto
  setup, switch schedule, start dry run; each sets its answer in the cache and invalidates
  what it changes).
- `live.ts` `connectLiveFeed`: checks messages (`stepOf`), drops repeats, reconnects after
  0.5/1/2/5 s with `?after=<last id>`, gives up a socket not open after 5 s at once (Vite's
  proxy with no backend never opens or closes it; Node's WebSocket sends no close for a
  connecting socket it closes). `LiveProvider` (in `main.tsx`) keeps one connection, the
  last 200 steps (`useLiveFeed`) and invalidates `staleKeysFor(step)`.
- `staleKeysFor` refreshes backend data only at run boundaries (`run_started`,
  `slot_booked`, `slot_failed`, `run_finished`; the run itself at `run_finished`) and for
  app events; a run's other steps send no request. `runSteps.ts` `useRunSteps(runId)`
  joins a run's stored steps with the live ones after the last stored id.

## Driver (`android/`)

An instrumentation in its own APK (`dev.courtbooker.driver`, Java, the usual Gradle layout
under `android/app/src/main`, no activity, service or permission), started with
`am instrument -w dev.courtbooker.driver/.Driver`. It gets Android's UiAutomation, the
connection uiautomator2 uses (`FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES`: enabled services
stay visible to apps); it is not an accessibility service, which the app refuses (field
notes, "Instrumentation driver"). Only one UiAutomation runs at a time, so a run uses the
driver or uiautomator2, never both.

`tools/build_driver.py` builds it with the SDK tools alone (aapt2, javac, d8, zipalign,
apksigner) into `src/court_booker/assets/court-driver.apk`, which is committed and shipped
as package data: a machine that only runs bookings needs no SDK. `court-driver.json` next
to it holds the SHA-256 of the sources, also the APK's version name (first 12 characters);
`tests/test_build_driver.py` fails when the sources change and the APK is not built again.
The version code stays 1. CI's `driver` job builds it (`--check`, into `android/build`).

`driver.py` is the PC side. `connect_driver` (inside the watchdog's `connect` call):
`ensure_installed` compares the SHA-256 of the installed `base.apk` (`pm path`,
`sha256sum`) with the packaged APK and runs `adb install -r` when they differ or it is
missing (a driver signed with another key is uninstalled first); `Adb.forward` forwards a
local port (reusing one already set) and `hello` is sent; a forward with no driver behind
it closes the connection at once. No answer: `start_driver` ends a uiautomator2 server
(`pkill -f 'com.wetest.uia2.Mai[n]'`) and starts
`setsid nohup am instrument -w ... > /data/local/tmp/court-driver.log 2>&1 &` (the `am`
process holds the UiAutomation connection, so it must outlive the adb shell), then `hello`
is retried for `START_TIMEOUT` (10 s; it answers 1-1.5 s after a start, the first install
takes about 4 s). No answer then stops it and raises `DriverUnavailableError`, like a
missing APK, a failed install or another protocol. `DriverDevice` offers the flow's device
calls: `dump_hierarchy`, `click(x, y, label)` (`click` by label; no label: `click_at`),
`press("back")`, `swipe`, `app_current` (`current`), `close` (`stop`, then `am force-stop`
and the forward removed), and `shell`, `app_start` (`monkey` with the launcher category),
`app_stop` (`am force-stop`) through adb. `DriverClient` sends one command at a time with
its own `id`; a refusal or a closed connection raises `DriverError`, no answer within
`COMMAND_TIMEOUT` (10 s) `DeviceNotRespondingError`, and a broken connection fails every
later command. The driver logs on the watchdog's thread, so `history.connect` allows that
thread and `History` writes under a lock.

- `Driver` (`Instrumentation`) listens on the abstract socket `court-driver`; the PC
  reaches it with `adb forward tcp:<port> localabstract:court-driver`. A new connection
  closes the one before, so a run that died cannot block the next. `stop` closes the socket
  and ends the instrumentation.
- An element is clicked by its label in the tree of the moment, with
  `AccessibilityNodeInfo.ACTION_CLICK`: no position comes from the PC, so a list that moved
  since the PC read it cannot send the click to another element. A node that is not
  clickable, or refuses the action, is touched at its middle where it is now (an injected
  touch down and up, `injectInputEvent`).
- `Tree` reads the active window as the uiautomator2 dump does: only nodes visible to the
  user, bounds clipped to the screen (the status bar, another window, is left out).

Protocol 1: one JSON object per line each way. A command has `op`, its arguments and an
optional `id`; the reply repeats `id` and has `ok`, plus `error` when `ok` is false (an
unknown `op`, a missing argument, a line that is not JSON).

| `op` | Arguments | Reply |
|---|---|---|
| `hello` | | `protocol` (1), `version` (the APK's), `sdk` |
| `dump` | | `xml` (`<hierarchy>` of `<node>` with `text`, `class`, `content-desc`, `clickable`, `enabled`, `bounds`; `<hierarchy/>` without a window) |
| `click` | `label`, `x`, `y` | `clicked`, `how` (`action` or `touch`), `bounds`: the visible node labelled exactly `label` that holds (x, y), else the nearest, clicked where it is now; `clicked` false when no node has the label |
| `click_at` | `x`, `y` | The same for the smallest visible clickable node holding (x, y), for elements without a label (the consent checkbox) |
| `back` | | Once a Back key down and up were injected |
| `swipe` | `x1`, `y1`, `x2`, `y2`, `ms` | Once the injected touch has moved there in `ms` (5 ms steps) and lifted |
| `current` | | `package` of the active window |
| `stop` | | Before the driver ends |

## Tests

- External effects are injectable (`run`, `probe`, `clock`, `sleep`, `post`, `set_state`),
  so nothing in the test suite touches a device, adb, the network or Task Scheduler.
- `tests/test_flow.py` has hand-written fakes: `FakeApp`, a scripted app that serves
  hierarchy XML per screen and switches screens on taps and Back, and `OpeningBooker`; a
  fake `flow.time` clock makes timeouts pass instantly. A full round must cost 16 commands.
- `tests/conftest.py` puts `src/` on `sys.path` and points `COURT_BOOKER_HOME` at a
  temporary folder for every test (fixture `data_home`), so tests never write the real
  history. Its `record_run` fixture writes runs through the history sink.
- Backend tests live in `tests/api/` and are skipped without FastAPI.
