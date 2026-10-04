import sounddevice as sd
import speech_recognition as sr
import numpy as np
import time


DEVICE = 17
SAMPLE_RATE = 48000
CHUNK_SECONDS = 5


def convert_audio_to_text(audio_data, recognizer):
    try:
        # Stereo → Mono
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Check whether there is useful audio
        volume = np.max(np.abs(audio_data))

        if volume < 0.01:
            return None

        audio_data = np.clip(audio_data, -1, 1)

        audio_data = (
            audio_data * 32767
        ).astype(np.int16)

        audio = sr.AudioData(
            audio_data.tobytes(),
            SAMPLE_RATE,
            2
        )

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        ).strip()

        return text

    except sr.UnknownValueError:
        return None

    except sr.RequestError as error:
        print("Speech service error:", error)
        return None

    except Exception as error:
        print("Speech processing error:", error)
        return None


def main():

    print("===================================")
    print(" LIVE SYSTEM AUDIO TRANSCRIPTION")
    print("===================================")

    recognizer = sr.Recognizer()

    print("Device: Stereo Mix")
    print("Chunk:", CHUNK_SECONDS, "seconds")
    print("\n🎧 Listening to system audio...")
    print("Start your Google Meet audio.")
    print("Press Ctrl+C to stop.\n")

    try:

        while True:

            print("Listening...")

            audio_data = sd.rec(
                int(SAMPLE_RATE * CHUNK_SECONDS),
                samplerate=SAMPLE_RATE,
                channels=2,
                dtype="float32",
                device=DEVICE
            )

            sd.wait()

            print("Processing...")

            text = convert_audio_to_text(
                audio_data,
                recognizer
            )

            if text:

                print("\n📝 SYSTEM AUDIO:")
                print(text)
                print()

    except KeyboardInterrupt:

        print("\n🛑 System audio transcription stopped.")

    except Exception as error:

        print("\n❌ Error:")
        print(error)


if __name__ == "__main__":
    main()