import json
from typing import Any, Awaitable, Callable
from server.state import CaptionSegment
from server.history import FinalHistory

ProcessUpdate = Callable[
    [dict[str, Any]],
    Awaitable[CaptionSegment | None]
]

async def handle_source(
    websocket: Any, 
    hello: dict[str, Any], 
    process_update: ProcessUpdate
) -> None:
    session = hello.get("session")
    print(f"source connected: session={session}", flush=True)

    try:
        async for raw in websocket:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            message_type = message.get("type")
            if message_type == "CAPTION_UPDATE":
                await process_update(message)

            elif message_type == "SOURCE_DONE":
                # Test-control message. The specification does not require it
                # to be forwarded to clients.
                print("---------------------- Source finished ----------------------",
                      flush=True)
            else:
                # Forward compatibility: ignore fields/messages this baseline
                # doesn't understand rather than crashing.
                continue
    finally:
        print("source disconnected", flush=True)