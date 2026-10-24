# Roadmap

## Product goal

Win the booking race: the app opens bookings at **06:00 every day**, and the user must not need
to be awake. Unattended, scheduled, as fast as possible.

- The target date is today + `days_ahead` (0-2); there is no `--date`.
- Windows Task Scheduler starts the run at `wake_at` (waking the PC). The run starts MuMu,
  connects ADB, restarts the app, waits on the home screen and opens the utilities list
  `warm_up_seconds` before the start, so only the booking taps happen after 06:00. A real run
  that ran its rounds closes MuMu at the end.
- Out of scope: getting around any check of the app, and accessibility services, which the app
  refuses (field notes, "Accessibility agent"). In scope: the project's own instrumentation
  driver (UiAutomation, as uiautomator2 uses); the app books with it running.

## Phases

The 0.x versions go through four phases toward 1.0.0: (1) it runs, (2) it handles every
situation, (3) it is fast, (4) it has a user-friendly UI. Releases 0.1.0 to 0.11.0 covered all
four (CHANGELOG). Failures are fixed as the 06:00 logs show them. What is left:

| Phase | Next | Scope |
|---|---|---|
| 3 Fast | MuMu tuning | Frame rate, performance, hidden bottlenecks |
| 3 Fast | Parallel MuMu | Several MuMu instances with separate accounts (one account cannot log in twice), one slot each: the last speed step |
| 4 UI | Desktop app, last before 1.0.0 | Tauri shell with a PyInstaller sidecar, installer, release automation; version number set when it starts ([spec](specs/0.5.0-desktop-app.md), "Packaging") |

## Situations

| Area | Situation | Today |
|---|---|---|
| App | Logged out | Fails early (exit 4) |
| App | App set to English | Works: the language is found on the first screen |
| App | Closed-hours notice (tap before 06:00) | Closed with Back and the utility tapped again until `open_retry_seconds`; the wait goes by NTP time on a counter, the first tap 0.1 s after the start |
| App | Update prompt, other dialogs, network error | Not handled |
| App | App crash or freeze during a round | Not handled |
| App | Slow server | Every screen awaited up to `timeout` (30 s), a tap repeated every 2 s while its element still shows |
| Booking | New date not open yet | Calendar reloaded for `open_retry_seconds` |
| Booking | Slot or court fully booked | Round fails; no fallback slot or court (by decision) |
| Booking | Slot taken by someone else at "Xác nhận" | Round fails with the app's notice |
| Booking | Booked court differs from the tapped one | The court list moves under the tap (field notes); the booking details page must name the configured court, another one is left with Back and the court tapped again |
| Booking | Target date in the next month | Code exists, untested: first testable on 30/10 (for 1/11) |
| Booking | Quota (2 slots a day, 8 a month per apartment) | Tracking is left to the user. The app's quota notice, after "Tiếp tục" or "Xác nhận", fails the round with "Booking quota used up" and skips the rounds left; the log and the notification say so (since 0.11.0). The 06:00 run books a new day, so there it means the month is used up |
| Device | MuMu not running / frozen | Started automatically / a device command over 60 s ends the run (exit 3); no restart, no retry (by decision) |
| Device | ADB lost during a run | Not handled |
| Device | Wrong MuMu resolution | Works but scrolls; no warning |
| Device | PC woke late, clock drift | Runs at once if under 10 min late; NTP time on a counter Windows does not set |
| Reporting | Every failure reported | Log file, history database, a Windows notification after every run; Telegram optional |

## Ruled out

- Opening the calendar before 06:00, two slots in one booking, pre-recorded coordinates.
- A health check before 06:00; fallback slots and courts (other users book within seconds).
- Setting up Telegram (the optional code stays).
- An on-device accessibility agent: the app refuses to book while one is enabled.
- Counting the month's bookings in the app's history before the run: the user tracks the quota.
