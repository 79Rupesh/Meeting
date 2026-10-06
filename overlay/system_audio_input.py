import os
import subprocess
import sys
import tempfile
import threading
import time
import wave

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from speech_worker_client import run_speech_worker


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
        self.block_seconds = 0.25

        # ==========================================
        # SPEECH DETECTION
        # ==========================================

        self.speech_threshold = -42
        self.silence_seconds = 0.8
        self.max_utterance_seconds = 15
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

                self.audio_buffer.extend(
                    audio.tolist()
                )

                self.speech_active = True

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
                        "Maximum speech segment reached"
                    )

                    self._finish_utterance()

            # ==========================================
            # SILENCE
            # ==========================================

            else:

                if self.speech_active:

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
                            "Natural speech pause detected"
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

        audio_data = np.array(
            self.audio_buffer,
            dtype=np.float32
        )

        duration = (
            len(audio_data) /
            self.sample_rate
        )

        print(
            f"Speech segment: {duration:.1f} seconds"
        )

        self._reset_segment()

        if duration < self.min_utterance_seconds:

            print(
                "Segment too short - ignored"
            )

            return

        # ==========================================
        # PROCESS OUTSIDE AUDIO CALLBACK
        # ==========================================

        thread = threading.Thread(
            target=self._convert_to_text,
            args=(audio_data,),
            daemon=True,
            name="system-audio-speech-to-text"
        )

        thread.start()

    # ==================================================
    # RESET
    # ==================================================

    def _reset_segment(self):

        self.audio_buffer = []

        self.speech_active = False

        self.silence_time = 0

        self.speech_duration = 0

    # ==================================================
    # FIND SPEECH WORKER
    # ==================================================

    def _get_worker_path(self):

        # Python development mode

        if not getattr(
            sys,
            "frozen",
            False
        ):

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

        return os.path.join(
            base_dir,
            "AI-Meeting-Speech-Worker.exe"
        )

    # ==================================================
    # SAVE AUDIO AS WAV
    # ==================================================

    def _save_audio(
        self,
        audio_data
    ):

        audio_data = np.clip(
            audio_data,
            -1,
            1
        )

        audio_int16 = (
            audio_data * 32767
        ).astype(
            np.int16
        )

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        temp_file.close()

        try:

            with wave.open(
                temp_file.name,
                "wb"
            ) as wav_file:

                wav_file.setnchannels(1)

                wav_file.setsampwidth(2)

                wav_file.setframerate(
                    self.sample_rate
                )

                wav_file.writeframes(
                    audio_int16.tobytes()
                )

            return temp_file.name

        except Exception:

            try:

                os.remove(
                    temp_file.name
                )

            except OSError:

                pass

            raise

    # ==================================================
    # SPEECH -> TEXT
    # ==================================================

    def _convert_to_text(
        self,
        audio_data
    ):

        audio_file = None

        try:

            self.on_status(
                "processing",
                "Converting meeting speech..."
            )

            print(
                "SYSTEM_AUDIO_WAV_CREATED"
            )

        # ==========================================
        # SAVE AUDIO
        # ==========================================

            audio_file = self._save_audio(
                audio_data
            )

            worker = self._get_worker_path()

            print(
                "SYSTEM_AUDIO_WORKER:",
                worker
            )

        # ==========================================
        # CHECK WORKER
        # ==========================================

            if not os.path.exists(worker):

                print(
                    "Speech worker not found:",
                    worker
                )

                return

        # ==========================================
        # RUN SHARED SPEECH WORKER
        # ==========================================

            print(
                "SYSTEM_AUDIO_WORKER_STARTED"
            )

            text = run_speech_worker(
                audio_file,
                worker,
                timeout=60
            )

        # ==========================================
        # NO TEXT
        # ==========================================

            if not text:

                print(
                    "No speech text returned."
                )

                return

        # ==========================================
        # SEGMENT NUMBER
        # ==========================================

            self.segment_number += 1

            print(
                "=" * 60
            )

            print(
                f"Meeting Segment "
                f"{self.segment_number}"
            )

            print(text)

            print(
                "=" * 60
            )

        # ==========================================
        # SEND TO UI
        # ==========================================

            print(
                "SYSTEM_AUDIO_TRANSCRIPT_SENT"
            )

            self.on_text(
                "Meeting Speaker",
                text
            )

        except Exception as error:

            print(
                "System audio speech processing error:",
                type(error).__name__,
                repr(error)
            )

        finally:

        # ==========================================
        # DELETE TEMP WAV
        # ==========================================

            if audio_file:

                try:

                    os.remove(
                        audio_file
                    )

                except OSError:

                    pass

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
                "System audio started"
            )

            print(
                "Device:",
                self.device
            )

            print(
                "Continuous meeting audio capture started"
            )

            print(
                "SYSTEM_AUDIO_CAPTURE_STARTED"
            )

            # ==========================================
            # CREATE STREAM
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
                "System audio stream started"
            )

            # ==========================================
            # KEEP THREAD ALIVE
            # ==========================================

            while not self._stop_event.is_set():

                time.sleep(
                    0.1
                )

        except Exception as error:

            print(
                "System audio error:",
                type(error).__name__,
                repr(error)
            )

            self.on_status(
                "idle",
                "System audio unavailable."
            )

        finally:

            # ==========================================
            # CLOSE STREAM
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

            self._stop_event.set()

            try:

                self._lock.release()

            except RuntimeError:

                pass

            print(
                "System audio stopped"
            )

            self.on_status(
                "idle",
                "System audio stopped."
            )