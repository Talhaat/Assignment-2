
import csv
import math
import re
from pathlib import Path

from fitness_analyzer.analysis import is_valid
from fitness_analyzer.exceptions import InvalidIdentifierError, InvalidRecordError
from fitness_analyzer.models import (
    ReferenceProfile,
    Participant,
    Observation,
    FitnessSession
)

PARTICIPANT_COLUMNS = [
    "participant_id",
    "name",
    "baseline_heart_rate",
    "baseline_skin_response",
    "baseline_temperature",
]

SESSION_COLUMNS = [
    "session_id",
    "participant_id",
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
]

# Identifier formats from section 4.2. Used with re.fullmatch, so the whole value must match
# (same as ^P\d{3}$ and ^FIT-\d{4}-\d{3}$).
PARTICIPANT_ID_PATTERN = r"P\d{3}"
SESSION_ID_PATTERN = r"FIT-\d{4}-\d{3}"

# Type of each number column. Heart rate and timestamp are whole numbers, the rest are decimals.
PARTICIPANT_TYPES = {
    "baseline_heart_rate": int,
    "baseline_skin_response": float,
    "baseline_temperature": float,
}

SESSION_TYPES = {
    "timestamp": int,
    "heart_rate": int,
    "skin_response": float,
    "temperature": float,
    "activity_level": float,
    "signal_quality": float,
}

# Heart rate limits are the same as in Assignment 1 (30-220 bpm).
MIN_HEART_RATE = 30
MAX_HEART_RATE = 220

# Skin temperature limits in degrees Celsius. 25-42 is the range the Assignment 1 data generator
# keeps skin temperature inside. A value outside it (like 55.0) is a sensor error, not a real reading.
MIN_TEMPERATURE = 25.0
MAX_TEMPERATURE = 42.0

# Allowed ranges as (field, lowest, highest). Both ends are allowed. None means no limit on that side.
# Range checks are plain comparisons, not regex (section 4.2).
PARTICIPANT_LIMITS = [
    ("baseline_heart_rate", MIN_HEART_RATE, MAX_HEART_RATE),
    ("baseline_skin_response", 0, None),
    ("baseline_temperature", MIN_TEMPERATURE, MAX_TEMPERATURE),
]

SESSION_LIMITS = [
    ("timestamp", 0, None),
    ("heart_rate", MIN_HEART_RATE, MAX_HEART_RATE),
    ("skin_response", 0, None),
    ("temperature", MIN_TEMPERATURE, MAX_TEMPERATURE),
    ("activity_level", 0, 1),
    ("signal_quality", 0, 1),
]


#Function to load the participants file and all session files
# Input is participants file path and a list of session file paths, return participants dictionary,
# list of FitnessSession objects, list of rejected row dictionaries and number of accepted session rows.
def load_data(profiles_path, session_paths):
    rejected = []
    participants = load_participants(profiles_path, rejected)

    # Without participants every session row would be rejected as unknown, so stop here.
    if not participants:
        return participants, [], rejected, 0

    sessions, accepted_count = load_sessions(session_paths, participants, rejected)
    return participants, sessions, rejected, accepted_count


#Function to read participants.csv into Participant objects
# Input is file path and the list to add rejected rows to, return dictionary of Participant objects keyed by participant id.
def load_participants(path, rejected):
    participants = {}
    rows = read_csv_rows(path, PARTICIPANT_COLUMNS)

    if rows is None:
        return participants

    for line_number, row in rows:
        try:
            values = validate_row(row, PARTICIPANT_COLUMNS, PARTICIPANT_TYPES, PARTICIPANT_LIMITS)

            if values["participant_id"] in participants:
                raise InvalidRecordError(
                    "participant_id",
                    f"participant_id {values['participant_id']} is listed more than once"
                )
        except (InvalidIdentifierError, InvalidRecordError) as error:
            rejected.append(make_rejected_row(path, line_number, error))
            continue

        reference = ReferenceProfile(
            values["baseline_heart_rate"],
            values["baseline_skin_response"],
            values["baseline_temperature"]
        )
        participants[values["participant_id"]] = Participant(
            values["participant_id"],
            values["name"],
            reference
        )

    return participants


#Function to read session files and group the accepted rows into one FitnessSession per session id
# Input is list of session file paths, participants dictionary and the list to add rejected rows to,
# return list of FitnessSession objects and number of accepted rows.
def load_sessions(paths, participants, rejected):
    sessions = {}
    accepted_count = 0

    for path in paths:
        rows = read_csv_rows(path, SESSION_COLUMNS)

        # The file could not be read, the reason is already printed, so go on with the next file.
        if rows is None:
            continue

        for line_number, row in rows:
            try:
                values = validate_row(row, SESSION_COLUMNS, SESSION_TYPES, SESSION_LIMITS)
                participant = find_participant(values["participant_id"], participants)
                session = find_session(sessions, values["session_id"], participant)
            except (InvalidIdentifierError, InvalidRecordError) as error:
                rejected.append(make_rejected_row(path, line_number, error))
                continue

            # Poor-signal rule (section 4.3): signal_quality is checked to be 0-1 above. A row with
            # signal_quality below 0.5 is still a real measurement, so it is accepted and not rejected,
            # but is_valid() marks it unusable, like in Assignment 1. A session where under half the
            # rows are usable then becomes "insufficient data" in the analysis (FIT-2026-005).
            observation = Observation.from_dict(values)
            observation.mark_validity(is_valid(observation))
            session.add_observation(observation)
            accepted_count += 1

    return list(sessions.values()), accepted_count


