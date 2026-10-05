
class InvalidIdentifierError(ValueError):
    """Raised when an identifier has an invalid format."""

    #Field is the column name (or several, comma separated), message is the reason.
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field



class InvalidRecordError(ValueError):
    """Raised when a CSV record cannot be accepted."""

    #Field is the column name (or several, comma separated, or "row"), message is the reason.
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
