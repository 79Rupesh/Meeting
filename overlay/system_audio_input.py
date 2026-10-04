import threading
import time

import numpy as np
import sounddevice as sd
import speech_recognition as sr


class SystemAudioSpeechProvider:

    def __init__(self, on_text, on_status):

        self.on_text = on_text
        self.on_status = on_status

        # ==========================================
        # STEREO MIX DEVICE
        # ==========================================

        self.device = 17

        # ==========================================
        # AUDIO SETTINGS
        # ==========================================

        self.sample_rate = 48000
        self.channels = 2

        # Small blocks = better real-time response
        self.block_seconds = 0.25

        # ==========================================
        # SPEECH DETECTION
        # ==========================================

        self.speech_threshold = -42

        # Speaker must remain silent for this time
        # before the speech segment is completed.
        self.silence_seconds = 1.5

        # Maximum size of one transcript block.
        self.max_utterance_seconds = 30

        # Ignore extremely short sounds.
        self.min_utterance_seconds = 0.7

        # ==========================================
        # SPEECH RECOGNITION
        # ==========================================

        self.recognizer = sr.Recognizer()

        # ==========================================
        # THREAD CONTROL
        # ==========================================

        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.stream = None

        # ==========================================
        # CURRENT AUDIO SEGMENT
        # ==========================================

        self.audio_buffer = []

        self.speech_active = False
        self.silence_time = 0
        self.speech_duration = 0

        self.segment_number = 0

    # ==================================================
    # START
    # ==================================================

    def start(self):

        if not self._lock.acquire(blocking=False):

            return {
                "started": False,
                "message": "System audio already running."
            }

        self._stop_event.clear()

        self.audio_buffer = []
        self.speech_active = False
        self.silence_time = 0
        self.speech_duration = 0
        self.segment_number = 0

        thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="system-audio-input"
        )

        thread.start()

        return {
            "started": True,
            "message": "Meeting audio listening..."
        }

    # ==================================================
    # STOP
    # ==================================================

    def stop(self):

        self._stop_event.set()

        try:

            if self.stream:

                self.stream.stop()
                self.stream.close()

                self.stream = None

        except Exception as error:

            print("Stream stop error:", error)

        return {
            "stopped": True,
            "message": "System audio stopping..."
        }

    # ==================================================
    # AUDIO CALLBACK
    # ==================================================

    def _audio_callback(
        self,
        indata,
        frames,
        time_info,
        status
    ):

        if self._stop_event.is_set():
            return

        try:

            if status:
                print("Audio status:", status)

            # ==========================================
            # STEREO -> MONO
            # ==========================================

            audio = np.mean(
                indata,
                axis=1
            )

            # ==========================================
            # RMS VOLUME
            # ==========================================

            volume = np.sqrt(
                np.mean(
                    np.square(audio)
                )
            )

            if volume > 0:

                db = 20 * np.log10(volume)

            else:

                db = -100

            # ==========================================
            # BLOCK DURATION
            # ==========================================

            block_duration = (
                frames /
                self.sample_rate
            )

            # ==========================================
            # SPEECH DETECTED
            # ==========================================

            if db > self.speech_threshold:

                # Add audio to current segment
                self.audio_buffer.extend(
                    audio.tolist()
                )

                self.speech_active = True

                # Speech is active again
                self.silence_time = 0

                self.speech_duration += (
                    block_duration
                )

                # ======================================
                # MAXIMUM SEGMENT
                # ======================================

                if (
                    self.speech_duration
                    >= self.max_utterance_seconds
                ):

                    print(
                        "⏱️ Maximum speech segment reached"
                    )

                    self._finish_utterance()

            # ==========================================
            # SILENCE DETECTED
            # ==========================================

            else:

                if self.speech_active:

                    # Keep small amount of silence
                    # at the end of the segment.
                    self.audio_buffer.extend(
                        audio.tolist()
                    )

                    self.silence_time += (
                        block_duration
                    )

                    # ==================================
                    # NATURAL PAUSE
                    # ==================================

                    if (
                        self.silence_time
                        >= self.silence_seconds
                    ):

                        print(
                            "⏸️ Natural speech pause detected"
                        )

                        self._finish_utterance()

        except Exception as error:

            print(
                "Audio callback error:",
                error
            )

    # ==================================================
    # FINISH CURRENT SPEECH
    # ==================================================

    def _finish_utterance(self):

        if not self.audio_buffer:

            self._reset_segment()

            return

        # ==========================================
        # CREATE NUMPY AUDIO ARRAY
        # ==========================================

        audio_data = np.array(
            self.audio_buffer,
            dtype=np.float32
        )

        duration = (
            len(audio_data) /
            self.sample_rate
        )

        print()
        print(
            f"🎙️ Speech segment: "
            f"{duration:.1f} seconds"
        )

        # ==========================================
        # RESET BUFFER IMMEDIATELY
        # ==========================================

        self._reset_segment()

        # ==========================================
        # IGNORE VERY SHORT AUDIO
        # ==========================================

        if duration < self.min_utterance_seconds:

            print(
                "🔇 Segment too short - ignored"
            )

            return

        # ==========================================
        # CONVERT IN SEPARATE THREAD
        # ==========================================

        thread = threading.Thread(
            target=self._convert_to_text,
            args=(audio_data,),
            daemon=True,
            name="speech-to-text"
        )

        thread.start()

    # ==================================================
    # RESET SEGMENT
    # ==================================================

    def _reset_segment(self):

        self.audio_buffer = []

        self.speech_active = False

        self.silence_time = 0

        self.speech_duration = 0

    # ==================================================
    # SPEECH -> TEXT
    # ==================================================

    def _convert_to_text(
        self,
        audio_data
    ):

        try:

            self.on_status(
                "processing",
                "Converting meeting speech..."
            )

            # ==========================================
            # NORMALIZE AUDIO
            # ==========================================

            audio_data = np.clip(
                audio_data,
                -1,
                1
            )

            # ==========================================
            # FLOAT32 -> INT16
            # ==========================================

            audio_int16 = (
                audio_data * 32767
            ).astype(
                np.int16
            )

            # ==========================================
            # SPEECH RECOGNITION AUDIO
            # ==========================================

            audio = sr.AudioData(
                audio_int16.tobytes(),
                self.sample_rate,
                2
            )

            print(
                "🧠 Converting speech to text..."
            )

            # ==========================================
            # GOOGLE SPEECH RECOGNITION
            # ==========================================

            text = self.recognizer.recognize_google(
                audio,
                language="en-IN"
            ).strip()

            if not text:

                return

            # ==========================================
            # SEGMENT NUMBER
            # ==========================================

            self.segment_number += 1

            print()
            print("=" * 60)
            print(
                f"📝 Meeting Segment "
                f"{self.segment_number}"
            )
            print(text)
            print("=" * 60)

            # ==========================================
            # SEND TO UI
            #
            # Speaker identification intentionally
            # disabled for now.
            # ==========================================

            self.on_text(
                "Meeting Speaker",
                text
            )

        except sr.UnknownValueError:

            print(
                "❓ Could not understand speech segment."
            )

        except sr.RequestError as error:

            print(
                "Speech recognition error:",
                error
            )

            self.on_status(
                "idle",
                "Speech service unavailable."
            )

        except Exception as error:

            print(
                "Speech processing error:",
                error
            )

        finally:

            self.on_status(
                "listening",
                "Meeting audio listening..."
            )

    # ==================================================
    # MAIN AUDIO LOOP
    # ==================================================

    def _run(self):

        try:

            self.on_status(
                "listening",
                "Meeting audio listening..."
            )

            print()
            print(
                "🎧 System audio started"
            )

            print(
                "🎧 Device:",
                self.device
            )

            print(
                "🎧 Continuous meeting audio capture started"
            )

            # ==========================================
            # CREATE AUDIO STREAM
            # ==========================================

            self.stream = sd.InputStream(

                samplerate=self.sample_rate,

                channels=self.channels,

                dtype="float32",

                device=self.device,

                blocksize=int(
                    self.sample_rate *
                    self.block_seconds
                ),

                callback=self._audio_callback
            )

            # ==========================================
            # START STREAM
            # ==========================================

            self.stream.start()

            print(
                "✅ System audio stream started"
            )

            # ==========================================
            # KEEP THREAD ALIVE
            # ==========================================

            while not self._stop_event.is_set():

                time.sleep(0.1)

        except Exception as error:

            print(
                "System audio error:",
                error
            )

            self.on_status(
                "idle",
                "System audio unavailable."
            )

        finally:

            # ==========================================
            # CLOSE AUDIO STREAM
            # ==========================================

            try:

                if self.stream:

                    self.stream.stop()

                    self.stream.close()

            except Exception:

                pass

            self.stream = None

            # ==========================================
            # PROCESS REMAINING AUDIO
            # ==========================================

            if self.audio_buffer:

                try:

                    self._finish_utterance()

                except Exception as error:

                    print(
                        "Final audio processing error:",
                        error
                    )

            # ==========================================
            # RELEASE LOCK
            # ==========================================

            self._stop_event.set()

            try:

                self._lock.release()

            except RuntimeError:

                pass

            print(
                "🎧 System audio stopped"
            )

            self.on_status(
                "idle",
                "System audio stopped."
            )