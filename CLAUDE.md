# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Last updated: 2026-10-10.

## Commands

The Python `Scripts` folder is not on PATH on the dev machine, so prefix tools with `python -m`.

```bash
python -m pip install -e ".[dev]"                    # install package + pytest, ruff, pre-commit
python -m pytest                                     # all tests (no emulator needed)
python -m pytest tests/test_flow.py -k slot          # single file / single test
python -m ruff check . && python -m ruff format .    # CI runs `ruff format --check .`
python -m court_booker --dry-run --verbose           # real run against the emulator
python -m court_booker --at 06:00 --dry-run          # timed run
python tools/setup_runner.py v0.4.0 --schedule       # runner folder + daily task (CONTRIBUTING)
python -m court_booker schedule status               # task details (install, remove)
python tools/inspect_screen.py --near "Tôi đã hiểu"  # dump nodes level with a label
```

Run `--dry-run` against the emulator whenever the booking flow changes; CI cannot.

## Goal

A learning project to build a realistic, CV-worthy product: Python code on Windows that drives the
**Vinhomes Resident** Android app (Flutter) inside the **MuMu Player** emulator to book a
tennis court. Personal use only; not published commercially.

**Developer mode:** ADB requires Android developer mode. In the MuMu setup the app accepted
real bookings with it on (verified 2026-10-08). Bypassing any app check is out of scope and
will not be done. On-device automation (an Android app using AccessibilityService) is also
out of scope.

## Current state: 0.4.0 released

- Repo: `github.com/servedbyhau/vh-tennis-booker` (private), local path `D:\VH-Booker\vh-tennis-booker`
- Python package `court_booker` (src layout), CLI `court-booker` / `python -m court_booker`
- `tools/inspect_screen.py`: dumps the UI hierarchy and lists nodes level with a text
- pytest suite with fakes only (device, subprocess, port probe, clock, HTTP, schtasks);
  CI on GitHub Actions: `lint` (ruff check + format) and `test` (Python 3.9, 3.11, 3.12, 3.13, 3.14)
- Tooling: pre-commit (ruff, basic hooks), `.editorconfig`, `.gitattributes` (LF),
  Dependabot, PR and issue templates, `CONTRIBUTING.md`, `CHANGELOG.md` (Keep a Changelog)
- 0.2.0 (spec: `docs/specs/0.2.0-unattended.md`) was verified on 2026-10-08: dry run with
  MuMu closed, `--at` timed run, and a scheduled task run that woke the PC and booked two
  real slots (rounds took 6-9 s; the PC clock was 0.87 s slow, corrected by NTP).
- 0.3.0 (spec: `docs/specs/0.3.0-fast-rounds.md`) was released on 2026-10-09 after a timed
  dry run on MuMu at 540x1600: round 1 reached the accepted terms in 5.9 s (8.7 s with 0.2.0).
  The first real 06:00 run with it (2026-10-10) booked both slots: round 1 took 7.3 s (booked
  at 06:00:07.2, 0.2.0 needed 11.0 s), round 2 4.5 s (06:00:11.7, 0.2.0: 7.1 s). Rounds used
  41-43 device commands including polls while the app loads; no closed-hours popup, no re-taps.
- 0.4.0 code (failure screen log) ran the 06:00 task on 2026-10-11 and 2026-10-12 and booked
  both slots each day: rounds 10.5 s + 4.3 s (11/10) and 7.0 s + 4.3 s (12/10). On 11/10 the
  court list appeared 2.3 s after "Tiếp tục", so the 2 s re-tap fired once (92 commands in
  round 1); the booking still succeeded.
- The scheduled task has no `--dry-run`; it books for real. For a scheduled test, add
  `--dry-run` to the task arguments by hand (`schedule install` overwrites it).

## Code architecture

- `cli.py` parses args (or dispatches `schedule ...` to `schedule.main`), applies overrides onto
  `Config`, adds the log file (and logs the Python and code folder it runs from), resolves
  the start time, measures the NTP offset, and inside `power.keep_awake()` calls `runner.connect_device` then `runner.run_booking`. Errors map to
  exit codes (`RequestError` 2, `DeviceError` 3, `AppNotReadyError` 4, Ctrl+C 130); the summary
  is logged and optionally sent with `notify.send_telegram` on every path.
- `runner.connect_device`: `emulator.MuMu.ensure_started` (MuMuManager `info`/`control launch`),
  `adb.find_adb` + `adb.resolve_device` (prefers the serial MuMu reports), `uiautomator2.connect`
  (imported lazily so tests do not need it). `runner.run_booking`: `Booker.prepare()`,
  `wait_until(start - LOCATE_AHEAD)`, `Booker.locate_entry()`, `wait_until(start)`, then one
  round per slot; a `BookingError` (or any exception) fails that round only. Results are
  appended to a caller-owned list; the debug log counts device commands per round. When a
  round, `prepare()` or `locate_entry()` fails, `log_last_screen` writes `Booker.last_screen`
  to the debug log, so a failure seen once at 06:00 can be fixed from the log alone.
