import asyncio
from email import message
from enum import Enum, auto

from server.config import CLIENT_QUEUE_MAXSIZE
from server.protocol import OutgoingMessage
from collections import deque

class AddResult(Enum):
    """Represents the outcome of adding a message to a SemanticQueue"""

    ENQUEUED = 1 # message added to queue normally
    COALESCED = 2 # new message added, make room for the new message by removing either removing its own provisional OR by removing 1 oldest provisional segment
    DROPPED_PROVISIONAL = 3 # new message isn't added as all messages in the queue are Final/HISTORY message
    OVERFLOW = 4
    CLOSED = 5


class SemanticQueue:
    """Bounded queue with overload handling"""

    def __init__(self, max_size: int = CLIENT_QUEUE_MAXSIZE):
        if max_size <= 0:
            raise ValueError("max_size must be positive number")

        self.max_size= max_size
        self.items: deque[OutgoingMessage] = deque() # use deque instead of [] so that all insert/delete takes O(1)

        # wake up signal for reading tasks that are waiting for new message to arrive to the queue
        # used in get() method as caller will wait if there is no message in the queue
        # need this to wake the caller up once there is queue is no longer empty
        self.not_empty_event = asyncio.Event()

        # Useful for experiments and debugging
        self.coalesced_count = 0
        self.dropped_provisional_count = 0
        self.overflow_count = 0


    @property
    def size(self):
        return len(self.items)

    @staticmethod
    def is_provisional(message: OutgoingMessage):
        return message.get("type") == "CAPTION_UPDATE" and message.get("final") is False

    def _append(self, message: OutgoingMessage) -> None:
        self.items.append(message)
        self.not_empty_event.set() # wake up sending Task that is waiting for new item in the queue





    def add_message(self, new_message: OutgoingMessage):
        """Add message into the queue without waiting
        
        May remove the provisional segments in the queue if
        the queue if almost full, i.e. client is overloaded

        - Normal condition will keep all segments revision
        - Overload condition will remove some provisional segment 
          before removing all provisional segment
        """

        if self.size < self.max_size: # queue not full, add normally
            self._append(new_message)
            return AddResult.ENQUEUED


        # queue is FULL !!!

        # if queue is full and the message is HISTORY -> overflow
        if new_message["type"] == "HISTORY":
            # HISTORY is a recovery message and must not be dropped
            self.overflow_count += 1
            return AddResult.OVERFLOW

        # new message is not final segment
        if new_message["final"] is False:
            # 1) remove older provisional revision of this segment
            removed_count = self._remove_matching(
                lambda msg: (
                    msg["type"] == "CAPTION_UPDATE" 
                    and msg["final"] is False
                    and msg["segment"] == new_message["segment"]
                )
            )
            if removed_count > 0:
                self._append(new_message)
                self.coalesced_count += removed_count
                return AddResult.COALESCED

            # 2) if there is no older revision of this segment, then try to make room by
            #    removing one Oldest provisional segment --> won't affect user experience that much
            if self._remove_oldest_provisional_segment():
                self._append(new_message)
                self.coalesced_count += 1
                return AddResult.COALESCED

            # 3) Don't have any provisional segment in the queue currently, all are Final segment / HISTORY message.
            #    Drop the current new_message as it is provisional
            self.dropped_provisional_count += 1
            return AddResult.DROPPED_PROVISIONAL


        # else: new_message is Final

        # Final segment supersedes all queued revision for this segmen
        removed_count = self._remove_matching(
            lambda msg: (
                msg["type"] == "CAPTION_UPDATE" 
                and msg["final"] is False
                and msg["segment"] == new_message["segment"]
            )
        )

        # queue is still full, remove one oldest provisional
        if self.size >= self.max_size:
            if self._remove_oldest_provisional_segment():
                removed_count += 1

        if self.size < self.max_size: # manage to free up at least one space
            self._append(new_message)

            if removed_count > 0:
                self.coalesced_count += removed_count
                return AddResult.COALESCED

            else:
                return AddResult.ENQUEUED # in rare case where the queue got freed up mid-execution without removing any message

        # Cant remove any provisional message and queue is still full of Final/History messages --> overflow
        self.overflow_count += 1
        return AddResult.OVERFLOW



    async def get_message(self) -> OutgoingMessage:
        """Retrive and remove rhe next message in the queue
        
        Blocks asynchronously if the queue is empty, waiting until a new message is added.
        Behave like asyncio.Queue().get()
        """
        while True:
            if self.items:
                return self.items.popleft()

            self.not_empty_event.clear() # set the event flag back to False

            # recheck again after clearing event flag to avoid missed wake up
            if self.items:
                continue

            # asyncio Task will be suspended here until not_empty_event.set() is called,
            # then the while loop will resume
            await self.not_empty_event.wait()





    # ------- helper function :) -----
    
    def _remove_matching(self, predicate) -> int:
        """Remove matching items and return the number of removed items"""
        original_size = self.size
        self.items = deque(
            message
            for message in self.items
            if not predicate(message)
        )
        removed_count = original_size - self.size
        return removed_count


    def _remove_oldest_provisional_segment(self) -> bool:
        """Try to remove one single oldest provisional segment
        
        Return True if manage to found one and remove it, False otherwise
        """

        removed = False
        retained_items: deque[OutgoingMessage] = deque()

        while self.items:
            msg = self.items.popleft() # pop the oldest segment

            if not removed and self.is_provisional(msg): # found one oldest provisional segment
                removed = True
                continue # dont add it to the queue, i.e remove it from the queue

            retained_items.append(msg)

        self.items = retained_items
        return removed


        
