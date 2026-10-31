# Known issues

Open bugs, by severity: **1** may cost the 06:00 run, **2** reports wrongly or too little,
**3** UI or docs. Remove an issue once it is fixed and confirmed (`CHANGELOG.md` keeps the
history). Ideas the user ruled out are listed last, so they are not proposed again.

Last updated: 2026-10-31.

No confirmed open bugs. The next-month day tap was confirmed by the 2026-10-31 06:00 run
(2/2 bookings).

## Unhandled situations

See the roadmap's "Situations": an update or unknown dialog, a network error, the app
crashing mid-round, ADB lost mid-run, MuMu at the wrong resolution (the run still works but
must scroll, without a warning). Fixed when a log shows one.

## Ruled out by the user

- Throttling screen reads while a screen stays long (2026-10-27): MuMu froze only under test
  bursts, never in a real run.
- Other subdivisions as a bug: they are a feature (the subdivision choice), not a defect.
- Counting the month's bookings in the app's history: the user tracks the quota; the quota
  notice stops the run (0.11.0).
- A PC that did not wake (the user had shut it down). A scrolled home screen where Back
  leaves the app (only after someone touched it).
- The schedule switch in a development UI replacing the runner's task (2026-10-16, not fixed:
  never switch the schedule from a development backend).
- Tapping by MuMu's clock instead of NTP (2026-10-24): it would save a few hundred
  milliseconds at most. Measured at 21:00 on 2026-10-24: MuMu ran 0.71 s behind NTP, and the
  app seems to check against MuMu's clock; the 0.2 s re-tap covers most of it.
- A health check at 05:58, backup slots or courts, Telegram setup, opening the calendar
  before 06:00, booking two slots in one flow, double taps, an AccessibilityService agent.
- Risks reviewed on 2026-10-10, fixed only if a log shows them: a slow first tap after a long
  idle, the 2 s re-tap threshold, load from continuous screen reads, uiautomator2 not pinned,
  Windows Update restarting the PC.
