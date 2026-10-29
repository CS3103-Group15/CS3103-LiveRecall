"""Register client sessions and publish work without waiting on sockets."""
import json

from server.client_session import ClientSession
from server.protocol import CaptionUpdateMessage


class DeliveryHub:
    def __init__(self):
        self.client_list: set[ClientSession] = set()

    @property
    def client_count(self):
        return len(self.client_list)

    def register_client(self, new_client: ClientSession) -> None:
        if new_client.is_closed:
            raise ValueError("Cannot register a closed client session")
        self.client_list.add(new_client)

    def unregister_client(self, client: ClientSession) -> None:
        self.client_list.discard(client)

    def publish(self, caption_update_msg: CaptionUpdateMessage) -> None:
        raw = json.dumps(caption_update_msg)
        for client in tuple(self.client_list):
            # enqueue records failure and wakes the client's own sender, which
            # closes on failure. Keep registration until detach cleans it up;
            # never silently unregister an otherwise connected client.
            client.enqueue(caption_update_msg, raw)
