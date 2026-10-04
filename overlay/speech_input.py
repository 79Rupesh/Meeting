"""Authorized continuous microphone input provider for the desktop companion."""

import threading
from abc import ABC, abstractmethod

import speech_recognition as sr


class MeetingInputProvider(ABC):

    @abstractmethod
    def start(self):
        """Start authorized input without blocking the UI."""

    @abstractmethod
    def stop(self):
        """Stop authorized input."""


class MicrophoneSpeechProvider(MeetingInputProvider):

    def __init__(self, on_text, on_status):

        self.on_text = on_text
        self.on_status = on_status

        # ==========================================
        # SPEECH RECOGNIZER
        # ==========================================

        self.recognizer = sr.Recognizer()

        self.recognizer.pause_threshold = 1.5
        self.recognizer.non_speaking_duration = 0.8
        self.recognizer.dynamic_energy_threshold = True

        # ==========================================
        # MICROPHONE DEVICE
        # ==========================================

        # Same microphone that worked in direct test.
        self.device_index = 1

        # ==========================================
        # THREAD CONTROL
        # ==========================================

        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # ==========================================
        # CALIBRATION
        # ==========================================

        self._calibrated = False

    # ==================================================
    # START
    # ==================================================

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

    # ==================================================
    # STOP
    # ==================================================

    def stop(self):

        if not self._stop_event.is_set():

            self._stop_event.set()

            return {
                "stopped": True,
                "message": "Stopping microphone..."
            }

        return {
            "stopped": True,
            "message": "Microphone already stopped."
        }

    # ==================================================
    # CONTINUOUS LISTENING
    # ==================================================

    def _listen_continuously(self):

        try:

            self.on_status(
                "listening",
                "Listening continuously… speak normally."
            )

            print()
            print("🎤 Microphone started")
            print(
                f"🎤 Microphone device: "
                f"{self.device_index}"
            )

            # ==========================================
            # OPEN SPECIFIC MICROPHONE
            # ==========================================

            with sr.Microphone(
                device_index=self.device_index
            ) as source:

                # ======================================
                # AMBIENT NOISE CALIBRATION
                # ======================================

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

                # ======================================
                # CONTINUOUS LOOP
                # ======================================

                while not self._stop_event.is_set():

                    try:

                        print(
                            "Listening for speech..."
                        )

                        # ==================================
                        # LISTEN
                        # ==================================

                        audio = self.recognizer.listen(
                            source,
                            timeout=3,
                            phrase_time_limit=20
                        )

                        if self._stop_event.is_set():
                            break

                        # ==================================
                        # PROCESSING
                        # ==================================

                        self.on_status(
                            "processing",
                            "Converting speech to text…"
                        )

                        print(
                            "Processing speech..."
                        )

                        # ==================================
                        # GOOGLE SPEECH RECOGNITION
                        # ==================================

                        text = self.recognizer.recognize_google(
                            audio,
                            language="en-IN"
                        ).strip()

                        # ==================================
                        # RESULT
                        # ==================================

                        if text:

                            print()
                            print(
                                "🎤 Recognized:"
                            )
                            print(text)

                            self.on_text(text)

                        self.on_status(
                            "listening",
                            "Listening continuously…"
                        )

                    # ======================================
                    # NO SPEECH
                    # ======================================

                    except sr.WaitTimeoutError:

                        continue

                    # ======================================
                    # SPEECH NOT UNDERSTOOD
                    # ======================================

                    except sr.UnknownValueError:

                        print(
                            "❓ Could not understand "
                            "this speech chunk."
                        )

                        self.on_status(
                            "listening",
                            "Listening…"
                        )

                        continue

                    # ======================================
                    # GOOGLE SERVICE ERROR
                    # ======================================

                    except sr.RequestError as error:

                        print(
                            "❌ Speech recognition "
                            f"service error: {error}"
                        )

                        self.on_status(
                            "idle",
                            "Speech service is temporarily unavailable."
                        )

                        break

                    # ======================================
                    # OTHER ERROR
                    # ======================================

                    except Exception as error:

                        print(
                            "❌ Speech processing error:",
                            error
                        )

                        self.on_status(
                            "listening",
                            "Listening…"
                        )

                        continue

        # ==================================================
        # MICROPHONE ERROR
        # ==================================================

        except Exception as error:

            print()
            print(
                "❌ Microphone error:",
                error
            )

            self.on_status(
                "idle",
                "Microphone is unavailable. "
                "Check its permissions."
            )

        # ==================================================
        # CLEANUP
        # ==================================================

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