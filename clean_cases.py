"""The loader for the Cold Case File (Person C).

BIG PICTURE
-----------
Run it with one command:    python clean_cases.py

    midterm_cases_raw.csv  --load()-->  clean Case objects + quarantine list
                           --write_outputs()-->  cases_clean.csv + quarantine.csv
                           --build_report()-->   report.txt

Every row of the raw file ends up in EXACTLY ONE bucket:
    blank line  |  repeated header  |  quarantined  |  duplicate  |  clean

So the "intake funnel" always adds up:
    rows_read = blank_rows + header_rows + quarantined + duplicates + clean
    5129      = 14         + 3           + 204         + 312        + 4596

THE PIPELINE (matches briefing slide 13)
    csv.reader -> Case.from_row() -> try/except -> set of case_ids -> csv.writer
"""

# "csv" is Python's built-in CSV module (week 6). We use it instead of
# line.split(",") because names like "Mendoza, C" contain commas INSIDE
# quotes. split(",") would cut that name in half; csv.reader knows the
# quotes mean "this comma is part of the value".
import csv

# Our Case class (case_model.py). Case.from_row() does all the cleaning.
from case_model import Case

# The exact column order for cases_clean.csv, copied from slide 5.
# The output is compared against an answer key, so this must match exactly.
# Writing it in CAPITALS is a Python convention meaning "constant - don't change".
CLEAN_HEADER = ["case_id", "victim_name", "sex", "age", "incident_date",
                "year", "beat", "status", "callback_phone"]

# The columns for quarantine.csv, also from slide 5.
QUARANTINE_HEADER = ["line_number", "reason", "raw_row"]

# The decades slide 7 asks about, 1980s to 2020s. Each number is the first
# year of its decade (1980 covers 1980-1989).
DECADES = [1980, 1990, 2000, 2010, 2020]


def load(path):
    """Read the raw CSV and return (clean_cases, quarantine, counts)."""

    # ---- Accumulators (week 3): start empty, fill up during the loop ----
    clean_cases = []   # list of Case objects that passed every check
    quarantine = []    # list of (line_number, reason, row) tuples for rejected rows

    # A SET (week 4) of case_ids we've already kept. We use a set, not a list,
    # because "x in my_set" is instant no matter how big it gets, while
    # "x in my_list" has to scan the whole list - slow with 4,000+ ids.
    seen_ids = set()

    # A DICT (week 4) of counters. One dict keeps all the counts together
    # so we can return them as one thing and print them all at once.
    counts = {"rows_read": 0, "blank_rows": 0, "header_rows": 0,
              "duplicates": 0}

    # "with open(...) as f" opens the file and AUTOMATICALLY closes it when
    # the block ends - even if an error happens partway through.
    #   newline=""        is what the csv module docs require; it lets
    #                     csv.reader handle line endings itself.
    #   encoding="utf-8"  reads the text the same way on Mac and Windows.
    with open(path, newline="", encoding="utf-8") as f:
        # csv.reader turns each line of the file into a LIST of strings,
        # one string per column, with the quotes already handled.
        reader = csv.reader(f)

        # next() pulls ONE row off the reader. We throw it away because
        # line 1 is the real header ("case_id,victim_name,..."), not data.
        # It isn't counted anywhere - "rows_read" means DATA rows.
        next(reader)

        # We've just read line 1, so the counter starts at 1.
        # Inside the loop we add 1 BEFORE using it, so the first data
        # row is line 2 - the same number you'd see in VS Code's gutter.
        # That way a grader can open the raw file and jump straight to
        # any line we quarantined.
        line_number = 1

        # ---- ONE pass over every row (week 3) ----
        for row in reader:
            line_number += 1           # same as: line_number = line_number + 1
            counts["rows_read"] += 1   # every row after the header counts as "read"

            # SKIP #1: blank lines.
            # Some blank lines come through as [] (no fields at all), others
            # as ["   "] (one field of just spaces). field.strip() turns
            # "   " into "", so this check catches BOTH kinds.
            # all(...) is True only if EVERY field is empty. (all([]) is
            # also True, which is why the [] case works too.)
            # Slide 4: blank lines are SKIPPED, not quarantined.
            if all(field.strip() == "" for field in row):
                counts["blank_rows"] += 1
                continue   # "continue" jumps straight to the next row

            # SKIP #2: the header row repeated mid-file.
            # When several exports are merged, the header line gets pasted
            # in again. It's not a case, so we skip it (also not quarantined).
            # .strip() handles a header with stray spaces around "case_id".
            if row[0].strip() == "case_id":
                counts["header_rows"] += 1
                continue

            # ---- The quarantine pattern (week 6) ----
            # "try" means: attempt this, and if a ValueError happens,
            # don't crash the whole program - jump to "except" instead.
            try:
                case = Case.from_row(row)
            except ValueError as error:
                # "as error" saves the error object. str(error) gives back the
                # message we raised, e.g. "bad case_id" or "future date".
                # We save the line number, the reason, and the original raw
                # row so anyone can see exactly what was rejected and why.
                # This log IS our methodology - it proves we didn't just
                # silently drop data.
                quarantine.append((line_number, str(error), row))
                continue

            # ---- Duplicates (week 4 set) ----
            # This runs AFTER cleaning on purpose: " cc-12345 " and "CC12345"
            # look different raw but are the same case once cleaned to
            # "CC-12345". Slide 4: same case_id after cleaning -> keep the FIRST.
            # Because we read the file top to bottom, the first one we see
            # is the one already in seen_ids, and later copies are dropped.
            if case.case_id in seen_ids:
                counts["duplicates"] += 1
                continue

            # The row passed everything: remember its id and keep the case.
            seen_ids.add(case.case_id)
            clean_cases.append(case)

    # Return three things at once. Python packs them into a tuple, and the
    # caller unpacks them: cases, quarantine, counts = load(...)
    return clean_cases, quarantine, counts


