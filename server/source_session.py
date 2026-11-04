"""Read caption-source messages and delegate application processing."""
import json
from typing import Any, Awaitable, Callable

from server.state import CaptionSegment

ProcessUpdate = Callable[[dict[str, Any]], Awaitable[CaptionSegment | None]]


async def handle_source(websocket, hello: dict[str, Any],
                        process_update: ProcessUpdate) -> None:
    print(f"source connected: session={hello.get('session')}", flush=True)
    try:
        # Waits for messages from caption source
        async for raw in websocket:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            # If is caption, process the update and publish to clients
            if message.get("type") == "CAPTION_UPDATE":
                try:
                    await process_update(message)
                except OverflowError:
                    await websocket.close(code=1013, reason="Final history capacity exhausted")
                    return
            elif message.get("type") == "SOURCE_DONE":
                print("source finished", flush=True)
    finally:
        print("source disconnected", flush=True)