#Function to read the header and rows of one CSV file
# Input is file path and list of expected column names, return list of (line number, row) pairs, or None if the file can not be used.
def read_csv_rows(path, columns):
    path = Path(path)

    try:
        with open(path, encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            header = next(reader, None)
            rows = []

            for row in reader:
                # A blank line has no data, so it is skipped instead of rejected.
                if row:
                    rows.append((reader.line_num, row))
    except FileNotFoundError:
        print(f"Error: could not find {path}, skipping this file.")
        return None
    except PermissionError:
        print(f"Error: no permission to read {path}, skipping this file.")
        return None
    except IsADirectoryError:
        print(f"Error: {path} is a folder, not a CSV file, skipping it.")
        return None
    except UnicodeDecodeError:
        print(f"Error: {path} is not UTF-8 text, skipping this file.")
        return None
    except csv.Error as error:
        print(f"Error: {path} could not be read as CSV ({error}), skipping this file.")
        return None

    if header is None:
        print(f"Error: {path} is empty, skipping this file.")
        return None

    # The columns must not be renamed (section 3), so the header has to match exactly.
    header = [name.strip() for name in header]
    if header != columns:
        print(f"Error: {path} has the columns {header}, expected {columns}, skipping this file.")
        return None

    return rows


#Function to run the checks that are the same for every CSV file, in the order listed at the top
# Input is row as a list of strings, column names, type dictionary and limits list, return dictionary with converted values.
def validate_row(row, columns, types, limits):
    check_row_length(row, columns)
    values = {column: text.strip() for column, text in zip(columns, row)}
    check_missing_fields(values)
    check_identifiers(values)
    convert_numbers(values, types)
    check_ranges(values, limits)
    return values


#Function to check that a row has one value per column
# Input is row as a list of strings and list of column names, raise InvalidRecordError if the length is wrong.
def check_row_length(row, columns):
    if len(row) != len(columns):
        raise InvalidRecordError(
            "row",
            f"expected {len(columns)} fields but found {len(row)}"
        )


#Function to check that no field in a row is empty
# Input is dictionary of column name to text, raise InvalidRecordError naming every empty field.
def check_missing_fields(values):
    problems = [(field, f"{field} is missing") for field, text in values.items() if text == ""]
    raise_if_problems(problems, InvalidRecordError)


#Function to check participant id and session id with regex (section 4.2)
# Input is dictionary of column name to text, raise InvalidIdentifierError naming every bad identifier.
def check_identifiers(values):
    problems = []

    if not re.fullmatch(PARTICIPANT_ID_PATTERN, values["participant_id"]):
        problems.append((
            "participant_id",
            f"participant_id '{values['participant_id']}' is not P followed by three digits (like P001)"
        ))

    # participants.csv has no session_id column, so this check is only for session files.
    if "session_id" in values and not re.fullmatch(SESSION_ID_PATTERN, values["session_id"]):
        problems.append((
            "session_id",
            f"session_id '{values['session_id']}' is not in the format FIT-YYYY-NNN (like FIT-2026-001)"
        ))

    raise_if_problems(problems, InvalidIdentifierError)


#Function to convert the number columns from text to int or float
# Input is dictionary of column name to text and type dictionary, change the values in place,
# raise InvalidRecordError naming every value that is not a number.
def convert_numbers(values, types):
    problems = []

    for field, number_type in types.items():
        text = values[field]
        type_name = "whole number" if number_type is int else "number"

        try:
            number = number_type(text)
        except ValueError:
            problems.append((field, f"{field} '{text}' is not a {type_name}"))
            continue

        # float() also accepts "nan" and "inf", which would slip past the range checks.
        if not math.isfinite(number):
            problems.append((field, f"{field} '{text}' is not a finite {type_name}"))
            continue

        values[field] = number

    raise_if_problems(problems, InvalidRecordError)


#Function to check that numbers are inside the allowed limits
# Input is dictionary with converted values and list of (field, lowest, highest) limits, raise InvalidRecordError naming every value out of range.
def check_ranges(values, limits):
    problems = []

    for field, lowest, highest in limits:
        value = values[field]

        if lowest is not None and value < lowest:
            problems.append((field, f"{field} {value} is below the minimum of {lowest}"))
        elif highest is not None and value > highest:
            problems.append((field, f"{field} {value} is above the maximum of {highest}"))

    raise_if_problems(problems, InvalidRecordError)


#Function to find the participant a session row belongs to
# Input is participant id and participants dictionary, return Participant object, raise InvalidRecordError if it is unknown.
def find_participant(participant_id, participants):
    try:
        return participants[participant_id]
    except KeyError:
        raise InvalidRecordError(
            "participant_id",
            f"participant {participant_id} does not exist in the participants file"
        )


#Function to get the session for a row, or create it the first time the session id is seen
# Input is sessions dictionary, session id and Participant object, return FitnessSession object,
# raise InvalidRecordError if the session already belongs to another participant.
def find_session(sessions, session_id, participant):
    if session_id not in sessions:
        sessions[session_id] = FitnessSession(session_id, participant)

    session = sessions[session_id]

    if session.participant is not participant:
        raise InvalidRecordError(
            "participant_id",
            f"session {session_id} already belongs to participant {session.participant.participant_id}"
        )

    return session


#Function to raise one error that names every bad field found in one check
# Input is list of (field, reason) pairs and the exception class to raise, return nothing when the list is empty.
def raise_if_problems(problems, error_class):
    if not problems:
        return

    fields = ", ".join(field for field, reason in problems)
    reasons = "; ".join(reason for field, reason in problems)
    raise error_class(fields, reasons)


#Function to build the dictionary that describes one rejected row
# Input is file path, line number in the file (header = 1) and the exception that was raised, return dictionary with file, row, field and reason.
def make_rejected_row(path, line_number, error):
    return {
        "file": Path(path).name,
        "row": line_number,
        "field": error.field,
        "reason": str(error),
    }
