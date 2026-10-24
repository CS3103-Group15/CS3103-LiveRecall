#!/usr/bin/env python3
"""
CS3103 Assignment 4 - LiveRecall naive working baseline.

This starter is intentionally useful but incomplete. It provides the required
CLI and a basic WebSocket broadcaster so that caption_source.py -> server ->
browser/load clients works on day one.

It DOES NOT implement the graded networking mechanisms:
  - revision-state management or deduplication
  - recent-history recovery or late-join recovery
  - bounded per-client application queues
  - slow-client isolation
  - semantic coalescing / backpressure
  - constrained-bandwidth overload handling

Required evaluator command:
    python solution_server.py --port 8765

Teams should replace or substantially extend the implementation while keeping
this command-line interface and the protocol in the assignment specification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets

from server.history import FinalHistory
from server.state import CaptionState

# Naive global set of currently connected student clients.
# There is deliberately no per-client queue or recovery state here.
CLIENTS: set[Any] = set()
CAPTION_STATE = CaptionState(session="L1")
FINAL_HISTORY = FinalHistory()

DELIVERY_LOCK = asyncio.Lock()


async def broadcast_naively(raw_message: str) -> None:
    """Send one message directly to every connected client.

    This is intentionally a naive baseline. The source handler waits for all
    sends to complete. Under pressure, this design may accumulate delay and is
    not the target architecture for the assignment.
    """
    async with DELIVERY_LOCK:
        if not CLIENTS:
            return

        snapshot = list(CLIENTS)

        results = await asyncio.gather(
            *(client.send(raw_message) for client in snapshot),
            return_exceptions=True,
        )

        for client, result in zip(snapshot, results):
            if isinstance(result, Exception):
                CLIENTS.discard(client)


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

                await broadcast_naively(current_update)
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

    registered = False

    try:
        # Prevent concurrent live broadcasts from overtaking
        # the initial HISTORY response.
        async with DELIVERY_LOCK:
            history_items = FINAL_HISTORY.get_recent(
                seconds=history_seconds,
                last_segment=last_segment,
                last_revision=last_revision,
            )

            await ws.send(json.dumps({
                "type": "HISTORY",
                "items": history_items,
            }))

            # Registration occurs before releasing the lock.
            CLIENTS.add(ws)
            registered = True

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
        if registered:
            CLIENTS.discard(ws)
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
