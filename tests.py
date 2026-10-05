#----------------------------------------------------------
#--------File for tests, Assignment 2, ACIT4422------------
#----------------------------------------------------------

# Tests for section 6: valid, invalid, missing-file and boundary cases, plus the report files.
# Run from this folder with: python3 tests.py
# The official CSV files in data/ are only read. Test files are written to a temporary folder.

import contextlib
import csv
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from fitness_analyzer.analysis import build_session_report
from fitness_analyzer.exceptions import InvalidIdentifierError, InvalidRecordError
from fitness_analyzer.loader import (
    load_data,
    validate_row,
    SESSION_COLUMNS,
    SESSION_TYPES,
    SESSION_LIMITS
)
from fitness_analyzer.reports import write_reports

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PARTICIPANTS_FILE = DATA_DIR / "participants.csv"
SESSIONS_FILE = DATA_DIR / "fitness_sessions.csv"
INVALID_FILE = DATA_DIR / "fitness_sessions_invalid.csv"
MISSING_FILE = DATA_DIR / "does_not_exist.csv"

# Expected classification of each session in the valid file (see CHECKLIST.md).
EXPECTED_CLASSES = {
    "FIT-2026-001": "resting",
    "FIT-2026-002": "moderate activity",
    "FIT-2026-003": "high activity",
    "FIT-2026-004": "recovering",
    "FIT-2026-005": "insufficient data",
}


#Function to make one session row for participant P001, with normal values unless others are given
# Input is timestamp and optional heart rate, activity level, signal quality and session id, return list of strings.
def make_row(timestamp, heart_rate=70, activity_level=0.1, signal_quality=0.9, session_id="FIT-2026-900"):
    return [
        session_id,
        "P001",
        str(timestamp),
        str(heart_rate),
        "1.20",
        "32.4",
        str(activity_level),
        str(signal_quality),
    ]


#Function to write session rows to a CSV file in a temporary folder and load it with the official participants
# Input is list of rows (each a list of strings), return list of FitnessSession objects, list of rejected rows and accepted row count.
def load_test_rows(rows):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "test_sessions.csv"

        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(SESSION_COLUMNS)
            writer.writerows(rows)

        participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [path])

    return sessions, rejected, accepted_count


#Function to load the official invalid session file and look up its rejected rows by line number
# Input is none, return dictionary of rejected row dictionaries keyed by row number (header = 1).
def rejected_rows_by_line():
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [INVALID_FILE])
    return {record["row"]: record for record in rejected}


#Function to run the row checks on one row and catch the custom exception it raises
# Input is row as a list of strings, return the raised exception, or None if the row passed.
def get_validation_error(row):
    try:
        validate_row(row, SESSION_COLUMNS, SESSION_TYPES, SESSION_LIMITS)
    except (InvalidIdentifierError, InvalidRecordError) as error:
        return error

    return None


#Function to run load_data and keep what it prints, so the error message can be checked
# Input is participants file path and list of session file paths, return the four values from load_data and the printed text.
def load_and_capture(profiles_path, session_paths):
    printed = io.StringIO()

    with contextlib.redirect_stdout(printed):
        participants, sessions, rejected, accepted_count = load_data(profiles_path, session_paths)

    return participants, sessions, rejected, accepted_count, printed.getvalue()


#Function to load the official files, analyse every session and write the reports
# Input is output folder path, return list of the created file paths.
def write_official_reports(output_dir):
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [SESSIONS_FILE, INVALID_FILE])
    reports = [build_session_report(session) for session in sessions]
    return write_reports(output_dir, reports, rejected)


#Function to run main.py as its own program, like from the command line
# Input is list of command line arguments, return the finished process with return code, stdout and stderr.
def run_main(arguments):
    return subprocess.run(
        [sys.executable, "main.py"] + arguments,
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )


# ---------------- Valid cases ----------------

#Test that each session in the valid file gets its expected classification
# Input is none, return is not used. Uses assert to check the result.
def test_valid_sessions_classified():
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [SESSIONS_FILE])
    classes = {session.session_id: build_session_report(session)["classification"] for session in sessions}
    assert classes == EXPECTED_CLASSES


