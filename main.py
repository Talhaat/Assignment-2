#----------------------------------------------------------
#--------Main file for running the application-------------
#----------------------------------------------------------

# Run from this folder with:
# python3 main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv --output output
# Every option has a default (relative to this folder), so plain "python3 main.py" does the same.

import argparse
import sys
from pathlib import Path

from fitness_analyzer.analysis import build_session_report
from fitness_analyzer.loader import load_data
from fitness_analyzer.reports import write_reports


#Function to run the program: load the files, analyse each session, write the reports and print a summary
# Input is none (the paths come from the command line), return nothing. Exits with code 1 if there is
# nothing to analyse or the reports can not be written.
def main():
    arguments = parse_arguments()

    # Section 4.1 wants both session files loaded, so the invalid file is added after --sessions.
    # It is skipped if it was already given with --sessions, so its rows are not loaded twice.
    session_paths = [arguments.sessions]
    if arguments.invalid.resolve() != arguments.sessions.resolve():
        session_paths.append(arguments.invalid)

    participants, sessions, rejected, accepted_count = load_data(arguments.profiles, session_paths)

    # Every session row needs a known participant, so without participants there is nothing to analyse.
    # The loader has already printed any file problem. Rejected participant rows are printed here,
    # because no report files are written in this case.
    if not participants:
        print(f"Error: no participants could be loaded from {arguments.profiles}, so there is nothing to analyse.")
        for record in rejected:
            print(f"  {record['file']} row {record['row']}: {record['reason']}")
        sys.exit(1)

    reports = [build_session_report(session) for session in sessions]

    # Writing can fail if the output folder is not writable, or if the output path is a file.
    try:
        created_files = write_reports(arguments.output, reports, rejected)
    except PermissionError as error:
        print(f"Error: no permission to write the reports in {arguments.output} ({error}).")
        sys.exit(1)
    except OSError as error:
        print(f"Error: could not write the reports in {arguments.output} ({error}).")
        sys.exit(1)

    print_completion_summary(accepted_count, len(rejected), len(reports), created_files)


#Function to read the file paths from the command line (section 7)
# Input is none, return argparse namespace with profiles, sessions, invalid and output as Path objects.
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Smart Fitness Session Analyzer: analyse fitness sessions from CSV files and write reports."
    )

    parser.add_argument(
        "--profiles",
        type=Path,
        default="data/participants.csv",
        help="participants CSV file (default: %(default)s)"
    )
    parser.add_argument(
        "--sessions",
        type=Path,
        default="data/fitness_sessions.csv",
        help="fitness sessions CSV file (default: %(default)s)"
    )

    # The invalid file gets its own option with a default, instead of letting --sessions take several
    # paths (nargs="+"). That way the exact command from the PDF, which gives only one --sessions path,
    # still loads both session files (section 4.1).
    parser.add_argument(
        "--invalid",
        type=Path,
        default="data/fitness_sessions_invalid.csv",
        help="fitness sessions CSV file with invalid rows (default: %(default)s)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="output",
        help="folder for the report files, created if missing (default: %(default)s)"
    )

    return parser.parse_args()


#Function to print the completion summary (section 7)
# Input is accepted row count, rejected row count, number of sessions analysed and list of created file paths, return nothing.
def print_completion_summary(accepted_count, rejected_count, session_count, created_files):
    # Accepted rows are session rows. Rejected rows come from every file, the participants file included.
    print("Analysis complete.")
    print(f"Accepted rows: {accepted_count}")
    print(f"Rejected rows: {rejected_count}")
    print(f"Sessions analysed: {session_count}")
    print("Report files created:")

    for path in created_files:
        print(f"  {path}")


if __name__ == "__main__":
    main()
