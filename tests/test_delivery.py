import asyncio
import json
import time
import unittest

from server.client_session import ClientSession
from server.history import FinalHistory
from server.state import CaptionState, CaptionSegment


def caption(segment, revision=1, final=False):
    return CaptionSegment('L1', segment, revision, time.time(), final, 'example')


class Socket:
    def __init__(self, blocked=False):
        self.gate = asyncio.Event()
        if not blocked:
            self.gate.set()
        self.messages = []
        self.closed = asyncio.Event()
        self.code = None

    async def send(self, raw):
        await self.gate.wait()
        self.messages.append(json.loads(raw))

    async def close(self, code=1000, reason=''):
        self.code = code
        self.closed.set()


async def settle(predicate):
    async def wait():
        while not predicate():
            await asyncio.sleep(0)
    await asyncio.wait_for(wait(), 1)


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_history_does_not_block_healthy_client(self):
        h = FinalHistory()
        slow, fast = Socket(True), Socket()
        a, b = ClientSession(slow, h, []), ClientSession(fast, h, [])
        a.start(); b.start()
        try:
            for seg in range(1, 5):
                c = caption(seg, final=True)
                h.add(c)
                for d in (a, b):
                    d.enqueue(c.to_dict(), json.dumps(c.to_dict()))
            await settle(lambda: len(fast.messages) == 5)
            self.assertEqual(slow.messages, [])
            self.assertEqual([m['segment'] for m in fast.messages[1:]], [1, 2, 3, 4])
            self.assertEqual(len(a.outgoing_queue), 0)  # No per-client final backlog.
            slow.gate.set()
            await settle(lambda: len(slow.messages) == 5)
            self.assertEqual(slow.messages[0]['type'], 'HISTORY')
        finally:
            await a.close(); await b.close()

    async def test_full_revision_order_and_history_boundary(self):
        h = FinalHistory()
        h.add(caption(1, 3, True))
        ws = Socket(True)
        d = ClientSession(ws, h, h.get_recent(60))
        d.start()
        try:
            for seg in (2, 3):
                for rev in (1, 2, 3):
                    c = caption(seg, rev, rev == 3)
                    if c.final:
                        h.add(c)
                    d.enqueue(c.to_dict(), json.dumps(c.to_dict()))
            ws.gate.set()
            await settle(lambda: len(ws.messages) == 7)
            self.assertEqual(len(ws.messages[0]['items']), 1)
            self.assertEqual([(m['segment'], m['revision']) for m in ws.messages[1:]],
                             [(2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3)])
        finally:
            await d.close()

    async def test_queue_overflow_is_bounded_and_closes(self):
        ws = Socket(True)
        d = ClientSession(ws, FinalHistory(), [], max_pending=2,
                           semantic_backpressure=False)
        d.start()
        for rev in range(1, 10):
            c = caption(1, rev)
            d.enqueue(c.to_dict(), json.dumps(c.to_dict()))
        self.assertEqual(len(d.outgoing_queue), 2)
        self.assertIsNotNone(d.failure)
        ws.gate.set()
        await asyncio.wait_for(ws.closed.wait(), 1)
        await d.close()
        self.assertEqual(ws.code, 1013)
        self.assertEqual(d.outgoing_bytes, 0)

    async def test_byte_limit(self):
        d = ClientSession(Socket(), FinalHistory(), [], max_pending_bytes=1)
        c = caption(1)
        d.enqueue(c.to_dict(), json.dumps(c.to_dict()))
        self.assertEqual(len(d.outgoing_queue), 0)
        self.assertIsNotNone(d.failure)

    async def test_stalled_send_times_out(self):
        ws = Socket(True)
        d = ClientSession(ws, FinalHistory(), [], send_timeout=0.01)
        d.start()
        await asyncio.wait_for(ws.closed.wait(), 1)
        await d.close()
        self.assertEqual(ws.code, 1013)

    async def test_expired_bookmark_fails_explicitly(self):
        h = FinalHistory()
        ws = Socket(True)
        d = ClientSession(ws, h, [])
        d.start()
        h.add(caption(1, 3, True))
        h.remove_old_entries(time.monotonic() + 100)
        ws.gate.set()
        await asyncio.wait_for(ws.closed.wait(), 1)
        await d.close()
        self.assertIn('retained', d.failure)

    async def test_cleanup_cancels_blocked_sender(self):
        ws = Socket(True)
        d = ClientSession(ws, FinalHistory(), [])
        d.start()
        await asyncio.sleep(0)
        await d.close()
        await d.close()
        self.assertTrue(d.sender_task.done())
        self.assertTrue(ws.closed.is_set())

    async def test_history_capacity_failure_does_not_commit_final(self):
        s = CaptionState('L1')
        h = FinalHistory(max_items=0)
        c = caption(1, 3, True)
        with self.assertRaises(OverflowError):
            s.accept_update(c.to_dict(), h.add)
        self.assertEqual(s.highest_finalized_segment, 0)
        self.assertEqual(s.accepted_count, 0)
        h.max_items = 1
        self.assertIsNotNone(s.accept_update(c.to_dict(), h.add))
        self.assertEqual(s.highest_finalized_segment, 1)


if __name__ == '__main__':
    unittest.main()
