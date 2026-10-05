
# Rules for the analysis. All numbers are the same as in Assignment 1, except MIN_USABLE_OBSERVATIONS.
MIN_SIGNAL_QUALITY = 0.5        # observations with lower signal quality are not used (poor-signal rule)
MIN_USABLE_SHARE = 0.5          # at least half of the observations in a session must be usable
RESTING_LIMIT = 0.25            # average activity below this is resting
MODERATE_LIMIT = 0.65           # average activity below this is moderate activity, from here it is high activity
RECOVERY_HEART_RATE_DROP = 10   # second half heart rate must be more than this many bpm lower than the first half
RECOVERY_ACTIVITY_DROP = 0.15   # second half activity must be more than this much lower than the first half
 
MIN_USABLE_OBSERVATIONS = 4


#Function that gathers the whole analysis into one structured dictionary
# Input is session object (its participant has the reference profile), return dictionary containing analysis results.
def build_session_report(session):
    participant = session.participant
    reference = participant.reference_profile
    valid_observations = session.valid_observations()

    heart_rate_summary = calculate_summary([o.heart_rate for o in valid_observations])
    temperature_summary = calculate_summary([o.temperature for o in valid_observations])
    skin_response_summary = calculate_summary([o.skin_response for o in valid_observations])
    activity_summary = calculate_summary([o.activity_level for o in valid_observations])

    comparison = compare_to_reference(
        heart_rate_summary,
        temperature_summary,
        skin_response_summary,
        reference
    )

    classification = classify_session(
        len(valid_observations),
        len(session.observations),
        activity_summary,
        valid_observations
    )

    explanation = explain_classification(
        classification,
        activity_summary,
        len(valid_observations),
        len(session.observations)
    )

    return {
        "session_id": session.session_id,
        "participant_id": participant.participant_id,
        "participant_name": participant.name,
        "total_observations": len(session.observations),
        "usable_observations": len(valid_observations),
        "heart_rate_summary": heart_rate_summary,
        "temperature_summary": temperature_summary,
        "skin_response_summary": skin_response_summary,
        "activity_summary": activity_summary,
        "comparison_to_reference": comparison,
        "classification": classification,
        "explanation": explanation,
    }


#Function to check if an observation can be used in the analysis (poor-signal rule)
# Input is observation object, return boolean value, true or false.
def is_valid(observation):
    return observation.signal_quality >= MIN_SIGNAL_QUALITY


#Function to compare session averages against participant reference values
# Input is three summary dictionaries and a reference profile object, return dictionary containing deviation values.
def compare_to_reference(heart_rate_summary, temperature_summary, skin_response_summary, reference):
    return {
        "heart_rate_deviation": calculate_deviation(heart_rate_summary["average"], reference.baseline_heart_rate),
        "temperature_deviation": calculate_deviation(temperature_summary["average"], reference.baseline_temperature),
        "skin_response_deviation": calculate_deviation(skin_response_summary["average"], reference.baseline_skin_response),
    }


#Function to calculate how far an average is from a reference value
# Input is average (None when there were no usable values) and reference value, return the difference, or None if there is no average.
def calculate_deviation(average, reference_value):
    if average is None:
        return None

    return average - reference_value


#Function to check if heart rate and activity are declining near the end
# Input is list of observation objects, return boolean value, true or false.
def is_recovering(observations):
    # With fewer than 2 observations the first half is empty and the averages would divide by zero.
    if len(observations) < 2:
        return False

    midpoint = len(observations) // 2
    first_half = observations[:midpoint]
    second_half = observations[midpoint:]

    first_heart_rate = sum(o.heart_rate for o in first_half) / len(first_half)
    second_heart_rate = sum(o.heart_rate for o in second_half) / len(second_half)

    first_activity = sum(o.activity_level for o in first_half) / len(first_half)
    second_activity = sum(o.activity_level for o in second_half) / len(second_half)

    return (
        second_heart_rate < first_heart_rate - RECOVERY_HEART_RATE_DROP
        and second_activity < first_activity - RECOVERY_ACTIVITY_DROP
    )


#Function to list why a session does not have enough usable observations to be classified
# Input is usable count and total count, return list of reason strings, empty when there is enough data.
def insufficient_data_reasons(usable_count, total_count):
    reasons = []

    if usable_count < MIN_USABLE_OBSERVATIONS:
        reasons.append(f"fewer than {MIN_USABLE_OBSERVATIONS} usable observations")

    # total_count is checked first so an empty session does not divide by zero.
    if total_count > 0 and usable_count / total_count < MIN_USABLE_SHARE:
        reasons.append(f"less than {MIN_USABLE_SHARE:.0%} of its observations usable")

    return reasons


#Function to classify the session
# Input is usable count, total count, activity summary dictionary and list of valid observations, return classification string.
def classify_session(usable_count, total_count, activity_summary, valid_observations):
    if insufficient_data_reasons(usable_count, total_count):
        return "insufficient data"

    # From here there are at least MIN_USABLE_OBSERVATIONS (4) usable observations,
    # so the recovery check has two per half and the activity average is not None.
    if is_recovering(valid_observations):
        return "recovering"

    average_activity = activity_summary["average"]

    if average_activity < RESTING_LIMIT:
        return "resting"
    elif average_activity < MODERATE_LIMIT:
        return "moderate activity"
    else:
        return "high activity"


#Function to explain how many observations were usable and why the session got its classification
# Input is classification string, activity summary dictionary, usable count and total count, return explanation string.
def explain_classification(classification, activity_summary, usable_count, total_count):
    usable_text = f"{usable_count} of {total_count} observations were usable"

    unusable_count = total_count - usable_count
    if unusable_count > 0:
        usable_text += f" ({unusable_count} had signal quality below {MIN_SIGNAL_QUALITY})"

    if classification == "insufficient data":
        reasons = " and ".join(insufficient_data_reasons(usable_count, total_count))

        if usable_count == 0:
            result_text = "There are no averages to compare with the reference values."
        else:
            result_text = "Averages from so few observations are not a reliable result."

        return f"Insufficient data: {usable_text}. The session has {reasons}, so it was not classified. {result_text}"

    if classification == "recovering":
        return (
            f"{usable_text}. In the second half of the session heart rate was more than "
            f"{RECOVERY_HEART_RATE_DROP} bpm lower and activity more than {RECOVERY_ACTIVITY_DROP} lower "
            f"than in the first half, indicating recovery."
        )

    if classification == "resting":
        rule = f"below {RESTING_LIMIT}"
    elif classification == "moderate activity":
        rule = f"from {RESTING_LIMIT} up to {MODERATE_LIMIT}"
    else:
        rule = f"{MODERATE_LIMIT} or higher"

    return f"{usable_text}. Average activity level was {activity_summary['average']:.2f}, {rule}, so the session is {classification}."


#Function to calculate average, minimum and maximum values
# Input is list of numbers, return dictionary containing average, minimum and maximum (all None for an empty list).
def calculate_summary(values):

    if len(values) == 0:
        return {
            "average": None,
            "minimum": None,
            "maximum": None
        }

    return {
        "average": sum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values)
    }
