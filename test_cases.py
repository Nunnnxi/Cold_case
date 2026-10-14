from datetime import date

import pytest

from case_model import Case, clean_phone
from clean_cases import clearance_rate, load, raw_closed_rate
from dates_recent import parse_date  # Person A's date parser.

HEADER = ("case_id,victim_name,sex,age,incident_date,address,beat,status,"
          "tip_notes\n")


def make_row(case_id="CC-12345", date_text="2013-05-20", status="OPEN",
             tips="cb: (214) 555-4240"):
    """Return a valid 9-field raw row, with a few fields swappable."""
    return [case_id, "  walker,  g ", "male", " 37 ", date_text,
            "123 Main St", "beat 631", status, tips]


# --- parse_date (dates_recent.py) -------------------------------------------

def test_parse_date_iso():
    assert parse_date("2018-03-22") == date(2018, 3, 22)


def test_parse_date_slashes():
    assert parse_date("6/7/2000") == date(2000, 6, 7)


def test_parse_date_month_name():
    assert parse_date(" July 1, 2022 ") == date(2022, 7, 1)


@pytest.mark.parametrize("raw", ["", "   ", "N/A", "unknown", "UNKNOWN"])
def test_parse_date_missing(raw):
    with pytest.raises(ValueError, match="missing date"):
        parse_date(raw)


@pytest.mark.parametrize("raw", ["2004-02-30", "13/01/2000", "Smarch 3, 2001",
                                 "07/27/02x", "2018/03/22"])
def test_parse_date_invalid(raw):
    with pytest.raises(ValueError, match="invalid date"):
        parse_date(raw)


def test_parse_date_future():
    with pytest.raises(ValueError, match="future date"):
        parse_date("2026-10-08")  # One day after "today", 10/07/2026.


def test_parse_date_today_is_not_future():
    assert parse_date("10/7/2026") == date(2026, 10, 7)


# --- Case.from_row ------------------------------------------------------------

def test_from_row_cleans_every_field():
    case = Case.from_row(make_row(case_id=" cc 12345 ", status="CLSD"))
    assert case.case_id == "CC-12345"
    assert case.victim_name == "Walker, G"
    assert case.sex == "M"
    assert case.age == "37"
    assert case.incident_date == date(2013, 5, 20)
    assert case.year == 2013
    assert case.beat == "631"
    assert case.status == "CLOSED"
    assert case.callback_phone == "214-555-4240"


def test_from_row_wrong_field_count():
    with pytest.raises(ValueError, match="wrong field count"):
        Case.from_row(make_row()[:8])


def test_from_row_bad_case_id():
    with pytest.raises(ValueError, match="bad case_id"):
        Case.from_row(make_row(case_id="CC-123"))


def test_from_row_unknown_status():
    with pytest.raises(ValueError, match="unknown status"):
        Case.from_row(make_row(status="PENDING"))


def test_from_row_bad_date_passes_through():
    with pytest.raises(ValueError, match="invalid date"):
        Case.from_row(make_row(date_text="2004-02-30"))


def test_years_unsolved_and_is_stale():
    old_open = Case.from_row(make_row(date_text="2013-05-20", status="OPEN"))
    new_open = Case.from_row(make_row(date_text="2023-01-01", status="OPEN"))
    old_closed = Case.from_row(make_row(date_text="2013-05-20", status="CLOSED"))
    assert old_open.years_unsolved == 13
    assert old_open.is_stale
    assert not new_open.is_stale  # Only 3 years unsolved.
    assert not old_closed.is_stale  # Closed cases are never stale.


# --- clean_phone ----------------------------------------------------------------

@pytest.mark.parametrize("raw", ["Caller left callback 214.555.3072",
                                 "cb: (214) 555-3072",
                                 "Witness can be reached at 214-555-3072"])
def test_clean_phone_formats(raw):
    assert clean_phone(raw) == "214-555-3072"


def test_clean_phone_none():
    assert clean_phone("Walk-in tip, declined to give contact") == ""


# --- load() on a small file -----------------------------------------------------

def test_load_skips_blanks_headers_and_duplicates(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text(
        HEADER
        + 'CC-11111,"Smith, A",F,30,2001-01-01,1 A St,101,OPEN,\n'
        + "\n"                                                         # blank
        + "   ,  ,\n"                                                  # spaces only
        + HEADER                                                       # repeated header
        + 'cc 11111,"Smith, A",F,30,2001-01-01,1 A St,101,OPEN,\n'    # duplicate
        + 'CC-22222,"Lee, B",M,40,2004-02-30,2 B St,202,OPEN,\n'      # invalid date
        + 'CC-33333,"Kim, C",M,50\n',                                 # truncated
        encoding="utf-8",
    )
    cases, quarantine, counts = load(raw)
    assert [c.case_id for c in cases] == ["CC-11111"]
    assert counts == {"rows_read": 7, "blank_rows": 2, "header_rows": 1,
                      "duplicates": 1}
    assert [(line, reason) for line, reason, row in quarantine] == [
        (7, "invalid date"), (8, "wrong field count")]


# --- report helpers ----------------------------------------------------------------

def test_clearance_rate():
    cases = [Case.from_row(make_row(status=s))
             for s in ["OPEN", "CLOSED", "CLEARED", "OPN"]]
    assert clearance_rate(cases) == 50.0
    assert clearance_rate([]) == 0.0


def test_raw_closed_rate_counts_only_exact_closed(tmp_path):
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
