import asyncio
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._user_sockets: Dict[int, Set[WebSocket]] = {}
        self._conversation_sockets: Dict[int, Set[WebSocket]] = {}
        self._socket_metadata: Dict[WebSocket, tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, conversation_id: int, user_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            if user_id not in self._user_sockets:
                self._user_sockets[user_id] = set()
            self._user_sockets[user_id].add(websocket)

            if conversation_id not in self._conversation_sockets:
                self._conversation_sockets[conversation_id] = set()
            self._conversation_sockets[conversation_id].add(websocket)

            self._socket_metadata[websocket] = (conversation_id, user_id)

        logger.info(f"User {user_id} connected to conversation {conversation_id}.")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            metadata = self._socket_metadata.pop(websocket, None)
            if not metadata:
                return

            conversation_id, user_id = metadata

            if conversation_id in self._conversation_sockets:
                self._conversation_sockets[conversation_id].discard(websocket)
                if not self._conversation_sockets[conversation_id]:
                    del self._conversation_sockets[conversation_id]

            if user_id in self._user_sockets:
                self._user_sockets[user_id].discard(websocket)
                if not self._user_sockets[user_id]:
                    del self._user_sockets[user_id]
                    logger.info(f"User {user_id} went OFFLINE.")

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self._user_sockets and len(self._user_sockets[user_id]) > 0

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)
            return False

    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        delivered = 0
        sockets = list(self._user_sockets.get(user_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(message)
                delivered += 1
            except Exception as e:
                logger.warning(f"Error sending message to user {user_id}: {e}")
                await self.disconnect(ws)
        return delivered

    async def broadcast_to_conversation(
        self,
        conversation_id: int,
        message: Dict[str, Any],
        exclude_socket: WebSocket | None = None,
    ) -> int:
        delivered = 0
        sockets = list(self._conversation_sockets.get(conversation_id, set()))
        for ws in sockets:
            if exclude_socket and ws == exclude_socket:
                continue
            try:
                await ws.send_json(message)
                delivered += 1
            except Exception as e:
                logger.warning(f"Error broadcasting to conversation {conversation_id}: {e}")
                await self.disconnect(ws)
        return delivered


manager = ConnectionManager()
