import asyncio
from contextlib import redirect_stdout
import io
import unittest

from server.application import LiveRecallApplication
from server.client_session import ClientSession
from server.source_session import handle_source
from test_delivery import Socket, caption, settle


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_attach_captures_history_and_cursor_together(self):
        app = LiveRecallApplication()
        ws = Socket()
        client = ClientSession(ws, app.final_history, [], client_id=7)
        # A final arrives between session construction and actual registration.
        await app.process_source_update(caption(1, 3, True).to_dict())
        await app.attach_client(client, 0, 0, 60)
        client.start()
        try:
            await app.process_source_update(caption(2, 3, True).to_dict())
            await settle(lambda: len(ws.messages) == 2)
            self.assertEqual([c['segment'] for c in ws.messages[0]['items']], [1])
            self.assertEqual(ws.messages[1]['segment'], 2)
            self.assertEqual(app.connected_client_count, 1)
        finally:
            await app.detach_client(client)
        self.assertEqual(app.connected_client_count, 0)

    async def test_hub_does_not_wait_for_blocked_history(self):
        app = LiveRecallApplication()
        slow, fast = Socket(True), Socket()
        a = ClientSession(slow, app.final_history, [], client_id=1)
        b = ClientSession(fast, app.final_history, [], client_id=2)
        await app.attach_client(a, 0, 0, 60)
        await app.attach_client(b, 0, 0, 60)
        a.start(); b.start()
        try:
            for seg in range(1, 4):
                await app.process_source_update(caption(seg, 3, True).to_dict())
            await settle(lambda: len(fast.messages) == 4)
            self.assertEqual(slow.messages, [])
        finally:
            await app.detach_client(a); await app.detach_client(b)

    async def test_overflow_closes_instead_of_silently_unregistering(self):
        app = LiveRecallApplication(semantic_backpressure=False)
        ws = Socket()
        client = ClientSession(ws, app.final_history, [], max_pending=1,
                               semantic_backpressure=False)
        await app.attach_client(client, 0, 0, 60)
        # Fill queue before starting its sender so overflow is deterministic.
        app.delivery_hub.publish(caption(1, 1).to_dict())
        app.delivery_hub.publish(caption(1, 2).to_dict())
        client.start()
        try:
            await asyncio.wait_for(ws.closed.wait(), 1)
            self.assertEqual(ws.code, 1013)
            self.assertTrue(client.is_closed)
        finally:
            await app.detach_client(client)
        self.assertEqual(app.connected_client_count, 0)

    async def test_source_done_uses_application_statistics(self):
        app = LiveRecallApplication()
        class Source:
            def __aiter__(self):
                async def messages():
                    yield '{"type":"SOURCE_DONE"}'
                return messages()
        output = io.StringIO()
        with redirect_stdout(output):
            await handle_source(Source(), {'session': 'L1'},
                                app.process_source_update, app.caption_state)
        self.assertIn('accepted=0', output.getvalue())
        self.assertIn('rejected=0', output.getvalue())

    async def test_close_before_sender_start_releases_connection(self):
        ws = Socket()
        client = ClientSession(ws, LiveRecallApplication().final_history, [])
        client.start()
        await client.close()  # Cancel before the new task gets a turn.
        self.assertTrue(ws.closed.is_set())
        self.assertTrue(client.sender_task.done())

    async def test_storage_failure_keeps_application_state_retryable(self):
        app = LiveRecallApplication()
        app.final_history.max_items = 0
        with self.assertRaises(OverflowError):
            await app.process_source_update(caption(1, 3, True).to_dict())
        self.assertEqual(app.caption_state.highest_finalized_segment, 0)
        self.assertEqual(len(app.final_history), 0)

    async def test_applications_do_not_share_global_state(self):
        a, b = LiveRecallApplication(), LiveRecallApplication()
        await a.process_source_update(caption(1, 3, True).to_dict())
        self.assertEqual(len(a.final_history), 1)
        self.assertEqual(len(b.final_history), 0)


if __name__ == '__main__':
    unittest.main()
