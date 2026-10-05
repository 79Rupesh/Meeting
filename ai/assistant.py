"""AI analysis for the authorized AI Meeting Companion."""

import os
import time
import json
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.genai import types


if getattr(sys, "frozen", False):
    load_dotenv(Path(sys.executable).resolve().parent / ".env")
else:
    load_dotenv()
# ---------------------------------------------------------
# Persistent Gemini Quota Lock
# ---------------------------------------------------------

if getattr(sys, "frozen", False):
    _quota_directory = Path(os.getenv("LOCALAPPDATA", Path.home())) / "AI Meeting Companion"
    _quota_directory.mkdir(parents=True, exist_ok=True)
    QUOTA_LOCK_FILE = str(_quota_directory / "gemini_quota_lock.json")
else:
    QUOTA_LOCK_FILE = "database/gemini_quota_lock.json"


def is_gemini_quota_locked():
    if not os.path.exists(QUOTA_LOCK_FILE):
        return False

    try:
        with open(QUOTA_LOCK_FILE, "r") as file:
            data = json.load(file)

        locked_until = data.get("locked_until", 0)

        if time.time() < locked_until:
            remaining = int(locked_until - time.time())

            print(
                f"Gemini quota locked. "
                f"Approx {remaining // 60} minutes remaining."
            )

            return True

        # Lock expired
        os.remove(QUOTA_LOCK_FILE)

        print("Gemini quota lock expired.")

        return False

    except Exception as error:
        print(f"Quota lock read error: {error}")
        return False


def lock_gemini_quota(error_text):
    # Default: 24 hours
    wait_seconds = 24 * 60 * 60

    # Try to read Google's retry delay
    match = re.search(
        r"retryDelay.*?(\d+)s",
        error_text
    )

    if match:
        wait_seconds = int(match.group(1))

    locked_until = time.time() + wait_seconds

    try:
        os.makedirs(
            os.path.dirname(QUOTA_LOCK_FILE),
            exist_ok=True
        )

        with open(
            QUOTA_LOCK_FILE,
            "w"
        ) as file:

            json.dump(
                {
                    "locked_until": locked_until,
                    "wait_seconds": wait_seconds
                },
                file,
                indent=4
            )

        print(
            f"Gemini quota locked for "
            f"{wait_seconds // 60} minutes."
        )

    except Exception as error:
        print(
            f"Quota lock save error: {error}"
        )

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

_client = None

# Prevent repeated questions from consuming quota
_recent_questions = {}
DUPLICATE_WINDOW_SECONDS = 30

gemini_quota_blocked = False

# ---------------------------------------------------------
# Gemini Client
# ---------------------------------------------------------

def _get_client():
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Gemini API key not found.")
        return None

    try:
        from google import genai

        _client = genai.Client(api_key=api_key)

        print("Gemini client initialized.")

        return _client

    except Exception as error:
        print(f"Gemini client unavailable: {error}")
        return None


# ---------------------------------------------------------
# Local Question Detection
# ---------------------------------------------------------

def detect_question_locally(message):
    text = message.lower().strip()

    if "?" in text:
        return True

    question_words = {
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "which",
        "can",
        "could",
        "would",
        "should",
        "is",
        "are",
        "do",
        "does",
        "did",
        "will",
        "shall"
    }

    words = text.split()

    if words and words[0] in question_words:
        return True

    return False


# ---------------------------------------------------------
# Local Topic Detection
# ---------------------------------------------------------

def detect_topic_locally(message):
    text = message.lower()

    topics = {
        "Programming": (
            "python",
            "java",
            "javascript",
            "code",
            "programming",
            "api",
            "database",
            "software"
        ),

        "Project": (
            "project",
            "development",
            "feature",
            "module",
            "system"
        ),

        "Meeting": (
            "meeting",
            "discussion",
            "agenda",
            "discussion"
        ),

        "Schedule": (
            "schedule",
            "time",
            "deadline",
            "tomorrow",
            "today"
        ),

        "Task": (
            "task",
            "work",
            "assignment",
            "responsibility"
        ),

        "Problem": (
            "problem",
            "issue",
            "error",
            "bug",
            "failed",
            "failure"
        )
    }

    for topic, keywords in topics.items():

        for keyword in keywords:

            if keyword in text:
                return topic

    return "General Discussion"


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def _field(text, label, default):

    for line in text.splitlines():

        if line.strip().lower().startswith(
            f"{label.lower()}:"
        ):

            value = line.split(":", 1)[1].strip()

            if value:
                return value

    return default


