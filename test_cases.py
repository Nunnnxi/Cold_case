"""Tests for the Cold Case File (Person D).

HOW TO RUN
    pytest            (or: python3 -m pytest)

HOW PYTEST WORKS
- pytest finds every file named test_*.py and runs every function in it
  whose name starts with test_.
- "assert X" means "X must be True". If it's False, that test FAILS.
- A test with no failed asserts and no crash PASSES.
- "proof, not vibes" (lecture 7): these tests PROVE the parser works,
  instead of us just eyeballing the output.

TWO KINDS OF TESTS (rubric: 5+ tests, at least 2 failure paths)
- HAPPY PATH:   good input -> check we get the right answer.
- FAILURE PATH: bad input  -> check we raise ValueError with the RIGHT reason.
  These use "with pytest.raises(ValueError, match=...)", which PASSES only
  if the code inside raises a ValueError whose message contains that text.
  If no error happens, the test FAILS.

pytest reports 28 passed: some functions below run several times
(see @pytest.mark.parametrize), and each run counts as its own test.
"""

# date lets us build the exact date we expect, e.g. date(2018, 3, 22).
from datetime import date

# pytest gives us pytest.raises and pytest.mark.parametrize.
import pytest

# The code under test, from each teammate's file.
from case_model import Case, clean_phone
from clean_cases import clearance_rate, load, raw_closed_rate
from dates import parse_date  # Person A's date parser.

# The real header line from the raw file, used to build small fake CSV files.
# Two strings side by side inside ( ) are joined into one string.
# "\n" at the end is a newline, just like a real file.
HEADER = ("case_id,victim_name,sex,age,incident_date,address,beat,status,"
          "tip_notes\n")


def make_row(case_id="CC-12345", date_text="2013-05-20", status="OPEN",
             tips="cb: (214) 555-4240"):
    """Return a valid 9-field raw row, with a few fields swappable."""
    # A helper (not a test - its name doesn't start with test_).
    # The defaults make a GOOD row. A test changes just ONE field, e.g.
    # make_row(status="PENDING"), so if the test fails we know exactly
    # which field caused it.
    # The other fields are deliberately messy ("  walker,  g ", "male",
    # " 37 ", "beat 631") so every row also exercises the cleaners.
    return [case_id, "  walker,  g ", "male", " 37 ", date_text,
            "123 Main St", "beat 631", status, tips]


# --- parse_date (dates.py) -------------------------------------------

# HAPPY PATHS: one test for each of the 3 allowed date formats (slide 3).

def test_parse_date_iso():
    # YYYY-MM-DD
    assert parse_date("2018-03-22") == date(2018, 3, 22)


def test_parse_date_slashes():
    # M/D/YYYY - month comes first, so 6/7 is June 7, not July 6.
    assert parse_date("6/7/2000") == date(2000, 6, 7)


def test_parse_date_month_name():
    # Month D, YYYY - with extra spaces to prove they get stripped.
    assert parse_date(" July 1, 2022 ") == date(2022, 7, 1)


# FAILURE PATHS.
# @pytest.mark.parametrize runs the SAME test once for each value in the
# list, passing it in as "raw". So this one function is really 5 tests.
@pytest.mark.parametrize("raw", ["", "   ", "N/A", "unknown", "UNKNOWN"])
def test_parse_date_missing(raw):
    # Passes only if parse_date raises ValueError("missing date").
    with pytest.raises(ValueError, match="missing date"):
        parse_date(raw)


# Each value is broken in a different way:
#   2004-02-30      right shape, impossible day (Feb 30)
#   13/01/2000      right shape, impossible month (13)
#   Smarch 3, 2001  right shape, made-up month name
#   07/27/02x       junk on the end, 2-digit year
#   2018/03/22      not one of the 3 allowed formats
@pytest.mark.parametrize("raw", ["2004-02-30", "13/01/2000", "Smarch 3, 2001",
                                 "07/27/02x", "2018/03/22"])
def test_parse_date_invalid(raw):
    with pytest.raises(ValueError, match="invalid date"):
        parse_date(raw)


def test_parse_date_future():
    # Edge case: the day right after the cutoff must be rejected...
    with pytest.raises(ValueError, match="future date"):
        parse_date("2026-10-08")  # One day after "today", 10/07/2026.


def test_parse_date_today_is_not_future():
    # ...but the cutoff day itself is allowed (day > TODAY, not >=).
    # Testing both sides of a boundary catches "off by one" mistakes.
    assert parse_date("10/7/2026") == date(2026, 10, 7)


# --- Case.from_row ------------------------------------------------------------

def test_from_row_cleans_every_field():
    # HAPPY PATH for the whole constructor: messy row in, clean Case out.
    # " cc 12345 " tests case_id cleaning; "CLSD" tests the status mapping.
    case = Case.from_row(make_row(case_id=" cc 12345 ", status="CLSD"))
    # One assert per field, so a failure points at the exact field.
    assert case.case_id == "CC-12345"
    assert case.victim_name == "Walker, G"     # stripped, spaces collapsed, Title Case
    assert case.sex == "M"                     # "male" -> "M"
    assert case.age == "37"                    # " 37 " -> "37"
    assert case.incident_date == date(2013, 5, 20)
    assert case.year == 2013                   # derived from the date
    assert case.beat == "631"                  # "beat 631" -> "631"
    assert case.status == "CLOSED"             # "CLSD" -> "CLOSED"
    assert case.callback_phone == "214-555-4240"  # "(214) 555-4240" reformatted


