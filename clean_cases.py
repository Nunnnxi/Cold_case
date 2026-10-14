"""The loader for the Cold Case File (Person C).

BIG PICTURE
-----------
Run it with one command:    python clean_cases.py

    midterm_cases_raw.csv  --load()-->  clean Case objects + quarantine list
                           --write_outputs()-->  cases_clean.csv + quarantine.csv

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
# ONE COMMAND (slide 8: "One command: raw file in, files out")
# ---------------------------------------------------------------------------
# __name__ is a special variable Python sets automatically:
#   - "python clean_cases.py"       -> __name__ is "__main__", so this block RUNS
#   - "from clean_cases import load" (e.g. in test_cases.py)
#                                   -> __name__ is "clean_cases", so it's SKIPPED
# That way the tests can import load() without rewriting our output files.
if __name__ == "__main__":
    # Unpack the three things load() returns.
    cases, quarantine, counts = load("midterm_cases_raw.csv")
    write_outputs(cases, quarantine)
    # Show the intake counts in the terminal so we can check the funnel.
    print(counts)
