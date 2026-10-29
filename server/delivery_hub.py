from pydoc import cli

from server.client_session import ClientSession
from server.state import CaptionUpdateMessage

class DeliveryHub:
    """Manage client sessions and updates each client's outgoing queue
    
    Does not invoke websocket send method, it is handled by ClientSession"""

    def __init__(self):
        self.client_list: set[ClientSession] = set()

    @property
    def client_count(self):
        return len(self.client_list)

    def register_client(self, new_client: ClientSession) -> None:
        """Register a new client for future live updates"""

        if new_client.is_closed:
            raise ValueError("Cannot register a closed client session")

        self.client_list.add(new_client)

    def unregister_client(self, client: ClientSession) -> None:
        """Stop delivering live updates to client
        
        Does not close client websocket connection, only remove client
        from the client list
        """
        self.client_list.discard(client)
        
    def publish(self, caption_update_msg: CaptionUpdateMessage) -> list[ClientSession]:
        """Only insert the message into the queue of each client
        
        Does not send packet to client thru websocket

        Returns clients that could not accept the message because their session
        is closed or their outgoing queue is full.
        """

        overflow_clients = []

        # use tuple() to make sure it doesnt crash when the client_list changes due to some clients disconnecting
        for client in tuple(self.client_list):
            if client.enqueue(caption_update_msg):
                continue

            # fail to enqueue due to queue is full or session is closed -- for stage 5, need to change in stage 6!!!
            self.client_list.discard(client)
            overflow_clients.append(client)

        return overflow_clients



