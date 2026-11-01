from server.client_session import AddResult, ClientSession
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
        
    def publish(self, message: CaptionUpdateMessage) -> list[ClientSession]:
        """Offer each client a new live message, if client can't receive the message, then discard the client.

        Returns: client sessions to be closed
        """

        clients_to_close: list[ClientSession] = []

        for client in tuple(self.client_list):
            result = client.offer(message)

            if result in {
                AddResult.ENQUEUED,
                AddResult.COALESCED,
            }:
                continue

            # AddResult.CLOSE or OVERFLOW -> disconnect client
            self.client_list.discard(client)
            clients_to_close.append(client)

        return clients_to_close



