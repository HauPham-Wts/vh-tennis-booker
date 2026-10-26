# Field notes

What the Vinhomes Resident app and the MuMu emulator do, as measured on the development
machine. The code relies on these facts; the app can change without notice. How the code uses
them: [how-it-works.md](how-it-works.md), [architecture.md](architecture.md).

## Booking flow (app screens)

Home ("Tiện ích") → Utilities list ("Sân Tennis") → Calendar (date, then the slot list; slot;
"Tiếp tục") → venues ("Chọn phân khu", optional) → Court list ("Chọn vị trí/dịch vụ") → Booking
details ("Số lượng cư dân", "Tiếp tục") → Confirmation (consent checkbox, "Xác nhận") → Ticket.
One Back from the ticket returns to the Utilities list, where the next round starts.

- The calendar, venues, court list and details page share the title "Đăng ký tiện ích", so each
  is known by a label of its own (above). The venues and the court list are one page, below
  "Thông tin dịch vụ".
- With a single venue (`'Origami_ Sân tennis'`) the app moves on to the courts by itself within
  a fraction of a second; a read may catch the venues or not, and a read right after the venue
  tap may still show them. A heading can show a read before its entries (8 of 30 reads for the
  venues). The details page's caption shows about 24 reads before its "Tiếp tục" is enabled.
- Back: each screen shows 0.13-0.24 s after Back, at times after an empty frame (the root and
  the status bar only). The status bar's labels change on their own, so they never tell screens
  apart. A notice dialog closes back to the page beneath ("Đóng" or Back). Back on the home
  screen leaves the app.

## Reading the app

- Flutter exposes text in `content-desc`, not `text`, and builds lazily: off-screen elements
  are absent and bounds are clipped to what shows.
- Day label: `2, Thứ Sáu, 2 tháng 10, 2026`. Slot: `09:00 - 10:00`; full: `18:00 - 19:00\nHết
  chỗ`; a full court: `S9 - Sân tennis\nHết chỗ`. 13 slots (06-12, 14-21) fit at 540x1600 without
  scrolling. Bookable: today to today + 2.
- The slot selection is not in the tree. The app takes a tap a few frames later: "Tiếp tục"
  11-40 ms after the slot tap booked the slot selected before, 60-100 ms after it the slot
  tapped (the flow waits 0.1 s). "Tiếp tục" usually shows enabled in the same read as the slot
  list, but once (06:00:10, 2026-10-19) the list showed with it still disabled.
- A month shows only its own days (no days of the next month on its last row), so a date in
  the next month needs the next-month button. The calendar opens on the current month.
- The month buttons, `‹` and `›` right of "Tháng 10 ▾ 2026 ▾", are unlabelled `Button`
  nodes at 540x1600: `‹` [403,162][469,228], `›` [469,162][535,228] (2026-10-25). Both are
  greyed out and not clickable while that month has no bookable day. `next_month_xy` and
  `prev_month_xy` tap their middles; the driver clicks the smallest clickable element at the
  point, so a point right of x 469 is the next-month button. Switching to a month with
  bookable days is unverified: first possible on 30/10 for 1/11.

## Court list moves under the tap

