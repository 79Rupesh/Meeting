import json
import sys
import threading
import time
import urllib.request

import uvicorn
import webview

from speech_input import MicrophoneSpeechProvider
from system_audio_input import SystemAudioSpeechProvider


def _start_embedded_backend():
    """Run the FastAPI server inside the packaged desktop application."""
    from backend.main import app as backend_app

    server = uvicorn.Server(
        uvicorn.Config(backend_app, host="127.0.0.1", port=8000, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True, name="meeting-backend").start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=0.5):
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("The embedded meeting backend did not start on port 8000.")


class API:

    def __init__(self):

        self.speech = MicrophoneSpeechProvider(
            self._send_mic_text,
            self._set_status
        )

        self.system_audio = SystemAudioSpeechProvider(
            self._send_system_text,
            self._set_system_status
        )

    # ---------------------------------------------------------
    # SEND DATA TO WEBVIEW
    # ---------------------------------------------------------

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

                error_text = str(error)

                if "disposed" in error_text.lower():

                    print(
                        "⚠️ WebView already closed."
                    )

                    return

                print(
                    f"UI update skipped: {error}"
                )

        except Exception as error:

            print(
                f"WebView update error: {error}"
            )

    # ---------------------------------------------------------
    # MICROPHONE CALLBACK
    # ---------------------------------------------------------

    def _send_mic_text(self, text):

        print(
            "🎤 My Voice:",
            text
        )

        self._call_page(
            "receiveSpeechTranscript",
            text
        )

    # ---------------------------------------------------------
    # MICROPHONE STATUS
    # ---------------------------------------------------------

    def _set_status(
        self,
        state,
        message
    ):

        self._call_page(
            "setSpeechStatus",
            state,
            message
        )

    # ---------------------------------------------------------
    # SYSTEM AUDIO CALLBACK
    # ---------------------------------------------------------

    def _send_system_text(
        self,
        speaker,
        text
    ):

        print(
            f"🎧 {speaker}: {text}"
        )

        self._call_page(
            "receiveSystemAudioTranscript",
            speaker,
            text
        )

    # ---------------------------------------------------------
    # SYSTEM AUDIO STATUS
    # ---------------------------------------------------------

    def _set_system_status(
        self,
        state,
        message
    ):

        self._call_page(
            "setSystemAudioStatus",
            state,
            message
        )

    # ---------------------------------------------------------
    # MICROPHONE START
    # ---------------------------------------------------------

    def start_speaking(self):

        return self.speech.start()

    # ---------------------------------------------------------
    # MICROPHONE STOP
    # ---------------------------------------------------------

    def stop_speaking(self):

        return self.speech.stop()

    # ---------------------------------------------------------
    # SYSTEM AUDIO START
    # ---------------------------------------------------------

    def start_system_audio(self):

        return self.system_audio.start()

    # ---------------------------------------------------------
    # SYSTEM AUDIO STOP
    # ---------------------------------------------------------

    def stop_system_audio(self):

        return self.system_audio.stop()

    # ---------------------------------------------------------
    # CLOSE APPLICATION
    # ---------------------------------------------------------

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

    def stop_capture(self):
        """Window-close hook: stop providers even if JavaScript did not run."""
        self.speech.stop()
        self.system_audio.stop()


def main():

    if getattr(sys, "frozen", False):
        _start_embedded_backend()

    api = API()

    window = webview.create_window(
        title="AI Meeting Companion",
        url=(
            "http://127.0.0.1:8000/"
            "frontend/meeting.html"
        ),
        js_api=api,
        width=470,
        height=620,
        min_size=(450, 580),
        resizable=False,
        on_top=True
    )

    window.events.closing += api.stop_capture

    webview.start(
        debug=not getattr(sys, "frozen", False)
    )


if __name__ == "__main__":

    main()
