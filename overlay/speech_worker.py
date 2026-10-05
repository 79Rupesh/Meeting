import sys
import speech_recognition as sr


def recognize_audio(audio_file):
    recognizer = sr.Recognizer()

    try:
        print("WORKER_STARTED", flush=True)

        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)

        print("WORKER_RECOGNIZING", flush=True)

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        ).strip()

        if text:
            print("RESULT:" + text, flush=True)
        else:
            print("RESULT:", flush=True)

    except sr.UnknownValueError:
        print("UNKNOWN_VALUE", flush=True)

    except sr.RequestError as error:
        print(
            "REQUEST_ERROR:" + str(error),
            flush=True
        )

    except Exception as error:
        print(
            "ERROR:"
            + type(error).__name__
            + ":"
            + repr(error),
            flush=True
        )


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERROR:No audio file", flush=True)
        sys.exit(1)

    audio_file = sys.argv[1]

    recognize_audio(audio_file)
    