import asyncio
import json
import time
import unittest

from server.client_session import ClientSession
from server.history import FinalHistory
from test_delivery import Socket, caption, settle


class FeedbackSocket(Socket):
    def __init__(self, delay=0):
        super().__init__()
        self.delay = delay
        self.pings = 0
        self.waiters = []

    async def ping(self):
        self.pings += 1
        future = asyncio.get_running_loop().create_future()
        self.waiters.append(future)
        if self.delay is not None:
            def acknowledge():
                if not future.done():
                    future.set_result(self.delay)
            asyncio.get_running_loop().call_later(self.delay, acknowledge)
        return future

    async def close(self, **kwargs):
        for future in self.waiters:
            if not future.done():
                future.cancel()
        await super().close(**kwargs)


class FeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_fast_feedback_preserves_every_revision(self):
        h, ws = FinalHistory(), FeedbackSocket()
        d = ClientSession(ws, h, [], feedback_window=2)
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 1)
            count = 1
            for seg in range(1, 5):
                for rev in (1, 2, 3):
                    c = caption(seg, rev, rev == 3)
                    if c.final:
                        h.add(c)
                    d.enqueue(c.to_dict())
                    count += 1
                    await settle(lambda: len(ws.messages) == count and d.feedback_started is None)
            self.assertGreater(ws.pings, 0)
            self.assertEqual(d.coalesced_count, 0)
            self.assertEqual(d.feedback_delays, 0)
            self.assertEqual(len(ws.messages), 13)
        finally:
            await d.close()

    async def test_steady_propagation_delay_is_not_receive_congestion(self):
        ws = FeedbackSocket(delay=0.02)
        d = ClientSession(ws, FinalHistory(), [], feedback_window=1,
                          slow_send_seconds=0.005)
        await d.delivery_checkpoint()
        await d.delivery_checkpoint()
        self.assertFalse(d.congested)
        self.assertEqual(d.feedback_delays, 0)
        await d.close()

    async def test_delayed_feedback_compacts_and_holds_recovery(self):
        ws, h = FeedbackSocket(delay=0.03), FinalHistory()
        d = ClientSession(ws, h, [], feedback_window=1,
                          slow_send_seconds=0.005, lag_seconds=0.005, recovery_seconds=0)
        d.feedback_baseline = 0.001
        await d.delivery_checkpoint()
        self.assertTrue(d.congested)
        self.assertEqual(d.feedback_delays, 1)
        self.assertGreater(d.feedback_hold_until, time.monotonic())
        for rev in (1, 2, 3):
            d.enqueue(caption(1, rev).to_dict())
        self.assertEqual(len(d.outgoing_queue), 1)
        self.assertEqual(json.loads(d.outgoing_queue[0][1])['revision'], 3)
        d.outgoing_queue.clear()
        d.outgoing_bytes = 0
        d.update_pressure(time.monotonic())
        self.assertTrue(d.congested)
        d.feedback_hold_until = time.monotonic() - 1
        d.update_pressure(time.monotonic())
        self.assertFalse(d.congested)
        await d.close()

    async def test_pending_feedback_applies_pressure_before_pong(self):
        ws = FeedbackSocket(delay=0.05)
        d = ClientSession(ws, FinalHistory(), [], feedback_window=1,
                          slow_send_seconds=0.005, lag_seconds=0.005)
        d.feedback_baseline = 0.001
        probe = asyncio.create_task(d.delivery_checkpoint())
        await settle(lambda: d.feedback_started is not None)
        await asyncio.sleep(0.01)
        d.enqueue(caption(1, 1).to_dict())
        self.assertTrue(d.congested)
        await probe
        await d.close()

    async def test_feedback_congestion_preserves_ordered_shared_finals(self):
        ws, h = FeedbackSocket(delay=0.03), FinalHistory()
        d = ClientSession(ws, h, [], feedback_window=1,
                          slow_send_seconds=0.005)
        d.feedback_baseline = 0.001
        d.start()
        try:
            await settle(lambda: d.feedback_started is not None)
            await asyncio.sleep(0.01)
            for seg in range(1, 6):
                for rev in (1, 2, 3):
                    c = caption(seg, rev, rev == 3)
                    if c.final:
                        h.add(c)
                    d.enqueue(c.to_dict())
            await settle(lambda: d.next_final == h.next_sequence)
            finals = [m['segment'] for m in ws.messages
                      if m.get('final')]
            self.assertEqual(finals, [1, 2, 3, 4, 5])
            self.assertEqual(ws.messages[0]['type'], 'HISTORY')
            self.assertGreater(d.coalesced_count, 0)
            self.assertEqual(d.outgoing_bytes, 0)
            self.assertIsNone(d.failure)
        finally:
            await d.close()

    async def test_congested_provisional_wait_is_interrupted_by_final(self):
        ws, h = FeedbackSocket(), FinalHistory()
        d = ClientSession(ws, h, [], lag_seconds=0.2)
        d.congested = True
        d.feedback_hold_until = time.monotonic() + 1
        d.enqueue(caption(1, 1).to_dict())
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 1)
            await asyncio.sleep(0.01)
            self.assertEqual(len(ws.messages), 1)
            d.enqueue(caption(1, 2).to_dict())
            final = caption(1, 3, True)
            h.add(final)
            d.enqueue(final.to_dict())
            await settle(lambda: d.next_final == 1)
            self.assertEqual([(m['segment'], m['revision'])
                              for m in ws.messages[1:]], [(1, 3)])
        finally:
            await d.close()

    async def test_congested_latest_provisional_is_sent_without_a_final(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [], lag_seconds=0.03)
        d.congested = True
        d.feedback_hold_until = time.monotonic() + 1
        d.enqueue(caption(1, 7).to_dict())
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 2)
            self.assertEqual(ws.messages[1]['revision'], 7)
            self.assertFalse(ws.messages[1]['final'])
        finally:
            await d.close()

    async def test_propagation_delay_allows_a_small_pipeline(self):
        ws = FeedbackSocket(delay=0.03)
        d = ClientSession(ws, FinalHistory(), [])
        d.feedback_baseline = 0.03
        d.update_interval = 0.02
        try:
            await d.send('{}')
            await d.send('{}')
            self.assertEqual(ws.pings, 0)
            third = asyncio.create_task(d.send('{}'))
            await settle(lambda: ws.pings == 1)
            self.assertFalse(third.done())
            await third
            self.assertFalse(d.congested)
            self.assertEqual(len(ws.messages), 3)
        finally:
            await d.close()

    async def test_fast_link_retains_one_message_feedback(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [])
        d.feedback_baseline = 0.001
        d.update_interval = 0.2
        try:
            for _ in range(3):
                await d.send('{}')
            self.assertEqual(ws.pings, 3)
        finally:
            await d.close()

    async def test_pipeline_is_capped_even_for_bursty_sources(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [], max_feedback_window=4)
        d.feedback_baseline = 1.0
        d.update_interval = 0.001
        try:
            for _ in range(3):
                await d.send('{}')
            self.assertEqual(ws.pings, 0)
            await d.send('{}')
            self.assertEqual(ws.pings, 1)
        finally:
            await d.close()

    async def test_byte_limit_checks_feedback_before_window_fills(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [], max_feedback_bytes=4)
        d.feedback_baseline = 1.0
        d.update_interval = 0.001
        try:
            await d.send('{}')
            self.assertEqual(ws.pings, 0)
            await d.send('{}')
            self.assertEqual(ws.pings, 1)
            self.assertEqual(d.feedback_bytes, 0)
        finally:
            await d.close()

    async def test_stalled_ping_write_times_out_and_cleans_up(self):
        class StalledPing(FeedbackSocket):
            async def ping(self):
                await asyncio.Event().wait()
        ws = StalledPing()
        d = ClientSession(ws, FinalHistory(), [], send_timeout=0.01)
        d.start()
        await asyncio.wait_for(ws.closed.wait(), 1)
        await d.close()
        self.assertEqual(ws.code, 1013)
        self.assertTrue(d.sender_task.done())

    async def test_replacement_wait_adapts_to_update_spacing(self):
        ws, h = FeedbackSocket(), FinalHistory()
        d = ClientSession(ws, h, [], lag_seconds=0.02)
        d.congested = True
        d.feedback_hold_until = time.monotonic() + 1
        d.enqueue(caption(1, 1).to_dict())
        d.update_interval = 0.05
        d.start()
        try:
            await settle(lambda: len(ws.messages) == 1)
            await asyncio.sleep(0.04)
            self.assertEqual(len(ws.messages), 1)
            final = caption(1, 2, True)
            h.add(final)
            d.enqueue(final.to_dict())
            await settle(lambda: d.next_final == 1)
            self.assertEqual([m.get('revision') for m in ws.messages[1:]], [2])
        finally:
            await d.close()

    async def test_continuous_provisionals_have_a_maximum_delivery_wait(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [], lag_seconds=0.05,
                          max_provisional_delay=0.08)
        d.congested = True
        d.feedback_hold_until = time.monotonic() + 1
        d.start()
        async def produce():
            for rev in range(1, 41):
                d.enqueue(caption(1, rev).to_dict())
                await asyncio.sleep(0.005)
        producer = asyncio.create_task(produce())
        try:
            await settle(lambda: len(ws.messages) >= 2)
            self.assertFalse(producer.done())
            self.assertFalse(ws.messages[1]['final'])
            await producer
            await settle(lambda: ws.messages[-1].get('revision') == 40)
            self.assertEqual(d.outgoing_bytes, 0)
            self.assertIsNone(d.failure)
        finally:
            await producer
            await d.close()

    async def test_brief_scheduling_delays_do_not_enable_coalescing(self):
        class BriefDelay(FeedbackSocket):
            send_delay = 0.12
            async def send(self, raw):
                await asyncio.sleep(self.send_delay)
                await super().send(raw)
        ws = BriefDelay()
        d = ClientSession(ws, FinalHistory(), [])
        d.feedback_baseline = 0.001
        d.update_interval = 0.2
        try:
            await d.send('{}')
            self.assertFalse(d.congested)
            ws.send_delay = 0
            ws.delay = 0.12
            await d.send('{}')
            self.assertFalse(d.congested)
            self.assertEqual(d.coalesced_count, 0)
        finally:
            await d.close()

    async def test_repeated_mild_sends_confirm_pressure(self):
        class MildSend(FeedbackSocket):
            async def send(self, raw):
                await asyncio.sleep(0.02)
                await super().send(raw)
        d = ClientSession(MildSend(), FinalHistory(), [], slow_send_seconds=0.01,
                          lag_seconds=0.1)
        try:
            await d.send('{}')
            self.assertFalse(d.congested)
            await d.send('{}')
            self.assertTrue(d.congested)
        finally:
            await d.close()

    async def test_repeated_mild_feedback_confirms_pressure(self):
        d = ClientSession(FeedbackSocket(delay=0.02), FinalHistory(), [],
                          slow_send_seconds=0.01, lag_seconds=0.1)
        d.feedback_baseline = 0.001
        try:
            await d.delivery_checkpoint()
            self.assertFalse(d.congested)
            await d.delivery_checkpoint()
            self.assertTrue(d.congested)
        finally:
            await d.close()

    async def test_disabled_policy_does_not_add_ping_barriers(self):
        ws = FeedbackSocket()
        d = ClientSession(ws, FinalHistory(), [], feedback_window=1,
                          semantic_backpressure=False)
        await d.send('{}')
        self.assertEqual(ws.pings, 0)
        await d.close()

    async def test_missing_pong_times_out_and_cleans_up(self):
        ws = FeedbackSocket(delay=None)
        d = ClientSession(ws, FinalHistory(), [], feedback_window=1, send_timeout=0.01)
        d.start()
        await asyncio.wait_for(ws.closed.wait(), 1)
        await d.close()
        self.assertEqual(ws.code, 1013)
        self.assertTrue(d.sender_task.done())
        self.assertTrue(all(w.done() for w in ws.waiters))

    async def test_cancellation_during_feedback_cleans_up(self):
        ws = FeedbackSocket(delay=None)
        d = ClientSession(ws, FinalHistory(), [], feedback_window=1)
        d.start()
        await settle(lambda: d.feedback_started is not None)
        await d.close()
        self.assertTrue(d.sender_task.done())
        self.assertTrue(ws.closed.is_set())


if __name__ == '__main__':
    unittest.main()
