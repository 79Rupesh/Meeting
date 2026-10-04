import soundcard as sc
import numpy as np
import speech_recognition as sr


def system_audio_to_text():

    print("Starting system audio speech test...")

    speakers = sc.all_speakers()

    if not speakers:
        print("❌ No speaker found.")
        return

    speaker = speakers[0]

    print("Speaker:", speaker.name)

    loopback = sc.get_microphone(
        id=speaker.name,
        include_loopback=True
    )

    print("Loopback:", loopback.name)

    sample_rate = 48000

    print("\n🎧 System audio listening started...")
    print("Play an English YouTube video now.")
    print("Recording for 10 seconds...\n")

    try:

        with loopback.recorder(
            samplerate=sample_rate,
            channels=2
        ) as recorder:

            print("🔴 Recording started...")

            audio_data = recorder.record(
                numframes=sample_rate * 10
            )

            print("🟢 Recording finished.")

    except Exception as error:

        print("\n❌ Recording error:")
        print(error)
        return

    if audio_data is None:

        print("❌ No audio captured.")
        return

    print("Audio captured successfully.")

    # Stereo → Mono
    if len(audio_data.shape) > 1:
        audio_data = np.mean(
            audio_data,
            axis=1
        )

    # Normalize
    audio_data = np.clip(
        audio_data,
        -1,
        1
    )

    # Convert to 16-bit PCM
    audio_data = (
        audio_data * 32767
    ).astype(np.int16)

    print("Samples:", len(audio_data))

    # Speech Recognition
    recognizer = sr.Recognizer()

    raw_audio = audio_data.tobytes()

    audio = sr.AudioData(
        raw_audio,
        sample_rate,
        2
    )

    print("\n🧠 Converting audio to text...")

    try:

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        print("\n==============================")
        print("SYSTEM AUDIO TEXT")
        print("==============================")
        print(text)
        print("==============================")

    except sr.UnknownValueError:

        print("\n❌ Speech could not be understood.")

    except sr.RequestError as error:

        print("\n❌ Google Speech Recognition error:")
        print(error)


if __name__ == "__main__":
    system_audio_to_text()