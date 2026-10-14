"""Date cleaning for the Cold Case File (Person A)."""

# --- IMPORTS ---------------------------------------------------------------
import re                                  # regex: checks the SHAPE of the text (week 5)
from datetime import date, datetime        # date = a calendar day; datetime.strptime reads text into a date


# --- SETTINGS --------------------------------------------------------------
# The cleaning standard (slide 4) says "today" is 10/07/2026.
# We hard-code it instead of using date.today() so the program gives the
# SAME counts no matter what day we run it (slide 8: "get the same numbers").
TODAY = date(2026, 10, 7)

# Words the raw file uses to mean "there is no date here."
# We compare in UPPERCASE so "unknown", "Unknown" and "UNKNOWN" all match.
MISSING_WORDS = ("", "N/A", "UNKNOWN")


# --- THE FUNCTION ----------------------------------------------------------
def parse_date(raw):
    """Return a datetime.date, or raise ValueError if the date is bad or missing.

    Accepts the 3 formats in the raw file:
        2018-03-22      (YYYY-MM-DD)
        6/7/2000        (M/D/YYYY)
        July 1, 2022    (Month D, YYYY)

    The ValueError message is the quarantine reason:
        "missing date", "invalid date", or "future date".
    """
    # STEP 1: clean up the text (week 2 strings).
    # strip() removes spaces on both ends, so "  " becomes "".
    text = raw.strip()

    # STEP 2: is the date missing?
    # .upper() lets us match "unknown" and "UNKNOWN" with one check.
    if text.upper() in MISSING_WORDS:
        raise ValueError("missing date")       # the message becomes the quarantine reason

    # STEP 3: which of the 3 formats is it? (week 5 regex)
    # re.fullmatch means the WHOLE string must match, so junk like
    # "07/27/02x" is rejected instead of half-matching.
    #   \d      = one digit
    #   \d{4}   = exactly 4 digits
    #   \d{1,2} = 1 or 2 digits (so "6" and "06" both work)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):            # 2018-03-22
        pattern = "%Y-%m-%d"                                # %Y=4-digit year, %m=month, %d=day
    elif re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", text):      # 6/7/2000 or 06/07/2000
        pattern = "%m/%d/%Y"                                # month first, then day, then year
    elif re.fullmatch(r"[A-Za-z]+ \d{1,2}, \d{4}", text):   # July 1, 2022
        pattern = "%B %d, %Y"                               # %B = full month name, like "July"
    else:
        raise ValueError("invalid date")       # not one of the 3 allowed formats

    # STEP 4: turn the text into a real date (week 6 try/except).
    # The regex only checked the shape. strptime also checks the calendar,
    # so it raises ValueError for impossible dates like Feb 30, month 13,
    # or a made-up month name like "Smarch".
    try:
        day = datetime.strptime(text, pattern).date()     # .date() drops the time part
    except ValueError:
        raise ValueError("invalid date")       # swap Python's long message for our short reason

    # STEP 5: a cold case can't happen in the future.
    if day > TODAY:                            # dates can be compared with > like numbers
        raise ValueError("future date")

    # STEP 6: the date passed every check.
    # The caller can use day.isoformat() for "YYYY-MM-DD" and day.year for the year column.
    return day
