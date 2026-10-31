# Progress

The current state of the project. Overwrite entries when the state changes; history belongs
in `CHANGELOG.md` and git. The next task is in [next.md](next.md), open bugs in
[known-issues.md](known-issues.md).

Last updated: 2026-10-31.

## Release and runner

- Released: **0.18.1** (tag `v0.18.1`, 2026-10-30). `develop` is ahead of `main` with
  tooling and docs only (Ruff pin, `tools/release.py`, the `Tag` workflow, README: PRs
  #220-#222), which the 06:00 run does not need; they go out with the next release.
- The Android app is developed in `servedbyhau/v-court`, which ports this repo's booking
  flow and driver; this repo is its behavior reference.
- Runner folder: at `v0.18.1`, moved 2026-10-30 without a dry run (the user's call).
- Daily task `\court-booker`: wakes the PC at 05:50 and books at 06:00 with the runner's
  `pythonw.exe`, the development `config.toml` and `logs/`. After any session that ran the
  development backend, check `python -m court_booker schedule status`: "Task To Run" must be
  the runner's Python.
- The real config books one court on instance 0 and has no `[[instances]]` table yet (the
  second machine is off). Instance 0 holds an Origami account with the app in English;
  instance 1 holds a BS account.

## Last 06:00 runs

| Date | Version | Result |
|---|---|---|
| 2026-10-31 | 0.18.1 | 2/2 (5.9 s, 3.8 s); both rounds switched to November and selected 2026-11-02 within 0.4 s |
| 2026-10-30 | 0.18.0 | 0/2: the first day tap in the next month landed while the month slid in (fixed in 0.18.1; a real booking through the month switch passed the same day) |
| 2026-10-29 | 0.17.0 | 2/2 (7.0 s, 3.6 s) |
| 2026-10-28 | 0.15.0 | 2/2 (7.1 s, 5.2 s) |
| 2026-10-26 | 0.13.1 | 2/2 (5.6 s, 6.2 s) |
| 2026-10-25 | 0.12.0 | 2/2 (6.2 s, 3.9 s) |

## Real bookings still to come

- Both instances booking for real at once: in November, when both accounts have slots left.

## Decisions in force

These are not written elsewhere (CLAUDE.md, the roadmap or the specs):

- UI: for end users, ready-made choices only; one screen without menus; light theme, desktop
  width and Vietnamese by default. It sends no request per step while a run is going, and does
  not check MuMu while the run lock is held.
- The runner stays until the desktop app exists, and moves only at a release. Packaging the
  desktop app is the last step before 1.0.0.
- Choosing days of the week: later, not decided.
- No GitHub Release pages. Releases go ahead without asking again.
- Accounts, quotas, re-logins and adding instances to `config.toml` are the user's job.
- Test tickets booked during development are cancelled by the user.

## Test environment notes

- The UI suite run fully parallel on the dev machine has two tests time out; with
  `--maxWorkers=2` all pass.
- One process at a time against MuMu: when it freezes, shut MuMu down fully and run again.