# ---------------------------------------------------------
# Temporary AI Unavailable
# ---------------------------------------------------------

def _unavailable_analysis(is_question, topic):

    return {
        "is_question": is_question,
        "topic": topic,
        "answer": (
            "AI answer is temporarily unavailable. "
            "Please try again later."
            if is_question
            else "Not a question."
        ),
        "suggestion": (
            "Continue the meeting discussion. "
            "The transcript is still being saved."
        )
    }


# ---------------------------------------------------------
# Check Duplicate Question
# ---------------------------------------------------------

def _is_duplicate_question(message):

    now = time.time()

    key = message.lower().strip()

    # Remove old entries
    expired = [
        question
        for question, timestamp in _recent_questions.items()
        if now - timestamp > DUPLICATE_WINDOW_SECONDS
    ]

    for question in expired:
        del _recent_questions[question]

    # Check duplicate
    if key in _recent_questions:

        print("Duplicate question ignored:", message)

        return True

    _recent_questions[key] = now

    return False


# ---------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------

def analyze_message(message, recent_context=""):

    message = message.strip()

    if not message:

        return {
            "is_question": False,
            "topic": "General Discussion",
            "suggestion": "Please enter a meeting message.",
            "answer": ""
        }

    # ---------------------------------------------
    # Local analysis first
    # ---------------------------------------------

    is_question = detect_question_locally(message)

    topic = detect_topic_locally(message)

    # ---------------------------------------------
    # Normal message → NO Gemini request
    # ---------------------------------------------

    if not is_question:

        return {
            "is_question": False,
            "topic": topic,
            "answer": "Not a question.",
            "suggestion": (
                "Continue the discussion and "
                "capture important points."
            )
        }

    # ---------------------------------------------
    # Duplicate question protection
    # ---------------------------------------------

    if _is_duplicate_question(message):

        return {
            "is_question": True,
            "topic": topic,
            "answer": "This question was already analyzed.",
            "suggestion": "Continue with the meeting discussion."
        }

    # ---------------------------------------------
    # Gemini quota already exhausted
    # ---------------------------------------------

    global gemini_quota_blocked

    if gemini_quota_blocked:

        print("Gemini quota is locked. Skipping API request.")

        return {
            "is_question": True,
            "topic": topic,
            "answer": (
                "Gemini API quota is currently exhausted. "
                "Please try again after the quota resets."
            ),
            "suggestion": (
                "Your meeting transcript is still being saved."
            )
        }

    if is_gemini_quota_locked():

        return {
            "is_question": True,
            "topic": topic,
            "answer": (
                "Gemini API quota is currently exhausted. "
                "Please try again after the quota resets."
            ),
            "suggestion": (
                "The meeting transcript is still being saved."
            )
        }

    # ---------------------------------------------
    # Gemini Client
    # ---------------------------------------------

    client = _get_client()

    if client is None:

        return _unavailable_analysis(
            is_question,
            topic
        )

    # ---------------------------------------------
    # Gemini Prompt
    # ---------------------------------------------

    prompt = f"""
You are an AI Meeting Assistant for an authorized live meeting.

Analyze the following meeting question using the recent meeting context when it
helps resolve references such as "it", "this", or "they".

Return exactly these four lines:

Question: Yes
Topic: a short specific topic in 2 to 5 words
Answer: direct and useful answer to the question
Suggestion: one concise practical suggestion

Rules:

- Answer the actual question.
- Detect the topic from the meaning of the question.
- Do not use a fixed topic list.
- Keep the topic between 2 and 5 words.
- Do not invent information.
- If the question needs context, clearly mention that.
- Keep the answer concise and useful.

Recent meeting context (may be empty):

{recent_context[-6000:]}

Meeting question:

{message}
"""

    # ---------------------------------------------
    # ONE Gemini request only
    # ---------------------------------------------

    try:

        print(
            "Gemini request:",
            message
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            )
        )

        text = (response.text or "").strip()

        result = {
            "is_question": True,

            "topic": _field(
                text,
                "Topic",
                topic
            ),

            "answer": _field(
                text,
                "Answer",
                "No answer generated."
            ),

            "suggestion": _field(
                text,
                "Suggestion",
                "Continue the discussion."
            )
        }

        print(
            "Gemini result:",
            result
        )

        return result

    # ---------------------------------------------
    # Quota / API Errors
    # ---------------------------------------------

    except Exception as error:

        error_text = str(error)

        print(
            "Gemini AI Error:",
            error_text
        )

        # 429 = quota/rate limit
        if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:

            lock_gemini_quota(error_text)

            print(
                "Gemini quota exceeded. "
                "Persistent quota lock enabled."
            )

            return {
                "is_question": True,
                "topic": topic,
                "answer": (
                    "Gemini API quota is currently exhausted. "
                    "Please try again after the quota resets."
                ),
                "suggestion": (
                    "The meeting transcript is still being saved."
                )
            }

        # 503 = temporary service problem
        if "503" in error_text or "UNAVAILABLE" in error_text:

            return {
                "is_question": True,
                "topic": topic,
                "answer": (
                    "Gemini is temporarily unavailable. "
                    "Please try again later."
                ),
                "suggestion": (
                    "Continue the meeting while "
                    "the AI service recovers."
                )
            }

        # Other errors
        return {
            "is_question": True,
            "topic": topic,
            "answer": (
                "AI answer is temporarily unavailable."
            ),
            "suggestion": (
                "The transcript is still being saved."
            )
        }


