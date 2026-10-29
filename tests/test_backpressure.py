import asyncio
import json
import time
import unittest

from server.client_session import ClientSession
from server.history import FinalHistory
from test_delivery import Socket, caption, settle


def offer(delivery, history, update):
    if update.final:
        history.add(update)
    delivery.enqueue(update.to_dict(), json.dumps(update.to_dict()))


class BackpressureTests(unittest.IsolatedAsyncioTestCase):
    async def test_overload_keeps_all_finals_and_latest_active(self):
        h, ws = FinalHistory(), Socket(True)
        d = ClientSession(ws, h, [], high_pending=4)
        d.start()
        try:
            for seg in range(1, 21):
                for rev in range(1, 4):
                    offer(d, h, caption(seg, rev, rev == 3))
                self.assertLessEqual(len(d.outgoing_queue), 1 if d.congested else d.high_pending)
                self.assertEqual(d.outgoing_bytes, sum(e[2] for e in d.outgoing_queue))
            for rev in range(1, 10):
                offer(d, h, caption(21, rev))
            self.assertEqual(len(d.outgoing_queue), 1)
            self.assertEqual(json.loads(d.outgoing_queue[0][1])['revision'], 9)
            self.assertIsNone(d.failure)
            ws.gate.set()
            await settle(lambda: len(ws.messages) == 22)
            live = ws.messages[1:]
            self.assertEqual([m['segment'] for m in live[:-1]], list(range(1, 21)))
            self.assertTrue(all(m['final'] for m in live[:-1]))
            self.assertEqual((live[-1]['segment'], live[-1]['revision']), (21, 9))
            self.assertGreater(d.coalesced_count, 0)
        finally:
            await d.close()

    async def test_disabled_policy_preserves_backlog_for_comparison(self):
        h, ws = FinalHistory(), Socket(True)
        d = ClientSession(ws, h, [], semantic_backpressure=False)
        d.start()
        try:
            for seg in range(1, 9):
                for rev in range(1, 4):
                    offer(d, h, caption(seg, rev, rev == 3))
            ws.gate.set()
            await settle(lambda: len(ws.messages) == 25)
            self.assertEqual(d.coalesced_count, 0)
            self.assertEqual(sum(m.get('final', False) for m in ws.messages), 8)
        finally:
            await d.close()

    async def test_normal_stream_preserves_every_revision(self):
        h, ws = FinalHistory(), Socket()
        d = ClientSession(ws, h, [])
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 1)
            count = 1
            for seg in range(1, 9):
                for rev in range(1, 4):
                    offer(d, h, caption(seg, rev, rev == 3))
                    count += 1
                    await settle(lambda: len(ws.messages) == count)
            self.assertEqual(d.coalesced_count, 0)
            self.assertEqual(d.congestion_count, 0)
            self.assertEqual(len(ws.messages), 25)
        finally:
            await d.close()

    async def test_recovery_returns_to_full_revision_delivery(self):
        h, ws = FinalHistory(), Socket(True)
        d = ClientSession(ws, h, [], high_pending=3, recovery_seconds=0.02)
        d.start()
        try:
            for rev in range(1, 7):
                offer(d, h, caption(1, rev))
            self.assertTrue(d.congested)
            offer(d, h, caption(1, 7, True))
            ws.gate.set()
            await settle(lambda: len(ws.messages) == 2)
            await asyncio.sleep(0.03)
            for rev in range(1, 4):
                expected = len(ws.messages) + 1
                offer(d, h, caption(2, rev, rev == 3))
                await settle(lambda: len(ws.messages) == expected)
            self.assertEqual([m['revision'] for m in ws.messages[2:]], [1, 2, 3])
            self.assertEqual(d.recovery_count, 1)
            self.assertFalse(d.congested)
        finally:
            await d.close()

    async def test_in_flight_message_finishes_before_compacted_work(self):
        class GatedSocket(Socket):
            async def send(self, raw):
                msg = json.loads(raw)
                if msg['type'] == 'CAPTION_UPDATE' and not self.gate.is_set():
                    await self.gate.wait()
                self.messages.append(msg)
        h, ws = FinalHistory(), GatedSocket(True)
        d = ClientSession(ws, h, [], high_pending=2)
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 1)
            offer(d, h, caption(1, 1))
            await settle(lambda: d.send_started is not None)
            for rev in (2, 3, 4):
                offer(d, h, caption(1, rev))
            offer(d, h, caption(1, 5, True))
            offer(d, h, caption(2, 1))
            offer(d, h, caption(2, 2))
            ws.gate.set()
            await settle(lambda: len(ws.messages) == 4)
            self.assertEqual([(m['segment'], m['revision']) for m in ws.messages[1:]],
                             [(1, 1), (1, 5), (2, 2)])
        finally:
            await d.close()

    async def test_byte_pressure_replaces_before_hard_limit(self):
        h = FinalHistory()
        sample = caption(1)
        size = len(json.dumps(sample.to_dict()).encode())
        d = ClientSession(Socket(), h, [], max_pending_bytes=size * 2 + 20,
                           high_bytes=size * 2, high_pending=100)
        for rev in range(1, 100):
            offer(d, h, caption(1, rev))
            self.assertLessEqual(d.outgoing_bytes, d.max_pending_bytes)
        self.assertIsNone(d.failure)
        self.assertEqual(len(d.outgoing_queue), 1)
        self.assertEqual(json.loads(d.outgoing_queue[0][1])['revision'], 99)

    async def test_age_transport_and_slow_send_trigger_congestion(self):
        h = FinalHistory()
        d = ClientSession(Socket(), h, [])
        offer(d, h, caption(1))
        seg, raw, size, _ = d.outgoing_queue[0]
        d.outgoing_queue[0] = (seg, raw, size, time.monotonic() - 1)
        d.update_pressure(time.monotonic())
        self.assertTrue(d.congested)

        class Transport:
            def get_write_buffer_size(self):
                return 65536
        ws = Socket()
        ws.transport = Transport()
        d = ClientSession(ws, h, [])
        d.update_pressure(time.monotonic())
        self.assertTrue(d.congested)

        class SlowSocket(Socket):
            async def send(self, raw):
                await asyncio.sleep(0.01)
                await super().send(raw)
        d = ClientSession(SlowSocket(), h, [], slow_send_seconds=0.001)
        await d.send('{}')
        self.assertTrue(d.congested)

    async def test_quiet_interval_prevents_immediate_mode_flapping(self):
        d = ClientSession(Socket(), FinalHistory(), [], recovery_seconds=0.5)
        now = time.monotonic()
        d.enter_congestion(now)
        d.update_pressure(now + 0.1)
        self.assertTrue(d.congested)
        d.update_pressure(now + 0.6)
        self.assertFalse(d.congested)

    async def test_slow_client_does_not_change_healthy_client_policy(self):
        h = FinalHistory()
        slow, fast = Socket(True), Socket()
        a = ClientSession(slow, h, [], high_pending=4)
        b = ClientSession(fast, h, [])
        a.start(); b.start()
        count = 1
        try:
            await settle(lambda: len(fast.messages) == count)
            for seg in range(1, 13):
                for rev in range(1, 4):
                    c = caption(seg, rev, rev == 3)
                    if c.final:
                        h.add(c)
                    raw = json.dumps(c.to_dict())
                    a.enqueue(c.to_dict(), raw); b.enqueue(c.to_dict(), raw)
                    count += 1
                    await settle(lambda: len(fast.messages) == count)
            self.assertEqual(b.coalesced_count, 0)
            self.assertEqual(len(fast.messages), 37)
            self.assertGreater(a.coalesced_count, 0)
            self.assertIsNone(a.failure)
            slow.gate.set()
            await settle(lambda: len(slow.messages) == 13)
            self.assertTrue(all(m['final'] for m in slow.messages[1:]))
        finally:
            await a.close(); await b.close()


if __name__ == '__main__':
    unittest.main()
