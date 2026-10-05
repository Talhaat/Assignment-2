
#Class for reference profile containing hearthrate, skin response and temperature
class ReferenceProfile:
    def __init__(
        self,
        baseline_heart_rate,
        baseline_skin_response,
        baseline_temperature
    ):
        self.baseline_heart_rate = baseline_heart_rate
        self.baseline_skin_response = baseline_skin_response
        self.baseline_temperature = baseline_temperature


#Class for participant containing participant id, name and reference profile
class Participant:
    def __init__(self, participant_id, name, reference_profile):
        self.participant_id = participant_id
        self.name = name
        self.reference_profile = reference_profile


#Class for observation containing timestamp, heart rate, skin response, temperature, activity level and signal quality
class Observation:
    def __init__(
        self,
        timestamp,
        heart_rate,
        skin_response,
        temperature,
        activity_level,
        signal_quality
    ):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality
        self._is_valid = None

    #Protected attribute, only readable through this property.
    #Set through mark_validity() instead of being assigned directly.
    @property
    def is_valid(self):
        return self._is_valid

    def mark_validity(self, value):
        self._is_valid = value

    #Classmethod constructor: builds an Observation straight from a dict with the six
    #measurement keys, like a converted CSV row from the loader. Other keys are ignored.
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["timestamp"],
            data["heart_rate"],
            data["skin_response"],
            data["temperature"],
            data["activity_level"],
            data["signal_quality"]
        )


#Class for fitness session containing session id, participant and list of observations
class FitnessSession:
    def __init__(self, session_id, participant):
        self.session_id = session_id
        self.participant = participant
        self.observations = []

    def add_observation(self, observation):
        self.observations.append(observation)

    def valid_observations(self):
        return [obs for obs in self.observations if obs.is_valid]
