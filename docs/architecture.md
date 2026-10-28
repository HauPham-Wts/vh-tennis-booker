# Architecture

Three parts: the **engine** (`python -m court_booker`) books a court in a run of its own; the
**backend** (`court_booker.api`, FastAPI) serves the app's screens; the **UI** (`ui/`, React)
is those screens. The 06:00 task runs the engine alone. How the flow reads the app:
[how-it-works.md](how-it-works.md); facts about the app and MuMu: [field-notes.md](field-notes.md);
the desktop app's design and the packaging still to do: [specs/0.5.0-desktop-app.md](specs/0.5.0-desktop-app.md).
Details live in the docstrings; this page says where things are and what must stay true.

## Engine: one run

- `cli.py` parses the arguments (`schedule ...` goes to `schedule.main`), applies them onto
  `Config`, adds the log file, measures the clock, and inside `power.keep_awake()` takes the run
  lock, connects the device and runs the rounds. Errors map to exit codes (`RequestError` 2,
  `DeviceError` 3, `AppNotReadyError` 4, `LockHeldError` 5, Ctrl+C 130; a failed round 1). On
  every path it logs the summary, records the run, sends the optional Telegram summary and the
  Windows notification (`notify.py`; a failure only logs a warning). After a real run with at
  least one round, `close_emulator` shuts MuMu down.
