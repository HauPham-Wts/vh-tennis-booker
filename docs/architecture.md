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
  launch`), `adb.find_adb` + `adb.resolve_device` (prefers the serial MuMu reports),
  `uiautomator2.connect` (imported lazily so tests do not need it).
- `runner.run_booking`: `Booker.prepare()` (ends on the home screen),
  `wait_until(start - warm_up_seconds)`, `Booker.locate_entry()` (taps "Tiện ích", loads
  the utilities list; a failure is logged and retried by the next call),
  `wait_until(start - LOCATE_AHEAD)`, `locate_entry()` again (read only),
  `wait_until(start)`, then one round per slot; a `BookingError` (or any exception) fails
  that round only. Results are appended to a caller-owned list; the debug log counts
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
  `find_next`, re-tap while `target` is still shown.
- `Booker.prepare()` first turns off Android animations (`ANIMATION_SCALES` set to 0 in one
  `shell` command, as Accessibility > Remove animations; a failure is logged and ignored),
  then restarts the app and ends on the home screen (`return_to_home()`, never Back on
  home: that leaves the app).
- `locate_entry()` opens the utilities list, then reads it again just before the start, so
  the first command at the start is the tap. `return_to_utilities()` presses Back until the
  utilities list or home appears (home: taps "Tiện ích") and returns that screen.
  `open_slot()` re-enters the calendar while the date or slot is missing.
- `accept_and_confirm` fails a round whose confirmation is answered by a notice dialog
  (`BookingRejectedError` with the message, `Booker.notice_text`).
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
  `booking_started`, `slot_started`, `slot_booked`/`slot_failed`; `Booker` emits
  `calendar_opened`, `date_selected`, `slot_selected`, `court_selected`, `terms_accepted`.
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
  through a temporary file and `os.replace` (comments are not kept); `ensure_config` writes
  the defaults once.
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
| `GET /api/runs`, `GET /api/runs/{id}` | `history.py` | Runs newest first (`month`, `trigger`, `before`, `limit`); one run with slots, steps and log lines (404 `not_found` via `api.errors.NotFoundError`) |
| `GET /api/events` | `history.py` | Activity steps newest first (`category`, `before`, `limit`) |
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
  and `localStorage` after each test. Helpers in `src/test/`: `stubBackend`/`reply`/
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
  `/settings/booking`) and is shared by the tests through `createMemoryRouter`. `App` lays
  out the skip link, `components/SiteHeader` (brand, `MainNav` with `NavLink`
  `aria-current="page"`, hidden on `/welcome` via `useMatch`, and `LanguageSwitch`) and
  `<main id="main">`. Pages set the window title with `components/PageTitle` (React 19
  hoists `<title>` above the static one of `index.html`).
- `src/i18n`: i18next with `locales/vi.json` and `en.json` (same keys, checked by
  `locales.test.ts`), Vietnamese default and fallback; `i18next.d.ts` types the keys
  against `vi.json`. The choice is stored under `court-booker.language` in `localStorage`
  (blocked storage falls back to Vietnamese) and sets `<html lang>`. `LanguageSwitch`
  buttons are named "VI Tiếng Việt" / "EN English" with `aria-label` (a hidden span lost
  the space).

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
- `queryClient.ts` retries reads only while `unreachable` (3 times), never mutations;
  `queries.ts` (`queryKeys`, one hook per read) and `mutations.ts` (save settings, auto
  setup, switch schedule, start dry run; each sets its answer in the cache and invalidates
  what it changes).
- `live.ts` `connectLiveFeed`: checks messages (`stepOf`), drops repeats, reconnects after
  0.5/1/2/5 s with `?after=<last id>`, gives up a socket not open after 5 s at once (Vite's
  proxy with no backend never opens or closes it; Node's WebSocket sends no close for a
  connecting socket it closes). `LiveProvider` (in `main.tsx`) keeps one connection, the
  last 200 steps (`useLiveFeed`) and invalidates `staleKeysFor(step)`.

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
