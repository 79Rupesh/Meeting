import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from ai.assistant import analyze_message
from database.database import add_user, create_meeting, get_transcript, initialize_database, save_message

initialize_database()
connected_users = {}
active_meeting_id = None
active_meeting_title = "AI Meeting Assistant"

def ensure_active_meeting():
    """A meeting begins with its first participant, never merely on module import."""
    global active_meeting_id
    if active_meeting_id is None:
        active_meeting_id = create_meeting(active_meeting_title)
        print(f"Started meeting {active_meeting_id}")
    return active_meeting_id

def get_active_transcript():
    return get_transcript(active_meeting_id) if active_meeting_id else []

async def broadcast(data):
    disconnected = []
    for connection_id, user in list(connected_users.items()):
        try:
            await user["socket"].send_json(data)
        except Exception:
            disconnected.append(connection_id)
    for connection_id in disconnected:
        connected_users.pop(connection_id, None)

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id, username = id(websocket), "Guest"
    try:
        username = (await websocket.receive_text()).strip() or "Guest"
        meeting_id = ensure_active_meeting()
        user_id = add_user(meeting_id, username)
        connected_users[connection_id] = {"socket": websocket, "username": username, "user_id": user_id}
        await broadcast({"type": "join", "username": username, "message": f"{username} joined the meeting", "online_users": len(connected_users)})
        while True:
            message = (await websocket.receive_text()).strip()
            if not message:
                continue
            save_message(meeting_id, user_id, message)
            await broadcast({"type": "message", "username": username, "message": message})
            result = await asyncio.to_thread(analyze_message, message)
            await websocket.send_json({"type": "ai_suggestion", **result})
    except WebSocketDisconnect:
        pass
    except Exception as error:
        print(f"WebSocket error: {error}")
    finally:
        if connected_users.pop(connection_id, None) is not None:
            await broadcast({"type": "leave", "username": username, "message": f"{username} left the meeting", "online_users": len(connected_users)})
        # The next participant starts a new meeting; imports and idle server time do not.
        if not connected_users:
            global active_meeting_id
            active_meeting_id = None
