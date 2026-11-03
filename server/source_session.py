"""Read caption-source messages and delegate application processing."""
import json
from typing import Any, Awaitable, Callable

from server.state import CaptionSegment, CaptionState

ProcessUpdate = Callable[[dict[str, Any]], Awaitable[CaptionSegment | None]]


async def handle_source(websocket, hello: dict[str, Any],
                        process_update: ProcessUpdate, caption_state: CaptionState) -> None:
    """Starting point of source update

    Decode incoming text from websocket into json and invoke the `process_update` application callback.
    If a session limit is exceeded, it terminates the connection gracefully.
    
    Args:
        process_update: Callback to application.process_source_update
    """

    print(f"source connected: session={hello.get('session')}", flush=True)
    try:
        async for raw in websocket:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            if message.get("type") == "CAPTION_UPDATE":
                try:
                    await process_update(message)
                except OverflowError:
                    await websocket.close(code=1013, reason="Final history capacity exhausted")
                    return
            elif message.get("type") == "SOURCE_DONE":
                print(f"source finished: accepted={caption_state.accepted_count}; "
                      f"rejected={caption_state.rejected_count}", flush=True)
    finally:
        print("source disconnected", flush=True)
