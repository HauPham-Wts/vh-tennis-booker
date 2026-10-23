# Field notes

What the Vinhomes Resident app and the MuMu emulator were seen to do, measured on the
development machine. Dates are when a fact was seen; the app can change without notice.
How the code uses these facts is in [how-it-works.md](how-it-works.md) and
[architecture.md](architecture.md).

## Booking flow (app screens)

Home ("Tiện ích") → Utilities list ("Sân Tennis") → Calendar (pick date, then a slot
appears; pick slot; "Tiếp tục") → optional venue screen ("Origami…") → Court list
("S10 - Sân tennis") → Booking details ("Tiếp tục") → Confirmation ("Xác nhận đăng ký":
tick consent checkbox, "Xác nhận") → Ticket screen. One Back from the ticket returns to the
Utilities list, where the next round starts. The app can also show English, with the same
screens ("App in English" below).

Back from inside the flow (2026-10-15 20:50): a notice dialog closes to the confirmation
page, with `'Đóng'` and with Back alike. From there Back goes to the booking details, the
court list, the venue ("Origami…"), the calendar and the Utilities list (5 Backs); one more
leaves to the home screen. Each screen shows 0.13-0.24 s after Back, at times after an
empty frame (only the full-screen root and the status bar). The status bar's labels change
on their own (the clock, a "Google Play services notification" seen at 20:13), so they
never tell one screen from another.

Venues and court list (logs of 14-23/10): the calendar, the venues, the court list and the
booking details page all have the title "Đăng ký tiện ích". The venues and the court list
are one page, below "Thông tin dịch vụ": first "Chọn phân khu" with one entry,
`'Origami_ Sân tennis'`, then "Chọn vị trí/dịch vụ" with the courts. With one venue the app
goes on to the courts by itself within a fraction of a second; a read may catch the
venues or not. In 8 of 30 reads "Chọn phân khu" showed before its entry; the court list's
heading showed with S10 but not yet S6 once (18/10). On 23/10 at 06:00 round 2 tapped
the venue and the read 8 ms later still showed it; the code took that for the next screen,
looked for S6 at once and failed the round. The details page shows
`'Phí đặt chỗ 0 VND\nSố lượng cư dân\n4'` (the fee and count as read; the confirmation page
and the ticket repeat it as `'Phí đặt chỗ\n0 VND\n...'`), in about 24 reads before "Tiếp
tục" is enabled. In English: "Select place/service", `'Booking fee 0 VND\nNumber of
residents\n4'`; the venues' heading was never read in English.

## Reading the app

- Flutter exposes text via `content-desc`, not `text`; select with `description=...`.
- Flutter builds lazily: off-screen slots are absent from the tree and dump bounds are
  clipped to what is shown. 13 slots (06-12, 14-21); at 540x1600 all fit without
  scrolling. On shorter screens the code swipes until the slot is mostly visible above the
  sticky "Tiếp tục" button.
- Day label format: `"2, Thứ Sáu, 2 tháng 10, 2026"`. Slot: `"09:00 - 10:00"`; full slot:
  `"18:00 - 19:00\nHết chỗ"`. Bookable range: today to today + 2.
- Slot selection is not exposed in the tree (no `selected`/`checked`); "Tiếp tục" is always
  clickable. Courts can be "Hết chỗ" (e.g. `"S9 - Sân tennis\nHết chỗ"`).
- The court list can show before the "Thông tin dịch vụ" block above it has loaded: the
  block is an empty clickable `[34,501][504,666]`, "Chọn vị trí/dịch vụ" sits at y=958
  and S6 at `[35,1157][505,1277]`. Once the block loads it shows "Xem thêm" and the whole
  list moves up 232 px (header y=725, S6 `[35,925][505,1045]`, S9 `[35,1193][505,1313]`),
  so a tap at S6's first centre (y=1217) lands on S9, two courts lower. Of 28 taps made on
  the first layout (14-16/10), two landed on S9 (15/10 06:00, 16/10 16:08), besides the S9
  booking of 13/10. In 12 dry rounds (16/10, quiet hours) "Xem thêm" was still missing
  over a second later. The reads just before and just after the wrong tap of 16/10 both
  showed the first layout, so a dump can lag behind the screen. On 17/10 at 06:00 it booked
  S9 again: round 1 read the first layout and tapped y=1217, which opened S9; round 2 read
  the same layout, tapped the same point and opened S6. By position the first court is no
  safer: S10's centre (y=1084) lies on S8 once the list has moved.
- The booking details page names the court it opened as a non-clickable label
  (`'S9 - Sân tennis'` at `[116,975][264,1004]`, above a clickable "Chỉ đường"). In the 19
  court taps of 14-17/10 it showed 0.23-0.45 s after the tap, always before "Tiếp tục"
  (0.53-1.11 s). Back from it returns to the court list.