- `events.py`: progress events beside the log lines (spec part 2). `EventKind` values are
  stable strings (future database values and message keys); `Reporter` stamps the time and
  hands an `Event` to a sink, swallowing sink errors so reporting never costs a booking. Sinks:
  `LogSink` (one debug line `Event <kind> key=value ...`), `MemorySink` (tests), `MultiSink`,
  `NullSink`. The CLI emits `run_started` (trigger `scheduled`/`dry_run`/`manual`),
  `device_ready` and `run_finished` (status `ok`/`partial`/`failed`/`interrupted`) on every
  path; `run_booking` emits `app_ready`, `waiting`, `booking_started`, `slot_started`,
  `slot_booked`/`slot_failed`; `Booker` emits `calendar_opened`, `date_selected`,
  `slot_selected`, `court_selected`, `terms_accepted`. Reporting sends no device command.
- `screen.Screen` parses one `dump_hierarchy` into `Node`s (label, visible bounds, clickable);
  `screen.Match` (desc / prefix / contains / full-match pattern / clickable) is applied locally.
  `Screen.describe()` gives one log line per labelled or clickable node (bounds, label).
- `flow.Booker` builds `Match`es from `config.labels` in `__init__`. The device is only used
  through `snapshot()` (one dump), `tap()`/`tap_point()` (`device.click(x, y)`), `press_back()`
  and `_scroll()`; each increments `commands`. `wait_for(find, timeout, screen=None)` reads the
  screen every 20 ms until a finder returns something; the found node carries the coordinates
  to tap. Every transition goes through `tap_and_advance(screen, target, name, find_next)`:
  tap `target` from `screen`, wait for `find_next`, re-tap while `target` is still shown.
  `return_to_utilities()` presses Back until the utilities list or home appears and returns
  that screen. `prepare()` restarts the app and ends on the utilities list; `locate_entry()`
  reads it again just before the start, so the first command at the start is the tap.
  `open_slot()` re-enters the calendar while the date or slot is missing.
- `geometry.py`, `screen.py` and most of `clock.py` are pure; logic testable without a device
  belongs there.
- External effects are injectable (`run`, `probe`, `clock`, `sleep`, `post`, `set_state`), so
  nothing in the test suite touches a device, adb, the network or Task Scheduler.
- `config.load_config` rejects unknown keys (`ConfigError`); the TOML key `continue` maps to
  `Labels.continue_`; keys ending in `_xy` become tuples. New config fields must be added to
  the dataclass and `config.example.toml`. A relative `log_dir` resolves against the config file.
- Tests use hand-written fakes (`tests/test_flow.py`: `FakeApp`, a scripted app that serves
  hierarchy XML per screen and switches screens on taps and Back; `OpeningBooker`) and a fake
  `flow.time` clock so timeouts pass instantly. A full round must cost 16 commands. `tests/conftest.py` puts
  `src/` on `sys.path`.

## Booking flow (app screens)

Home ("Tiện ích") → Utilities list ("Sân Tennis") → Calendar (pick date, then a slot appears;
pick slot; "Tiếp tục") → optional venue screen ("Origami…") → Court list ("S10 - Sân tennis")
→ Booking details ("Tiếp tục") → Confirmation ("Xác nhận đăng ký": tick consent checkbox,
"Xác nhận") → Ticket screen. One Back from the ticket returns to the Utilities list, where
the next round starts.

## Technical findings

- Flutter exposes text via `content-desc`, not `text`; select with `description=...`.
- Emulator screen: MuMu custom resolution **540x1600**, 220 DPI (since 2026-10-09; was the
  tablet mode 960x540 shown as 540x960 portrait, where `window_size()` wrongly returned
  (960, 540)). Never use hard-coded coordinates; the screen size comes from the dump.
- Command cost on MuMu: `dump_hierarchy` 69 ms (whole screen), `exists` 41 ms, `info` 60 ms,
  regex `info_list` 105-177 ms, `window_size` 125 ms. uiautomator2 `click()` on a selector
  is wait + info + click.
- App/server time: calendar 0.14 s after "Sân Tennis", slot list ~2.1 s after the date tap,
  court list 1.5-2.0 s, details 0.5 s, confirmation 0.14 s.
- Calendar at 540x1600 (failure log, 2026-10-10): two non-clickable nodes labelled
  `"Chọn năm"` at `[22,160][170,229]` and `[177,160][285,229]`, then a day grid from y=344;
  no node labelled "Tháng sau"/"Tháng trước" and no clickable unlabelled node near the
  `next_month_xy` fallback point. How the app shows next-month days is unknown until 30/10.