#Test that the valid file has no rejected rows, all 29 rows are accepted and values are numbers, not text
# Input is none, return is not used. Uses assert to check the result.
def test_valid_file_has_no_rejected_rows():
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [SESSIONS_FILE])
    assert rejected == []
    assert accepted_count == 29
    assert sorted(participants) == ["P001", "P002", "P003"]

    first = sessions[0].observations[0]
    assert first.heart_rate == 68
    assert first.temperature == 32.4


#Test that a session with no usable observations (FIT-2026-005) is "insufficient data" without averages, not a crash
# Input is none, return is not used. Uses assert to check the result.
def test_no_usable_observations():
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [SESSIONS_FILE])
    reports = {session.session_id: build_session_report(session) for session in sessions}
    report = reports["FIT-2026-005"]

    assert report["usable_observations"] == 0
    assert report["total_observations"] == 5
    assert report["heart_rate_summary"]["average"] is None
    assert report["comparison_to_reference"]["heart_rate_deviation"] is None
    assert report["explanation"].startswith("Insufficient data")


# ---------------- Invalid cases ----------------

#Test that only line 2 of the invalid file is accepted and every rejected row has file, row, field and reason
# Input is none, return is not used. Uses assert to check the result.
def test_invalid_file_only_first_row_accepted():
    participants, sessions, rejected, accepted_count = load_data(PARTICIPANTS_FILE, [INVALID_FILE])
    assert accepted_count == 1
    assert [record["row"] for record in rejected] == list(range(3, 13))

    for record in rejected:
        assert set(record) == {"file", "row", "field", "reason"}
        assert record["file"] == "fitness_sessions_invalid.csv"

    # The one accepted row is too little data to classify.
    assert len(sessions) == 1
    assert build_session_report(sessions[0])["classification"] == "insufficient data"


#Test that a participant id in the wrong format ("001") is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_bad_participant_id_rejected():
    record = rejected_rows_by_line()[4]
    assert record["field"] == "participant_id"
    assert "'001' is not P followed by three digits" in record["reason"]


#Test that a session id in the wrong format ("FIT-26-102") is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_bad_session_id_rejected():
    record = rejected_rows_by_line()[7]
    assert record["field"] == "session_id"
    assert "'FIT-26-102' is not in the format FIT-YYYY-NNN" in record["reason"]


#Test that values that are not numbers ("fast", "two") are rejected
# Input is none, return is not used. Uses assert to check the result.
def test_non_number_rejected():
    records = rejected_rows_by_line()
    assert records[3]["field"] == "heart_rate"
    assert "'fast' is not a whole number" in records[3]["reason"]
    assert records[9]["field"] == "timestamp"
    assert "'two' is not a whole number" in records[9]["reason"]


#Test that a row with an empty activity level is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_missing_field_rejected():
    record = rejected_rows_by_line()[5]
    assert record["field"] == "activity_level"
    assert "activity_level is missing" in record["reason"]


#Test that a row with only 7 fields is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_short_row_rejected():
    record = rejected_rows_by_line()[12]
    assert record["field"] == "row"
    assert "expected 8 fields but found 7" in record["reason"]


#Test that a participant id that is not in participants.csv (P999) is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_unknown_participant_rejected():
    record = rejected_rows_by_line()[8]
    assert record["field"] == "participant_id"
    assert "P999 does not exist" in record["reason"]


#Test that out-of-range values are rejected, and that a row with several bad values names all of them
# Input is none, return is not used. Uses assert to check the result.
def test_out_of_range_rejected():
    records = rejected_rows_by_line()
    assert records[6]["field"] == "signal_quality"
    assert "above the maximum of 1" in records[6]["reason"]
    assert records[10]["field"] == "heart_rate"
    assert "below the minimum of 30" in records[10]["reason"]
    assert records[11]["field"] == "skin_response, temperature, activity_level"


#Test that the row checks raise the two custom exceptions, and that a row with too many fields is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_custom_exceptions_raised():
    assert get_validation_error(make_row(0)) is None

    error = get_validation_error(make_row(0, session_id="FIT-26-001"))
    assert isinstance(error, InvalidIdentifierError)
    assert error.field == "session_id"

    error = get_validation_error(make_row(0, heart_rate="fast"))
    assert isinstance(error, InvalidRecordError)
    assert error.field == "heart_rate"

    error = get_validation_error(make_row(0) + ["extra"])
    assert isinstance(error, InvalidRecordError)
    assert error.field == "row"
    assert "expected 8 fields but found 9" in str(error)


