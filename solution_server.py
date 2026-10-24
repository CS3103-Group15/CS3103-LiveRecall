#!/usr/bin/env python3
"""LiveRecall server with revision validation, recovery and isolated delivery.

Run: python solution_server.py --port 8765
Stage 5 bounds each client's provisional queue and reads finals from shared
history. Semantic coalescing and overload recovery tuning remain stage 6.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets

from server.delivery import ClientDelivery
from server.history import FinalHistory
from server.state import CaptionState

CLIENTS: set[ClientDelivery] = set()
CAPTION_STATE = CaptionState(session="L1")
FINAL_HISTORY = FinalHistory()


def publish(caption) -> None:
    raw = json.dumps(caption.to_dict())
    for client in tuple(CLIENTS):
        client.offer(caption, raw)


async def handle_source(ws, hello: dict[str, Any]) -> None:
    session = hello.get("session")
    print(f"source connected: session={session}", flush=True)

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "CAPTION_UPDATE":
                try:
                    accepted = CAPTION_STATE.accept_update(msg, FINAL_HISTORY.add)
                except OverflowError:
                    # Do not commit a final that cannot be retained.
                    await ws.close(code=1013, reason="Final history capacity exhausted")
                    return

                if accepted is None:
                    continue

                publish(accepted)
                # Explicit fairness even when buffered source reads don't yield.
                await asyncio.sleep(0)
            elif msg_type == "SOURCE_DONE":
                # Test-control message. The specification does not require it
                # to be forwarded to clients.
                print("source finished: ",
                      f"accepted={CAPTION_STATE.accepted_count}",
                      f"rejected={CAPTION_STATE.rejected_count}",
                      flush=True)
            else:
                # Forward compatibility: ignore fields/messages this baseline
                # doesn't understand rather than crashing.
                continue
    finally:
        print("source disconnected", flush=True)


def parse_client_resume(hello:dict[str, Any]) -> tuple[int, int, int]:
    last_segment = hello.get("last_segment")
    last_revision = hello.get("last_revision")
    history_seconds = hello.get("history_seconds")

    if type(last_segment) is not int or last_segment < 0:
        last_segment = 0

    if type(last_revision) is not int or last_revision < 0:
        last_revision = 0

    if type(history_seconds) is not int or history_seconds < 0:
        history_seconds = 30

    if history_seconds > 60:
        history_seconds = 60

    return last_segment, last_revision, history_seconds


async def handle_client(ws, hello: dict[str, Any]) -> None:
    client_id = hello.get("client_id")

    if hello.get("session") != "L1":
        await ws.close(code=1008, reason="Invalid session")
        return

    last_segment, last_revision, history_seconds = parse_client_resume(hello)

    # Snapshot, cursor capture and registration contain no await, so source
    # processing cannot interleave and create a history/live gap.
    history_items = FINAL_HISTORY.get_recent(
        seconds=history_seconds,
        last_segment=last_segment,
        last_revision=last_revision,
    )
    delivery = ClientDelivery(ws, FINAL_HISTORY, history_items)
    CLIENTS.add(delivery)
    delivery.start()
    print(f"client connected: id={client_id}; recovered={len(history_items)}; "
          f"clients={len(CLIENTS)}", flush=True)
    try:
        async for _ in ws:
            pass
    finally:
        CLIENTS.discard(delivery)
        await delivery.close()
        print(f"client disconnected: id={client_id}; clients={len(CLIENTS)}", flush=True)


async def handler(ws) -> None:
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        hello = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await ws.close(code=1008, reason="Expected a valid hello message")
        return

    msg_type = hello.get("type")
    if msg_type == "SOURCE_HELLO":
        await handle_source(ws, hello)
    elif msg_type == "CLIENT_HELLO":
        await handle_client(ws, hello)
    else:
        await ws.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")


async def main_async(port: int) -> None:
    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        max_size=2**20,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=2,
        write_limit=32768,
    ):
        print(f"LiveRecall listening on ws://0.0.0.0:{port}", flush=True)
        await asyncio.Future()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
