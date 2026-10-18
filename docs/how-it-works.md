# How it works

## Reading a Flutter app from the outside

uiautomator2 reads Android's accessibility tree. Flutter renders its own widgets, but
publishes a *semantics* tree to accessibility services, where visible text appears in
`content-desc` (not `text`). Every element is therefore matched by its `content-desc`
label (`screen.Match`).

Each screen is read with **one hierarchy dump**, which returns every element with its
visible bounds in about 70 ms, no slower than a query for a single element. Elements are
then matched locally (`screen.Screen`), so a screen costs one device command however many
elements the step needs.

Two consequences of Flutter shaped the design:

1. **Only on-screen widgets exist.** Flutter builds lazily, so a time slot below the
   fold is absent from the tree until scrolled into view, and dump bounds are clipped to
   what is shown. At 540x1600 the whole slot list fits; on shorter screens
   `Booker.select_slot` swipes until the slot is mostly visible above the sticky bottom
   button, reading the screen until the list stops moving.
2. **Unlabeled widgets.** The consent checkbox is a plain clickable `View` with no
   label and `checkable=false`. It is located relative to its caption:

   ```
   [35,1323][79,1367]   View  clickable=true      <- checkbox
   [79,1322][313,1355]  View  "Tôi đã hiểu và đồng ý với "
   ```

   A candidate is accepted only if it is small, left of the caption and on the same
   row (`geometry.is_checkbox_beside`). Thresholds scale with screen width.

## "Coordinates" vs. elements

A tap names its element by label. With the driver (`docs/architecture.md`, "Driver") no
position is involved at all: the driver looks the label up in the screen's tree of that
moment and clicks the element with an accessibility click, so a list that moved since the
last read (the court list does, while it loads) cannot send the click to another element.
The consent checkbox has no label; it is the smallest clickable element at the point the
latest dump shows it. Waiting for the next screen and locating the next element are the
same read, so pre-recorded coordinates would not save a command: the screen must be read
anyway to know it has appeared.

With uiautomator2, the fallback when the driver does not start, a tap is a touch at the
point taken from the latest dump, never stored across screens: a touch down and up
(`runner.QuickTap`), since uiautomator2's `click` holds the touch about 100 ms, which the
app does not need.

## Navigation

`Booker.tap_and_advance()` taps an element of the current dump, then reads the screen every
20 ms until a finder returns what the next step needs (for example the target day). If the
next screen does not appear within 2 s (tap swallowed by lag), it taps again while the
element is still shown, up to 5 times. The court tap is checked as well: the court list
can move up while it loads, so the tap may open another court; the booking details page
names the court, and another one is left with Back and the court tapped again. A timed run
waits on the app's home screen and
opens the utilities list `warm_up_seconds` (60 s) before the start time, so the list is
freshly loaded; two seconds before the start it is read once more, so the first command at
the start time is the tap itself.

After confirming, the script reads the screen until the ticket's title shows: only then is
the slot booked. A "Thông báo" dialog with a button, for example when someone else took the
slot a moment earlier, fails the round with its message instead. Before either, the app
shows the confirmation page while its server answers and then, for a moment, a screen
without labels, so the page going away does not tell the outcome. If neither the ticket nor
a dialog shows within `timeout` (10 s), the round fails as "Outcome unknown": better a
booking reported missing than a missing one reported booked. The date, slot and court the
confirmation page shows, and the ticket's status, are read from screens already read,
logged (a warning when they differ from the target) and kept in the history; neither stops
the round. Every new screen a run reads, and every tap, is written to the debug
log, so a failure can be followed screen by screen. From the
ticket screen, one Back returns to the utilities list, where the next round begins. After a
failure deeper in the flow, such as a refusal (dialog, confirmation page, details, court
list, venue, calendar: six Backs), each Back follows as soon as the screen before shows,
about 0.2 s later, instead of after 2 s on each screen on the way.

## Lessons learned

- The first coordinate-based version failed because the emulator ran at **540×960**,
  not the assumed 900×1600. Label-based lookup removed the whole class of bugs.
- Count round trips, not lines of code. uiautomator2's `click()` on a selector waits for
  the element and reads its bounds before tapping; together with an explicit `wait()` a
  tap cost four commands. Reading a whole screen once is as cheap as one of them.
- `window_size()` reported (960, 540) while MuMu ran a tablet resolution with the app in
  portrait; the screen size is now taken from the dump.
- Measure before optimizing: every log line shows the time elapsed since the previous step,
  and the debug log counts device commands per round.
