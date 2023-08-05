import datetime as dt
import math


def delay_get() -> dt.timedelta:
    """
    Get the delay time for the next update based on day in week.
    During workweek, work hours, updates are every 15 minutes.
    Evenings and weekends, updates are every 60 minutes.
    Delay is set so that it is rounded to the next update time.

    Returns:
        int: Sleep delay in seconds to hit next update time.
    """

    now = dt.datetime.now()
    day = now.weekday()
    hr = now.hour

    def next_update_rounded(now: dt.datetime, delta: dt.timedelta):
        now += delta
        # return dt.datetime.min + round((now - dt.datetime.min) / delta) * delta
        return dt.datetime.min + math.floor((now - dt.datetime.min) / delta) * delta

    if day < 5:  # Weekday
        if hr < 6:  # Early morning
            # Weekdays: 11pm - 6:00am - 60 min updates
            delta = dt.timedelta(hours=1)
            next_update = next_update_rounded(now, delta)

        elif hr < 18:  # Daytime
            # Weekdays: 6:00am - 6:00pm - 15 min updates
            delta = dt.timedelta(minutes=15)
            next_update = next_update_rounded(now, delta)

        else:  # Evening & Night
            # Weekdays: 6:00pm - 11pm - 60 min updates
            delta = dt.timedelta(hours=1)
            next_update = next_update_rounded(now, delta)

    else:  # Weekend
        # Weekends:  60 min updates
        delta = dt.timedelta(hours=1)
        next_update = next_update_rounded(now, delta)

    # Scheduled delay
    delay_update_sec = (next_update - now).seconds
    delay_update = dt.timedelta(seconds=delay_update_sec)

    # Because we're caching images that are pre-rendered, we need to
    # delay the update by a few minutes to ensure the image is ready.
    delay_update += dt.timedelta(minutes=2)

    return delay_update