# ---------------- Missing-file cases ----------------

#Test that a missing participants file gives a clear error and empty results instead of a crash
# Input is none, return is not used. Uses assert to check the result.
def test_missing_profiles_file():
    participants, sessions, rejected, accepted_count, printed = load_and_capture(MISSING_FILE, [SESSIONS_FILE])
    assert participants == {}
    assert sessions == []
    assert accepted_count == 0
    assert "could not find" in printed
    assert "does_not_exist.csv" in printed


#Test that a missing session file is skipped with a clear error and the other session file is still loaded
# Input is none, return is not used. Uses assert to check the result.
def test_missing_session_file_skipped():
    participants, sessions, rejected, accepted_count, printed = load_and_capture(
        PARTICIPANTS_FILE,
        [MISSING_FILE, SESSIONS_FILE]
    )
    assert "could not find" in printed
    assert accepted_count == 29
    assert len(sessions) == 5
    assert rejected == []


#Test that main.py with a missing participants file stops with exit code 1 and a message, not a traceback
# Input is none, return is not used. Uses assert to check the result.
def test_main_missing_profiles_file():
    with tempfile.TemporaryDirectory() as folder:
        result = run_main(["--profiles", "data/does_not_exist.csv", "--output", folder])

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "no participants could be loaded" in result.stdout


# ---------------- Boundary cases ----------------

#Test that heart rate exactly 30 and 220 is accepted, and 29 and 221 is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_heart_rate_limits():
    sessions, rejected, accepted_count = load_test_rows([
        make_row(0, heart_rate=30),
        make_row(1, heart_rate=220),
        make_row(2, heart_rate=29),
        make_row(3, heart_rate=221),
    ])
    assert accepted_count == 2
    assert [o.heart_rate for o in sessions[0].observations] == [30, 220]
    assert [(record["row"], record["field"]) for record in rejected] == [(4, "heart_rate"), (5, "heart_rate")]


#Test that signal quality exactly 0.5 is usable and 0.49 is not, and that both are accepted rows, not rejected
# Input is none, return is not used. Uses assert to check the result.
def test_signal_quality_limit():
    sessions, rejected, accepted_count = load_test_rows([
        make_row(0, signal_quality=0.5),
        make_row(1, signal_quality=0.49),
        make_row(2, signal_quality=0),
        make_row(3, signal_quality=1),
    ])
    assert rejected == []
    assert accepted_count == 4
    assert [o.is_valid for o in sessions[0].observations] == [True, False, False, True]


#Test that activity level exactly 0 and 1 is accepted, and just outside 0-1 is rejected
# Input is none, return is not used. Uses assert to check the result.
def test_activity_level_limits():
    sessions, rejected, accepted_count = load_test_rows([
        make_row(0, activity_level=0),
        make_row(1, activity_level=1),
        make_row(2, activity_level=-0.01),
        make_row(3, activity_level=1.01),
    ])
    assert accepted_count == 2
    assert [o.activity_level for o in sessions[0].observations] == [0.0, 1.0]
    assert [(record["row"], record["field"]) for record in rejected] == [(4, "activity_level"), (5, "activity_level")]


#Test that a session with exactly 50% usable observations (4 of 8) is classified and not "insufficient data"
# Input is none, return is not used. Uses assert to check the result.
def test_half_usable_session_is_classified():
    rows = [make_row(t, signal_quality=0.9 if t % 2 == 0 else 0.3) for t in range(8)]
    sessions, rejected, accepted_count = load_test_rows(rows)
    report = build_session_report(sessions[0])

    assert report["usable_observations"] == 4
    assert report["total_observations"] == 8
    assert report["classification"] == "resting"


#Test that a session with just under 50% usable observations (4 of 9) is "insufficient data"
# Input is none, return is not used. Uses assert to check the result.
def test_under_half_usable_session_is_insufficient():
    rows = [make_row(t, signal_quality=0.9 if t < 4 else 0.3) for t in range(9)]
    sessions, rejected, accepted_count = load_test_rows(rows)
    report = build_session_report(sessions[0])

    assert report["usable_observations"] == 4
    assert report["classification"] == "insufficient data"
    assert "less than 50% of its observations usable" in report["explanation"]


