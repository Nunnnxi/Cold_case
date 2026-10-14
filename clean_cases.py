import csv
from case_model import Case

CLEAN_HEADER = ["case_id", "victim_name", "sex", "age", "incident_date",
                "year", "beat", "status", "callback_phone"]
QUARANTINE_HEADER = ["line_number", "reason", "raw_row"]


def load(path):
    """Read the raw CSV and return (clean_cases, quarantine, counts)."""
    clean_cases = []  # Case objects that passed cleaning.
    quarantine = []  # (line_number, reason, row) for each rejected row.
    seen_ids = set()  # case_ids already kept, to catch duplicates.
    counts = {"rows_read": 0, "blank_rows": 0, "header_rows": 0,
              "duplicates": 0}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the real header on line 1.
        line_number = 1

        for row in reader:
            line_number += 1
            counts["rows_read"] += 1

            # Skip blank lines, including lines that are only spaces.
            if all(field.strip() == "" for field in row):
                counts["blank_rows"] += 1
                continue

            # Skip header rows repeated mid-file by merged exports.
            if row[0].strip() == "case_id":
                counts["header_rows"] += 1
                continue

            # Clean the row; a broken critical field sends it to quarantine.
            try:
                case = Case.from_row(row)
            except ValueError as error:
                quarantine.append((line_number, str(error), row))
                continue

            # Same case_id after cleaning: keep the first one only.
            if case.case_id in seen_ids:
                counts["duplicates"] += 1
                continue

            seen_ids.add(case.case_id)
            clean_cases.append(case)

    return clean_cases, quarantine, counts


def write_outputs(clean_cases, quarantine):
    """Write cases_clean.csv (sorted by case_id) and quarantine.csv."""
    with open("cases_clean.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CLEAN_HEADER)
        for case in sorted(clean_cases, key=lambda c: c.case_id):
            writer.writerow([
                case.case_id,
                case.victim_name,
                case.sex,
                case.age,
                case.incident_date.strftime("%Y-%m-%d"),
                case.year,
                case.beat,
                case.status,
                case.callback_phone,
            ])

    with open("quarantine.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(QUARANTINE_HEADER)
        for line_number, reason, row in quarantine:
            writer.writerow([line_number, reason, ",".join(row)])


if __name__ == "__main__":
    cases, quarantine, counts = load("midterm_cases_raw.csv")
    write_outputs(cases, quarantine)
    print(counts)
