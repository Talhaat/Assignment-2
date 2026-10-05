# ACIT4422 Assignment 2 - Smart Fitness Session Analyzer
### Student name: **Thomas Talha Løberg**

### Student ID: **thlob4941**
Assignment 2 for **ACIT4422 Scripting with Python**. It continues **Smart Fitness Session Analyzer, Option A** from Assignment 1 as a file-based application.

## Summary
This program reads participants and fitness sessions from the official CSV files, validates every row with regular expressions and range checks, and rejects bad rows with the file, row number, field and reason. It keeps running when a row or a file is bad. The accepted rows are grouped into sessions, compared with the participant's reference profile and classified as resting, moderate activity, high activity, recovering or insufficient data. The results are saved in three report files in the output folder.


## Package and modules
* `main.py` – entry point. Reads the command line options with argparse, runs the loader, the analysis and the reports, and prints the completion summary.
* `fitness_analyzer/__init__.py` – makes `fitness_analyzer` a package.
* `fitness_analyzer/models.py` – the classes from Assignment 1.
* `fitness_analyzer/exceptions.py` – the two custom exceptions.
* `fitness_analyzer/loader.py` – reads the CSV files, validates every row, groups the accepted rows into sessions and saves the rejected rows.
* `fitness_analyzer/analysis.py` – the analysis from Assignment 1: summaries, comparison with the reference, recovery check, classification and explanation. Gives one result dictionary per session.
* `fitness_analyzer/reports.py` – writes the three report files.
* `tests.py` – 24 tests with plain `assert` for valid, invalid, missing-file and boundary cases and the report files.
* `data/` – the official CSV files, not changed.
* `output/` – the report files made by the program.


## Classes
* ReferenceProfile
  * Stores the participant's baseline heart rate, skin response and temperature.
* Participant
  * Represents a participant. Stores participant ID, name (new in Assignment 2) and ReferenceProfile.
* Observation
  * One measurement window from a fitness session. Stores timestamp, heart rate, skin response, temperature, activity level and signal quality. It also stores if the window is usable or not.
* FitnessSession
  * One complete fitness session. Stores session ID (new in Assignment 2), participant and a list of Observation objects. It adds observations and returns the usable ones.
* InvalidIdentifierError and InvalidRecordError
  * The custom exceptions, see Error handling.


## Composition, Encapsulation and Inheritance

* Composition
  * Participant has a ReferenceProfile.
  * FitnessSession has a Participant and a list of Observation objects.
  * The loader builds the objects this way from the CSV rows, one FitnessSession per session ID.

* Encapsulation
  * Observation uses `_is_valid` as a protected attribute.
  * The value is read through the `is_valid` property and changed with the `mark_validity()` method. The loader calls `mark_validity()` with the poor-signal rule.

* Class method
  * `Observation.from_dict()` creates an Observation from the dictionary of converted values from one CSV row.

* Inheritance and overriding
  * Inheritance is not used for the data classes. They do not have a natural parent and child relationship. A FitnessSession contains a participant and observations instead of being a type of them, so composition fits better.
  * The only inheritance is the two exception classes. They inherit from `ValueError`, like in the PDF, and override `__init__` to also store the field that failed.


## Validation rules
### Identifiers
* Participant ID: `P\d{3}`, like P001.
* Session ID: `FIT-\d{4}-\d{3}`, like FIT-2026-001.
* Both are checked with `re.fullmatch`, so the whole value must match (same as `^...$`). Participant ID is checked in both participants.csv and the session files.

### Row checks
Every row goes through these checks in order. The first check that fails rejects the row.
1. Row length – one value per column (8 in the session files, 5 in participants.csv).
2. Missing fields – no empty values.
3. Identifiers – the regex checks above.
4. Types – timestamp and heart rate must be whole numbers (`int`), the other measurements decimals (`float`). Text like `fast`, and `nan` or `inf`, are rejected.
5. Ranges – plain `if` checks, not regex. Both ends are allowed:

| Field | Allowed |
|---|---|
| heart_rate, baseline_heart_rate | 30–220 bpm |
| temperature, baseline_temperature | 25–42 °C |
| skin_response, baseline_skin_response | 0 or more |
| timestamp | 0 or more |
| activity_level | 0–1 |
| signal_quality | 0–1 |

6. Participant – the participant ID must exist in participants.csv, and one session ID can only belong to one participant. In participants.csv a participant ID that is listed twice is rejected.

If one check finds several bad fields, all of them are named (like line 11 in fitness_sessions_invalid.csv).

The header of each file must have the official column names, otherwise the whole file is skipped. Blank lines are skipped.

### Poor-signal rule
* signal_quality outside 0–1 is rejected as out of range (like `1.40` on line 6 of the invalid file).
* signal_quality from 0 up to (not including) 0.5 is **not rejected**. The row is a well-formed, real measurement, so it is accepted and counted, but it is marked unusable with `mark_validity(False)`. It is not used in the summaries, the comparison or the classification.
* Exactly 0.5 is usable.
* This is why FIT-2026-005 (signal quality 0.25–0.34 on all 5 rows) has 0 of 5 usable observations and becomes insufficient data, without being in rejected_records.txt.

### Rejected rows
Every rejected row is saved with the file name, the row (line number in the file, header = line 1), the field and the reason. They are written to `rejected_records.txt`.


## Error handling
### Where errors are caught
* `loader.read_csv_rows()` catches `FileNotFoundError`, `PermissionError`, `IsADirectoryError`, `UnicodeDecodeError` and `csv.Error` when a file is opened and read. It prints which file and why, skips that file and goes on with the next one. An empty file or a wrong header is also skipped (plain `if`, not an exception).
* `loader.convert_numbers()` catches `ValueError` from `int()` and `float()` and turns it into an InvalidRecordError that names the field.
* `loader.find_participant()` catches `KeyError` for an unknown participant ID and raises an InvalidRecordError instead.
* `loader.load_participants()` and `loader.load_sessions()` catch InvalidIdentifierError and InvalidRecordError for each row, save the rejected row and go on with the next row.
* `main.py` catches `PermissionError` and `OSError` when the report files are written, prints a message and exits with code 1. It also exits with code 1 and a message if no participants could be loaded, because there is nothing to analyse then.
* There are no empty `except` blocks and no `except Exception`, so programming errors are not hidden.

### Custom exceptions
* InvalidIdentifierError(ValueError)
  * Raised by `check_identifiers()` when participant_id or session_id does not match the regex.
* InvalidRecordError(ValueError)
  * Raised for wrong row length, missing field, value that is not a number, value out of range, unknown participant, a session ID used by two participants and a participant ID listed twice.
* Both store `field` (the column name, several names, or `row`), which is written to rejected_records.txt.
* Both are raised in loader.py and caught in `load_participants()` and `load_sessions()`.


## Assumptions and classification rules
### Assumptions
* Only usable observations (signal quality 0.5 or above) are used in the summaries, the comparison and the classification.
* The session averages are compared with the participant's baseline values. Deviation = session average − baseline. The deviation is reported, but not used for the classification.
* Both session files are always loaded : `--sessions` and `--invalid`, which defaults to `data/fitness_sessions_invalid.csv`. That way the exact command from the PDF loads both. If the same file is given to both options it is only loaded once.
* Temperature must be 25–42 °C, the same range the Assignment 1 data generator keeps temperature inside. A value like 55.0 is a sensor error.
* Timestamp and heart rate are whole numbers in the data, so a decimal value there is rejected.
* "Accepted rows" counts session rows. "Rejected rows" counts rejected rows from all files, participants.csv included.
* New in Assignment 2: a session needs at least 4 usable observations (`MIN_USABLE_OBSERVATIONS`). The recovery check compares the first and second half, so it needs at least two observations per half. With fewer, a session that is really recovering could get a class from its average only.