#Test that 4 usable observations is enough to classify a session, and 3 is not
# Input is none, return is not used. Uses assert to check the result.
def test_minimum_usable_observations():
    rows = [make_row(t, session_id="FIT-2026-901") for t in range(4)]
    rows += [make_row(t, session_id="FIT-2026-902") for t in range(3)]
    sessions, rejected, accepted_count = load_test_rows(rows)
    reports = {session.session_id: build_session_report(session) for session in sessions}

    assert reports["FIT-2026-901"]["classification"] == "resting"
    assert reports["FIT-2026-902"]["classification"] == "insufficient data"
    assert "fewer than 4 usable observations" in reports["FIT-2026-902"]["explanation"]


# ---------------- Report files ----------------

#Test that writing the reports twice into the same folder gives the same three files (overwritten, not appended)
# Input is none, return is not used. Uses assert to check the result.
def test_reports_same_on_second_run():
    with tempfile.TemporaryDirectory() as folder:
        # The output folder does not exist yet, so write_reports has to create it.
        output_dir = Path(folder) / "output"

        first_paths = write_official_reports(output_dir)
        first_texts = [path.read_text(encoding="utf-8") for path in first_paths]

        second_paths = write_official_reports(output_dir)
        second_texts = [path.read_text(encoding="utf-8") for path in second_paths]

        file_names = sorted(path.name for path in output_dir.iterdir())

    assert first_paths == second_paths
    assert first_texts == second_texts
    assert file_names == ["analysis_report.txt", "analysis_summary.csv", "rejected_records.txt"]


#Test that the summary has one row per session and the rejected file lists every rejected row
# Input is none, return is not used. Uses assert to check the result.
def test_report_files_content():
    with tempfile.TemporaryDirectory() as folder:
        summary_path, report_path, rejected_path = write_official_reports(Path(folder))

        with open(summary_path, encoding="utf-8", newline="") as file:
            summary_rows = list(csv.DictReader(file))

        report_text = report_path.read_text(encoding="utf-8")
        rejected_lines = rejected_path.read_text(encoding="utf-8").splitlines()

    expected = dict(EXPECTED_CLASSES)
    expected["FIT-2026-101"] = "insufficient data"
    assert {row["session_id"]: row["classification"] for row in summary_rows} == expected

    assert "Sessions analysed: 6" in report_text
    assert rejected_lines[0] == "Rejected records: 10"
    assert len(rejected_lines) == 11
    assert rejected_lines[2].startswith("file: fitness_sessions_invalid.csv | row: 4 | field: participant_id")


#Test that the command from the PDF (section 7) runs and prints accepted rows, rejected rows and the files
# Input is none, return is not used. Uses assert to check the result.
def test_main_runs_with_pdf_command():
    with tempfile.TemporaryDirectory() as folder:
        result = run_main([
            "--profiles", "data/participants.csv",
            "--sessions", "data/fitness_sessions.csv",
            "--output", folder,
        ])
        created = sorted(path.name for path in Path(folder).iterdir())

    assert result.returncode == 0
    assert "Accepted rows: 30" in result.stdout
    assert "Rejected rows: 10" in result.stdout
    assert created == ["analysis_report.txt", "analysis_summary.csv", "rejected_records.txt"]


if __name__ == "__main__":
    test_valid_sessions_classified()
    test_valid_file_has_no_rejected_rows()
    test_no_usable_observations()

    test_invalid_file_only_first_row_accepted()
    test_bad_participant_id_rejected()
    test_bad_session_id_rejected()
    test_non_number_rejected()
    test_missing_field_rejected()
    test_short_row_rejected()
    test_unknown_participant_rejected()
    test_out_of_range_rejected()
    test_custom_exceptions_raised()

    test_missing_profiles_file()
    test_missing_session_file_skipped()
    test_main_missing_profiles_file()

    test_heart_rate_limits()
    test_signal_quality_limit()
    test_activity_level_limits()
    test_half_usable_session_is_classified()
    test_under_half_usable_session_is_insufficient()
    test_minimum_usable_observations()

    test_reports_same_on_second_run()
    test_report_files_content()
    test_main_runs_with_pdf_command()
    print("All tests passed")
