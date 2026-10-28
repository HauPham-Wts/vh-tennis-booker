# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- The run tells the account's subdivision from the apartment code on the home screen, at no
  extra command, and records it as an `account_subdivision` step (the code itself is not
  kept). A court of another subdivision is a warning in the log and the Windows notification;
  the run goes on. The history reads the subdivision each MuMu instance told last.
- A catalog of the subdivisions Origami and BS with their sports, venues and courts
  (`catalog.py`). Of several venues the run taps the one the catalog lists the court under,
  so a BS account books a BE or BS court without `venue_keyword`; a court not in the catalog
  still picks its venue by `venue_keyword`. A full venue fails the round at once instead of
  after `timeout`.
- A `subdivision` setting, also per `[[instances]]` table: empty (the default, the
  account's), `origami` or `bs`; a set subdivision must have the chosen sport.
- Field notes on the BS subdivision: its utilities, the venues BE and BS with their courts,
  and how it differs from Origami.
- Field notes on the structure of each utility at Origami (venue, court list, slots, the
  pages the app passes by itself), and the next-month button's label when it is enabled.
- Every sport books with the app set to English: the English tiles of the seven other
  courts are built in, so a run no longer stops on an app in English.

## [0.15.0] - 2026-10-27

### Added
- Field notes on the seven other courts of the Origami subdivision (labels, courts, the
  utilities with a single court), and the plan for them in the roadmap.
- A `sport` setting, also per `[[instances]]` table: `tennis` (the default, so an existing
  config books as before), `multi`, `volleyball`, `table-tennis`, `basketball`, `football`,
  `pickleball` or `badminton`. The run taps that sport's tile on the utilities list; a
  `[labels] utility` set by hand still wins. Only tennis has its English tile so far: a run
  of another sport stops with a clear message if the app is in English.
- Table tennis and pickleball, which have a single court: their court list passes on to
  that court's booking details page by itself, often before a read shows it, as a single
  venue does. The round goes on from the details page wherever it shows, once the page names
  the configured court (another court fails the round).
- A court cut off by the bottom edge, such as the seventh basketball court, is tapped where
  it is, without swiping the list: it is in the tree, and the driver clicks it by its label.
- The ticket offers the sport above the courts, then the courts of that sport; choosing a
  sport saves it with its first court. A court is named by its sport and label everywhere
  ("Tennis S6", "Bóng rổ S8 · nửa sân"), and the Windows notification names a court of
  another sport with its sport ("S6 cầu lông").

## [0.14.0] - 2026-10-26

### Changed
- The ticket is in two parts: above the perforation only what is set, the play day, court
  and slots in booking order, large ("T4 28/10 · S6 · ① 18:00–19:00 ② 19:00–20:00"), and one
  line on when the run starts and the PC wakes; below it the choices, each press showing on
  top at once. The large start time is gone.
- Each run in the History takes two lines: the play day and court with a count ("2/2",
  "1/2", "0/2"; "THỬ" for a dry run) in place of the worded stamp, then the slots and when the
  run started, after a clock (on schedule) or a person (by hand). Why a slot failed shows on
  hover and in the run, which keeps its full stamp.

### Removed
- The play day is no longer a setting: a run always books two days ahead, the newest day the
  app opens at 06:00. The ticket shows the play day above the perforation instead of three
  buttons; `days_ahead` is dropped from the settings, `[[instances]]` and `config.example.toml`,
  and `--days` from the command line. A `days_ahead` line in an existing `config.toml` is
  read and ignored.

### Fixed
- The ticket's column no longer scrolls sideways: the perforation's notches reached past it.

## [0.13.1] - 2026-10-25

### Fixed
- The previous-month button is tapped where it is: its fallback point was on the next-month
  button, so going back a month went forward. Both month buttons are now tapped in their
  middle (`next_month_xy` 0.930, `prev_month_xy` 0.807, measured in the app).
- A date in the next month switches the calendar at once: a month shows only its own days, so
  the 1.5 s wait for the date on the current month is skipped (the last two days of a month
  at 06:00).
- The History names the court the app booked, as its ticket showed it, instead of the configured
  court (until a slot is booked, a run still shows the configured court).

## [0.13.0] - 2026-10-25

### Added
- Booking with more MuMu instances side by side, each logged in to its own account with its
  own settings: an `[[instances]]` table per instance in `config.toml` (its `mumu_index`,
  and its `days_ahead`, `slots`, `court`, `venue_keyword` where they differ; instances are
  added in the file, after their MuMu instance and account are set up). The run starts one
  process per instance that books exactly like a run with one instance, so all of them book
  at 06:00 at the same time, and one that fails or freezes holds up no other. Each has its own log file (`…-mumu1.log`), history
  entry and Windows notification ("MuMu 1 · …"). Without the table a run books as before.
  The runner must be upgraded before the table is added: an older one refuses it.
- The setup checks (`court-booker setup`, the app's setup screen) check the screen and the
  Vinhomes app on every MuMu instance, and auto setup sets the screen of each.
- While instances book side by side the Overview shows a ticket for each ("MuMu 1 · Đang đặt
  cho …"), and the History names the instance of each run beside the first ("· MuMu 1").
  The history database records each run's instance (schema 2; older runs have none).
- With more instances the next booking's ticket starts with a choice of instance ("Máy":
  MuMu 0, MuMu 1); the play day, court and slots shown and saved are that instance's.

### Changed
- Each run also turns off Android notification banners, in the same command that turns
  off animations, so none can drop over the app during a round.

## [0.12.0] - 2026-10-24

### Changed
- The Overview holds the History in a panel beside the next booking; the History and
  Activity screens are gone (their addresses lead to the Overview, and `?run=` still opens
  that run). The panel lists the runs of the last ten days, real bookings unless "Gồm cả
  chạy thử" is ticked, ten more days on request. Each row says what the run booked, its
  stamp ("ĐÃ ĐẶT 2/2", "ĐẶT ĐƯỢC 1/2", "KHÔNG ĐƯỢC 0/2", "CHẠY THỬ ĐẠT"), when and whether it
  ran on schedule or by hand, and each slot booked or not with the reason; a run opens in
  the panel with its slots, every step and the technical log.
- The status line moved to the header, on every screen; while a run goes on it names the
  run in place of the banner over the Overview. The live run no longer links to the
  activity log.
- The next booking's ticket holds the booking settings: the "Tự đặt mỗi sáng" switch, the
  play day (three buttons named by their dates, "Thứ Ba 27/10 · đặt trước 2 ngày"), the
  court and the slots, each press saved at once (no Save or Cancel), and the dry run with
  its last result. The Schedule screen and the Booking tab of Settings are gone (their
  addresses lead to the Overview). At most two slots can be chosen, as the app allows; a
  third press says so. During a booking or a dry run the ticket shows the slot being
  booked, the round, the progress and every step, the choices locked until it ends.
- The status line asks for a dry run, then for the daily switch, before it says "Sẵn sàng
  cho 06:00 sáng mai"; a passed dry run does not turn the switch on by itself.
- The UI is one screen without a menu: the panel beside the ticket has two tabs, Lịch sử and
  Thiết lập. The Settings, Device setup, Notification, Guide and Welcome screens are gone
  (their addresses lead to the one screen). The Setup tab holds three steps the user ticks
  (MuMu, the Vinhomes app, the login; kept in the browser, not checked by the app), auto
  setup in one line with its button, the notification switch (no more sample notification)
  and a short guide; while anything is left it starts with three lines on how to use the
  app, opens first and shows the count of tasks left, which the status line repeats
  ("Còn 2 việc thiết lập"). The UI no longer asks the backend for the setup checks.

- The README's screenshots show the one screen: during a dry run, ready for 06:00 with the
  History, and a first use on the Setup tab.

### Fixed
- The status line no longer says a device setup item is left because an old auto setup ran
  with MuMu closed: only the items auto setup fixes count, and the app's install is the
  user's own tick.

## [0.11.0] - 2026-10-24

### Changed
- The app's quota notice ("Căn hộ đã hết hạn mức đăng ký tiện ích cho phép.") stops the
  run: the round fails at once as "Booking quota used up" (after "Tiếp tục" it waited 30 s
  for the courts), the slots left are skipped without touching the app, and the log, the
  history and the Windows notification say so. A new label, `quota_full` ("hết hạn mức"),
  finds the notice; config.toml needs no change.
- `docs/architecture.md` says what each module, route and UI part does and what must stay
  true (43 KB to 12 KB); the details live in the docstrings.
- The field notes keep the facts about the app and MuMu the code relies on (the verified
  runs table and the dated accounts are gone: test evidence goes in the pull request); the
  roadmap keeps the goal, what is left and the situations; the desktop spec keeps the product
  decisions and the packaging plan; how-it-works is shorter.
- README, CONTRIBUTING and CLAUDE.md follow the trimmed docs: a real booking's results go in
  the pull request's description, a GitHub release page is optional, and CLAUDE.md's current
  state points to the changelog and the session notes instead of repeating them.
- Before the opening, only the first tap on the utility logs "Tapped" at info level (a tap
  every 0.2 s filled the log with them: 121 lines on 2026-10-20); a new line says after how
  many attempts the calendar opened.

### Fixed
- The settings model's description no longer mentions an "Advanced" section; the app
  changes the slots, court and day only.
- The Windows notification names the court the confirmation page showed, the one booked,
  instead of the configured one (the app once booked another court than the one tapped).

### Removed
- The historical specs of 0.2.0 and 0.3.0 (`docs/specs`): the current design is in
  `docs/architecture.md`, the old one in the git history.

## [0.10.0] - 2026-10-23

### Added
- A Windows notification after every run, dry runs too: the booking day, how many slots
  went through, and one line per slot with the court or why it failed, in Vietnamese or
  English. New settings `windows_notification` (on by default) and `notification_language`
  (`vi` by default); they are written to `config.toml` only when changed, so a config saved
  with both at their defaults still loads in a runner of 0.9.1.
- Backend routes for the notification: `GET`/`PUT /api/notifications` read and save
  whether it is on and its language; `POST /api/notifications/test` shows a sample one
  (503 `notification` when Windows does not show it).
- Settings › Notifications in the app: switch the notification on or off and send a test
  one. The notification follows the language of the app: switching the app's language
  saves it too.

## [0.9.1] - 2026-10-23

### Changed
- Documentation aligned with 0.9.0: release and runner status, instrumentation and
  fallback behaviour, bilingual labels, configuration, API coverage and release workflow.
  Mark the 0.2.0 and 0.3.0 specs as historical and distinguish the released browser UI
  from the unfinished desktop packaging. The clock used by the app for opening hours
  remains unverified.

### Fixed
- After the venue ("Origami…") is tapped, the court list is awaited: a read right after the
  tap could still show the venue screen, which was taken for the next one, so the round
  failed at once with "Button not found" for the court (06:00 on 2026-10-23). Each of these
  screens is now known by a label of its own: the venues by "Chọn phân khu" (a single
  venue is tapped whatever its name; `venue_keyword` picks one of several), the court list
  by "Chọn vị trí/dịch vụ", the booking details page by "Số lượng cư dân", each with a new
  default in `[labels]`; the court and "Tiếp tục" are then awaited on them. In English the
  three labels read "Select subdivision", "Select place/service" and "Number of residents".

## [0.9.0] - 2026-10-20

### Added
- Booking with the Vinhomes app set to English as well as Vietnamese. The English labels and
  calendar day labels are built in; the language is found on the app's first screen and
  logged ("App language: English"), with no new setting and no extra device command.
  `[labels]` in the config stays the Vietnamese set.

## [0.8.3] - 2026-10-20

### Fixed
- "Xác nhận" is tapped again every 3 s while the confirmation page still shows it enabled
  with no ticket or notice, never while the next screen is built. Under load on 2026-10-19
  the app ignored it in 2 of 26 rounds: the page stayed for 30 s with no ticket, and a tap
  by hand then booked. A notice after a second tap reports the outcome as unknown, since the
  first tap may have booked.

## [0.8.2] - 2026-10-19

### Changed
- Every screen is awaited up to `timeout`, now 30 s by default (was 10 s, and five taps of
  2 s for screen changes); a screen that shows sooner is acted on at once. A tap is repeated
  every 2 s while its element is still shown, never while the app loads the next screen. On
  2026-10-19 the ticket came more than 10 s after "Xác nhận": the round was booked but
  reported "Outcome unknown". An existing `config.toml` with `timeout = 10` needs 30.

## [0.8.1] - 2026-10-19

### Changed
- Branches: `develop` is the development line and `main` holds releases only, each commit
  on it tagged; work branches are cut from `develop` and merged back into it, and a release
  is a pull request from `develop` into `main`. The `stable` branch is gone (CONTRIBUTING).
  CI also runs on pushes to `develop`, and Dependabot opens its pull requests there.

### Fixed
- The first tap goes by NTP time carried forward on a counter that Windows does not set,
  checked again at the warm-up, and comes 0.1 s after the start: on 2026-10-19 Windows set
  the PC clock after the run's NTP check, so the tap came up to 0.76 s early and the app
  answered with its closed-hours notice.
- A clock check keeps the quickest of four answers from the time server, and the DNS lookup
  is no longer timed with the exchange: an answer is off by half its round trip, and a
  check that took 0.57 s read the PC clock 0.531 s fast where quick ones read 0.413 s.
- A notice in place of the calendar after the utility tap, such as "chỉ nhận đăng ký Sân
  Tennis từ 06:00", is closed with Back and the utility tapped again (about 0.2 s a try)
  until `open_retry_seconds`; the round waited 10 s for the calendar and failed.
- The slot is tapped once "Tiếp tục" shows enabled (read again for up to 2 s), and the
  button is looked for in a fresh read: on 2026-10-19 it was still disabled when the slot
  list showed, and the round failed with "Button not found".

## [0.8.0] - 2026-10-18

### Added
- The driver: the project's own APK (`android/`), run in MuMu as an instrumentation with
  `am instrument`, which gets UiAutomation as uiautomator2 does; it is not an accessibility
  service, and the app books with it running (2026-10-18). It reads the screen in about
  13 ms instead of 100 ms and clicks elements by their label in the tree of the moment,
  with no coordinates, so a list that moves while it loads cannot send a click to another
  court. A run installs it when missing or different (the APK ships in the package, built
  by `tools/build_driver.py`), starts it, and stops it at the end; it falls back to
  uiautomator2 when the driver does not start. `--driver instrumentation|uiautomator2`
  asks for one. First real booking: rounds of 4.8 s and 3.9 s against 7.0 s and 4.9 s with
  uiautomator2 the same evening.

### Changed
- "Tiếp tục" comes at least 0.1 s after the slot tap and "Xác nhận" at least 0.2 s after
  the consent tick: sooner, the app books the slot selected before or ignores the
  confirmation (seen with fast reads, 2026-10-18).

## [0.7.1] - 2026-10-18

### Changed
- An on-device AccessibilityService agent was tried and dropped: the Vinhomes app refuses
  to book while an accessibility service is enabled (field notes, "Accessibility agent").

### Fixed
- A court tap that the moving court list sends to another court no longer books that court
  (S9 instead of S6 on 2026-10-13 and 17). The booking details page names the court it
  opened: another court is left with Back and the court tapped again where the list shows
  it then (about 1 s more, only then). A list that moved under a tap that opened nothing,
  such as one landing on a full court, gets the tap again after 0.6 s instead of 2 s.

## [0.7.0] - 2026-10-16

### Changed
- Roadmap: packaging the desktop app (Tauri, PyInstaller, installer) is now the last step
  before 1.0.0, after the speed work, and gets its version number when it starts; it was
  planned as 0.7.0.
- README rewritten for a first visit: what the project does and for whom, highlights by
  outcome, a quick start in five steps (install, configure, device setup, dry run,
  schedule), the web UI, the command line, and a real 06:00 log; the internal details moved
  out to the docs it links. CONTRIBUTING asks for a real booking, not a dry run, after a
  booking flow change.
- Taps are a touch down and up instead of uiautomator2's `click`, which holds the touch
  about 100 ms: a tap takes 83-91 ms instead of 151-165 ms on MuMu, about 0.5-0.7 s less a
  round (measured 2026-10-16).

### Added
- A real run closes MuMu once its rounds are done (`MuMuManager control shutdown`); the next
  run starts it again. MuMu stays open after a dry run, Ctrl+C, an error before the rounds
  (such as a logged-out app) or a frozen MuMu. A failure to close it is only a warning. The
  welcome screen says so.
- Screenshots of the web UI in the README (the Overview during a dry run, History,
  Settings › Booking), with made-up data, in `docs/img/`. The rule against committing
  screenshots now covers screenshots of the Vinhomes app and of real data.

## [0.6.3] - 2026-10-16

### Changed
- The menu has five items: Activity (Nhật ký) is now the second tab of History (Lịch sử),
  next to the real bookings, as Settings holds its two tabs. The tabs have their own
  addresses (`/history/bookings`, `/history/activity`); `/history` and the old `/activity`
  lead to them, keeping the month or the run asked for. The Guide describes both tabs
  under History.
- The History tab shows the bookings of the newest ten days of play in the month picked,
  and ten days more with "Xem thêm"; the month is still read in one request, so showing
  more asks the backend nothing.
- The Activity tab lists the runs of the newest ten days (it was the last 30 runs, and
  older ones could not be opened); "Xem thêm" reads the ten days before, one request each
  (`GET /api/runs?days=10`).

### Added
- `GET /api/runs` takes `days` (1-60): every run of the newest days that have runs, by
  the day a run started, after the other filters; with `before` it pages back by days.

## [0.6.2] - 2026-10-16

### Changed
- Branches: every branch is cut from `main` and merged back into it; `main` is the
  development line and the new `stable` branch points at the latest release. Versions no
  longer get a `release/X.Y.Z` branch (CONTRIBUTING.md).
- A round is booked only once the ticket's title shows after "Xác nhận"; frames without
  the ticket or a notice are read again. The `slot_booked` event no longer has `ticket`
  (always true now) and the "No ticket after confirming" warning is gone.
- Going back to the utilities list (or home) presses the next Back as soon as the screen
  before shows, instead of waiting 2 s on every screen on the way. After a refusal at
  "Xác nhận" (six Backs) this took 11 s on 2026-10-14 at 06:00; each screen shows
  0.13-0.24 s after Back.
- The clock check asks the configured `ntp_server` twice, then time.google.com,
  time.windows.com and pool.ntp.org in turn, with a 1 s timeout, and logs which one
  answered; only when none does is the PC clock used, with a warning (time.google.com
  timed out once on 2026-10-15). A reply that does not carry the time (not from a server,
  or stratum 0) is no longer taken as an offset. No new setting.

### Fixed
- A round could be reported booked when the screen was read in the moment without labels
  that follows "Xác nhận", although the app then refused the booking (seen 2026-10-15 with
  the slot taken by another account). The round now waits for the ticket or the notice.
- Neither the ticket nor a notice within `timeout` (10 s) fails the round as "Outcome
  unknown ... check the app" (in the UI: "Không rõ đã đặt được chưa, xem app Vinhomes").

## [0.6.1] - 2026-10-15

### Added
- Each round reads the date, slot and court on the confirmation page, from the screen it
  has already read (still 16 commands per round), and logs them; a difference from the
  target is a warning and the round still confirms. The first read after "Xác nhận" also
  tells whether the ticket title and status show; a missing title is a warning only. The
  `slot_booked` event keeps them as `shown_date`, `shown_slot`, `shown_court`, `ticket`
  and `ticket_status`.
- Five app labels for this: `booked_time`, `booked_place`, `ticket`, `processing`,
  `registered`.
- A time limit of 60 s on the connection and every device command (`watchdog.py`). A frozen
  emulator fails the round, ends the run with "MuMu did not answer ...", is recorded in the
  history, releases the run lock and exits with code 3, instead of hanging until Task
  Scheduler ends it an hour later.

### Changed
- Saving the settings writes only the labels that differ from the defaults, so a runner of
  an older version never meets a label it does not know.
- ruff 0.17.0, also in pre-commit.

### Fixed
- Welcome step 2: the title sat 40 px above its lead line; it is now as close as on step 4.

## [0.6.0] - 2026-10-15

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
- The Activity screen: the 30 newest runs with when, how and a ✓/✕ mark; the run shown
  (`?run=`, else the newest) with its stamp, every step in plain words, and its technical
  log, closed until asked for.
- The History screen: the real bookings of a month as tickets with their slots, court and
  stamp, a month picker kept in the address, and the slots booked that month (helps with
  the quota of 8 per month). Runs from the API carry their slots; `GET /api/runs` filters
  real bookings or dry runs (`dry_run`), and `GET /api/runs/months` lists the months.
- The Overview: one status line on whether the next start is ready or what to do first
  (set up the device, turn the schedule on), the next booking as a ticket (start time,
  wake time, play date, court, slots), and the last real booking with one card per slot
  and the reason a slot failed in a few words ("Hết chỗ", "Sân S6 đã kín").
- While a booking or a dry run goes on, the Overview shows it as it goes: a banner, the slot
  being booked, every step with the newest marked, the slots still to come and the
  progress, from the live feed alone. It leaves this view once the run gives the emulator
  back.
- Settings > Booking: the resident picks the slots (13 toggles, numbered in the order they
  are booked), the court (S6, S8, S9, S10) and the day (today, tomorrow or the day after),
  then saves or cancels. Only these three change: the rest of `config.toml` goes back to the
  backend as it was. A slot or court set by hand outside the lists is still shown. The two
  settings tabs are links, so each keeps its address.
- Settings > Device setup: the three steps only the resident can do (install MuMu, install
  the Vinhomes app, log in), each marked done, to do or not sure with what to do next in
  plain words, and "Kiểm tra lại". The login comes from the runs: a run the app did not let
  in ("check that it is logged in", now also worded on the Overview) asks to log in again.
  Auto setup shows each item it takes care of and asks before restarting an open MuMu.
  The checks ask MuMu and adb, so they wait while a run holds the lock.
- The Schedule screen: step 1 starts a dry run and says how the last one went (passed, or
  why not in a few words); while a run goes on its button is off and the line points to
  the Overview. Step 2 switches the daily booking on (once a dry run has passed) or off,
  with the wake and start times, the next booking and its play date, and the three habits
  the PC needs (sleep, stay signed in, plugged in).
- The Guide screen: four steps to get started, each a link to the screen where it is done;
  what each screen of the menu is for; and answers to the usual problems (no run this
  morning, "Hết chỗ", the monthly quota, a logged-out app, device setup not done), opened
  one at a time. It quotes the other screens' labels from their own messages and sends no
  request.
- The Welcome screen: an app not used yet (no dry run passed, schedule off, nothing
  running) opens on it instead of the Overview, once per opening. Four steps in a bar of
  links: what happens every morning with this PC's wake and start times and what to
  prepare; then the device setup, the slots and the schedule, the same screens as in
  Settings and Schedule. Any step can be opened; "Để sau" leads back to the Overview, and
  slots chosen but not saved hold "Tiếp" back until saved or cancelled.

### Changed
- The OpenAPI schema describes every error response as a `Problem` (also 422, which it
  listed as FastAPI's own validation error) and names the `/api/status` model `Overview`.
- The UI keeps a read fresh for 30 seconds, so returning to the window no longer reads
  everything again; the live feed still refreshes what each step changes at once.
- The OpenAPI schema lists every step kind (`EventKind`) and category, so a step the UI
  has no words for fails its type check.
- While a run goes on, the UI asks the backend nothing per step: steps come from the live
  feed, and only a run's start, the end of a slot and the run's end refresh the data. A
  window left open at 06:00 no longer starts `schtasks` and rereads the run at every step.

### Fixed
- After a dry run passed, the schedule switch stayed locked for up to 30 seconds: the end
  of a run now refreshes the schedule too.

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
