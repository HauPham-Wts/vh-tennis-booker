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
Utilities list, where the next round starts.

Back from inside the flow (2026-10-15 20:50): a notice dialog closes to the confirmation
page, with `'Đóng'` and with Back alike. From there Back goes to the booking details, the
court list, the venue ("Origami…"), the calendar and the Utilities list (5 Backs); one more
leaves to the home screen. Each screen shows 0.13-0.24 s after Back, at times after an
empty frame (only the full-screen root and the status bar). The status bar's labels change
on their own (the clock, a "Google Play services notification" seen at 20:13), so they
never tell one screen from another.

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
  2026-10-10.
- Each apartment may book 8 slots per month (1 hour = 1 slot). Once they are used, tapping
  "Tiếp tục" on the calendar opens a dialog "Thông báo": "Căn hộ đã hết hạn mức đăng ký
  tiện ích cho phép." with a "Đóng" button (seen 2026-10-10); the round then fails after
  the re-taps with "Tapped 'Tiếp tục' but the next screen did not appear". On 2026-10-16
  the same dialog showed only after "Xác nhận" (0.72 s after the tap), so the round failed
  with its message.

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

## App and server timings

- Calendar 0.14 s after "Sân Tennis", slot list ~2.1 s after the date tap, court list
  1.5-2.0 s, details 0.5 s, confirmation 0.14 s.
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
| UI part 3 | 2026-10-14 | Requests through the Vite proxy, and the live feed across a backend stop and restart (no step lost or repeated), against a scratch backend |