- Day label format: `"2, Thứ Sáu, 2 tháng 10, 2026"`. Slot: `"09:00 - 10:00"`;
  full slot: `"18:00 - 19:00\nHết chỗ"`. Bookable range: today to today + 2.
- Consent checkbox has no label and `checkable=false`: it is the clickable View left of the
  caption `"Tôi đã hiểu và đồng ý với "`, found in the dump as the smallest clickable node
  level with the caption (`geometry.is_checkbox_beside`).
- "Xác nhận" is disabled until the checkbox is ticked; used to verify the tick.
- Flutter builds lazily: off-screen slots are absent from the tree and dump bounds are clipped
  to what is shown. 13 slots (06-12, 14-21); at 540x1600 all fit without scrolling. On shorter
  screens the code swipes until the slot is mostly visible above the sticky "Tiếp tục" button.
- Slot selection is not exposed in the tree (no `selected`/`checked`); "Tiếp tục" is always
  clickable. Courts can be "Hết chỗ" (e.g. `"S9 - Sân tennis\nHết chỗ"`).
- Consent checkbox at 540x1600: `[35,1323][79,1367]` (seen shifted to x=43 once), so it is
  located per run, never stored.
- Success is verified by waiting for the confirmation screen to disappear.
- Outside 06:00-21:00, tapping "Sân Tennis" opens a dialog "Thông báo": "Ban quản lý BQL Grand
  Park chỉ nhận đăng ký Sân Tennis từ 06:00 đến 21:00 mỗi ngày" with a "Đóng" button; it hides
  the utilities list. The 06:00:00.0 tap of 0.3.0 did not trigger it on 2026-10-10.
- Each apartment may book 8 slots per month (1 hour = 1 slot). Once they are used, tapping
  "Tiếp tục" on the calendar opens a dialog "Thông báo": "Căn hộ đã hết hạn mức đăng ký tiện
  ích cho phép." with a "Đóng" button (seen 2026-10-10); the round then fails after the
  re-taps with "Tapped 'Tiếp tục' but the next screen did not appear".
- The MuMu clock follows the PC clock (+15 ms measured); the NTP offset of the PC varies
  (+0.035 to +0.144 s).

## Environment

- Windows 11, Python 3.14, Git; Python `Scripts` folder not on PATH (use `python -m ...`)
- Runner folder `D:\VH-Booker\runner` at `v0.4.0` since 2026-10-12; the task runs its
  `.venv\Scripts\pythonw.exe` with `Start In` the development folder (src layout, so the
  development code is not imported)
- MuMu Player (instance 0 serves ADB on `127.0.0.1:16384`); adb is found and connected
  automatically (`device = "auto"`)

## Product goal and decisions (2026-10-07)

The only goal is to win the booking race: the app opens bookings at **06:00 every day** and the
user must not need to be awake. Priority is unattended, scheduled, fastest-possible booking.

- Target date is always today + `days_ahead` (default 2); no specific `--date`.
- No stop button / cancellation token; Ctrl+C prints the summary instead.
- UI, backend and desktop packaging are phase 4 of the roadmap; started on 2026-10-12 as
  0.5.0 to 0.7.0 (`docs/specs/0.5.0-desktop-app.md`).
- Each run waits on the utilities list ("Sân Tennis", screen 2) before the start time, so only
  the booking taps happen after 06:00.
- Trigger is Windows Task Scheduler at `wake_at` (default 05:45; 05:50 on the dev machine,
  where preparing takes under a minute), time-based, not logon. The script itself starts
  MuMu, connects ADB and restarts the app. MuMu and the app are left open after the run.

**ADB strategy:** reuse a running ADB server if present → user-configured adb path →
adb on PATH; then auto-detect emulator ports (MuMu 7555 and 16384+, LDPlayer/BlueStacks 5555+,
Nox 62001). MuMu is started with `C:/Program Files/Netease/MuMuPlayer/nx_main/MuMuManager.exe`:
`info -v 0` returns JSON with `is_android_started`, `adb_host_ip`, `adb_port` (16384 for
instance 0); `control -v 0 launch` starts it. MuMu ships its own `adb.exe` in the same folder.

## Roadmap

The 0.x versions go through four phases: (1) it runs, (2) it handles every situation,
(3) it is fast, (4) it has a user-friendly UI, toward 1.0.0. Speed came early (0.3.0) because
it decides the 06:00 race. There is no 0.3.1: its candidate fixes were judged to have no impact.
On 2026-10-12 the UI phase moved ahead of the remaining speed work: 0.4.0 waits for failures
in the logs, and the core books reliably.

