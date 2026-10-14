"""The Case class for the Cold Case File (Person C).

BIG PICTURE
-----------
The raw CSV gives us each case as a plain list of 9 strings, like:
    [" CC-76856 ", "walker, g", "M", "41", "6/7/2000", "7840 Webb Chapel Rd",
     " 157 ", "OPEN", "Witness can be reached at 214-555-0202"]

This file turns that messy list into ONE tidy Case object:
    Case(case_id="CC-76856", victim_name="Walker, G", sex="M", age="41",
         incident_date=date(2000, 6, 7), year=2000, beat="157",
         status="OPEN", callback_phone="214-555-0202")

WHY A CLASS? (week 7)
A dict is just a bag of facts. A class is facts PLUS the questions you ask
about them (years_unsolved, is_stale) kept together in one place. If the
"5-year stale" rule ever changes, we change it in ONE spot and every report
updates.

WHO DOES WHAT
- Person A wrote parse_date (dates_recent.py)  -> cleans the date column
- Person B wrote the field cleaners (fields.py) -> case_id, name, status, sex, age, beat
- This file (Person C) calls all of them, in the order slide 4 requires,
  and builds the Case object. clean_cases.py then loops over every row.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------

# "re" is Python's built-in regular-expression module (week 5).
# We use it to find phone numbers inside the free-text tip notes.
import re

# Import Person A's date parser. It returns a datetime.date, or raises
# ValueError("missing date" / "invalid date" / "future date").
# We use dates_recent, NOT the old dates.py, because only dates_recent
# tells missing/future dates apart from invalid ones (slide 4 needs all three).
from dates_recent import parse_date

# Import Person B's six field cleaners. The parentheses just let one import
# statement span several lines so it's easy to read.
from fields import (
    clean_age,      # "37 " -> "37";  "unknown"/"-1"/"999" -> ""
    clean_beat,     # "beat 631"/"B-150" -> "631"/"150";  blank -> ""
    clean_case_id,  # "cc-19495"/"CC 16288" -> "CC-19495"; junk -> ValueError("bad case_id")
    clean_name,     # "  JORDAN, C " -> "Jordan, C"
    clean_sex,      # "male"/"m" -> "M"; "female" -> "F"; anything else -> "U"
    clean_status,   # "opn"/"Open" -> "OPEN"; "CLSD"/"CLEARED" -> "CLOSED"; junk -> None
)

# ---------------------------------------------------------------------------
# PHONE NUMBERS (week 5 regex)
# ---------------------------------------------------------------------------

# The tip notes write phone numbers three different ways:
#     214-555-1234      214.555.1234      (214) 555-1234
# This ONE pattern matches all three. Reading it piece by piece:
#     \(?        an optional "("            (the ? means "zero or one")
#     (\d{3})    exactly 3 digits -> GROUP 1, the area code   ("214")
#     \)?        an optional ")"
#     [ .-]?     an optional space, dot, or dash after the area code
#     (\d{3})    exactly 3 digits -> GROUP 2                   ("555")
#     [.-]       a REQUIRED dot or dash
#     (\d{4})    exactly 4 digits -> GROUP 3                   ("1234")
# The r"..." makes it a "raw string" so Python leaves the backslashes alone.
# re.compile() builds the pattern once, up front, instead of on every row.
# It will NOT match "CC-12345" in notes like "possibly linked to CC-12345",
# because that has only 5 digits, not 3 + 3 + 4.
PHONE_PATTERN = re.compile(r"\(?(\d{3})\)?[ .-]?(\d{3})[.-](\d{4})")


def clean_phone(raw):
    """Return the first phone number in raw as '214-555-1234', or ''."""
    # .search() scans the whole note and stops at the FIRST match
    # (slide 5: "first phone number in tip_notes"). It returns a Match
    # object if it finds one, or None if there's no phone at all.
    match = PHONE_PATTERN.search(raw)
    # A Match object counts as True, None counts as False.
    if match:
        # .groups() gives the 3 captured pieces as a tuple: ("214", "555", "1234").
        # "-".join(...) glues them together with dashes: "214-555-1234".
        # This is how all three input styles end up in the SAME output format.
        return "-".join(match.groups())
    # No phone in the note -> blank, exactly as slide 5 asks.
    return ""


# ---------------------------------------------------------------------------
# THE CASE CLASS (week 7)
# ---------------------------------------------------------------------------

class Case:
    """One cleaned case."""

    # __init__ is the "constructor". Python runs it automatically every time
    # a new Case is created, e.g. Case("CC-10003", "Ramirez, K", ...).
    # "self" means "this particular case" - the object being built.
    # The parameters are listed in the SAME order as the columns in
    # cases_clean.csv (slide 5), which makes the output easy to check.
    def __init__(self, case_id, victim_name, sex, age, incident_date, year,
                 beat, status, callback_phone):
        """Store the nine cleaned fields on this case."""
        # Each line saves one value onto the object as an "attribute",
        # so later we can write case.case_id, case.status, etc.
        self.case_id = case_id              # str, always "CC-#####"
        self.victim_name = victim_name      # str, "Last, I" in Title Case (may be "")
        self.sex = sex                      # str, "M", "F", or "U"
        self.age = age                      # str, "0" to "110", or "" if unusable
        self.incident_date = incident_date  # datetime.date object (NOT a string)
        self.year = year                    # int, e.g. 2018 - used for decades & years_unsolved
        self.beat = beat                    # str, 3 digits like "157", or ""
        self.status = status                # str, "OPEN" or "CLOSED" (never anything else)
        self.callback_phone = callback_phone  # str, "214-555-1234", or ""

    # @classmethod means this method belongs to the CLASS, not to one object.
    # We call it as Case.from_row(row) BEFORE any Case exists.
    # Python passes the class itself in as "cls", so "cls(...)" at the end
    # is the same as writing "Case(...)".
    # This is the "parser becomes a constructor" idea from lecture 7, slide 6:
    # all of week 2's cleaning now lives inside one function that builds a Case.
    @classmethod
    def from_row(cls, row):
        """Clean a 9-field row. Raise ValueError if a critical field is bad."""

        # ---- CHECK 1: field count (slide 4, first quarantine rule) ----
        # A truncated row (e.g. only 5 fields) can't be trusted - we don't
        # even know which value belongs to which column. So reject it first,
        # before trying to unpack it.
        if len(row) != 9:
            # "raise" stops this function immediately and hands the error
            # back to whoever called from_row (the loader in clean_cases.py).
            # The message text becomes the "reason" column in quarantine.csv.
            raise ValueError("wrong field count")

        # ---- Unpack the 9 raw strings into named variables ----
        # This is "tuple unpacking": Python assigns the 9 list items to the
        # 9 names, left to right. It only works because we KNOW there are
        # exactly 9 (we just checked). Named variables are much easier to read
        # than row[0], row[4], row[7]...
        # raw_address is unpacked but never used - slide 3 says to drop the
        # address from the clean file.
        (raw_id, raw_name, raw_sex, raw_age, raw_date,
         raw_address, raw_beat, raw_status, raw_tips) = row

        # ---- CRITICAL fields: a bad value QUARANTINES the row ----
        # The order matches slide 4: case_id, then date, then status.
        # Order matters because a row can only get ONE reason - the first
        # check it fails. E.g. a row with a bad id AND a bad date is
        # reported as "bad case_id".
        #
        # Notice there's no try/except here. If clean_case_id or parse_date
        # raises ValueError, we deliberately let it "bubble up" out of
        # from_row to the loader, which catches it and quarantines the row.
        case_id = clean_case_id(raw_id)        # may raise ValueError("bad case_id")
        incident_date = parse_date(raw_date)   # may raise "missing date"/"invalid date"/"future date"

        # Person B's clean_status doesn't raise - it returns None when the
        # status is unknown (like "PENDING?" or "??"). So WE turn that None
        # into the quarantine error. "is None" is the correct way to test
        # for None in Python (not "== None").
        status = clean_status(raw_status)
        if status is None:
            raise ValueError("unknown status")

        # ---- NON-CRITICAL fields: REPAIR and keep the row ----
        # These cleaners never raise. A bad age just becomes "", a bad beat
        # becomes "", an unknown sex becomes "U". Slide 4 says a messy age
        # isn't a reason to throw away an entire case.
        victim_name = clean_name(raw_name)
        sex = clean_sex(raw_sex)
        age = clean_age(raw_age)
        beat = clean_beat(raw_beat)

        # ---- DERIVED fields: computed from other fields ----
        # incident_date is a datetime.date, which has a .year attribute,
        # so the year is free once the date is parsed. (No string slicing.)
        year = incident_date.year
        # Pull the first phone number out of the free-text tip notes.
        callback_phone = clean_phone(raw_tips)

        # ---- Build and return the finished Case ----
        # cls(...) calls __init__ above with all nine cleaned values.
        # We only reach this line if NOTHING above raised an error.
        return cls(case_id, victim_name, sex, age, incident_date, year,
                   beat, status, callback_phone)

    # @property lets us use a method like a plain attribute: we write
    # case.years_unsolved (no parentheses), and Python runs this code.
    # The value is calculated fresh each time, so it can never go stale
    # or get out of sync with self.year.
    @property
    def years_unsolved(self):
        """How many years since the incident, as of 2026."""
        # 2026 is hard-coded (not date.today()) so every squad and every
        # re-run gets the same numbers, matching the answer key.
        return 2026 - self.year

    @property
    def is_stale(self):
        """True if the case is open and has been unsolved for 5+ years."""
        # "and" means BOTH must be true. A closed case is never stale,
        # no matter how old. Because this is a property, the 5-year rule
        # lives in exactly one place - reports just ask "if case.is_stale".
        # Python checks the left side first; if the case is CLOSED it
        # skips the right side entirely ("short-circuit").
        return self.status == "OPEN" and self.years_unsolved >= 5
