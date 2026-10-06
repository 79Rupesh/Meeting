import os
import subprocess
import sys
import threading


# Microphone aur system audio ke workers
# ek saath run nahi honge.
_worker_lock = threading.Lock()


def run_speech_worker(
    audio_file,
    worker_path,
    timeout=60
):

    acquired = _worker_lock.acquire(
        timeout=timeout
    )

    if not acquired:

        print(
            "❌ Speech worker is busy."
        )

        return ""

    try:

        print(
            "🔒 Speech worker lock acquired"
        )

        print(
            "🧠 Worker:",
            worker_path
        )

        # ==========================================
        # CHECK WORKER
        # ==========================================

        if not os.path.exists(worker_path):

            print(
                "❌ Speech worker not found:",
                worker_path
            )

            return ""

        # ==========================================
        # PYTHON MODE
        # ==========================================

        if not getattr(
            sys,
            "frozen",
            False
        ):

            command = [
                sys.executable,
                worker_path,
                audio_file
            ]

        # ==========================================
        # EXE MODE
        # ==========================================

        else:

            command = [
                worker_path,
                audio_file
            ]

        print(
            "🧠 Starting speech worker..."
        )

        # ==========================================
        # RUN WORKER
        # ==========================================

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            )
        )

        output = result.stdout.strip()

        error_output = (
            result.stderr.strip()
        )

        # ==========================================
        # OUTPUT
        # ==========================================

        print(
            "🧠 Worker output:"
        )

        print(output)

        if error_output:

            print(
                "🧠 Worker error:"
            )

            print(error_output)

        # ==========================================
        # READ RESULT
        # ==========================================

        for line in output.splitlines():

            if line.startswith(
                "RESULT:"
            ):

                text = line[
                    len("RESULT:"):
                ].strip()

                print(
                    "🟢 Worker result:",
                    text
                )

                return text

            if line == "UNKNOWN_VALUE":

                print(
                    "❓ Worker could not "
                    "understand audio."
                )

                return ""

            if line.startswith(
                "REQUEST_ERROR:"
            ):

                print(
                    "❌ Google Speech "
                    "service error:",
                    line
                )

                return ""

            if line.startswith(
                "ERROR:"
            ):

                print(
                    "❌ Speech worker error:",
                    line
                )

                return ""

        print(
            "⚠️ Worker returned no text."
        )

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

        _worker_lock.release()

        print(
            "🔓 Speech worker lock released"
        )