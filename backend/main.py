import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.assistant import analyze_message, generate_meeting_summary
from backend.websocket import get_active_transcript, websocket_endpoint
from database.database import get_connection, save_summary

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
app.mount("/frontend", StaticFiles(directory=_resource_root / "frontend"), name="frontend")

class AnalyzeRequest(BaseModel):
    message: str


def _extract_action_items(messages):
    """Conservative local extraction so action items work without Gemini."""
    triggers = ("will ", "need to", "needs to", "assigned", "action item", "todo", "by ")
    return [
        {"speaker": item["username"], "text": item["message"], "created_at": item["created_at"]}
        for item in messages
        if any(trigger in item["message"].lower() for trigger in triggers)
    ][-20:]

@app.get("/")
async def home():
    return {"message": "AI Meeting Assistant Backend Running"}

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

@app.post("/ai/analyze")
async def ai_analyze(request: AnalyzeRequest):
    return await asyncio.to_thread(analyze_message, request.message)

@app.post("/meeting/summary")
async def meeting_summary():
    from backend import websocket as meeting_state
    messages = get_active_transcript()
    transcript = "\n".join(f"{item['username']}: {item['message']}" for item in messages)
    participants = list(dict.fromkeys(item["username"] for item in messages))
    summary = await asyncio.to_thread(generate_meeting_summary, transcript, meeting_state.active_meeting_title, participants)
    if meeting_state.active_meeting_id is not None:
        save_summary(meeting_state.active_meeting_id, summary)
    return {"summary": summary}


@app.get("/meeting/action-items")
async def meeting_action_items():
    return {"action_items": _extract_action_items(get_active_transcript())}

@app.get("/meetings")
async def get_meetings():
    with get_connection() as db:
        meetings = db.execute("SELECT id, title, summary, created_at FROM meetings ORDER BY id DESC").fetchall()
    return {"meetings": [dict(meeting) for meeting in meetings]}

@app.get("/meetings/{meeting_id}")
async def get_meeting_details(meeting_id: int):
    with get_connection() as db:
        meeting = db.execute("SELECT id, title, summary, created_at FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if not meeting:
            return {"error": "Meeting not found"}
        users = db.execute("SELECT id, username FROM users WHERE meeting_id = ?", (meeting_id,)).fetchall()
        messages = db.execute("""SELECT transcript_messages.id, transcript_messages.message,
            transcript_messages.created_at, users.username FROM transcript_messages
            JOIN users ON transcript_messages.user_id = users.id
            WHERE transcript_messages.meeting_id = ? ORDER BY transcript_messages.id ASC""", (meeting_id,)).fetchall()
    return {"meeting": dict(meeting), "participants": [dict(user) for user in users], "messages": [dict(message) for message in messages]}


@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    return {}