- Other MuMu instances (`[[instances]]` in the config, each with its own account and its own
  `mumu_index`, `slots`, `subdivision`, `sport`, `court`, `venue_keyword`;
  `config.instance_config`):
  the run's process, once it holds the lock and has cleared stale runs, starts one process per
  entry (`start_instances`: the same command with `--instance N`, without `--slots`,
  `--device`; console output dropped) and waits for them, holding its lock. Each such process
  is a whole run of its own with its instance's settings: its lock `run-mumu<N>.lock`, its log file
  `court-booker-<date>-mumu<N>.log`, its history run, its notification titled "MuMu N · …"
  (the first instance's too, as "MuMu 0"); it never clears stale runs. So an instance that
  fails or freezes holds up no other. Several instances need `mumu_manager` and
  `device = "auto"`; otherwise, or for an entry repeating an instance, the run books with its
  own instance alone (warning). Each run's `run_started` names its instance as `device`.
- `lock.py` + `processes.py`: the run lock `run.lock` in the data folder (pid and process start
  time, so a reused pid is never taken for the holder). A scheduled run takes over a holder
  2 minutes before the start; a stale lock is cleared. The quiet time refuses a dry run or auto
  setup from `wake_at` to start + 5 min.
- `runner.connect_device`: start MuMu (`emulator.py`, MuMuManager), find adb and the serial
  (`adb.py`), then the instrumentation driver (`driver.py`), falling back to uiautomator2 when
  it does not start (not after a freeze). `--driver` picks one. Every device call runs on one
  worker thread (`watchdog.py`) and fails with `DeviceNotRespondingError` after 60 s; the run
  then ends (exit 3, through `os._exit`, as a stuck thread could hold the exit).
- `runner.run_booking`: `prepare()` (animations and notification banners off in one shell
  command, app restarted, home screen), wait until
  `start - warm_up_seconds`, measure the clock again, open the utilities list (`locate_entry`),
  read it again 2 s before the start, wait until start + 0.1 s, then one round per slot.
  A `BookingError` fails its round only, except: `DeviceNotRespondingError` ends the run after
  its round, and `QuotaFullError` leaves the rounds left unrun ("Skipped: the booking quota is
  used up", no device command). A failure logs the last screen read (`log_last_screen`).
- `clock.py`: NTP (the configured server, then fallbacks; the answer with the shortest round
  trip) anchored on `time.perf_counter()`, so Windows setting the PC clock during the wait
  changes nothing. Without an answer it is the PC clock, with a warning.

## Engine: the booking flow (`flow.Booker`)

- `screen.Screen` is one `dump_hierarchy` parsed into `Node`s (label, visible bounds,
  clickable); `screen.Match` finds nodes locally. One read per screen state, no element queries.
- The device is used only through `snapshot()`, `tap()`/`tap_point()` (label and point),
  `press_back()` and `_scroll()`, each counted in `commands`. A full round costs 16 commands
  (tests hold it). A screen that differs from the last read is logged at debug level, so the
  log holds every screen of a run.
- Labels come from `app_language.app_languages(config.labels, config.sport)`: Vietnamese from
  `[labels]`, English built in; the utility tapped is the tile of `sport` (`config.SPORTS`,
  `app_language.ENGLISH_SPORTS`) unless `[labels] utility` names one. `prepare()` finds the
  language on the first screen and uses it; a language without a tile for the sport stops the
  run there.
- `prepare()` then tells the account's subdivision (`read_account`) from the apartment code
  on the home screen it read anyway ("BS…" → `bs`, "S…" → `origami`; 0 commands). Only the
  subdivision is logged and reported (`account_subdivision`), never the code (personal data).
  A court the catalog lists in another subdivision is a warning in the log and the Windows
  notification (`cli.AccountSink`), not an error: the guess may be wrong. Any failure there
  only logs.
- Every transition is `tap_and_advance(screen, target, name, find_next)`: tap, then read until
  `find_next` finds the next screen, up to `timeout` (30 s). The tap is repeated every 2 s
  while `target` still shows (a swallowed tap), never while the app loads (target gone).
  Closed loop everywhere: act on what the read shows, never on a fixed delay alone.
- Round: `open_slot` (utility → calendar; a notice in its place, such as the closed-hours one,
  is closed and the utility tapped again until `open_retry_seconds`; a date or slot not listed
  yet reloads the calendar) → `select_date` → `select_slot` (tapped once "Tiếp tục" shows
  enabled) → "Tiếp tục" → `_after_calendar` (court list, the venue page, the booking details
  page of a utility with a single court, or a notice, which fails the round at once) →
  `select_court` (or `check_single_court` when a page with one choice passed on to the
  details page by itself: it must name the configured court)
  → "Tiếp tục" → confirmation page → `accept_and_confirm`.
- Venue page (`_venue_entry`): a single venue is tapped whatever its name; of several, the one
  `catalog.py` lists the court under (its name before the line break), else the one naming
  `venue_keyword` (a court typed by hand). A full venue ("Hết chỗ") fails the round at once.
- `catalog.py`: the subdivisions (`origami`, `bs`), their sports in the app's order, venues and
  courts (app name; block, kind and number for the UI's label, the kind one of
  `COURT_KINDS`), from the field notes. The run needs no subdivision: the
  court names its venue. The `subdivision` setting (empty: the account's) only checks the
  settings (`validate_config`: a known subdivision that has the sport).
- A court cut off by the bottom edge is tapped without a swipe: it is in the tree, and the
  driver clicks it by its label (seven basketball courts).
- `select_court`: the court list can move under the tap (field notes), so the booking details
  page must name the configured court; another court is left with Back and tapped again.
- `accept_and_confirm`: tick, then "Xác nhận" at least 0.2 s later. Booked only once the
  ticket's title shows; a notice fails the round (`BookingRejectedError`, `QuotaFullError` when
  it holds the `quota_full` label). "Xác nhận" is tapped again every 3 s while the page still
  shows it enabled; a notice after such a second tap, or nothing within `timeout`, is
  "Outcome unknown" (`BookingUnconfirmedError`). A dry run stops before "Xác nhận".
- Navigation back (`return_to_utilities`, `return_to_home`, `go_back`) presses the next Back as
  soon as the screen before shows; Back is never pressed on the home screen (it leaves the app).
- `book()` returns `Booked`: date, slot and court read on the confirmation page (a difference is
  a warning only) and the ticket's status, from reads the round makes anyway.
- Pure modules (testable without a device): `geometry.py`, `screen.py`, `app_language.py`,
  `catalog.py`,
  most of `clock.py`.

## Events and history

- `events.py`: progress events beside the log lines. `EventKind` values are stable strings
  (database values, UI message keys). `Reporter` swallows sink errors: reporting never costs a
  booking. The CLI emits `run_started`, `device_ready`, `run_finished`; `run_booking` the run's
  steps and `slot_booked`/`slot_failed`; `Booker` the steps of a round.
- `history.py`: `booker.db` (SQLite, WAL, migrations by `PRAGMA user_version`) as an event sink:
  `runs` (with the MuMu instance as `device`, from schema 2; empty for older runs; `court` is
  the configured court until a slot is booked, then the court the app booked), `run_slots`,
  `events`, and the run's log lines. The first database error turns history off for the process.
  Schema changes only add columns, so an older runner still writes to a newer database.
- `history_read.py`: read-only queries for the backend (runs, one run, events, the live feed's
  `events_after`, `dry_run_passed`, `last_setup`, `account_subdivisions`: the subdivision each
  MuMu instance last told); it migrates an older database first.

## Configuration and data folder

- `config.py`: `load_config` refuses unknown keys but never validates, so an existing config
  never stops the 06:00 run. `validate_config` runs before every save. `save_config` writes
  atomically, without comments, with only the labels that differ from the defaults and the keys
  of `_WRITTEN_WHEN_CHANGED` (and an instance's `sport`) only when changed: an older runner
  refuses keys it does not know.
  New fields go into the dataclass and `config.example.toml`.
- `paths.data_folder()`: `%LOCALAPPDATA%\CourtBooker` (`COURT_BOOKER_HOME` overrides) with
  `booker.db`, `run.lock`, `logs/` and the app's `config.toml`. The CLI's config comes from
  `--config`; a relative `log_dir` resolves beside it.
- `device_setup.py`: checks (MuMu installed, MuMu screen settings, wake timers, app installed)
  and `auto_setup` for the fixable ones; `court-booker setup [--auto]` and the API share it.
  The screen and the app are checked on every instance (`[[instances]]` too) as one item: the
  worst status, each instance's detail ("MuMu 1: …"); auto setup sets each wrong screen.
- `schedule.py`: the Windows task (`schtasks`) that wakes the PC at `wake_at` and runs the
  runner folder's Python.

## Backend (`court_booker.api`)

`create_app(AppContext)`; `court-booker serve` listens on 127.0.0.1:8765, docs at `/api/docs`.
`cli.serve` imports it lazily, so a run never loads FastAPI. Route modules skip
`from __future__ import annotations` and use `Optional` (Python 3.9 evaluates them).
`CourtBookerError`s become `Problem` JSON with an `error` code (409 `lock_held`, 400
`bad_request`, 503 `device`/`app_not_ready`/`notification`/`schedule`, 500 `engine`); invalid
values 422 `invalid_request`.

| Route | Does |
|---|---|
| `GET /api/health` | Version; no device access |
| `GET /api/status` | The Overview in one call: running run (with `runs`: the lock holder's run, then those of the instances it started), schedule, last run, setup; never calls MuMu |
| `GET /api/runs`, `/api/runs/{id}`, `/api/runs/months` | Runs newest first (filters, paging by id or by days), one run with steps and log lines, months of real bookings |
| `GET /api/events` | Activity steps newest first |
| `GET`/`PUT /api/settings` | Booking settings without the hidden keys (`HIDDEN`: Telegram, the notification), with each `[[instances]]` entry in full; `PUT` validates, refuses added or removed instances, saves only on a change |
| `GET`/`PUT /api/notifications`, `POST .../test` | The Windows notification's switch and language; a sample notification |
| `GET /api/setup`, `POST /api/setup/auto` | Device checks; auto setup (quiet time and lock respected) |
| `GET`/`PUT /api/schedule` | The task: state, times; switching on needs a passed dry run. Never switch it on from a development backend: the task would run the development Python |
| `POST /api/runs/dry-run` | Starts a dry run in its own process (refused in the quiet time or while a run holds the lock) |
| `GET /api/accounts` | The subdivision each MuMu instance's account told last (`history_read.account_subdivisions`); one the catalog no longer lists is left out |
| `WS /api/live` | Pushes each new step |

After a route, model or catalog change: `python tools/export_openapi.py` (writes
`ui/openapi.json` and `ui/src/catalog.json`), then `npm run api:types`
(`tests/api/test_api_schema.py`, `tests/test_catalog.py` and CI fail until they match).

## UI (`ui/`)

- Vite, React 19, strict TypeScript, ESLint (type-aware), Prettier, Vitest + Testing Library
  (jsdom). Version holds that need Node 22.22 (jsdom 30, React Router 8) are skipped by Dependabot.
- `src/paths.ts` names the one screen and the old addresses that lead to it, keeping
  `?run=`; `routes.tsx` maps them to `pages/`. `i18n/` (Vietnamese
  default, English; same keys, checked by a test). `styles/` holds the tokens (contrast checked
  by `tokens.test.ts`); components use CSS Modules on them.
- `src/api/`: types generated from `openapi.json` (`schema.d.ts`), a typed client, React Query
  hooks (`queries.ts`, `mutations.ts`) and the live feed (`live.ts`, one WebSocket, reconnects
  with `?after=`). Data is refreshed only at run boundaries (`staleKeysFor`): a run's own steps
  send no request, so the UI never slows a booking.
- `steps.ts` words each event kind (a new kind fails the type check); `reasons.ts` turns the
  engine's English reasons into a few words (`notify.REASONS` holds the same words; a test
  compares them).
- One screen (`pages/HomePage.tsx`, parts in `pages/home/`): the ticket (`BookingTicket`:
  on top the daily switch and what is set: the play day and court side by side, the slots
  on a row of their own (fixed rows, whatever the court's name), and a line only while the
  switch is off, for the MuMu instance chosen below, following each press as its save goes
  out; under the perforation that instance's subdivision, sport, court and up to two slots,
  saved on each press, and the dry run;
  or `LiveTicket` while a booking or a dry run goes on: one ticket per run of `running.runs`,
  named "MuMu N" when several instances book side by side) and `SidePanel` beside it, two tabs:
  `HistoryTab` (runs ten days at a time, real bookings unless dry runs are ticked, `?run=`
  opens one run's slots, steps and log) and `SetupTab` (the user's ticks, auto setup, the
  guide). The result notification's switch (`NotifySwitch`) sits on the ticket under the daily
  one. The header's status line (`components/StatusLine.tsx`)
  shows the run going on, else the one thing to do. `manualSteps.ts` keeps the user's ticks in
  `localStorage` (memory when storage fails); `setupState.ts` counts the setup tasks left and
  picks the panel's first tab. `booking.ts` holds the slots and the two-slot limit, and reads
  the subdivisions, sports and courts from `catalog.json`, written from `catalog.py`.
  `useFormat`'s `courtLabel` tells a court from the others of its sport ("BE7 · tập ném 01",
  in English "BE7 · shooting 01": the app keeps court names in Vietnamese in both languages,
  so the kind's words are in `courtKinds` of the language files) and `court` adds the sport
  ("Tennis S6"). The ticket's subdivision is the one the settings
  name, else the one the account told last (`GET /api/accounts`, refreshed when a run ends,
  "Theo tài khoản"), else Origami; pressing one saves it, keeps the sport if the subdivision
  has it (else its first sport) and takes the first court. The UI never calls `GET /api/setup` or
  `POST /api/notifications/test` (the routes stay for the command line and tools).

## Driver (`android/`)

An instrumentation APK (`dev.courtbooker.driver`), started with `am instrument`. It uses
UiAutomation, like uiautomator2, so only one of them runs at a time; it is not an
accessibility service, which the app refuses (field notes). `tools/build_driver.py` builds it
with the SDK tools into `src/court_booker/assets/court-driver.apk` (committed; a test fails
when the sources change without a rebuild). `driver.py` installs it when its SHA-256 differs,
forwards a port and talks to it; no answer within 10 s per command is
`DeviceNotRespondingError`.

Protocol 1, one JSON object per line each way (`op`, arguments, optional `id`; the reply has
`ok`, `error`):

| `op` | Does |
|---|---|
| `hello` | `protocol`, `version`, `sdk` |
| `dump` | The window as uiautomator2's XML (visible nodes, bounds clipped) |
| `click` `label x y` | Clicks the node labelled `label` nearest (x, y) where it is now (`ACTION_CLICK`, else a touch at its middle); `clicked` false when gone |
| `click_at` `x y` | The same for the smallest clickable node at (x, y): unlabelled elements |
| `back`, `swipe x1 y1 x2 y2 ms` | Injected key or touch |
| `current` | Package of the active window |
| `stop` | Ends the driver |

## Tests

- External effects are injectable; nothing in the suite touches a device, adb, the network,
  Task Scheduler, MuMu or PowerShell. `tests/conftest.py` points `COURT_BOOKER_HOME` at a
  temporary folder.
- `tests/test_flow.py`: `FakeApp`, a scripted app (screens as node lists, taps and Back switch
  screens), with a fake clock; `in_english` turns it English. A full round costs 16 commands.
- Backend tests are in `tests/api/` (skipped without FastAPI); UI tests sit beside the code.
