"""Continuous microphone input for AI Meeting Companion."""

import os
import subprocess
import sys
import tempfile
import threading
import wave
from abc import ABC, abstractmethod

import speech_recognition as sr


class MeetingInputProvider(ABC):

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class MicrophoneSpeechProvider(MeetingInputProvider):

    def __init__(self, on_text, on_status):

        self.on_text = on_text
        self.on_status = on_status

        # ---------------------------------------------------------
        # SPEECH RECOGNIZER SETTINGS
        # ---------------------------------------------------------

        self.recognizer = sr.Recognizer()

        # Don't stop too quickly when there is a small pause.
        self.recognizer.pause_threshold = 0.9

        # Keep a little silence around the speech.
        self.recognizer.non_speaking_duration = 0.4

        # Minimum speech before recognition starts.
        self.recognizer.phrase_threshold = 0.3

        # Automatically adjust according to background noise.
        self.recognizer.dynamic_energy_threshold = True

        # Microphone device
        self.device_index = 1

        # Thread control
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Calibrate only once
        self._calibrated = False

    # ---------------------------------------------------------
    # START
    # ---------------------------------------------------------

    def start(self):

        if not self._lock.acquire(blocking=False):

            return {
                "started": False,
                "message": "Already listening."
            }

        self._stop_event.clear()

        thread = threading.Thread(
            target=self._listen_continuously,
            daemon=True,
            name="meeting-speech-input"
        )

        thread.start()

        return {
            "started": True,
            "message": "Listening..."
        }

    # ---------------------------------------------------------
    # STOP
    # ---------------------------------------------------------

    def stop(self):

        self._stop_event.set()

        return {
            "stopped": True,
            "message": "Stopping microphone..."
        }

    # ---------------------------------------------------------
    # FIND SPEECH WORKER
    # ---------------------------------------------------------

    def _get_worker_path(self):

        # Python development mode
        if not getattr(sys, "frozen", False):

            current_dir = os.path.dirname(
                os.path.abspath(__file__)
            )

            return os.path.join(
                current_dir,
                "speech_worker.py"
            )

        # Packaged EXE mode
        base_dir = os.path.dirname(
            sys.executable
        )

        worker_exe = os.path.join(
            base_dir,
            "AI-Meeting-Speech-Worker.exe"
        )

        return worker_exe

    # ---------------------------------------------------------
    # SAVE AUDIO TO WAV
    # ---------------------------------------------------------

    def _save_audio(self, audio):

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        temp_file.close()

        with wave.open(
            temp_file.name,
            "wb"
        ) as wav_file:

            wav_file.setnchannels(1)

            wav_file.setsampwidth(
                audio.sample_width
            )

            wav_file.setframerate(
                audio.sample_rate
            )

            wav_file.writeframes(
                audio.get_raw_data(
                    convert_rate=audio.sample_rate,
                    convert_width=audio.sample_width
                )
            )

        return temp_file.name

    # ---------------------------------------------------------
    # SPEECH WORKER
    # ---------------------------------------------------------

    def _recognize_using_worker(self, audio):

        audio_file = None

        try:

            audio_file = self._save_audio(audio)

            worker = self._get_worker_path()

            print(
                "🧠 Speech worker:",
                worker
            )

            # Python development mode
            if not getattr(sys, "frozen", False):

                command = [
                    sys.executable,
                    worker,
                    audio_file
                ]

            # Packaged EXE mode
            else:

                command = [
                    worker,
                    audio_file
                ]

            result = subprocess.run(

                command,

                capture_output=True,

                text=True,

                timeout=30,

                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                )
            )

            output = result.stdout.strip()

            error_output = result.stderr.strip()

            print("🧠 Worker output:")
            print(output)

            if error_output:

                print(
                    "🧠 Worker error:"
                )

                print(error_output)

            for line in output.splitlines():

                # Successful recognition
                if line.startswith("RESULT:"):

                    text = line[
                        len("RESULT:"):
                    ].strip()

                    return text

                # Speech not understood
                if line == "UNKNOWN_VALUE":

                    return ""

                # Google speech service error
                if line.startswith("REQUEST_ERROR:"):

                    print(
                        "❌ Google Speech service error:",
                        line
                    )

                    return ""

                # Worker error
                if line.startswith("ERROR:"):

                    print(
                        "❌ Speech worker error:",
                        line
                    )

                    return ""

            return ""

        except subprocess.TimeoutExpired:

            print(
                "❌ Speech worker timeout."
            )

            return ""

        except Exception as error:

            print(
                "❌ Speech worker execution error:"
            )

            print(
                type(error).__name__
            )

            print(
                repr(error)
            )

            return ""

        finally:

            if audio_file:

                try:

                    os.remove(audio_file)

                except Exception:

                    pass

    # ---------------------------------------------------------
    # CONTINUOUS LISTENING
    # ---------------------------------------------------------

    def _listen_continuously(self):

        try:

            self.on_status(
                "listening",
                "Listening continuously…"
            )

            print()
            print("🎤 Microphone started")

            print(
                f"🎤 Microphone device: "
                f"{self.device_index}"
            )

            with sr.Microphone(
                device_index=self.device_index
            ) as source:

                # -------------------------------------------------
                # MICROPHONE CALIBRATION
                # -------------------------------------------------

                if not self._calibrated:

                    print(
                        "🎤 Calibrating microphone..."
                    )

                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=1
                    )

                    self._calibrated = True

                    print(
                        "🎤 Microphone calibrated"
                    )

                print(
                    "🎤 Continuous listening started"
                )

                # -------------------------------------------------
                # CONTINUOUS LOOP
                # -------------------------------------------------

                while not self._stop_event.is_set():

                    try:

                        print(
                            "Listening for speech..."
                        )

                        # -------------------------------------------------
                        # CAPTURE COMPLETE SPEECH PHRASE
                        # -------------------------------------------------

                        audio = self.recognizer.listen(
                            source,

                            # Wait up to 3 seconds
                            # for speech to start.
                            timeout=3,

                            # Bound latency while keeping complete phrases.
                            phrase_time_limit=12
                        )

                        if self._stop_event.is_set():
                            break

                        # -------------------------------------------------
                        # DEBUG: SHOW CAPTURED AUDIO LENGTH
                        # -------------------------------------------------

                        duration = (
                            len(audio.frame_data)
                            /
                            (
                                audio.sample_rate
                                *
                                audio.sample_width
                            )
                        )

                        print(
                            "🎙️ Captured audio:",
                            round(duration, 2),
                            "seconds"
                        )

                        # -------------------------------------------------
                        # PROCESSING STATUS
                        # -------------------------------------------------

                        self.on_status(
                            "processing",
                            "Converting speech to text…"
                        )

                        print(
                            "Processing speech..."
                        )

                        # -------------------------------------------------
                        # SEND AUDIO TO WORKER
                        # -------------------------------------------------

                        print(
                            "🔵 Sending audio to "
                            "speech worker..."
                        )

                        text = (
                            self._recognize_using_worker(
                                audio
                            )
                        )

                        print(
                            "🟢 Speech worker completed"
                        )

                        # -------------------------------------------------
                        # RESULT
                        # -------------------------------------------------

                        if text:

                            print(
                                "🎤 Recognized:"
                            )

                            print(text)

                            self.on_text(text)

                        else:

                            print(
                                "❓ Could not understand "
                                "this speech chunk."
                            )

                        self.on_status(
                            "listening",
                            "Listening continuously…"
                        )

                    # -------------------------------------------------
                    # NO SPEECH DETECTED
                    # -------------------------------------------------

                    except sr.WaitTimeoutError:

                        continue

                    # -------------------------------------------------
                    # OTHER MICROPHONE ERROR
                    # -------------------------------------------------

                    except Exception as error:

                        print(
                            "❌ Microphone processing error:"
                        )

                        print(
                            type(error).__name__
                        )

                        print(
                            repr(error)
                        )

                        self.on_status(
                            "listening",
                            "Listening…"
                        )

        # ---------------------------------------------------------
        # MICROPHONE OPEN ERROR
        # ---------------------------------------------------------

        except Exception as error:

            print()

            print(
                "❌ Microphone error:"
            )

            print(
                type(error).__name__
            )

            print(
                repr(error)
            )

            self.on_status(
                "idle",
                "Microphone is unavailable."
            )

        # ---------------------------------------------------------
        # CLEANUP
        # ---------------------------------------------------------

        finally:

            self._stop_event.set()

            try:

                self._lock.release()

            except RuntimeError:

                pass

            print(
                "🎤 Continuous microphone stopped"
            )

            self.on_status(
                "idle",
                "Microphone stopped."
            )
