import json
import webview

from speech_input import MicrophoneSpeechProvider
from system_audio_input import SystemAudioSpeechProvider


class API:

    def __init__(self):

        # Microphone input
        self.speech = MicrophoneSpeechProvider(
            self._send_mic_text,
            self._set_status
        )

        # Google Meet / system audio input
        self.system_audio = SystemAudioSpeechProvider(
            self._send_system_text,
            self._set_system_status
        )

    def _call_page(self, function, *args):

        try:

            if not webview.windows:
                return

            window = webview.windows[0]

            if window is None:
                return

            values = ", ".join(
                json.dumps(arg)
                for arg in args
            )

            try:

                window.evaluate_js(
                    f"window.{function}({values})"
                )

            except Exception as error:

                print(
                    f"UI update skipped: {error}"
                )

        except Exception as error:

            print(
                f"WebView update error: {error}"
            )

    # -----------------------------
    # MICROPHONE
    # -----------------------------

    def _send_mic_text(self, text):

        print("🎤 My Voice:", text)

        self._call_page(
            "receiveSpeechTranscript",
            text
        )

    def _set_status(self, state, message):

        self._call_page(
            "setSpeechStatus",
            state,
            message
        )

    # -----------------------------
    # SYSTEM AUDIO
    # -----------------------------

    def _send_system_text(self, speaker, text):
        print(f"🎧 {speaker}: {text}")

        self._call_page(
            "receiveSystemAudioTranscript",
            speaker,
            text
        )
        
    def _set_system_status(self, state, message):

        self._call_page(
            "setSystemAudioStatus",
            state,
            message
        )

    # -----------------------------
    # MICROPHONE CONTROLS
    # -----------------------------

    def start_speaking(self):

        return self.speech.start()

    def stop_speaking(self):

        return self.speech.stop()

    # -----------------------------
    # SYSTEM AUDIO CONTROLS
    # -----------------------------

    def start_system_audio(self):

        return self.system_audio.start()

    def stop_system_audio(self):

        return self.system_audio.stop()

    # -----------------------------
    # CLOSE
    # -----------------------------

    def close_app(self):

        try:

            self.speech.stop()
            self.system_audio.stop()

            if webview.windows:
                webview.windows[0].destroy()

            return "Application closed"

        except Exception as error:

            print(
                f"Close error: {error}"
            )

            return "Application closed"


api = API()


window = webview.create_window(
    title="AI Meeting Companion",
    url="http://127.0.0.1:8000/frontend/meeting.html",
    js_api=api,
    width=470,
    height=620,
    min_size=(450, 580),
    resizable=False,
    on_top=True,
)


webview.start(debug=True)