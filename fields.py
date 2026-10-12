def clean_case_id(raw):
    """Return 'CC-#####', or raise ValueError."""
    raise NotImplementedError

def clean_name(raw):
    """Strip spaces, collapse double spaces, Title Case."""
    raise NotImplementedError

def clean_status(raw):
    """Return 'OPEN', 'CLOSED', or None (unknown)."""
    raise NotImplementedError

def clean_sex(raw):
    """Return 'M', 'F', or 'U'."""
    raise NotImplementedError

def clean_age(raw):
    """Return a string from '0' to '110', or ''."""
    raise NotImplementedError

def clean_beat(raw):
    """Return the 3 digits as a string, or ''."""
    raise NotImplementedError
