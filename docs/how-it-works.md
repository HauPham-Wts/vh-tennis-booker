# How it works

## Reading a Flutter app from the outside

The instrumentation driver (or uiautomator2 as fallback) reads Android's accessibility tree.
Flutter draws its own widgets but publishes a *semantics* tree, where visible text appears in
`content-desc` (not `text`); every element is matched by that label (`screen.Match`).

Each screen is read with **one hierarchy dump**, which returns every element with its visible
bounds: about 13 ms with the driver, 70-100 ms with uiautomator2 ([field notes](field-notes.md)).
Elements are then matched locally (`screen.Screen`), so a step costs one read however many
elements it needs.

Two consequences of Flutter shaped the design:

1. **Only on-screen widgets exist.** Flutter builds lazily: a slot below the fold is absent until
   scrolled into view, and bounds are clipped to what shows. At 540x1600 the whole slot list
   fits; on shorter screens the booker swipes until the slot is mostly visible.
2. **Unlabelled widgets.** The consent checkbox is a plain clickable `View` with no label. It is
   found relative to its caption: small, left of it, on the same row
   (`geometry.is_checkbox_beside`).

   ```
   [35,1323][79,1367]   View  clickable=true      <- checkbox
   [79,1322][313,1355]  View  "Tôi đã hiểu và đồng ý với "
   ```

The app may be set to Vietnamese or English: the same screens with other labels. A language is
data (`app_language.AppLanguage`: labels, the calendar's day label, month names); the booker
finds it on the app's first screen, in a read it makes anyway.

## Elements, not coordinates

A tap names its element by label. The driver looks the label up in the tree of that moment and
clicks the element where it is now, so a list that moved since the last read is followed;
coordinates from the dump only tell apart nodes with the same label. Waiting for the next screen
and locating the next element are the same read, so stored coordinates would not save a command.
With uiautomator2 a tap is a touch down and up at the point of the latest read.

## Navigation: a closed loop

Every step taps, then reads the screen every 20 ms until the next screen shows, and acts at
once. A tap the app swallowed (the element still shows after 2 s) is tapped again; while the
app loads the next screen (the element gone) the booker only waits, up to `timeout` (30 s).
Each screen is known by a label of its own, never by one the screen being left also shows.

- **Before 06:00** a timed run waits on the home screen, opens the utilities list a minute ahead
  and reads it again 2 s ahead, so the first command at the start is the tap. The wait goes by
  NTP time carried on a counter Windows does not set; the tap comes 0.1 s after the start, and a
  "not open yet" notice is closed and the tap repeated.
- **The court list moves** while it loads, so a tap can open another court. The booking details
  page names the court opened; another one is left with Back and the court tapped again.
- **Success is the ticket.** After "Xác nhận" the page stays while the server answers, then a
  frame without labels shows on every path, so the page going away proves nothing: the round is
  booked only once the ticket's title shows. A notice fails it with its message; the quota
  notice also skips the rounds left. A "Xác nhận" the app swallowed under load is tapped again
  after 3 s; a notice after that second tap, or nothing within `timeout`, is reported as
  "Outcome unknown": better a booking reported missing than a missing one reported booked.
- **Every screen is logged.** Each new screen and each tap go to the debug log, so a failure at
  06:00 can be followed screen by screen.

## Lessons learned

- The first coordinate-based version failed because the emulator ran at **540×960**, not the
  assumed 900×1600. Label-based lookup removed the whole class of bugs.
- Count round trips, not lines of code. uiautomator2's `click()` on a selector waits for the
  element and reads its bounds before tapping; with an explicit `wait()` a tap cost four
  commands. Reading a whole screen once is as cheap as one of them.
- A screen that disappears is not a result. On 2026-10-14 a round was logged as booked because
  the confirmation page had gone, while the app had refused it; only a label the next screen
  owns proves anything.
- Measure before optimizing: the log shows the time between steps and counts device commands.
