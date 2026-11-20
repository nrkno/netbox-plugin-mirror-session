from datetime import timedelta

# A session may be scheduled to expire at most this far ahead.
MAX_EXPIRY = timedelta(days=183)

# Sessions expiring later than this get a warning in the UI.
LONG_EXPIRY = timedelta(days=7)

# NetBox stores interface speed in kbit/s. Sources at or above this get the stronger warning.
HIGH_SPEED_KBPS = 10_000_000