| Phase | Version | Scope |
|---|---|---|
| 1 Runs | 0.1.0 | Label-based booking flow (released) |
| 1 Runs | 0.2.0 Unattended | Start MuMu, ADB auto-connect, timed start with NTP offset, opening retry, keep awake, log file, Telegram summary, Task Scheduler with wake (released) |
| 3 Fast | 0.3.0 Fast rounds | MuMu 540x1600, one dump per screen, taps by coordinates, entry located before the start, command count (released 2026-10-09, verified at 06:00 on 2026-10-10) |
| 2 Every situation | 0.4.0 Hardening | Failure screen log; the situations below are fixed as the logs show them (released 2026-10-12) |
| 4 UI | **0.5.0 Backend** | Separate run folder, engine events, data folder, SQLite history and activity, run lock, device setup and Auto setup, FastAPI backend (spec: `docs/specs/0.5.0-desktop-app.md`) |
| 4 UI | 0.6.0 UI | React + TypeScript screens in the "Vé giấy" design, Vietnamese and English |
| 4 UI | 0.7.0 Desktop app | Tauri shell with PyInstaller sidecar, installer, release automation |
| 3 Fast | Later | Tuning from the log files; several MuMu instances with separate accounts in parallel (one account cannot log in twice) |

0.4.0 situations ("done" = handled, or at least reported clearly in the log file). Decided on
2026-10-10: 0.4.0 fixes failures as they show up in the log; no health check before 06:00,
no fallback slots or courts (other users book within seconds, a missed slot is lost), no
Telegram setup (the optional code stays) and no run history file until the app stores it.

| Area | Situation | Today |
|---|---|---|
| App | Logged out | Fails early (exit 4) |
| App | Closed-hours dialog after a too-early tap | Not handled (not seen so far) |
| App | Update prompt, other dialogs, network error | Not handled |
| App | App crash or freeze during a round | Not handled |
| App | Slow server at 06:00 | Re-tap after 2 s |
| Booking | New date not open yet | Calendar reloaded for `open_retry_seconds` |
| Booking | Slot fully booked | Round fails; no fallback slot (by decision) |
| Booking | Court fully booked | Round fails; no fallback court (by decision) |
| Booking | Slot taken by someone else at "Xác nhận" | Not handled |
| Booking | Target date in the next month | Code exists; untested since 0.3.0. Only testable on the last two days of a month (30/10 → 1/11, 31/10 → 2/11): the calendar does not switch to a month without bookable days |
| Booking | Booking limit per account | 8 slots per apartment per month; not handled by decision (users track their own quota), the log shows the dialog |
| Device | MuMu not running / frozen | Started automatically / not handled |
| Device | ADB lost during a run | Not handled |
| Device | Wrong MuMu resolution | Works but scrolls; no warning |
| Device | PC woke late, clock drift | Runs at once if under 10 min late; NTP offset |
| Reporting | Every failure reported | Log file (by decision); Telegram optional, not configured |

## Working conventions

- All code, comments, logs, commits and docs in English; app labels stay Vietnamese in config.
- Professional style: type hints, short imperative docstrings, comments explain why,
  module loggers, `BookingError` subclasses, named constants, Ruff line length 100.
- From 0.2.0: one branch per feature (`feat/...`, `fix/...`), Pull Request, green CI, merge,
  update CHANGELOG; Conventional Commits; Semantic Versioning; protect `main`.
- From 0.3.1: each version lives on `release/X.Y.Z` cut from `main`; feature branches are cut
  from it and PR'd into it (merge commit, never squash), one PR at a time, not stacked. One
  PR `release/X.Y.Z` → `main` when stable, then tag `vX.Y.Z` (see `CONTRIBUTING.md`). The
  user opens and merges PRs on GitHub (no `gh` CLI): give a compare link, title and description.
- The scheduled task runs the runner folder `D:\VH-Booker\runner` (git worktree at the last
  release tag, own `.venv`) with the development `config.toml` and `logs/`; move it with
  `tools/setup_runner.py` after each release. The development folder may stay on any branch.
- Never commit `config.toml`, screenshots or UI dumps (may contain personal data).

## Next step

Work happens on `release/0.5.0`, following `docs/specs/0.5.0-desktop-app.md`: one part at a
time (one branch, several small commits, one pull request), each part merged before the next.
Write code only when the user asks for it. Keep reading the 06:00 logs; a booking fix ships
as 0.4.1 from `main`. The next-month case first occurs on 2026-10-30. Ruled out on 2026-10-09:
opening the calendar before 06:00, two slots in one booking, pre-recorded coordinates. Ruled
out on 2026-10-10: health check, fallback slots and courts, Telegram setup, run history file
(history now comes with the app's database).
