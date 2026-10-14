# Bring in Python's regular expression module for pattern matching.
import re  # Load the regular expression tools.


# Define a function that cleans a case ID.
def clean_case_id(raw):  # Start the clean_case_id function.
    """Return 'CC-#####', or raise ValueError."""
    # Check that the whole value is CC, an optional dash or space, and 5 digits.
    match = re.fullmatch(r"\s*CC[- ]?(\d{5})\s*", raw, re.IGNORECASE)  # Try to match the case ID pattern.
    # See whether the pattern matched.
    if match:  # Only continue here if the case ID is valid.
        # Build the standard case ID from the 5 digits.
        return "CC-" + match.group(1)  # Return "CC-" plus the 5 digits.
    # Stop with an error because the case ID is not valid.
    raise ValueError("bad case_id")  # Raise an error for a bad case ID.


# Define a function that cleans a victim name.
def clean_name(raw):
    """Strip spaces, collapse double spaces, Title Case. Blank names stay blank."""
    # Split on spaces, rejoin with single spaces, then capitalize each word.
    # A blank name becomes "" here, and the row is kept.
    return " ".join(raw.split()).title()


# Define a function that cleans a case status.
def clean_status(raw):  # Start the clean_status function.
    """Return 'OPEN', 'CLOSED', or None (unknown)."""
    # Remove outside spaces and make the text uppercase.
    value = raw.strip().upper()  # Normalize the status text.
    # See whether the status means open.
    if value in ("OPEN", "OPN"):  # Check for the open spellings.
        # Give back the standard open status.
        return "OPEN"  # Return "OPEN".
    # See whether the status means closed.
    if value in ("CLOSED", "CLSD", "CLEARED"):  # Check for the closed spellings.
        # Give back the standard closed status.
        return "CLOSED"  # Return "CLOSED".
    # Give back None because the status is unknown.
    return None  # Return None for an unknown status.


# Define a function that cleans a victim's sex.
def clean_sex(raw):  # Start the clean_sex function.
    """Return 'M', 'F', or 'U'."""
    # Remove outside spaces and make the text uppercase.
    value = raw.strip().upper()  # Normalize the sex text.
    # See whether the value means male.
    if value in ("M", "MALE"):  # Check for the male spellings.
        # Give back the standard male code.
        return "M"  # Return "M".
    # See whether the value means female.
    if value in ("F", "FEMALE"):  # Check for the female spellings.
        # Give back the standard female code.
        return "F"  # Return "F".
    # Give back the unknown code for anything else.
    return "U"  # Return "U" for unknown.


# Define a function that cleans a victim's age.
def clean_age(raw):  # Start the clean_age function.
    """Return a string from '0' to '110', or ''."""
    # Remove outside spaces.
    value = raw.strip()  # Tidy the age text.
    # See whether the value is not made only of digits.
    if not value.isdigit():  # Check for non-numeric ages like "unknown" or "-1".
        # Give back a blank because the age is not a number.
        return ""  # Return a blank string.
    # Turn the digits into a whole number.
    age = int(value)  # Convert the text to an integer.
    # See whether the age is in a believable range.
    if 0 <= age <= 110:  # Check that the age is from 0 to 110.
        # Give back the age as text.
        return str(age)  # Return the age as a string.
    # Give back a blank because the age is out of range.
    return ""  # Return a blank string.


# Define a function that cleans a police beat.
def clean_beat(raw):  # Start the clean_beat function.
    """Return the 3 digits as a string, or ''."""
    # Look for the first group of 3 digits in the value.
    match = re.search(r"\d{3}", raw)  # Search for 3 digits in a row.
    # See whether 3 digits were found.
    if match:  # Only continue here if a beat number was found.
        # Give back the 3 digits that were found.
        return match.group(0)  # Return the 3 digits.
    # Give back a blank because no beat number was found.
    return ""  # Return a blank string.
