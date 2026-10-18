# Roadmap

## Product goal

The only goal is to win the booking race: the app opens bookings at **06:00 every day** and
the user must not need to be awake. Priority is unattended, scheduled, fastest-possible
booking (decided 2026-10-07).

- The target date is always today + `days_ahead` (default 2); there is no `--date`.
- No stop button or cancellation token; Ctrl+C prints the summary instead.
- The trigger is Windows Task Scheduler at `wake_at` (default 05:45), time-based, not
  logon. The run itself starts MuMu, connects ADB and restarts the app. A real run that ran
  its rounds closes MuMu at the end (since 0.7.0, no setting); MuMu stays open after a dry
  run, Ctrl+C, an error before the rounds, or a freeze.
- Each run waits on the home screen and opens the utilities list `warm_up_seconds` (60)
  before the start time, so only the booking taps happen after 06:00 and the app has loaded
  its data shortly before (2026-10-14).
- ADB: reuse a running ADB server if present, then a configured adb path, then adb on
  PATH; then detect emulator ports (MuMu 7555 and 16384+, LDPlayer/BlueStacks 5555+, Nox
  62001). MuMu is started with `MuMuManager.exe` in `nx_main`: `info -v 0` returns JSON
  with `is_android_started`, `adb_host_ip`, `adb_port` (16384 for instance 0);
  `control -v 0 launch` starts it. MuMu ships its own `adb.exe` in the same folder.

Out of scope: bypassing any app check, and on-device automation (an Android app using
AccessibilityService). ADB needs Android developer mode, which the app accepts. The
app refuses to book while an accessibility service is enabled (2026-10-18, field notes,
"Accessibility agent").

## Phases

The 0.x versions go through four phases toward 1.0.0: (1) it runs, (2) it handles every
situation, (3) it is fast, (4) it has a user-friendly UI. Speed came early (0.3.0) because
it decides the 06:00 race. On 2026-10-12 the UI phase moved ahead of the remaining speed
work: 0.4.0 waits for failures in the logs, and the core books reliably. Since 0.6.0 the
0.6.x patches fix what the 06:00 logs and daily use show. On 2026-10-16 packaging the
desktop app (the installer) moved to the very end, after the speed work, so it only wraps
what has proven itself; it gets its version number when it starts. On 2026-10-18 an
accessibility agent was tried for the speed work and dropped (the app refuses to book
with one enabled). The speed work goes on in this order: MuMu tuning, several MuMu
instances in parallel (the last step for two slots); each round is made as fast as it
can be before rounds run side by side.

| Phase | Version | Scope |
|---|---|---|
| 1 Runs | 0.1.0 | Label-based booking flow (released) |
| 1 Runs | 0.2.0 Unattended | Start MuMu, ADB auto-connect, timed start with NTP offset, opening retry, keep awake, log file, Telegram summary, Task Scheduler with wake (released; spec [0.2.0-unattended](specs/0.2.0-unattended.md)) |
| 3 Fast | 0.3.0 Fast rounds | MuMu 540x1600, one dump per screen, taps by coordinates, entry located before the start, command count (released 2026-10-09; spec [0.3.0-fast-rounds](specs/0.3.0-fast-rounds.md)) |
| 2 Every situation | 0.4.0 Hardening | Failure screen log; the situations below are fixed as the logs show them (released 2026-10-12) |
| 4 UI | 0.5.0 Backend | Separate run folder, engine events, data folder, SQLite history and activity, run lock, device setup and auto setup, FastAPI backend (released 2026-10-13; spec [0.5.0-desktop-app](specs/0.5.0-desktop-app.md)) |
| 2 Every situation | 0.5.1-0.5.3 | Refused bookings fail the round, every screen logged, warm-up on the utilities list (released 2026-10-14) |
| 4 UI | 0.6.0 UI | React + TypeScript screens in the "Vé giấy" design, Vietnamese and English (released 2026-10-15) |
| 2 Every situation | 0.6.1 | Court and date read on the confirmation page, ticket check (warning only), 60 s limit on device commands, labels saved only when changed (released 2026-10-15) |
| 2 Every situation | 0.6.2 | Booked only once the ticket shows (unknown outcome fails the round), Back pressed as soon as each screen shows, clock check with fallback servers; `main`/`stable` branch flow (released 2026-10-16) |
| 4 UI | 0.6.3 | Activity becomes the second tab of History (five menu items); both list ten days and "Xem thêm" (`GET /api/runs?days=`) (released 2026-10-16) |
| 3 Fast | 0.7.0 | Taps as a bare touch down and up (about 0.5-0.7 s less a round); a real run closes MuMu once its rounds are done (released 2026-10-16) |
| 2 Every situation | 0.7.1 | The court check on the booking details page (released 2026-10-18) |
| 3 Fast | Later | MuMu tuning (frame rate, performance, hidden bottlenecks); then several MuMu instances with separate accounts in parallel (one account cannot log in twice), the last speed step |
| 4 UI | Desktop app, last before 1.0.0 | Tauri shell with PyInstaller sidecar, installer, release automation; version number set when it starts (spec [0.5.0-desktop-app](specs/0.5.0-desktop-app.md), "Packaging") |