The court list can show before the "Thông tin dịch vụ" block above it has loaded. Once it loads
("Xem thêm" appears) the whole list moves up 232 px, so a tap placed from the read before lands
two courts lower: a tap at S6's first centre (y=1217) opened S9 (booked by mistake on 13/10 and
17/10). The read just before the tap can show the old layout, so a dump cannot predict it; the
first court is no safer (S10's centre falls on S8 after the move).

The booking details page names the court it opened (a non-clickable label, 0.23-0.45 s after
the tap, before its "Tiếp tục"). The flow checks it there, goes back and taps again; each wrong
court costs about 1.5 s.

## Consent and confirmation

- The consent checkbox has no label: it is the smallest clickable node level with the caption
  `Tôi đã hiểu và đồng ý với ` (seen at `[35,1323][79,1367]`, once shifted to x=43), so it is
  located per run. "Xác nhận" is disabled until it is ticked.
- The app takes the tick a few frames after "Xác nhận" shows enabled: "Xác nhận" 65-79 ms after
  the tick did nothing (the page stayed), 97 ms after it booked (the flow waits 0.2 s).
- Before "Xác nhận" the page names what it books in one label: `Sân Tennis\nThời gian đặt
  lịch\n17/10/2026 15:00 - 16:00\nVị trí/dịch vụ\nS6 - Sân tennis\n...`.
- After "Xác nhận": the page stays about 0.75-1.0 s while the server answers, then a frame
  without any app label, then the ticket or a notice. The empty frame shows on both paths, so
  the page going away proves nothing (a round was logged booked by mistake on 2026-10-14).
- The ticket's title showed 0.66-1.6 s after "Xác nhận" at 06:00, more than 10 s once with a
  slow server at midday.
- "Xác nhận" can be swallowed under load: in 2 of 26 loaded rounds (lag, packet loss, CPU) the
  page stayed unchanged for 30 s and a tap by hand then booked. The page also stays while the
  server answers, so a read cannot tell the two apart. A second tap while the server was still
  answering the first booked the slot once, with no notice.

## Ticket screen

The first read after "Xác nhận" holds the title `Chi tiết đặt lịch` and, at 06:00, often the
status `Đang xử lý` but no time or court yet; later the status `Đã đăng ký`, the codes, time,
court and a clickable `Đặt lịch khác`.

## Dialogs

All are titled "Thông báo": the title node spans `[0,33][540,1600]` and holds the message and a
clickable "Đóng"; the page beneath leaves the dump.

- **Closed hours** (a tap on "Sân Tennis" before 06:00 or after 21:00): "Ban quản lý BQL Grand
  Park chỉ nhận đăng ký Sân Tennis từ 06:00 đến 21:00 mỗi ngày". Back closes it and the list
  shows 0.1 s later. The app most likely checks the MuMu clock: on 2026-10-24, with MuMu 0.71 s
  behind NTP time, taps every 0.35 s still opened the calendar at 21:00:00.73 NTP (21:00:00.02
  on MuMu) and got the notice from 21:00:01.14 NTP on, 0.05 s after the tap like the calendar.
  The flow closes it and taps again until `open_retry_seconds`.
- **Quota**: each apartment may book 2 slots a day and 8 a month; once either is used the app
  shows "Căn hộ đã hết hạn mức đăng ký tiện ích cho phép." (the same message for the day and the
  month), usually after the calendar's "Tiếp tục" (0.9 s after the tap, 2026-10-24), once after
  "Xác nhận" (0.72 s after the tap). The flow knows it by `quota_full` ("hết hạn mức") and the run skips the rounds left,
  which book the same day.
- **Slot taken** (someone booked it first): after "Xác nhận", "Tiện ích đã hết chỗ, vui lòng
  chọn vị trí/thời gian khác".

## Other sports (Origami)

Surveyed 2026-10-26 with an account of the Origami subdivision, app in Vietnamese. The
utilities list ("Danh sách tiện ích", section "Tiện ích Vinhomes Grand Park") holds ten
clickable tiles; eight are courts, booked the same way as tennis (the other two, "Nhà Tập Golf
Vip" and "Nướng BBQ", are out of scope). Only "Sân Tennis" has a capital T.

- The calendar is the same for all eight: "Đăng ký tiện ích", the utility's name, today to
  today + 2, "Khung giờ khả dụng", 13 one-hour slots (06-12, 14-21), "| Hết chỗ", "Tiếp tục".
- The quota counts per utility: with the tennis quota used, the quota notice showed after the
  calendar's "Tiếp tục" for tennis only; the other seven went on.
- A page with a single choice passes on to the next by itself, as the tennis venue does
  (above): a venue page with one venue, a court list with one court. It shows for a moment,
  so a read may catch it or not; it stays when the app is slow, and shows after Back. So after
  "Tiếp tục" the first page read may be the venues ("Chọn phân khu"), the court list ("Chọn
  vị trí/dịch vụ") or, for a utility with a single court, its booking details page (its
  name, "Số lượng cư dân", "Tiếp tục"). Seen: table tennis and pickleball went to the details
  page in the survey, and pickleball's list of one court was read in a dry run; the
  multi-purpose courts' single venue ("Origami _ Sân đa năng") was read in a dry run only
  (2026-10-26). The details and confirmation pages are the same as tennis.
- A full court still shows on the list ("| Hết chỗ"), so the lists below are complete. Courts
  are shown as the app lists them for an Origami account, whatever their S prefix.

| Tile | Court list | Courts |
|---|---|---|
| Sân Tennis | list | S10, S6, S8, S9 - Sân tennis |
| Sân đa năng | list | S10, S7, S9 - Sân đa năng |
| Sân bóng chuyền | list | S10 - Sân bóng chuyền hơi 01, S10 - Sân bóng chuyền hơi 02, S8 - Sân bóng chuyền hơi, S9 - Sân bóng chuyền hơi |
| Sân bóng bàn | one court, passes by itself | S5 - Sân tập bóng bàn 03 |
| Sân bóng rổ | list | S10 - Sân bóng rổ nửa sân 03, S10 - Sân tập bóng rổ 01, S6 - Sân bóng rổ tập ném 01, S6 - Sân bóng rổ tập ném 02, S8 - Sân bóng rổ nửa sân, S9 - Sân bóng rổ tập ném 01, S9 - Sân bóng rổ tập ném 02 |
| Sân bóng đá | list | S5 - Sân bóng đá 5, S5 - Sân bóng đá 7 |
| Sân Pickleball | one court, passes by itself | S9 - Sân Pickleball |
| Sân cầu lông | list | S10 - Sân cầu lông, S6 - Sân cầu lông, S8 - Sân Cầu lông |

- Court names are not uniform: "S8 - Sân Cầu lông" has a capital C.
- The basketball list has seven courts; the seventh sits at the bottom edge (y 1594-1600 at
  540x1600) and needs a scroll before it can be tapped.
- Each volleyball court row has a child "Chỉ đường" button (x 53-178); a tap in the middle of
  the row still opens the court.

## App in English

Set in the app; every screen keeps its layout and order, only the labels differ. Court names,
slots and the booked date and time read the same.

| `Labels` field | Vietnamese | English |
|---|---|---|
| `home` | Tiện ích | Utilities |
| `utility` | Sân Tennis | Tennis |
| `continue` | Tiếp tục | Next |
| `fully_booked` | Hết chỗ | Full |
| `venue_list` | Chọn phân khu | Select subdivision |
| `court_list` | Chọn vị trí/dịch vụ | Select place/service |
| `residents` | Số lượng cư dân | Number of residents |
| `agree` | Tôi đã hiểu (caption `Tôi đã hiểu và đồng ý với `) | I have read (caption `I have read, understood, and agree to `) |
| `confirm` | Xác nhận | Confirm |
| `confirm_page` | Xác nhận đăng ký | Confirm registration |
| `booked_time` | Thời gian đặt lịch | Schedule time |
| `booked_place` | Vị trí/dịch vụ | Place/service |
| `ticket` | Chi tiết đặt lịch | Booking details |
| `processing` | Đang xử lý | Processing |
| `registered` | Đã đăng ký | Registered |
| `notice` | Thông báo | Notification |
| `quota_full` | hết hạn mức | registration quota (seen in a dry run, 2026-10-25) |
| (dialog button) | Đóng | Close |

- A day reads `21, Wednesday, October 21, 2026`.
- Quota notice: "The apartment has reached the allowed utility registration quota."
  Closed hours: "The BQL Grand Park Management Board only accepts Tennis registration from
  06:00 to 21:00 everyday".
- Whole labels tell the languages apart: "Tennis" is clickable only on the utilities list, and
  "Registered" is not the "Registered information" heading of a loading ticket.

## Emulator (MuMu)

- Screen: custom resolution **540x1600**, 220 DPI. In tablet mode `window_size()` reports the
  landscape size, so the screen size is read from the dump; no stored coordinates.
- A screen read (dump) costs 60-75 ms with uiautomator2, 13 ms with the driver (8-31 ms; parsing
  1.2 ms). A uiautomator2 `click(x, y)` holds the touch about 100 ms (151-165 ms a tap); touch
  down + up takes 83-91 ms and the app takes every such tap.
- The MuMu clock follows the PC clock (+15 ms). One NTP answer can be off by half its round trip
  (a 0.57 s check read 0.12 s wrong). Windows Time sets the PC clock on its own schedule: at
  05:50:21 on 2026-10-19, after the run had measured it 0.757 s slow, so a wait on the PC clock
  tapped up to 0.76 s early. The run waits on `perf_counter` instead.
- MuMu can freeze (twice on 2026-10-13 in dry runs, around the court list): device calls hang,
  and `MuMuManager control shutdown` answers but does nothing; `MuMuNxDevice` must be ended by
  hand. A running MuMu shuts down with it within 18 s and starts again in about 24 s (42-48 s
  when the run starts it from cold).
- A second instance for a second account (2026-10-25): `MuMuManager clone -v 0`, with
  instance 0 off, copies its disk (5.4 GB, about 70 s) with the app, the driver and the screen
  settings. The command prints `-502 mainnx request failed` after 10 s while MuMu's main process
  finishes the copy (`MPCopyEmulator code=0` in `%APPDATA%\Netease\MuMuPlayerGlobal\logs\nx_main.log`).
  The clone gets its own `android_id` and MAC address and ADB port 16416 (instance 0: 16384).
  Both boot side by side in about 35 s. The clone holds instance 0's app session: its app data
  was cleared (`pm clear com.vinhomes.resident`) before the app ever opened there, then the
  second account logged in, and instance 0 stayed logged in.
- Two instances side by side (timed dry run, 2026-10-25 04:01, one process each): both booted
  from cold in 23-26 s, connected the driver in 4-5 s and were ready on the home screen in
  6 s, as one alone; both tapped the utility 0.06 s after the start, and both retapped through
  the closed-hours notice at the same pace (43-44 times in 5 s).

## Accessibility agent (refused by the app)

The app refuses to book while any accessibility service is enabled: at "Xác nhận" it shows
"Cảnh báo" ("Thiết bị đang sử dụng ứng dụng không được phép ... Vui lòng tắt quyền
'Accessibility' ...") instead of the ticket; every earlier step works. An on-device agent
(2026-10-18) was dropped for this reason.

## Instrumentation driver

`am instrument` gets UiAutomation, the connection uiautomator2 uses; it is not an accessibility
service (`enabled_accessibility_services` stays `null`) and the app books with it running.

- `am instrument -w` must keep running (its process holds the connection): started with
  `setsid nohup ... &` it outlives the adb shell.
- Only one UiAutomation at a time: a uiautomator2 server must end before the driver starts,
  and uiautomator2 cannot connect while the driver runs.
- The first install takes about 4 s; the driver answers 1.0-1.5 s after `am instrument`.

## App and server timings

- Calendar 0.14 s after "Sân Tennis" (1.3-2.0 s at 06:00, server load), slot list about 2 s
  after the date, court list 1.5-2.5 s after "Tiếp tục", details 0.5 s, confirmation 0.14 s.
- Slow server (2026-10-19, 10:03): court list 4.3 s, details 7.7 s, ticket over 10 s. Nobody
  saw a step take 30 s, busy days included, hence `timeout = 30`.
