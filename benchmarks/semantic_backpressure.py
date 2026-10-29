"""Controlled before/after experiment; does not modify instructor harnesses.

A socket gate holds the client during a source burst. On release, each send is
charged a small byte-proportional delay. This is a delivery-policy microbenchmark,
not a real TCP, tc/netem or Ubuntu performance measurement.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.client_session import ClientSession
from server.history import FinalHistory
from server.state import CaptionSegment


class RateLimitedSocket:
    def __init__(self):
        self.gate = asyncio.Event()
        self.messages = []
        self.bytes = 0

    async def send(self, raw):
        await self.gate.wait()
        await asyncio.sleep(len(raw.encode()) / 200000)
        self.bytes += len(raw.encode())
        self.messages.append(json.loads(raw))

    async def close(self, **kwargs):
        pass


async def one_run(enabled):
    history, ws = FinalHistory(), RateLimitedSocket()
    delivery = ClientSession(ws, history, [], semantic_backpressure=enabled)
    delivery.start()
    try:
        for segment in range(1, 41):
            for revision in range(1, 4):
                c = CaptionSegment('L1', segment, revision, time.time(), revision == 3,
                                  'Caption text ' * 30)
                if c.final:
                    history.add(c)
                delivery.enqueue(c.to_dict(), json.dumps(c.to_dict()))
        queued_at_release = len(delivery.outgoing_queue)
        started = time.monotonic()
        ws.gate.set()
        async with asyncio.timeout(10):
            while delivery.next_final < history.next_sequence:
                if delivery.failure:
                    raise RuntimeError(delivery.failure)
                await asyncio.sleep(0.001)
        finals = [m['segment'] for m in ws.messages if m.get('final')]
        assert finals == list(range(1, 41)), finals
        return dict(policy='stage6' if enabled else 'stage5',
                    final_completeness_pct=100,
                    live_messages=len(ws.messages) - 1,
                    transmitted_bytes=ws.bytes,
                    queued_provisionals_at_release=queued_at_release,
                    coalesced_provisionals=delivery.coalesced_count,
                    catch_up_ms=round((time.monotonic() - started) * 1000, 3))
    finally:
        await delivery.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = [await one_run(False), await one_run(True)]
    report = dict(workload='40 segments x 3 revisions, held then byte-paced socket',
                  scope='controlled local policy microbenchmark', results=results)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')


if __name__ == '__main__':
    asyncio.run(main())
