from dates import parse_date  # Person A's date parser.
from fields import (  # Person B's field cleaners.
    clean_age,
    clean_beat,
    clean_case_id,
    clean_name,
    clean_sex,
    clean_status,
)


class Case:
    """One cleaned case."""

    def __init__(self, case_id, victim_name, sex, age, incident_date, year,
                 beat, status, callback_phone):
        """Store the nine cleaned fields on this case."""
        self.case_id = case_id  # 'CC-#####'
        self.victim_name = victim_name  # 'Last, I' in Title Case
        self.sex = sex  # 'M', 'F', or 'U'
        self.age = age  # '0' to '110', or ''
        self.incident_date = incident_date  # a datetime.date
        self.year = year  # the incident year as an int
        self.beat = beat  # 3 digits, or ''
        self.status = status  # 'OPEN' or 'CLOSED'
        self.callback_phone = callback_phone  # '214-555-1234', or ''

    @classmethod
    def from_row(cls, row):
        """Clean a 9-field row. Raise ValueError if a critical field is bad."""
        # A row with the wrong number of fields can't be trusted at all.
        if len(row) != 9:
            raise ValueError("wrong field count")

        # Unpack the 9 raw values into their own variables.
        (raw_id, raw_name, raw_sex, raw_age, raw_date,
         raw_address, raw_beat, raw_status, raw_tips) = row

        # Critical fields: any ValueError here passes through to the loader.
        case_id = clean_case_id(raw_id)
        incident_date = parse_date(raw_date)
        status = clean_status(raw_status)
        if status is None:  # clean_status returns None for unknown statuses.
            raise ValueError("unknown status")

        # Non-critical fields: repaired, never rejected.
        victim_name = clean_name(raw_name)
        sex = clean_sex(raw_sex)
        age = clean_age(raw_age)
        beat = clean_beat(raw_beat)

        # Derived fields.
        year = incident_date.year
        callback_phone = ""  # TODO: use Person A's clean_phone(raw_tips) once it exists.

        return cls(case_id, victim_name, sex, age, incident_date, year,
                   beat, status, callback_phone)

    @property
    def years_unsolved(self):
        """How many years since the incident, as of 2026."""
        return 2026 - self.year

    @property
    def is_stale(self):
        """True if the case is open and has been unsolved for 5+ years."""
        return self.status == "OPEN" and self.years_unsolved >= 5
