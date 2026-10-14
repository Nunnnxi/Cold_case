import re  # Regular expressions let us check that each date has the right shape.
from datetime import date, datetime  # These classes represent and parse calendar dates.

# Match the full string first so strptime cannot quietly accept extra text.
DATE_FORMATS = (  # Pair each allowed text pattern with its matching parser format.
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "%Y-%m-%d"),  # Match dates like 2013-05-20.
    (re.compile(r"\d{1,2}/\d{1,2}/\d{4}"), "%m/%d/%Y"),  # Match dates like 6/7/2000.
    (
        re.compile(  # Match a spelled-out month, then a day and four-digit year.
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}",  # Require a day, comma, and year after the month.
            re.IGNORECASE,  # Allow month names in upper, lower, or mixed case.
        ),  # Finish building the regular-expression pattern.
        "%B %d, %Y",  # Tell datetime how to read a full month name and day.
    ),  # Finish the spelled-out-month pattern and format pair.
)  # Finish the collection of accepted date formats.


def parse_date(raw):  # Define the function that converts raw date text into a date.
    """Return a real date from one of the three formats used in the raw file."""  # Explain the function's result.
    value = raw.strip()  # Remove spaces around the date before checking its format.

    for pattern, date_format in DATE_FORMATS:  # Try each supported format in turn.
        if pattern.fullmatch(value):  # Continue only if the whole string matches this format.
            try:  # The shape may be valid even when the calendar date is impossible.
                return datetime.strptime(value, date_format).date()  # Parse the text and keep only its date.
            except ValueError:  # The matching shape contained an invalid calendar date.
                break  # No other format can make this same-shaped invalid date valid.

    raise ValueError("invalid date")  # Tell the caller this row's date cannot be used.
