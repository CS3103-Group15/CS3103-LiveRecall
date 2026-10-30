#!/usr/bin/env python3
"""
The source path validates revision state and fans updates into independent
per-client queues and sender tasks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets

from server.client import Client
from server.history import FinalHistory
from server.state import CaptionState

CLIENTS: set[Client] = set()
CAPTION_STATE = CaptionState(session="L1")
FINAL_HISTORY = FinalHistory()


def broadcast(raw_message: str) -> None:
    for client in CLIENTS:
        client.append(raw_message)


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
                accepted = CAPTION_STATE.accept_update(msg)

                if accepted is None:
                    continue

                if accepted.final:
                    FINAL_HISTORY.add(accepted)

                current_update = json.dumps(accepted.to_dict())

                broadcast(current_update)
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

    client: Client | None = None

    try:
        history_items = FINAL_HISTORY.get_recent(
            seconds=history_seconds,
            last_segment=last_segment,
            last_revision=last_revision,
        )

        client = Client(ws, client_id=client_id)
        client.append(json.dumps({"type": "HISTORY", "items": history_items}))
        # HISTORY contains finals only. Replaying the latest active state after
        # it lets a reconnecting/late client converge even if overload forced
        # it off the previous socket mid-segment.
        for active in sorted(CAPTION_STATE.active.values(), key=lambda c: c.segment):
            client.append(json.dumps(active.to_dict()))
        CLIENTS.add(client)
        client.start()

        print(
            f"client connected: id={client_id}; "
            f"recovered={len(history_items)}; "
            f"clients={len(CLIENTS)}",
            flush=True,
        )

        # Keep the client connection open.
        async for _ in ws:
            pass
    finally:
        if client is not None:
            CLIENTS.discard(client)
            await client.stop()
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
    ):
        print(f"LiveRecall baseline listening on ws://0.0.0.0:{port}", flush=True)
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
