import numpy as np


class SpeakerIdentifier:

    def __init__(self):
        self.speakers = {}

    def identify(self, audio_data, sample_rate):
        """
        Identify the speaker from an audio segment.

        Returns:
            Speaker 1, Speaker 2, etc.
        """

        if audio_data is None:
            return "Unknown Speaker"

        if len(audio_data) == 0:
            return "Unknown Speaker"

        # Convert to numpy array
        audio = np.asarray(
            audio_data,
            dtype=np.float32
        )

        # Remove DC offset
        audio = audio - np.mean(audio)

        # Normalize
        maximum = np.max(
            np.abs(audio)
        )

        if maximum > 0:
            audio = audio / maximum

        # -----------------------------------------
        # Basic voice features
        # -----------------------------------------

        energy = np.mean(
            audio ** 2
        )

        zero_crossing_rate = np.mean(
            np.abs(
                np.diff(
                    np.sign(audio)
                )
            ) > 0
        )

        feature = np.array([
            energy,
            zero_crossing_rate
        ])

        # -----------------------------------------
        # Compare with existing speakers
        # -----------------------------------------

        for speaker_name, profile in self.speakers.items():

            distance = np.linalg.norm(
                feature - profile
            )

            if distance < 0.05:
                return speaker_name

        # -----------------------------------------
        # New speaker
        # -----------------------------------------

        speaker_number = len(
            self.speakers
        ) + 1

        speaker_name = (
            f"Speaker {speaker_number}"
        )

        self.speakers[speaker_name] = feature

        print(
            f"🆕 New speaker detected: "
            f"{speaker_name}"
        )

        return speaker_name