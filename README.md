# AI Meeting Assistant

A desktop companion for authorized meeting or lecture input. It accepts manual text and Python-side microphone speech recognition, sends recognized speech to the live transcript through the existing WebSocket, stores it in SQLite, and updates the AI panel when Gemini is available.

## Run

1. Create/activate a Python environment and install dependencies:
   `python -m pip install -r requirements.txt`
2. Add `GEMINI_API_KEY` to `.env` if AI generation is required. The app still runs without it.
3. Start the backend:
   `python -m uvicorn backend.main:app --reload`
4. In another terminal, start the always-on-top desktop companion:
   `python overlay/app.py`

Microphone input is initiated only by the visible **Start Speaking** button. It uses the system microphone through SpeechRecognition/PyAudio; it does not capture meeting-platform audio or browser Web Speech.

## Testing note

The speech service needs an available microphone and network access to Google Speech Recognition. Gemini quota/network errors are logged in the backend and return a temporary-unavailable state without stopping transcript storage or WebSocket delivery.
"# Meeting" 
