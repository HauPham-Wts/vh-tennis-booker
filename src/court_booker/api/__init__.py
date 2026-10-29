"""The local backend of the desktop app (spec part 7): FastAPI on 127.0.0.1.

It reads and writes the config, runs device checks, switches the schedule (allowing wake
timers), starts dry runs and serves the history. It needs the ``app`` extra; the booking
engine does not import it.
"""
