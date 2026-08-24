from datetime import datetime, timedelta

VALID_KEYS = {
    "this_month",
    "last_month",
    "last_7_days",
    "last_30_days",
    "all",
    "custom",
}

DEFAULT_KEY = "this_month"
# YYYY-MM-DD — anything longer is rejected without hitting strptime.
MAX_DATE_LEN = 10


def _fmt(d):
    return d.strftime("%d %b %Y").lstrip("0")


def _label(key, from_d, to_d):
    pretty = {
        "this_month": "This month",
        "last_month": "Last month",
        "last_7_days": "Last 7 days",
        "last_30_days": "Last 30 days",
        "custom": "Custom range",
    }[key]
    return f"{pretty} · {_fmt(from_d)} – {_fmt(to_d)}"


def _preset_dates(key, today):
    if key == "this_month":
        return today.replace(day=1), today
    if key == "last_month":
        last_end = today.replace(day=1) - timedelta(days=1)
        return last_end.replace(day=1), last_end
    if key == "last_7_days":
        return today - timedelta(days=6), today
    if key == "last_30_days":
        return today - timedelta(days=29), today
    raise ValueError(f"not a bounded preset: {key}")


def _parse(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def resolve_range(range_key, from_str, to_str, today):
    """Resolve query params into a concrete date window.

    Returns a dict with:
        active_range: canonical key from VALID_KEYS
        from_date:    YYYY-MM-DD string
        to_date:      YYYY-MM-DD string
        label:        human-readable window description
        error:        None, or a message when custom input was invalid
    """
    if range_key not in VALID_KEYS:
        range_key = DEFAULT_KEY

    if range_key == "all":
        return {
            "active_range": "all",
            "from_date": None,
            "to_date": None,
            "label": "All time",
            "error": None,
        }

    if range_key != "custom":
        from_d, to_d = _preset_dates(range_key, today)
        return {
            "active_range": range_key,
            "from_date": from_d.isoformat(),
            "to_date": to_d.isoformat(),
            "label": _label(range_key, from_d, to_d),
            "error": None,
        }

    # Custom path — validate both inputs.
    error = None
    from_d = to_d = None
    if not from_str or not to_str:
        error = "Pick both a start and an end date. Showing this month instead."
    elif len(from_str) > MAX_DATE_LEN or len(to_str) > MAX_DATE_LEN:
        error = "That date range isn't valid. Showing this month instead."
    else:
        try:
            from_d = _parse(from_str)
            to_d = _parse(to_str)
        except ValueError:
            error = "That date range isn't valid. Showing this month instead."
        else:
            if from_d > to_d:
                error = "The start date must be before the end date. Showing this month instead."

    if error:
        fb_from, fb_to = _preset_dates(DEFAULT_KEY, today)
        return {
            "active_range": DEFAULT_KEY,
            "from_date": fb_from.isoformat(),
            "to_date": fb_to.isoformat(),
            "label": _label(DEFAULT_KEY, fb_from, fb_to),
            "error": error,
        }

    return {
        "active_range": "custom",
        "from_date": from_d.isoformat(),
        "to_date": to_d.isoformat(),
        "label": _label("custom", from_d, to_d),
        "error": None,
    }
