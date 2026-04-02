# omagent/server/routes.py
import json
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from omagent.core.events import (
    TextDeltaEvent, ToolCallEvent, ToolResultEvent,
    PermissionDeniedEvent, ErrorEvent, DoneEvent
)
from omagent.core.session import SessionStore


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    pack: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list[dict] = []


def create_router() -> APIRouter:
    router = APIRouter()
    store = SessionStore()

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: Request, body: ChatRequest):
        """Send a message and get a complete response (non-streaming)."""
        loop_factory = request.app.state.loop_factory
        pack_name = body.pack or request.app.state.default_pack

        loop = loop_factory(pack_name, body.session_id)

        response_text = ""
        tool_calls = []

        async for event in loop.run(body.message):
            if isinstance(event, TextDeltaEvent):
                response_text += event.content
            elif isinstance(event, ToolCallEvent):
                tool_calls.append({
                    "id": event.id,
                    "name": event.name,
                    "input": event.input,
                })
            elif isinstance(event, ToolResultEvent):
                tool_calls.append({
                    "id": event.tool_use_id,
                    "name": event.tool_name,
                    "result": event.result,
                    "type": "result",
                })

        return ChatResponse(
            session_id=loop.session.id,
            response=response_text,
            tool_calls=tool_calls,
        )

    @router.post("/stream")
    async def stream_chat(request: Request, body: ChatRequest):
        """Send a message and stream events via Server-Sent Events (SSE)."""
        loop_factory = request.app.state.loop_factory
        pack_name = body.pack or request.app.state.default_pack

        loop = loop_factory(pack_name, body.session_id)

        async def event_generator():
            async for event in loop.run(body.message):
                data = {
                    "type": event.type.value,
                    "session_id": loop.session.id,
                }

                if isinstance(event, TextDeltaEvent):
                    data["content"] = event.content
                elif isinstance(event, ToolCallEvent):
                    data["tool_call"] = {"id": event.id, "name": event.name, "input": event.input}
                elif isinstance(event, ToolResultEvent):
                    data["tool_result"] = {
                        "id": event.tool_use_id,
                        "name": event.tool_name,
                        "result": event.result,
                        "is_error": event.is_error,
                    }
                elif isinstance(event, PermissionDeniedEvent):
                    data["tool_name"] = event.tool_name
                    data["reason"] = event.reason
                elif isinstance(event, ErrorEvent):
                    data["message"] = event.message

                yield f"data: {json.dumps(data)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        """WebSocket endpoint for real-time streaming chat."""
        await websocket.accept()

        loop_factory = websocket.app.state.loop_factory
        default_pack = websocket.app.state.default_pack
        current_loop = None

        try:
            while True:
                data = await websocket.receive_json()
                message = data.get("message", "")
                pack_name = data.get("pack", default_pack)
                session_id = data.get("session_id")

                if not message:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Create or reuse loop
                if current_loop is None or session_id != getattr(current_loop, "_ws_session_id", None):
                    current_loop = loop_factory(pack_name, session_id)
                    current_loop._ws_session_id = session_id or current_loop.session.id

                async for event in current_loop.run(message):
                    event_data = {
                        "type": event.type.value,
                        "session_id": current_loop.session.id,
                    }

                    if isinstance(event, TextDeltaEvent):
                        event_data["content"] = event.content
                    elif isinstance(event, ToolCallEvent):
                        event_data["tool_call"] = {"id": event.id, "name": event.name, "input": event.input}
                    elif isinstance(event, ToolResultEvent):
                        event_data["tool_result"] = {
                            "id": event.tool_use_id,
                            "name": event.tool_name,
                            "result": event.result,
                            "is_error": event.is_error,
                        }
                    elif isinstance(event, PermissionDeniedEvent):
                        event_data["tool_name"] = event.tool_name
                    elif isinstance(event, ErrorEvent):
                        event_data["message"] = event.message

                    await websocket.send_json(event_data)

        except WebSocketDisconnect:
            pass

    @router.get("/sessions")
    async def list_sessions(limit: int = 50):
        """List recent sessions."""
        sessions = await store.list_sessions(limit=limit)
        return {"sessions": sessions}

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get a specific session with messages."""
        session = await store.load(session_id)
        if session is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        return session.to_dict()

    @router.delete("/sessions/{session_id}")
    async def delete_session(session_id: str):
        """Delete a session."""
        deleted = await store.delete(session_id)
        return {"deleted": deleted}

    @router.get("/tools")
    async def list_tools(request: Request, pack: str | None = None):
        """List available tools for a pack."""
        loop_factory = request.app.state.loop_factory
        pack_name = pack or request.app.state.default_pack
        loop = loop_factory(pack_name)
        schemas = loop.registry.get_schemas()
        return {"tools": schemas, "pack": pack_name}

    @router.get("/packs")
    async def list_packs():
        """List available domain packs."""
        try:
            from omagent.packs.loader import DomainPackLoader
            loader = DomainPackLoader()
            packs = loader.list_packs()
            return {"packs": packs}
        except Exception:
            return {"packs": []}

    @router.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return router
