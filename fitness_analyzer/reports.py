
import csv
from pathlib import Path

SUMMARY_FILE = "analysis_summary.csv"
REPORT_FILE = "analysis_report.txt"
REJECTED_FILE = "rejected_records.txt"

SUMMARY_COLUMNS = [
    "session_id",
    "participant_id",
    "participant_name",
    "total_observations",
    "usable_observations",
    "average_heart_rate",
    "average_temperature",
    "average_skin_response",
    "average_activity_level",
    "heart_rate_deviation",
    "temperature_deviation",
    "skin_response_deviation",
    "classification",
]

SEPARATOR = "-" * 60


#Function to write all three report files into the output folder
# Input is output folder path, list of session report dictionaries and list of rejected row dictionaries,
# return list of paths to the files that were created.
def write_reports(output_dir, reports, rejected):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / SUMMARY_FILE
    report_path = output_dir / REPORT_FILE
    rejected_path = output_dir / REJECTED_FILE

    write_summary_csv(summary_path, reports)
    write_analysis_report(report_path, reports)
    write_rejected_records(rejected_path, rejected)

    return [summary_path, report_path, rejected_path]


#Function to write analysis_summary.csv with one row per session
# Input is file path and list of session report dictionaries, return nothing.
def write_summary_csv(path, reports):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()

        for report in reports:
            writer.writerow(make_summary_row(report))


#Function to turn one session report into a row for analysis_summary.csv
# Input is session report dictionary, return dictionary with one value per summary column.
def make_summary_row(report):
    comparison = report["comparison_to_reference"]

    return {
        "session_id": report["session_id"],
        "participant_id": report["participant_id"],
        "participant_name": report["participant_name"],
        "total_observations": report["total_observations"],
        "usable_observations": report["usable_observations"],
        "average_heart_rate": format_number(report["heart_rate_summary"]["average"]),
        "average_temperature": format_number(report["temperature_summary"]["average"]),
        "average_skin_response": format_number(report["skin_response_summary"]["average"]),
        "average_activity_level": format_number(report["activity_summary"]["average"]),
        "heart_rate_deviation": format_number(comparison["heart_rate_deviation"]),
        "temperature_deviation": format_number(comparison["temperature_deviation"]),
        "skin_response_deviation": format_number(comparison["skin_response_deviation"]),
        "classification": report["classification"],
    }


#Function to write analysis_report.txt with a readable block for every session
# Input is file path and list of session report dictionaries, return nothing.
def write_analysis_report(path, reports):
    lines = [
        "Smart Fitness Session Analyzer - analysis report",
        f"Sessions analysed: {len(reports)}",
    ]

    for report in reports:
        lines.append(SEPARATOR)
        lines.extend(make_report_block(report))

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


#Function to build the text lines for one session, in the same layout as print_report() in Assignment 1
# Input is session report dictionary, return list of text lines.
def make_report_block(report):
    lines = [
        f"Session: {report['session_id']}",
        f"Participant: {report['participant_id']} ({report['participant_name']})",
        f"Observations: {report['usable_observations']} of {report['total_observations']} usable",
        "",
    ]

    for label, summary in [
        ("Heart rate", report["heart_rate_summary"]),
        ("Temperature", report["temperature_summary"]),
        ("Skin response", report["skin_response_summary"]),
        ("Activity level", report["activity_summary"]),
    ]:
        lines.append(
            f"{label} summary: average {format_number(summary['average'])}, "
            f"minimum {format_number(summary['minimum'])}, "
            f"maximum {format_number(summary['maximum'])}"
        )

    comparison = report["comparison_to_reference"]
    lines.extend([
        "",
        "Comparison to reference:",
        f"Heart rate deviation: {format_number(comparison['heart_rate_deviation'])}",
        f"Temperature deviation: {format_number(comparison['temperature_deviation'])}",
        f"Skin response deviation: {format_number(comparison['skin_response_deviation'])}",
        "",
        f"Session classification: {report['classification']}",
        f"Explanation: {report['explanation']}",
    ])

    return lines


#Function to write rejected_records.txt with one line per rejected row
# Input is file path and list of rejected row dictionaries (file, row, field, reason), return nothing.
def write_rejected_records(path, rejected):
    lines = [f"Rejected records: {len(rejected)}"]

    # " | " separates the parts, because one row can have several bad fields separated by commas.
    for record in rejected:
        lines.append(
            f"file: {record['file']} | row: {record['row']} | "
            f"field: {record['field']} | reason: {record['reason']}"
        )

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


#Function to round a number for the output files
# Input is number or None, return text with two decimals, or "n/a" when there is no value.
def format_number(value):
    if value is None:
        return "n/a"

    # Adding 0.0 turns -0.0 into 0.0, so a tiny negative value is not written as "-0.00".
    return f"{round(value, 2) + 0.0:.2f}"
