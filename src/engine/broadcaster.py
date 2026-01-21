import asyncio
from typing import List
import threading

class MessageBroadcaster:
    """
    Bridge between synchronous scraper threads and asynchronous WebSocket clients.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MessageBroadcaster, cls).__new__(cls)
                cls._instance.subscribers = []
                cls._instance.loop = None
        return cls._instance

    def set_loop(self, loop):
        """Set the main event loop"""
        self.loop = loop

    def broadcast_sync(self, message: str):
        """Called from sync threads to broadcast message"""
        if self.loop and self.subscribers:
            # Schedule the broadcast on the main loop
            asyncio.run_coroutine_threadsafe(self._broadcast_async(message), self.loop)

    async def _broadcast_async(self, message: str):
        """Internal async broadcast"""
        to_remove = []
        for queue in self.subscribers:
            try:
                queue.put_nowait(message)
            except Exception:
                to_remove.append(queue)
        
        for queue in to_remove:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

    def subscribe(self) -> asyncio.Queue:
        """Add a new subscriber and return their queue"""
        queue = asyncio.Queue()
        with self._lock:
            self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber"""
        with self._lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

# Global instance
broadcaster = MessageBroadcaster()