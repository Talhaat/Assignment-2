#----------------------------------------------------------
#--------File for custom exceptions, Assignment 2----------
#----------------------------------------------------------

# The two classes from the assignment PDF, section 4.4. Both are raised and caught in loader.py.
# They also store the field (column) that failed, so a rejected row can say which field was wrong.

#Exception for identifiers with wrong format, like participant id or session id
class InvalidIdentifierError(ValueError):
    """Raised when an identifier has an invalid format."""

    #Field is the column name (or several, comma separated), message is the reason.
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


#Exception for CSV rows that can not be accepted
class InvalidRecordError(ValueError):
    """Raised when a CSV record cannot be accepted."""

    #Field is the column name (or several, comma separated, or "row"), message is the reason.
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