- On 2026-10-18 at 13:25 (a real booking with the court check) both rounds tapped S6's
  first centre (y=1217) and opened S9. The court's name was in the first read of the
  details page (0.56 and 0.93 s after the tap); the check decides once "Tiếp tục" shows
  (0.3-0.5 s later). Back showed the court list 0.34-0.38 s later, already moved ("Xem
  thêm" loaded, S6 at `[35,925][505,1045]`), and the tap at y=985 opened S6. Each wrong
  court cost about 1.5 s.
- Calendar at 540x1600 (failure log, 2026-10-10): two non-clickable nodes labelled
  `"Chọn năm"` at `[22,160][170,229]` and `[177,160][285,229]`, then a day grid from
  y=344; no node labelled "Tháng sau"/"Tháng trước" and no clickable unlabelled node near
  the `next_month_xy` fallback point. How the app shows next-month days is unknown until a
  target date falls in the next month (first on 2026-10-30).

## Consent and confirmation

- The consent checkbox has no label and `checkable=false`: it is the clickable View left of
  the caption `"Tôi đã hiểu và đồng ý với "`, found in the dump as the smallest clickable
  node level with the caption (`geometry.is_checkbox_beside`).
- At 540x1600 it was at `[35,1323][79,1367]` (seen shifted to x=43 once), so it is located
  per run, never stored.
- "Xác nhận" is disabled until the checkbox is ticked; used to verify the tick.
- Up to 0.6.1 success was the confirmation screen disappearing; since 0.6.2 it is the
  ticket's title showing. A notice dialog hides the confirmation screen too: the dialog's
  title node `'Thông báo'` spans `[0,33][540,1600]` and holds the message and a clickable
  `'Đóng'`; the page beneath leaves the dump (8 elements in all, seen 2026-10-10 for the
  monthly quota).
- After "Xác nhận" (two accounts on 2026-10-15 20:50, the second one booking the slot
  first): the confirmation page stays about 0.75-1.0 s while the server answers, then a
  frame without any label of the app shows (5 elements: the full-screen root and the
  status bar; +0.94 s), then either the ticket or, here, the notice "Tiện ích đã hết chỗ,
  vui lòng chọn vị trí/thời gian khác" with `'Đóng'` (+1.04 s). The same empty frame was
  the first read at 16:44 on a booking that went through, so it says nothing about the
  outcome. On 2026-10-14 round 1 (18-19) was logged as
  booked but was not: round 2 then needed 11 s and 169 commands to get back to "Sân Tennis"
  (other days 0.6-0.8 s, one Back from the ticket), so a dialog had replaced the page.
  Since 0.5.1 such a round fails with the app's message.
- "Xác nhận" swallowed (2026-10-19, timed real bookings with load added on our side:
  outbound lag and packet loss on the PC, busy loops in MuMu): in 2 of 26 rounds the page
  stayed exactly as it was for 30 s after "Xác nhận" (0.20 s after the tick, the button
  enabled), with no ticket. With 0.5 s lag no ticket came at all; with 2.5 s lag, 10% loss
  and CPU load the user tapped "Xác nhận" by hand afterwards and got the ticket at once.
  While the server answers a tap it took, the page stays unchanged too, so a read cannot
  tell the two apart. No round without load or at 06:00 was swallowed. A "Xác nhận" 79 ms
  after the tick was swallowed the same way (2026-10-20). Since 0.8.3 "Xác nhận" is tapped
  again every 3 s while the page still shows it enabled; a second tap while the server was
  still answering the first booked the slot once, with no notice (2026-10-20, 1.5 s lag).
- The ticket after "Xác nhận": 0.66-1.6 s at 06:00 (7 taps, 15-20/10), 0.9-1.1 s without
  load, 0.7-2.7 s with 0.2-0.8 s outbound lag (2026-10-20), 1.7-6.6 s with 0.5-1.5 s lag and
  15.4 s with 2.5 s lag, CPU load and 10% loss (2026-10-19), more than 10 s once with a slow
  server at midday (see "App and server timings").
- Before "Xác nhận" the page already names what it books, in one label `[0,210][540,775]`
  (2026-10-14 and 15, every read):
  `'Sân Tennis\nThời gian đặt lịch\n17/10/2026 15:00 - 16:00\nVị trí/dịch vụ\n'`
  `'S6 - Sân tennis\nThông tin thanh toán\n...'`. Since 0.6.1 the round reads the date,
  slot and court there (no extra command), logs them, and only warns when they differ from
  the target; it confirms anyway, and the court shown goes into the `slot_booked` event.

## Ticket screen

Real test booking on 2026-10-14, 540x1600: the first read 0.9 s after "Xác nhận" held only
the title `'Chi tiết đặt lịch'` `[99,52][311,89]` and a back button; once loaded it adds
`'qr code'`, `'Thông tin dịch vụ'`, the status `'Đã đăng ký'`, one node `[0,642][540,1463]`
whose label lists the utility, booking and transaction codes,
`'Thời gian đặt lịch\n16/10/2026 10:00 - 11:00'` and `'Vị trí/dịch vụ\nS6 - Sân tennis'`,
and a clickable `'Đặt lịch khác'` at the bottom. At 06:00 on 2026-10-15 the first read
(0.8 s after "Xác nhận") already held the title, `'Đặt lịch khác'` and the status
`'Đang xử lý'` `[407,154][499,177]`, but no time or court yet. In all four real bookings
seen (2026-10-14 08:32, 10:46, 11:01; 2026-10-15 06:00) the title was in that first read,
the one that ends the round. The round notes the status from that read only (waiting for
the full ticket would delay the next round). Since 0.6.2 the title is required: a read
without it, such as the empty frame seen at 16:44 on 2026-10-15, is read again.

## Dialogs

- Outside 06:00-21:00, tapping "Sân Tennis" opens a dialog "Thông báo": "Ban quản lý BQL
  Grand Park chỉ nhận đăng ký Sân Tennis từ 06:00 đến 21:00 mỗi ngày" with a "Đóng"
  button; it hides the utilities list. The 06:00:00.0 tap of 0.3.0 did not trigger it on
  2026-10-10. On 2026-10-19 a tap at 05:59:59.244 by the PC clock, up to 0.76 s early by
  NTP time (see "Emulator"), got it 0.05 s later (four elements: the full-screen root, the
  title spanning `[0,33][540,1600]`, the message, "Đóng"); the round waited 10 s for the
  calendar and failed. Back closed it and the list showed 0.1 s later. A tap at PC
  05:59:59.92 got the calendar on 2026-10-17, initially suggesting a server-clock check.
  On 2026-10-20 the notice still appeared after a start at NTP 06:00:00.100 while the PC
  clock read 05:59:59.975; a later tap opened the calendar. These observations do not
  establish which clock the app checks. Comparing the server and emulator clocks around
  closing time was proposed, but no result establishing the clock source is recorded here.
  Since 0.8.1 the round closes any notice after the utility tap with Back and taps again,
  about 0.2 s a try, until `open_retry_seconds`.
- Each apartment may book 2 slots per day and 8 per month (1 hour = 1 slot; the user,
  2026-10-20). Once either is used, tapping "Tiếp tục" on the calendar opens a dialog
  "Thông báo": "Căn hộ đã hết hạn mức đăng ký tiện ích cho phép." with a "Đóng" button (seen
  2026-10-10; on 2026-10-20 for a day that already held 2 tickets); the round then fails after
  the re-taps with "Tapped 'Tiếp tục' but the next screen did not appear". On 2026-10-16
  the same dialog showed only after "Xác nhận" (0.72 s after the tap), so the round failed
  with its message.

## App in English (2026-10-20)

The app shows English when it is set to English in the app. Every screen keeps its layout,
its positions and its order; only the labels differ. Read on 2026-10-20 by walking each
screen, then by booking 21/10 10:00-12:00 on S10 for real in two rounds (cancelled):

| `Labels` field | Vietnamese | English |
|---|---|---|
| `home` | Tiện ích | Utilities |
| `utility` | Sân Tennis | Tennis |
| `continue` | Tiếp tục | Next |
| `fully_booked` | Hết chỗ | Full |
| `confirm_page` | Xác nhận đăng ký | Confirm registration |
| `agree` | Tôi đã hiểu (caption `Tôi đã hiểu và đồng ý với `) | I have read (caption `I have read, understood, and agree to `) |
| `confirm` | Xác nhận | Confirm |
| `booked_time` | Thời gian đặt lịch | Schedule time |
| `booked_place` | Vị trí/dịch vụ | Place/service |
| `ticket` | Chi tiết đặt lịch | Booking details |
| `processing` | Đang xử lý | Processing |
| `registered` | Đã đăng ký | Registered |
| `notice` | Thông báo | Notification |
| (dialog button) | Đóng | Close |
| (ticket button) | Đặt lịch khác | Book another time |

- Calendar: title "Register utility", a heading "Tennis" that is not clickable, "Select
  year" twice, "Select expected date of use" until a day is picked, then "Available time
  frame". A day reads `21, Wednesday, October 21, 2026` (the month by name); slots read as
  in Vietnamese (`09:00 - 10:00`, `18:00 - 19:00\nFull`). The month buttons have no label,
  as in Vietnamese.
- Court list: "Service information", "View more", "Select place/service", then the courts
  with their Vietnamese names (`S10 - Sân tennis`, `S9 - Sân tennis\nFull`) and a
  "Directions" button each. It moved up once loaded, as in Vietnamese. No venue screen
  showed. The booking details page names the court and has "Next".
- The confirmation page and the ticket hold one label such as `Tennis\nSchedule
  time\n21/10/2026 10:00 - 11:00\nPlace/service\nS10 - Sân tennis\n...` (the ticket adds
  "Scheduling code" and "Transaction ID"): the date, time and court read as in Vietnamese.
  The consent checkbox is the same unlabelled node left of its caption (tick at x=57).
- The quota notice: "Notification", "The apartment has reached the allowed utility
  registration quota.", "Close". The closed-hours notice (after "Tennis" on the utilities
  list, 2026-10-20 21:00): "The BQL Grand Park Management Board only accepts Tennis
  registration from 06:00 to 21:00 everyday", with "Close"; the booker reads it as "not open
  yet" in English too.