# ---------------------------------------------------------
# Meeting Summary
# ---------------------------------------------------------

def generate_meeting_summary(
    transcript,
    title="AI Meeting Assistant",
    participants=None
):

    participants = participants or []

    client = _get_client()

    if transcript.strip() and client is not None:

        prompt = f"""
Summarize this authorized meeting transcript.

Return these sections:

Meeting Title
Date/Time
Participants
Short Summary
Key Points
Decisions
Action Items
Important Questions Discussed

Be concise and factual.

Transcript:

{transcript}
"""

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            return (
                response.text or ""
            ).strip()

        except Exception as error:

            print(
                f"Gemini Summary Error: {error}"
            )

    return _local_summary(
        transcript,
        title,
        participants
    )


# ---------------------------------------------------------
# Local Summary
# ---------------------------------------------------------

def _local_summary(
    transcript,
    title,
    participants
):

    lines = [
        line.strip()
        for line in transcript.splitlines()
        if line.strip()
    ]

    messages = [
        line.split(":", 1)[-1].strip()
        for line in lines
    ]

    questions = [
        item
        for item in messages
        if detect_question_locally(item)
    ][:5]

    actions = [
        item
        for item in messages
        if any(
            term in item.lower()
            for term in (
                "will ",
                "need to",
                "assigned",
                "action item",
                "task"
            )
        )
    ][:5]

    decisions = [
        item
        for item in messages
        if any(
            term in item.lower()
            for term in (
                "decided",
                "agreed",
                "final decision",
                "will use"
            )
        )
    ][:5]

    def bullets(items, empty):

        if items:
            return "\n".join(
                f"- {item}"
                for item in items
            )

        return f"- {empty}"

    return f"""
Meeting Title
{title}

Date/Time
Generated from the stored transcript

Participants
{", ".join(participants) or "No participants recorded"}

Short Summary
{len(messages)} transcript message(s) were recorded.

Key Points
{bullets(messages[:5], "No key points detected.")}

Decisions
{bullets(decisions, "No decisions detected.")}

Action Items
{bullets(actions, "No action items detected.")}

Important Questions Discussed
{bullets(questions, "No questions detected.")}
"""