# FAILURE PATHS: one for each quarantine reason that from_row raises.

def test_from_row_wrong_field_count():
    # make_row()[:8] slices off the last field -> only 8 fields.
    with pytest.raises(ValueError, match="wrong field count"):
        Case.from_row(make_row()[:8])


def test_from_row_bad_case_id():
    # Only 3 digits - can't become CC-#####.
    with pytest.raises(ValueError, match="bad case_id"):
        Case.from_row(make_row(case_id="CC-123"))


def test_from_row_unknown_status():
    # clean_status returns None for "PENDING", and from_row turns that
    # None into ValueError("unknown status").
    with pytest.raises(ValueError, match="unknown status"):
        Case.from_row(make_row(status="PENDING"))


def test_from_row_bad_date_passes_through():
    # Proves from_row lets parse_date's error "bubble up" unchanged.
    with pytest.raises(ValueError, match="invalid date"):
        Case.from_row(make_row(date_text="2004-02-30"))


def test_years_unsolved_and_is_stale():
    # Three cases that differ in exactly one way each.
    old_open = Case.from_row(make_row(date_text="2013-05-20", status="OPEN"))
    new_open = Case.from_row(make_row(date_text="2023-01-01", status="OPEN"))
    old_closed = Case.from_row(make_row(date_text="2013-05-20", status="CLOSED"))
    assert old_open.years_unsolved == 13   # 2026 - 2013
    assert old_open.is_stale               # open AND 13 >= 5
    assert not new_open.is_stale  # Only 3 years unsolved.
    assert not old_closed.is_stale  # Closed cases are never stale.


# --- clean_phone ----------------------------------------------------------------

# All three phone styles from the tip notes must come out the SAME way.
@pytest.mark.parametrize("raw", ["Caller left callback 214.555.3072",
                                 "cb: (214) 555-3072",
                                 "Witness can be reached at 214-555-3072"])
def test_clean_phone_formats(raw):
    assert clean_phone(raw) == "214-555-3072"


def test_clean_phone_none():
    # No phone in the note -> blank, not an error.
    assert clean_phone("Walk-in tip, declined to give contact") == ""


# --- load() on a small file -----------------------------------------------------

# tmp_path is a pytest "fixture": pytest gives the test a brand-new empty
# folder that's deleted afterwards. We write a tiny fake CSV there, so the
# test never touches the real data files.
def test_load_skips_blanks_headers_and_duplicates(tmp_path):
    # The / operator on a path joins folder + file name.
    raw = tmp_path / "raw.csv"
    # One tiny file with one example of every kind of problem.
    # Line numbers: header = 1, then 2, 3, 4, ... in order.
    raw.write_text(
        HEADER
        + 'CC-11111,"Smith, A",F,30,2001-01-01,1 A St,101,OPEN,\n'    # line 2: good -> kept
        + "\n"                                                         # line 3: blank
        + "   ,  ,\n"                                                  # line 4: spaces only (blank)
        + HEADER                                                       # line 5: repeated header
        + 'cc 11111,"Smith, A",F,30,2001-01-01,1 A St,101,OPEN,\n'    # line 6: duplicate of line 2
        + 'CC-22222,"Lee, B",M,40,2004-02-30,2 B St,202,OPEN,\n'      # line 7: invalid date
        + 'CC-33333,"Kim, C",M,50\n',                                 # line 8: truncated
        encoding="utf-8",
    )
    cases, quarantine, counts = load(raw)
    # Only the first CC-11111 survives. The "cc 11111" copy is caught as a
    # duplicate only AFTER cleaning - this proves we dedupe on cleaned ids.
    assert [c.case_id for c in cases] == ["CC-11111"]
    # Every one of the 7 lines after the header lands in exactly one bucket:
    # 1 clean + 2 blank + 1 header + 1 duplicate + 2 quarantined = 7.
    assert counts == {"rows_read": 7, "blank_rows": 2, "header_rows": 1,
                      "duplicates": 1}
    # The quarantine log records the right line numbers and reasons.
    assert [(line, reason) for line, reason, row in quarantine] == [
        (7, "invalid date"), (8, "wrong field count")]


# --- report helpers ----------------------------------------------------------------

def test_clearance_rate():
    # 4 cases: "CLOSED" and "CLEARED" both clean to CLOSED -> 2 of 4 = 50%.
    cases = [Case.from_row(make_row(status=s))
             for s in ["OPEN", "CLOSED", "CLEARED", "OPN"]]
    assert clearance_rate(cases) == 50.0
    # No cases -> 0.0 instead of a ZeroDivisionError crash.
    assert clearance_rate([]) == 0.0


def test_raw_closed_rate_counts_only_exact_closed(tmp_path):
    # Proves the "raw" number really is naive: only the exact text
    # "CLOSED" counts, so "Closed" and "CLSD" are missed -> 1 of 4 = 25%.
    # (The clean pipeline would count 3 of 4 as closed.)
    raw = tmp_path / "raw.csv"
    raw.write_text(
        HEADER
        + "CC-11111,a,M,1,2001-01-01,x,101,CLOSED,\n"   # counted as closed
        + "CC-22222,b,M,1,2001-01-01,x,101,Closed,\n"   # not exact
        + "CC-33333,c,M,1,2001-01-01,x,101,CLSD,\n"     # not exact
        + "CC-44444,d,M,1,2001-01-01,x,101,OPEN,\n",
        encoding="utf-8",
    )
    assert raw_closed_rate(raw) == 25.0
