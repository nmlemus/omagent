# omagent/server/routes.py
import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from omagent.server.auth import verify_bearer_token
from omagent.server.ws import manager

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


# In-memory permission response store (simple approach)
_permission_responses: dict[str, asyncio.Event] = {}
_permission_decisions: dict[str, bool] = {}


def create_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_bearer_token)])
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
            event_counter = 0
            async for event in loop.run(body.message):
                data = event.to_dict()
                data["session_id"] = loop.session.id

                event_id = str(event_counter)
                event_counter += 1
                yield f"id: {event_id}\nevent: {data['type']}\ndata: {json.dumps(data)}\n\n"

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
        connection_id = str(uuid.uuid4())
        await manager.connect(websocket, connection_id)

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
                    await manager.send_to_connection(connection_id, {"type": "error", "message": "Empty message"})
                    continue

                # Create or reuse loop
                if current_loop is None or session_id != getattr(current_loop, "_ws_session_id", None):
                    current_loop = loop_factory(pack_name, session_id)
                    current_loop._ws_session_id = session_id or current_loop.session.id

                # Bind connection to session after first message
                manager.bind_session(connection_id, current_loop.session.id)

                async for event in current_loop.run(message):
                    event_data = event.to_dict()
                    event_data["session_id"] = current_loop.session.id
                    await manager.send_to_connection(connection_id, event_data)

        except WebSocketDisconnect:
            manager.disconnect(connection_id)

    @router.post("/sessions/{session_id}/approve/{tool_call_id}")
    async def approve_tool(session_id: str, tool_call_id: str):
        """Approve a pending tool execution."""
        key = f"{session_id}:{tool_call_id}"
        _permission_decisions[key] = True
        if key in _permission_responses:
            _permission_responses[key].set()
        return {"approved": True}

    @router.post("/sessions/{session_id}/deny/{tool_call_id}")
    async def deny_tool(session_id: str, tool_call_id: str):
        """Deny a pending tool execution."""
        key = f"{session_id}:{tool_call_id}"
        _permission_decisions[key] = False
        if key in _permission_responses:
            _permission_responses[key].set()
        return {"denied": True}

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

    @router.get("/sessions/{session_id}/timeline")
    async def get_session_timeline(
        session_id: str,
        limit: int = 100,
        event_types: str | None = None,
    ):
        """Get chronological activity events for a session."""
        from omagent.core.tracker import ActivityTracker
        tracker = ActivityTracker()
        types = event_types.split(",") if event_types else None
        timeline = await tracker.get_timeline(session_id, limit=limit, event_types=types)
        return {"session_id": session_id, "timeline": timeline}

    @router.get("/activity/daily")
    async def get_daily_activity(date: str | None = None):
        """Get daily activity report. Pass ?date=2026-04-01 or omit for today."""
        from omagent.core.tracker import ActivityTracker
        tracker = ActivityTracker()
        report = await tracker.get_daily_report(target_date=date)
        return report

    @router.post("/sessions/{session_id}/fork")
    async def fork_session(session_id: str):
        """Fork a session, creating a deep copy with a new ID."""
        from fastapi import HTTPException
        session = await store.load(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        forked = session.fork()
        await store.save(forked)
        return {"forked_id": forked.id, "original_id": session_id, "message_count": len(forked.messages)}

    @router.get("/sessions/{session_id}/export")
    async def export_session(session_id: str, format: str = "json"):
        """Export a session as JSON or Markdown."""
        from fastapi import HTTPException
        from fastapi.responses import PlainTextResponse
        session = await store.load(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        if format == "markdown":
            return PlainTextResponse(session.export_markdown(), media_type="text/markdown")
        return session.to_dict()

    @router.post("/sessions/import")
    async def import_session(request: Request):
        """Import a session from JSON."""
        body = await request.json()
        json_str = json.dumps(body) if isinstance(body, dict) else body
        from omagent.core.session import Session as SessionModel
        session = SessionModel.import_json(json_str)
        await store.save(session)
        return {"session_id": session.id, "message_count": len(session.messages)}

    @router.patch("/sessions/{session_id}")
    async def update_session(session_id: str, request: Request):
        """Update session metadata (pack_name)."""
        from fastapi import HTTPException
        session = await store.load(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        body = await request.json()
        if "pack_name" in body:
            session.pack_name = body["pack_name"]
        await store.save(session)
        return session.to_dict()

    @router.get("/sessions/{session_id}/journal")
    async def get_journal(session_id: str, limit: int = 100, event_types: str | None = None):
        """Get structured events from the session journal."""
        from omagent.core.journal import EventJournal
        from omagent.core.workspace import get_workspaces_dir

        logs_dir = get_workspaces_dir() / session_id / "logs"
        if not logs_dir.exists():
            return {"events": [], "message": "No journal found for this session"}

        journal = EventJournal(session_id=session_id, logs_dir=logs_dir)
        types = event_types.split(",") if event_types else None
        events = journal.read_events(limit=limit, event_types=types)
        return {"events": events, "count": len(events)}

    @router.get("/sessions/{session_id}/artifacts")
    async def list_artifacts(session_id: str):
        """List artifacts in a session workspace."""
        from omagent.core.workspace import Workspace, get_workspaces_dir

        ws_root = get_workspaces_dir() / session_id
        if not ws_root.exists():
            return {"artifacts": [], "message": "No workspace found"}

        ws = Workspace(session_id=session_id)
        return {"artifacts": ws.list_artifacts()}

    @router.get("/sessions/{session_id}/plan")
    async def get_plan(session_id: str):
        """Get the current agent plan for a session."""
        try:
            from omagent.core.planner import PlanStore
            plan_store = PlanStore()
            plan = await plan_store.load(session_id)
            if plan:
                return plan.to_dict()
            return {"message": "No plan found for this session"}
        except Exception:
            return {"message": "Plan store not available"}

    @router.get("/sessions/{session_id}/memory")
    async def get_memory(session_id: str):
        """Get persistent memories for a session."""
        from omagent.core.memory import MemoryStore
        mem_store = MemoryStore()
        memories = await mem_store.get_all(session_id)
        return {"memories": memories}

    @router.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return router
