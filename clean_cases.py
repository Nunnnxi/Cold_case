import csv
from case_model import Case

CLEAN_HEADER = ["case_id", "victim_name", "sex", "age", "incident_date",
                "year", "beat", "status", "callback_phone"]
QUARANTINE_HEADER = ["line_number", "reason", "raw_row"]
DECADES = [1980, 1990, 2000, 2010, 2020]


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


def clearance_rate(cases):
    """Return CLOSED / total as a percent, or 0.0 if there are no cases."""
    if not cases:
        return 0.0
    closed = sum(1 for case in cases if case.status == "CLOSED")
    return closed / len(cases) * 100


def raw_closed_rate(path):
    """Clearance rate from the raw file taken at face value.

    Every non-blank, non-header row counts as a case, and only rows whose
    status is exactly "CLOSED" (no stripping, no other spellings) count as closed.
    """
    total = 0
    closed = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # Skip the real header on line 1.
        for row in reader:
            if all(field.strip() == "" for field in row):
                continue
            if row[0].strip() == "case_id":
                continue
            total += 1
            # Truncated rows may not reach the status column at all.
            if len(row) > 7 and row[7] == "CLOSED":
                closed += 1
    if total == 0:
        return 0.0
    return closed / total * 100


def build_report(clean_cases, quarantine, counts, raw_path):
    """Return the full report as one string."""
    lines = []

    # 1. Intake: the funnel from raw rows to clean cases.
    data_rows = counts["rows_read"] - counts["blank_rows"] - counts["header_rows"]
    reasons = {}  # quarantine reason -> count
    for line_number, reason, row in quarantine:
        reasons[reason] = reasons.get(reason, 0) + 1

    lines.append("COLD CASE FILE REPORT")
    lines.append("=" * 40)
    lines.append("")
    lines.append("1. INTAKE")
    lines.append(f"   Lines read after header:  {counts['rows_read']}")
    lines.append(f"   Blank lines skipped:      {counts['blank_rows']}")
    lines.append(f"   Header rows skipped:      {counts['header_rows']}")
    lines.append(f"   Data rows:                {data_rows}")
    lines.append(f"   Quarantined:              {len(quarantine)}")
    for reason in sorted(reasons):
        lines.append(f"      {reason}: {reasons[reason]}")
    lines.append(f"   Duplicates removed:       {counts['duplicates']}")
    lines.append(f"   Clean cases:              {len(clean_cases)}")
    lines.append("")

    # 2. Clearance: overall and by decade.
    overall = clearance_rate(clean_cases)
    lines.append("2. CLEARANCE")
    lines.append(f"   Overall clearance rate: {overall:.1f}%")
    for decade in DECADES:
        in_decade = [c for c in clean_cases if decade <= c.year < decade + 10]
        rate = clearance_rate(in_decade)
        lines.append(f"   {decade}s: {rate:5.1f}%  ({len(in_decade)} cases)")
    lines.append("")

    # 3. Open cases: stale count and the 5 oldest.
    open_cases = [c for c in clean_cases if c.status == "OPEN"]
    stale = [c for c in open_cases if c.is_stale]
    oldest = sorted(open_cases, key=lambda c: (c.incident_date, c.case_id))[:5]
    lines.append("3. OPEN CASES")
    lines.append(f"   Open cases:             {len(open_cases)}")
    lines.append(f"   Stale (open 5+ years):  {len(stale)}")
    lines.append("   5 oldest open cases:")
    for case in oldest:
        lines.append(f"      {case.case_id}  {case.incident_date.isoformat()}  "
                     f"{case.years_unsolved} yrs  {case.victim_name}")
    lines.append("")

    # 4. Beats: top 10 by open cases, with each beat's clearance rate.
    beat_cases = {}  # beat -> list of cases in that beat
    for case in clean_cases:
        if case.beat:  # Cases with a blank beat can't be ranked.
            beat_cases.setdefault(case.beat, []).append(case)
    beat_open = {beat: sum(1 for c in cases if c.status == "OPEN")
                 for beat, cases in beat_cases.items()}
    top_beats = sorted(beat_open, key=lambda b: (-beat_open[b], b))[:10]
    lines.append("4. TOP 10 BEATS BY OPEN CASES")
    for beat in top_beats:
        rate = clearance_rate(beat_cases[beat])
        lines.append(f"   Beat {beat}: {beat_open[beat]:3d} open, "
                     f"{rate:5.1f}% cleared ({len(beat_cases[beat])} cases)")
    lines.append("")

    # 5. Leads: open cases with a callback phone.
    with_phone = sum(1 for c in open_cases if c.callback_phone)
    phone_pct = with_phone / len(open_cases) * 100 if open_cases else 0.0
    lines.append("5. LEADS")
    lines.append(f"   Open cases with a callback phone: {with_phone} of "
                 f"{len(open_cases)} ({phone_pct:.1f}%)")
    lines.append("")

    # 6. Raw vs clean clearance rate.
    raw_rate = raw_closed_rate(raw_path)
    lines.append("6. RAW VS CLEAN")
    lines.append(f"   Raw rate (status exactly \"CLOSED\"): {raw_rate:.1f}%")
    lines.append(f"   Clean rate:                          {overall:.1f}%")
    lines.append(f"   Raw is off by {raw_rate - overall:+.1f} percentage points")

    return "\n".join(lines) + "\n"


def write_report(text, path="report.txt"):
    """Save the report text to path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    cases, quarantine, counts = load("midterm_cases_raw.csv")
    write_outputs(cases, quarantine)
    report = build_report(cases, quarantine, counts, "midterm_cases_raw.csv")
    write_report(report)
    print(report)