There is no 0.3.1: its candidate fixes were judged to have no impact.

## Situations (phase 2)

"Done" means handled, or at least reported clearly in the log file. Decided on 2026-10-10:
failures are fixed as they show up in the log.

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
| Booking | Slot taken by someone else at "Xác nhận" | Round fails with the app's notice (0.5.1; was logged as booked on 2026-10-14) |
| Booking | Booked court differs from the tapped one | Seen 2026-10-13 (S6 tapped, S9 booked), 2026-10-15 at 06:00 (the tap hit S9, fully booked: 2.45 s lost), 2026-10-16 (confirmation page on S9, refused by the quota) and 2026-10-17 at 06:00 (S9 booked). Cause: the court list moves up 232 px when the service info above it finishes loading (field notes). Since 0.6.1 the court on the confirmation page is logged (a warning when it differs) and kept in the history. Fixed (0.7.1): the booking details page must name the configured court, another one is left with Back and the court tapped again; a list that moved under a tap that opened nothing gets the tap again after 0.6 s. On 2026-10-18 both rounds of a real booking opened S9 and were set right this way (about 1.5 s each). |
| Booking | Target date in the next month | Code exists; untested since 0.3.0. Only testable on the last two days of a month (30/10 → 1/11, 31/10 → 2/11): the calendar does not switch to a month without bookable days |
| Booking | Booking limit per account | 8 slots per apartment per month; not handled by decision (users track their own quota), the log shows the dialog |
| Device | MuMu not running / frozen | Started automatically / since 0.6.1 a command over 60 s ends the run with an error (exit code 3); no restart, no retry (by decision) |
| Device | ADB lost during a run | Not handled |
| Device | Wrong MuMu resolution | Works but scrolls; no warning |
| Device | PC woke late, clock drift | Runs at once if under 10 min late; NTP offset |
| Reporting | Every failure reported | Log file and history database; Telegram optional, not configured |

## Ruled out

- 2026-10-09: opening the calendar before 06:00, two slots in one booking, pre-recorded
  coordinates.
- 2026-10-10: a health check before 06:00, fallback slots and courts (other users book
  within seconds, a missed slot is lost), Telegram setup (the optional code stays), a run
  history file (history came with the app's database in 0.5.0).
- 2026-10-18: an on-device AccessibilityService agent. It read the screen in 3 ms and tapped
  by label, but the app refuses to book while an accessibility service is enabled. Taps
  written straight to `/dev/input/event4` came out no faster than the other ways to tap
  once the same change detection was used (field notes, "Accessibility agent").
