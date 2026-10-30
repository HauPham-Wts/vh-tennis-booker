# Roadmap

## Product goal

Win the booking race: the app opens bookings at **06:00 every day**, and the user must not need
to be awake. Unattended, scheduled, as fast as possible.

- The target date is always today + 2 (`config.DAYS_AHEAD`), the newest day the app opens at
  06:00; neither the config nor the command line changes it.
- Windows Task Scheduler starts the run at `wake_at` (waking the PC). The run starts MuMu,
  connects ADB, restarts the app, waits on the home screen and opens the utilities list
  `warm_up_seconds` before the start, so only the booking taps happen after 06:00. A real run
  that ran its rounds closes MuMu at the end.
- More accounts book side by side: each other MuMu instance (`[[instances]]`) runs the same
  run in its own process, with its own account, court and slots, switched on in the UI ("Máy 2",
  "Dùng máy này"). Each books only its own slots, so 4 hours take 2 slots on each of 2
  instances.
- Out of scope: getting around any check of the app, and accessibility services, which the app
  refuses (field notes, "Accessibility agent"). In scope: the project's own instrumentation
  driver (UiAutomation, as uiautomator2 uses); the app books with it running.

## Phases

The 0.x versions go through four phases toward 1.0.0: (1) it runs, (2) it handles every
situation, (3) it is fast, (4) it has a user-friendly UI. Releases 0.1.0 to 0.13.1 covered all
four (CHANGELOG); 0.13.0 ended phase 3 with MuMu instances side by side. Failures are fixed
as the 06:00 logs show them. What is left:

| Phase | Next | Scope |
|---|---|---|
| 1 Runs | Other subdivisions | Origami and BS are in `catalog.py` with every sport (Origami 0.15.0, each sport booked for real 2026-10-27; BS dry runs of tennis BE7, BCX3 01 and basketball BE7 01 in Vietnamese and English, 2026-10-28), the subdivision chosen on the ticket or told by the account; left: survey each other subdivision with `dev-tools/survey/walk.py` and add it to the catalog |
| 3 Fast | Two instances booking for real at once | Each instance booked for real alone and both together in a dry run (2026-10-25); a real booking with both is due in November, when both accounts have slots left |
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
| Booking | Target date in the next month | The month switch worked at 06:00 on 30/10, but the day tap landed while the month slid in and was lost (no booking); fixed: the day is tapped once clickable and again while the calendar's prompt stays. A real 06:00 run for the next month is still to come |
| Booking | Quota (2 slots a day, 8 a month per apartment) | Tracking is left to the user. The app's quota notice, after "Tiếp tục" or "Xác nhận", fails the round with "Booking quota used up" and skips the rounds left; the log and the notification say so (since 0.11.0). The 06:00 run books a new day, so there it means the month is used up |
| Device | MuMu not running / frozen | Started automatically / a device command over 60 s ends the run (exit 3); no restart, no retry (by decision) |
| Device | One of several MuMu instances fails or freezes | Only its own process ends; the others book on, and the main log names its exit code. Its slots are not moved to another instance (by decision) |
| Device | ADB lost during a run | Not handled |
| Device | Wrong MuMu resolution | Set by the run while MuMu is off; a running MuMu is logged (WARNING) and scrolls |
| Device | PC woke late, clock drift | Runs at once if under 10 min late; NTP time on a counter Windows does not set |
| Reporting | Every failure reported | Log file, history database, a Windows notification after every run; Telegram optional |

## Ruled out

- Opening the calendar before 06:00, two slots in one booking, pre-recorded coordinates.
- A health check before 06:00; fallback slots and courts (other users book within seconds).
- Setting up Telegram (the optional code stays).
- An on-device accessibility agent: the app refuses to book while one is enabled.
- Counting the month's bookings in the app's history before the run: the user tracks the quota.
- MuMu tuning for speed (resolution, CPU and memory, frame rate, renderer) and tapping by the
  MuMu clock: about 80% of a round waits on the server (2026-10-24), the taps and dumps take
  milliseconds, and the retries after the closed-hours notice make up a slow clock. Turning
  off Play Store updates and locking the rotation: not worth the effort.