### Classification rules
The rules are checked in this order.
* Insufficient data
  * Fewer than 4 usable observations, or
  * less than 50% of the observations usable. Exactly 50% is enough.
  * The session gets no class and the explanation says why. With 0 usable observations all averages and deviations are `n/a`. This keeps "not enough usable data" separate from a real result (section 4.5).
* Recovering
  * Average heart rate in the second half is more than 10 bpm lower than in the first half, and
  * average activity in the second half is more than 0.15 lower than in the first half.
* Resting
  * Average activity level is below 0.25
* Moderate activity
  * Average activity level is from 0.25 up to (not including) 0.65
* High activity
  * Average activity level is 0.65 or above

## Example output
Running the command from the PDF prints this completion summary:
```
Analysis complete.
Accepted rows: 30
Rejected rows: 10
Sessions analysed: 6
Report files created:
  output/analysis_summary.csv
  output/analysis_report.txt
  output/rejected_records.txt
```

Results from the official files:

| Session | Participant | Usable | Classification |
|---|---|---|---|
| FIT-2026-001 | P001 Amina Noor | 6 of 6 | resting |
| FIT-2026-002 | P002 Jonas Berg | 6 of 6 | moderate activity |
| FIT-2026-003 | P003 Maya Chen | 6 of 6 | high activity |
| FIT-2026-004 | P001 Amina Noor | 6 of 6 | recovering |
| FIT-2026-005 | P002 Jonas Berg | 0 of 5 | insufficient data |
| FIT-2026-101 | P001 Amina Noor | 1 of 1 | insufficient data |

FIT-2026-101 is the only session in fitness_sessions_invalid.csv. Lines 3–12 are rejected, so only line 2 is left, and 1 usable observation is too few.

One block from `output/analysis_report.txt`:
```
Session: FIT-2026-004
Participant: P001 (Amina Noor)
Observations: 6 of 6 usable

Heart rate summary: average 113.17, minimum 72.00, maximum 151.00
Temperature summary: average 33.28, minimum 32.60, maximum 33.90
Skin response summary: average 2.58, minimum 1.35, maximum 3.90
Activity level summary: average 0.55, minimum 0.18, maximum 0.92

Comparison to reference:
Heart rate deviation: 45.17
Temperature deviation: 0.88
Skin response deviation: 1.38

Session classification: recovering
Explanation: 6 of 6 observations were usable. In the second half of the session heart rate was more than 10 bpm lower and activity more than 0.15 lower than in the first half, indicating recovery.
```

The first lines of `output/rejected_records.txt`:
```
Rejected records: 10
file: fitness_sessions_invalid.csv | row: 3 | field: heart_rate | reason: heart_rate 'fast' is not a whole number
file: fitness_sessions_invalid.csv | row: 4 | field: participant_id | reason: participant_id '001' is not P followed by three digits (like P001)
file: fitness_sessions_invalid.csv | row: 5 | field: activity_level | reason: activity_level is missing
```

## Known limitation
### Fixed from Assignment 1
* The crash on sessions with no usable observations is fixed. They are now insufficient data with `n/a` values (FIT-2026-005).
* The program analyses every session in the files, not only one participant and one scenario at a time.
* The data is read from the CSV files instead of the data generator.

# Installation and running instructions
Needs Python 3 and only the standard library, so there is nothing to install.

Go into the project folder (the folder with `main.py`), for example:

```bash
cd assignment2
```

Run the program with the command from the PDF:

```bash
python3 main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv --output output
```

All options have defaults, so `python3 main.py` does the same:
* `--profiles` – participants file (default `data/participants.csv`)
* `--sessions` – sessions file (default `data/fitness_sessions.csv`)
* `--invalid` – sessions file with invalid rows (default `data/fitness_sessions_invalid.csv`)
* `--output` – folder for the report files, created if it does not exist (default `output`)

The report files are overwritten on every run, so running the program again gives the same files.

Run the tests:

```bash
python3 tests.py
```