def write_outputs(clean_cases, quarantine):
    """Write cases_clean.csv (sorted by case_id) and quarantine.csv."""

    # ---- File 1: cases_clean.csv ----
    # "w" means write mode: create the file, or overwrite it if it exists.
    # Overwriting is what we want - re-running gives a fresh, identical file.
    with open("cases_clean.csv", "w", newline="", encoding="utf-8") as f:
        # csv.writer is the opposite of csv.reader: we give it a list, it
        # writes one properly formatted line. It automatically adds quotes
        # around values that contain commas, like "Ramirez, K".
        writer = csv.writer(f)
        writer.writerow(CLEAN_HEADER)   # first line = the column names

        # sorted() returns a NEW list in order; it doesn't change clean_cases.
        # key=lambda c: c.case_id means "sort the cases by their case_id".
        # A lambda is a tiny one-line function with no name - it takes a
        # case c and returns c.case_id. "CC-10003" < "CC-10017" as strings,
        # and since every id is exactly 5 digits, string order = number order.
        for case in sorted(clean_cases, key=lambda c: c.case_id):
            # One list = one output row, in the SAME order as CLEAN_HEADER.
            writer.writerow([
                case.case_id,
                case.victim_name,
                case.sex,
                case.age,
                # incident_date is a date object, so we format it as text.
                # strftime = "string format time". %Y = 4-digit year,
                # %m = 2-digit month, %d = 2-digit day -> "2000-06-07".
                # This is how 6/7/2000 and "June 7, 2000" both come out
                # as YYYY-MM-DD, as slide 5 requires.
                case.incident_date.strftime("%Y-%m-%d"),
                case.year,           # csv.writer turns the int 2000 into "2000"
                case.beat,
                case.status,
                case.callback_phone,
            ])

    # ---- File 2: quarantine.csv ----
    with open("quarantine.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(QUARANTINE_HEADER)

        # Each quarantine item is a 3-part tuple, so we unpack it straight
        # into three names in the for statement itself.
        for line_number, reason, row in quarantine:
            # ",".join(row) glues the raw fields back into ONE string so the
            # whole original row fits in the single raw_row column.
            # csv.writer then wraps it in quotes because it contains commas -
            # exactly like the example on slide 5.
            writer.writerow([line_number, reason, ",".join(row)])



# ---------------------------------------------------------------------------
# THE REPORT (Person D) - answers the 6 questions on slide 7
# ---------------------------------------------------------------------------

def clearance_rate(cases):
    """Return CLOSED / total as a percent, or 0.0 if there are no cases."""
    # An empty list counts as False. Without this check, len(cases) would be
    # 0 and the division below would crash with ZeroDivisionError.
    if not cases:
        return 0.0
    # sum(1 for ...) is a counting trick: it adds 1 for every case that
    # matches the "if", so the result is HOW MANY cases are CLOSED.
    closed = sum(1 for case in cases if case.status == "CLOSED")
    # Clearance rate = closed / total (slide 7), times 100 to make it a percent.
    return closed / len(cases) * 100


def raw_closed_rate(path):
    """Clearance rate from the raw file taken at face value.

    Every non-blank, non-header row counts as a case, and only rows whose
    status is exactly "CLOSED" (no stripping, no other spellings) count as closed.
    """
    # This is slide 7, question 6: what would a lazy analysis say if it
    # trusted the raw file? So on purpose, this does NOT clean anything.
    total = 0    # every data row, good or bad, duplicates included
    closed = 0   # only rows whose status is EXACTLY "CLOSED"
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the real header on line 1.
        for row in reader:
            # Even a lazy count wouldn't treat blank lines or headers as cases.
            if all(field.strip() == "" for field in row):
                continue
            if row[0].strip() == "case_id":
                continue
            total += 1
            # Truncated rows may not reach the status column at all, so check
            # the length first - row[7] on a 5-field row would crash with
            # IndexError. Because of "and", Python never reads row[7] when
            # len(row) > 7 is False.
            # == "CLOSED" is an EXACT match: "Closed", "closed", "CLSD",
            # "CLEARED" and " CLOSED " all count as NOT closed here. That's
            # exactly why the raw rate comes out too LOW.
            if len(row) > 7 and row[7] == "CLOSED":
                closed += 1
    if total == 0:
        return 0.0
    return closed / total * 100


def build_report(clean_cases, quarantine, counts, raw_path):
    """Return the full report as one string."""
    # We build the report as a list of lines, then join them at the end.
    # That's simpler than gluing one giant string together piece by piece.
    lines = []

    # ---- 1. Intake: the funnel from raw rows to clean cases ----
    # "Data rows" = everything that was a real attempt at a case.
    data_rows = counts["rows_read"] - counts["blank_rows"] - counts["header_rows"]

    # A DICT (week 4) that counts how many rows got each quarantine reason,
    # e.g. {"bad case_id": 38, "future date": 17, ...}.
    reasons = {}
    for line_number, reason, row in quarantine:
        # .get(reason, 0) returns the current count, or 0 if this is the
        # first time we've seen this reason. Then we add 1.
        reasons[reason] = reasons.get(reason, 0) + 1

    lines.append("COLD CASE FILE REPORT")
    lines.append("=" * 40)   # "=" repeated 40 times makes an underline
    lines.append("")         # an empty string becomes a blank line
    lines.append("1. INTAKE")
    # f-strings (week 2): anything inside { } is replaced by its value.
    # Inside an f-string that uses " quotes, the dict key needs ' quotes.
    lines.append(f"   Lines read after header:  {counts['rows_read']}")
    lines.append(f"   Blank lines skipped:      {counts['blank_rows']}")
    lines.append(f"   Header rows skipped:      {counts['header_rows']}")
    lines.append(f"   Data rows:                {data_rows}")
    lines.append(f"   Quarantined:              {len(quarantine)}")
    # sorted(reasons) gives the dict's KEYS in alphabetical order, so the
    # reasons always print in the same order on every run.
    for reason in sorted(reasons):
        lines.append(f"      {reason}: {reasons[reason]}")
    lines.append(f"   Duplicates removed:       {counts['duplicates']}")
    lines.append(f"   Clean cases:              {len(clean_cases)}")
    lines.append("")

    # ---- 2. Clearance: overall and by decade ----
    overall = clearance_rate(clean_cases)
    lines.append("2. CLEARANCE")
    # :.1f means "show as a decimal with 1 digit after the point" -> 62.2
    lines.append(f"   Overall clearance rate: {overall:.1f}%")
    for decade in DECADES:   # 1980, 1990, 2000, 2010, 2020
        # A list comprehension (lecture 7, slide 7): keep only the cases
        # whose year falls in this decade. For 1980 that's 1980 to 1989:
        # "decade <= c.year < decade + 10" is a chained comparison.
        in_decade = [c for c in clean_cases if decade <= c.year < decade + 10]
        rate = clearance_rate(in_decade)
        # :5.1f = 1 decimal place, padded to 5 characters wide so the
        # numbers line up in a neat column.
        lines.append(f"   {decade}s: {rate:5.1f}%  ({len(in_decade)} cases)")
    lines.append("")

    # ---- 3. Open cases: stale count and the 5 oldest ----
    open_cases = [c for c in clean_cases if c.status == "OPEN"]
    # c.is_stale is the @property from case_model.py - no 5-year logic here.
    stale = [c for c in open_cases if c.is_stale]
    # Sort by date, oldest first. The key is a TUPLE: Python compares the
    # date first, and only if two dates are equal does it compare case_id.
    # That tie-breaker makes the order the same on every run.
    # [:5] is a slice: keep only the first 5 items.
    oldest = sorted(open_cases, key=lambda c: (c.incident_date, c.case_id))[:5]
    lines.append("3. OPEN CASES")
    lines.append(f"   Open cases:             {len(open_cases)}")
    lines.append(f"   Stale (open 5+ years):  {len(stale)}")
    lines.append("   5 oldest open cases:")
    for case in oldest:
        # .isoformat() turns a date into "YYYY-MM-DD" text.
        # Two f-strings side by side are joined into one string automatically.
        lines.append(f"      {case.case_id}  {case.incident_date.isoformat()}  "
                     f"{case.years_unsolved} yrs  {case.victim_name}")
    lines.append("")

    # ---- 4. Beats: top 10 by open cases, with each beat's clearance rate ----
    # A dict that groups cases by beat: {"517": [case, case, ...], ...}
    beat_cases = {}
    for case in clean_cases:
        # A blank beat ("") counts as False, so those cases are skipped -
        # we can't rank a beat we don't know.
        if case.beat:
            # setdefault: if this beat isn't in the dict yet, add it with an
            # empty list; either way, return the list so we can append to it.
            beat_cases.setdefault(case.beat, []).append(case)
    # A dict comprehension: for each beat, count its OPEN cases.
    # Result looks like {"517": 51, "121": 43, ...}.
    beat_open = {beat: sum(1 for c in cases if c.status == "OPEN")
                 for beat, cases in beat_cases.items()}
    # Sort the beats by open count, highest first. The minus sign flips the
    # order (biggest number becomes "smallest"), and b breaks ties by beat
    # number so the order never changes. [:10] keeps the top 10.
    top_beats = sorted(beat_open, key=lambda b: (-beat_open[b], b))[:10]
    lines.append("4. TOP 10 BEATS BY OPEN CASES")
    for beat in top_beats:
        # Clearance rate for this beat uses ALL its cases, open and closed.
        rate = clearance_rate(beat_cases[beat])
        # :3d = a whole number padded to 3 characters wide.
        lines.append(f"   Beat {beat}: {beat_open[beat]:3d} open, "
                     f"{rate:5.1f}% cleared ({len(beat_cases[beat])} cases)")
    lines.append("")

    # ---- 5. Leads: open cases with a callback phone ----
    # An empty callback_phone ("") counts as False, so this counts the
    # open cases that DO have a phone.
    with_phone = sum(1 for c in open_cases if c.callback_phone)
    # A one-line if/else ("conditional expression") that avoids dividing by
    # zero if there were no open cases.
    phone_pct = with_phone / len(open_cases) * 100 if open_cases else 0.0
    lines.append("5. LEADS")
    lines.append(f"   Open cases with a callback phone: {with_phone} of "
                 f"{len(open_cases)} ({phone_pct:.1f}%)")
    lines.append("")

    # ---- 6. Raw vs clean clearance rate ----
    raw_rate = raw_closed_rate(raw_path)
    lines.append("6. RAW VS CLEAN")
    # \" puts a literal quote mark inside the string.
    lines.append(f"   Raw rate (status exactly \"CLOSED\"): {raw_rate:.1f}%")
    lines.append(f"   Clean rate:                          {overall:.1f}%")
    # :+.1f always shows the sign, so a negative gap prints as "-26.1".
    # Negative means the raw file UNDER-counts solved cases.
    lines.append(f"   Raw is off by {raw_rate - overall:+.1f} percentage points")

    # "\n".join(lines) puts a newline between every line, giving one big
    # string. The extra "\n" ends the file with a newline.
    return "\n".join(lines) + "\n"


def write_report(text, path="report.txt"):
    """Save the report text to path."""
    # path="report.txt" is a DEFAULT argument: if the caller doesn't pass
    # a path, it uses "report.txt".
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# ONE COMMAND (rubric: "One command: raw file in, three files out")
# ---------------------------------------------------------------------------
# __name__ is a special variable Python sets automatically:
#   - "python clean_cases.py"       -> __name__ is "__main__", so this block RUNS
#   - "from clean_cases import load" (e.g. in test_cases.py)
#                                   -> __name__ is "clean_cases", so it's SKIPPED
# That way the tests can import load() without rewriting our output files.
if __name__ == "__main__":
    # Unpack the three things load() returns.
    cases, quarantine, counts = load("midterm_cases_raw.csv")
    # Files 1 and 2: cases_clean.csv and quarantine.csv.
    write_outputs(cases, quarantine)
    # File 3: report.txt. Build the text once, save it, and also print it
    # so we can see the numbers in the terminal.
    report = build_report(cases, quarantine, counts, "midterm_cases_raw.csv")
    write_report(report)
    print(report)