- The two real rounds (13:27, a uiautomator2 script, not the booker): the slot list 1.1-1.3 s
  after the day tap, the court list 2.5 s after "Next", "Confirm" enabled 0.21-0.27 s after
  the tick, the ticket's title 0.82-1.04 s after "Confirm" (round 2's first read showed
  "Processing", the next "Registered"), and one Back to "Utilities list" in 0.3 s.
- Whole labels tell the languages apart: "Tennis" is clickable only on the utilities list,
  and "Registered" is not the "Registered information" heading of a loading ticket.
- Back on the calendar, after a notice was closed there and after Back from the court list,
  left the calendar only the second time.

## Emulator (MuMu)

- Screen: MuMu custom resolution **540x1600**, 220 DPI (since 2026-10-09; was the tablet
  mode 960x540 shown as 540x960 portrait, where `window_size()` wrongly returned
  (960, 540)). Never use hard-coded coordinates; the screen size comes from the dump.
- Command cost: `dump_hierarchy` 69 ms (whole screen), `exists` 41 ms, `info` 60 ms, regex
  `info_list` 105-177 ms, `window_size` 125 ms. uiautomator2 `click()` on a selector is
  wait + info + click.
- Taps (measured 2026-10-16, quiet hours): uiautomator2 `click(x, y)` takes 151-165 ms,
  since Android's `UiDevice.click` holds the touch about 100 ms; `touch.down` + `touch.up`
  takes 83-91 ms, and the app took every such tap (20/20 on "Tiện ích", 24/24 dry rounds to
  the confirmation page, 2/2 real bookings with the ticket 0.92 and 0.81 s after "Xác
  nhận"). Dry round 1 median 3.39 s vs 4.16 s with `click`. Used since 0.7.0.
- Tried the same day and dropped: a kept-alive HTTP connection to the uiautomator server
  (screen read 90 ms vs 75 ms), compressed dumps (63 vs 61 ms, same 91 nodes), waiting with
  `waitForWindowUpdate` (on a still screen it either timed out or reported a change after
  50 ms). A screen read is the dump (60-75 ms); parsing it takes 1.2 ms.
- The MuMu clock follows the PC clock (+15 ms measured); the NTP offset of the PC varies
  (+0.035 to +0.144 s; +0.34 s on 2026-10-15 at 22:00 from time.google.com,
  time.windows.com and pool.ntp.org alike). time.google.com timed out once (2026-10-15
  20:09) and the run used the PC clock; since 0.6.2 other servers are asked.
- One NTP answer can be off by half its round trip. At 10:00 on 2026-10-19 a check that
  took 0.57 s (the DNS lookup was timed with it until 0.8.1) read the PC clock 0.531 s
  fast and one 88 s later 0.462 s; quick answers (40-65 ms) from time.google.com,
  time.windows.com and time.cloudflare.com read 0.413 s minutes later, within 2 ms of
  each other. The PC clock drifted from -0.004 s at 08:34 to about -0.41 s by 10:15, with
  Windows Time "not synchronized" since 05:50:21. Since 0.8.1 a check keeps the quickest
  of four answers (0.4-0.5 s a check).
- Windows Time sets the PC clock on its own schedule (System log, Time-Service event 37):
  on 2026-10-19 at 05:50:21 (time.windows.com), 18 s after the run measured the PC clock
  0.757 s slow, the largest offset seen (0.12-0.21 s on 10-18/10). An error under 1 s
  (`MaxAllowedPhaseOffset` = 1) is slewed, not stepped (no Kernel-General event 1): at
  08:34 the offset was -0.004 s. The run still added 0.757 s at 06:00, so the tap came up
  to 0.76 s early. On 10-18/10 no synchronisation fell between the check and 06:00 (on
  14/10 it came at 05:49:28). Since 0.8.1 the run waits by NTP time carried forward on
  `perf_counter`, which Windows does not set, and checks again at the warm-up.
- Android animations were already off (removed in MuMu's Android settings on 2026-10-12);
  `Booker.prepare` turns them off anyway.
- MuMu froze twice on 2026-10-13 during dry runs (11:13, and 11:58 right after a restart),
  both times around the court list and booking details screens: `MuMuNxDevice` showed "Not
  responding", `dumpsys window` and app starts hung, and `MuMuManager control shutdown` did
  not end it; the user restarted MuMu by hand. A run then hung inside a uiautomator2 call
  (11:58: five reads 10 s apart, then nothing) until Task Scheduler ended it, and the
  history showed it as interrupted without a reason. Since 0.6.1 a device command that
  takes over 60 s ends the run with "MuMu did not answer ..." (log and history, lock
  released, exit code 3); MuMu is not restarted and the round is not retried.
- `MuMuManager control -v 0 shutdown` on a running MuMu (2026-10-16 16:08, after a timed
  real run): the command returned at once and the run exited 0.6 s after "Closing MuMu";
  `MuMuNxDevice` was gone within 18 s, and the next run started MuMu again in 24 s. On a
  frozen MuMu it answers errcode 0 but does nothing (16/10 15:14 and 17:36, both during
  heavy test runs): `MuMuNxDevice` must be ended by hand. Since 0.7.0 a real run closes
  MuMu this way; a frozen run never tries.

## Accessibility agent (tried and dropped, 2026-10-18)

A throwaway AccessibilityService APK (Java, 25 KB) on MuMu's Android 15, then a fuller
one driving real rounds. It read the screen in 3 ms (uiautomator2: 80 ms) and tapped by
label, but **the Vinhomes app refuses to book while an accessibility service is
enabled**: right after "Xác nhận" (two timed real bookings, 20/10 10:00-12:00) it showed
a dialog titled `'Cảnh báo'` instead of the ticket: "Thiết bị đang sử dụng ứng dụng không
được phép dev.courtbooker.agent. Vui lòng tắt quyền 'Accessibility' hoặc gỡ ứng dụng này
để tiếp tục", with `'Gỡ bỏ'` and `'Cài đặt'`; no booking was made. Every step before
"Xác nhận" worked, dry runs too, and the app showed nothing at all until that point. With
the agent uninstalled and the setting cleared, the 0.7.0 runner booked both slots the same
afternoon without the dialog. The app checks for accessibility services at the
confirmation; getting around that check is out of scope, so the idea was dropped.

What the experiment showed, kept in case the numbers matter:

- Reading the whole screen took 3 ms on the device (6.7 ms to the PC), against 80 ms for
  uiautomator2; tapping "Tiện ích" until "Sân Tennis" showed took about 365 ms against
  515 ms, about 150 ms a step. Waiting on accessibility events, a tap came 2-20 ms before
  the first event.
- uiautomator2 (3.x, a server started with `app_process`) and an accessibility service
  cannot run together: Android unbinds the service while uiautomator2 runs.
- After a MuMu restart an enabled service is not bound ("user 0 is stopped"), until the
  package's activity has been opened and the setting written again.
- `findAccessibilityNodeInfosByText` finds nothing in the Flutter app; labels are in
  `contentDescription`.
- The app takes a slot a few frames after the tap (agent clicks, dry rounds): a "Tiếp tục"
  11-40 ms after the slot click booked the slot selected before (3 of 3), one 60 or 100 ms
  after it the slot clicked (12 of 12). uiautomator2's taps were never that close.
- A tap by label cannot miss a court that moved, but a round with the agent still opened
  S9 once (2026-10-18): the court check on the booking details page is what catches it.
- Taps written to `/dev/input/event4` (the ADB shell may write there; 0.1 ms a tap) came
  out like the other ways to tap once the same change detection was used (402, 417 and
  428 ms from the tap to the next screen).

## Instrumentation driver (2026-10-18)

The agent's place went to an instrumentation (`docs/architecture.md`, "Driver"): its own
APK started with `am instrument`, which gets UiAutomation, the connection uiautomator2
uses. It is not an accessibility service: while it runs, `enabled_accessibility_services`
stays `null` and `dumpsys accessibility` lists no bound or enabled service;
`accessibility_enabled` reads 1 (0 once it stops), as with uiautomator2.

- **The app books with it running.** A probe (touch taps) booked 20/10 10:00-11:00 at
  18:44 without the `'Cảnh báo'` dialog, the ticket 0.86 s after "Xác nhận"; the driver
  itself (accessibility clicks by label) booked 10:00-11:00 and 11:00-12:00 at 19:26.
- Reading the screen took 13 ms to the PC with the XML parsed (median of 10, 8-31 ms, 72
  elements), against 99 ms with uiautomator2 (87-202) the same evening; a command round
  trip 2.3 ms. The first read after the app started took 175 ms, and a read after clearing
  UiAutomation's node cache 67 ms. From the tap on "Tiện ích" to "Sân Tennis" showing:
  443 ms reading every 20 ms as the flow does, 417 ms waiting on accessibility events on
  the device, 495 ms with uiautomator2 (n=10 each): events gain little over fast reads.
- `am instrument -w` must keep running: its process holds the UiAutomation connection.
  Started with `setsid nohup ... &` it outlives the adb shell. Only one UiAutomation runs at
  a time: a uiautomator2 server running must be ended first, and uiautomator2 cannot
  connect while the driver runs. After a run stops it, uiautomator2 reads the screen again.
- Start: the first install took 4.1 s, the driver answered 1.0-1.4 s after `am instrument`
  (0.8-2.5 s in the probe). An installed APK is the file sent (`sha256sum` of `base.apk`).
- **"Xác nhận" 65 ms after the consent tick did nothing** (probe round 2, the page stayed
  for 10 s, no dialog); 97 ms after it booked. uiautomator2 reads too slowly to come that
  close (0.14-0.23 s). With 0.2 s from the tick, accessibility clicks on "Xác nhận" booked
  both rounds at 19:26, so the agent's "page stayed" after one such click (14:25) was this,
  not the click.
- A real round at 19:26 took 4.8 s (138 commands; reads are cheap, so there are more of
  them) and 3.9 s (77), against 7.0 s and 4.9 s for uiautomator2 at 19:08 (S6, not S10):
  the steps that only wait for a screen to show (calendar, day, details, confirmation)
  came 0.1-0.6 s sooner each.

## App and server timings

- Calendar 0.14 s after "Sân Tennis", slot list ~2.1 s after the date tap, court list
  1.5-2.0 s, details 0.5 s, confirmation 0.14 s.
- Slow server, 2026-10-19 around 10:03: court list 4.3 s after "Tiếp tục", the details
  page's "Tiếp tục" 7.7 s after the court tap, the ticket more than 10 s after "Xác nhận"
  (the round, given up at 10 s, was booked all the same); at 10:18 the ticket took 7.7 s.
  The user, who booked by hand many times, never saw a step take 30 s, busy days included;
  since 0.8.2 every screen is awaited up to 30 s (`timeout`).
- "Tiếp tục" on the calendar showed enabled in the same read as the slot list in 77 reads
  on 14-18/10; at 06:00:10.463 on 2026-10-19 the list showed with it still disabled, and
  the round, which looked for it in that read, failed with "Button not found". Since 0.8.1
  the list is read again until the button is enabled (up to 2 s) before the slot tap.
- Round 1 took 1.3-2.0 s from "Sân Tennis" to the calendar at 06:00 on 2026-10-10 to 14,
  0.3-0.7 s at other times, also after long waits: mostly server load at 06:00. 0.5.3 opens
  the utilities list 60 s before the start; compare after the change.

## Verified runs

| Version | Date | What was checked |
|---|---|---|
| 0.2.0 | 2026-10-08 | Dry run with MuMu closed, `--at` timed run, and a scheduled task run that woke the PC and booked two real slots (rounds took 6-9 s; the PC clock was 0.87 s slow, corrected by NTP). The app accepted real bookings with Android developer mode on |
| 0.3.0 | 2026-10-09 | Timed dry run on MuMu at 540x1600: round 1 reached the accepted terms in 5.9 s (8.7 s with 0.2.0) |
| 0.3.0 | 2026-10-10 | First real 06:00 run: both slots booked; round 1 took 7.3 s (booked at 06:00:07.2, 0.2.0 needed 11.0 s), round 2 4.5 s (06:00:11.7, 0.2.0: 7.1 s). Rounds used 41-43 device commands including polls while the app loads; no closed-hours popup, no re-taps |
| 0.4.0 code | 2026-10-11, 12 | 06:00 task booked both slots each day: rounds 10.5 s + 4.3 s (11/10) and 7.0 s + 4.3 s (12/10). On 11/10 the court list appeared 2.3 s after "Tiếp tục", so the 2 s re-tap fired once (92 commands in round 1); the booking still succeeded |
| 0.5.0 | 2026-10-13 | Released with 287 tests; dry runs on MuMu wrote correct history; `POST /api/runs/dry-run` started a dry run with MuMu off; live feed steps reached a real client within 0.5 s |
| 0.4.0 | 2026-10-14 | 06:00 run logged 18-19 as booked, but the app had refused it (fixed in 0.5.1) |
| 0.5.2 | 2026-10-14 | Real booking 16/10 10:00-11:00 (cancelled afterwards) logged all 24 screens up to the ticket |
| 0.5.3 | 2026-10-14 | Timed real booking 16/10 11:00-12:00 (cancelled afterwards): start 10:46:21, "Tiện ích" at start - 60 s (list loaded in 0.63 s), read at start - 2 s, "Sân Tennis" tapped 1 ms after the start, booked in 6.0 s. The runner moved to v0.5.3 the same day |
| 0.6.1 code | 2026-10-15 | Timed real booking 17/10 at 16:44 (cancelled afterwards): 09:00-10:00 failed (court S6 fully booked), 10:00-11:00 booked in 8.6 s; the confirmation page read "2026-10-17 10:00 - 11:00 on S6"; the first read 0.9 s after "Xác nhận" was blank (5 elements), so the ticket warning showed. A run at 16:40 found both evening slots fully booked |
| 0.6.2 code | 2026-10-16 | Timed real booking 18/10 at 11:38 (cancelled afterwards): 10:00-11:00 booked in 5.7 s, the ticket's title in the first read 0.92 s after "Xác nhận" (status "Đang xử lý"); round 2 left the ticket with one Back and tapped "Sân Tennis" 0.32 s after it started; 11:00-12:00 reached "Xác nhận" and the app refused it with the monthly quota dialog 0.72 s later, which failed the round with the dialog's message. The clock check answered on the first try |
| 0.7.0 code | 2026-10-16 | Dry run at 16:04 (MuMu left open), then a timed real booking 18/10 at 16:08 (a test booking): 10:00-11:00 booked in 5.7 s with touch down + up taps; 11:00-12:00 reached "Xác nhận" and the app refused it with the monthly quota dialog. In that round the tap on S6 landed on S9 (the court list moved, see "Booking flow"). "Closing MuMu instance 0" after the summary; the process exited 0.6 s later and `MuMuNxDevice` was gone within 18 s |
| 0.7.0 + court check (`main`) | 2026-10-18 | Timed real booking 20/10 at 13:25 (test bookings): 10:00-11:00 booked in 9.4 s (50 commands) and 11:00-12:00 in 6.9 s (39), both on S6. In both rounds the tap on S6 opened S9; the details page check went back and tapped S6 where the moved list showed it (see "Booking flow"). MuMu closed after the summary |
| 0.7.1 | 2026-10-18 | Dry run at 19:03: round 1 found S6 fully booked (a test booking held it), round 2 reached the accepted terms on S6. Then a timed real booking 20/10 at 19:08 (test bookings): 10:00-11:00 booked in 7.0 s (54 commands) and 11:00-12:00 in 4.9 s (38), both on S6 with no court opened by mistake. MuMu closed after the summary |
| 0.8.0 code (driver) | 2026-10-18 | Dry run at 19:20 that started MuMu: the driver installed in 4.1 s and answered 1.4 s after its start; every step to "Tiếp tục" by accessibility clicks, then the monthly quota dialog (test bookings). After a cancellation, a timed real booking 20/10 at 19:26 on S10 (test bookings): 10:00-11:00 booked in 4.8 s and 11:00-12:00 in 3.9 s, every click an accessibility click by label, "Xác nhận" 0.20 s after the tick. The driver stopped after the run; MuMu closed after the summary |
| 0.8.0 | 2026-10-18 | Dry run at 19:39 (S10, 20/10 10:00-12:00): the driver answered 1.5 s after its start; both rounds reached the accepted terms (5.3 s and 3.8 s); the driver stopped after the run (no process, no forward, `accessibility_enabled` 0) |
| 0.8.1 code (`fix/opening-race`) | 2026-10-19 | Timed real bookings 21/10 on S6 (test bookings). At 10:02:57, before the NTP sampling fix: checks -0.531 s (a 0.57 s check) and -0.462 s at the warm-up, "Start reached at 10:02:57.100 (NTP), PC clock 10:02:57.562", no notice; the server was slow (court list 4.3 s, details 7.7 s) and no ticket showed within 10 s of "Xác nhận" in either round ("Outcome unknown"; one of the two was booked). At 10:15 checks 89 s apart left the anchored time off by +0.003 s (both slots taken). At 10:18:08: checks -0.398 s and -0.404 s (+0.006 s off), start reached at 10:18:08.100 (NTP); 10:00-11:00 booked in 18.9 s (ticket 7.7 s after "Xác nhận", "Đang xử lý") and 11:00-12:00 in 7.0 s (2.4 s). "Tiếp tục" showed enabled with the slot list and no notice showed, so neither new path ran. MuMu closed after the summary |
| 0.8.1 | 2026-10-19 | Timed dry run at 10:29 (S6, 21/10 10:00-12:00): clock checks -0.387 s at the start and at the warm-up 89 s later (anchored time off by +0.000 s), start reached at 10:29:25.100 (NTP), PC clock 10:29:25.487; both rounds reached the accepted terms (7.5 s and 8.1 s, 66 and 44 commands) |
| 0.8.2 code (`fix/screen-timeout`) | 2026-10-19 | Timed real booking 21/10 at 11:21 on S6 (test bookings), `timeout = 30`: start reached at 11:21:28.100 (NTP); 10:00-11:00 booked in 7.2 s (75 commands) and 11:00-12:00 in 6.7 s (69), each ticket 1.1 s after "Xác nhận", which came 0.23 s and 0.20 s after the tick. No screen came near the old 10 s limit, so the longer wait did not come into play |
| 0.8.2 | 2026-10-19 | Timed dry run at 11:33 (S6, 21/10 10:00-12:00): start reached at 11:33:03.101 (NTP); in round 1 the slot list showed with "Tiếp tục" disabled and the slot was tapped once it was enabled, 0.09 s later (the first time on the app); both rounds reached the accepted terms (6.8 s and 5.9 s). A dry run at 11:30, with the test tickets not cancelled yet, got the monthly quota notice after "Tiếp tục": not recognised at that step, it took each round 30 s to fail |
| 0.8.3 code (`fix/confirm-retap`) | 2026-10-20 | Timed real bookings 21/10 10:00-12:00 on S10 (test bookings, cancelled between runs). At 12:05, with the least wait from the tick to "Xác nhận" set to 0 for the test: in round 1 the button showed enabled late, "Xác nhận" came 0.48 s after the tick and booked (8.9 s); in round 2 it came 79 ms after the tick, the app swallowed it, the page stayed unchanged, "Xác nhận" was tapped again 3.03 s later and the ticket showed 0.64 s after that (10.0 s). At 12:10 with 1.5 s outbound lag and 5% loss: round 1 tapped "Xác nhận" again after 3.0 s and the ticket showed 5.3 s after the first tap, 2.3 s after the second, with no notice; the app held one ticket per slot (rounds 20.5 s and 16.1 s). At 12:16 without load: 8.8 s and 5.8 s, tickets 1.0 s and 0.9 s after "Xác nhận", no second tap |
| 0.8.3 | 2026-10-20 | Timed dry run at 12:28 (S10, 21/10 10:00-12:00): clock checks +0.455 s at the start and at the warm-up 83 s later (anchored time off by +0.001 s), start reached at 12:28:00.100 (NTP), PC clock 12:27:59.645; both rounds reached the accepted terms (6.6 s each, 57 and 47 commands) |
| 0.9.0 code (`feat/app-english`) | 2026-10-20 | Timed real bookings 21/10 10:00-12:00 on S10 (test bookings, cancelled). At 13:53 with the app in English: "App language: English", both rounds booked (7.6 s and 4.8 s), the confirmation page read in English, "Confirm" 0.20 s after the tick at x=57, the ticket 1.5 s and 0.8 s after it, no second tap. At 13:57 with the app in Vietnamese: "App language: Vietnamese", both booked (6.6 s and 4.8 s), the ticket 0.9 s after "Xác nhận" |
| 0.9.0 | 2026-10-20 | Timed dry run for 20:57:45 (S10, 21/10 10:00-12:00), app in Vietnamese: "App language: Vietnamese"; MuMu was started by the run (Android after 47.5 s), so the start was reached at 20:57:47.775 (NTP), 2.8 s late; clock offset +0.177 s, anchored time off by +0.000 s at the warm-up; both rounds reached the accepted terms (10.9 s and 9.1 s, 33 and 62 commands). Closed-hours run at 21:00:50 with the app in English (`open_retry_seconds = 10`, same slots): "App language: English", the English notice read as "not open yet", "Tennis" tapped 48 and 74 times, both rounds failed "not open" after 10 s as expected, MuMu closed at the end |
| UI part 3 | 2026-10-14 | Requests through the Vite proxy, and the live feed across a backend stop and restart (no step lost or repeated), against a scratch backend |
