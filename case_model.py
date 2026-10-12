class Case:
    """One cleaned case."""

    @classmethod
    def from_row(cls, row):
        """Clean a 9-field row. Raise ValueError if a critical field is bad."""
        raise NotImplementedError
