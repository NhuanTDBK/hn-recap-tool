"""Access control for the Telegram bot: allowlist and per-user rate limit.

Registered as an outer middleware on ``Dispatcher.update`` so a rejected update never reaches a
handler, the FSM storage or a database session.
"""

import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)

_MAX_TRACKED_USERS = 10_000


def parse_id_list(raw: str | None) -> frozenset[int]:
    """Parse a comma/space separated list of Telegram ids. Bad tokens are skipped with a warning."""
    ids: set[int] = set()
    for token in (raw or "").replace(",", " ").split():
        try:
            ids.add(int(token))
        except ValueError:
            logger.warning("Ignoring invalid Telegram id in allowlist: %r", token)
    return frozenset(ids)


class AccessControlMiddleware(BaseMiddleware):
    """Drop updates from users who are not allowed, and from users sending too fast.

    Rules:
      * Updates in the configured group chat are always allowed (members cannot be listed by id).
      * Updates in any other non-private chat are dropped.
      * Private chats are allowed when ``allowed_user_ids`` is empty (open mode, logged at startup)
        or the sender is in ``allowed_user_ids``.
      * Every allowed sender is limited to ``max_per_minute`` updates in a sliding 60 second window
        (0 disables the limit).
    """

    WINDOW_SECONDS = 60.0

    def __init__(
        self,
        allowed_user_ids: Iterable[int] = (),
        group_chat_id: int | None = None,
        max_per_minute: int = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.allowed_user_ids = frozenset(allowed_user_ids)
        self.group_chat_id = group_chat_id
        self.max_per_minute = max_per_minute
        self._clock = clock
        self._hits: dict[int, deque[float]] = {}

        if self.allowed_user_ids:
            logger.info("Bot access control: %d allowed user(s)", len(self.allowed_user_ids))
        else:
            logger.warning(
                "Bot access control is OPEN: TELEGRAM_ALLOWED_USER_IDS is empty, so anyone who finds the "
                "bot can register. Set it to restrict direct messages."
            )

    def is_allowed(self, user_id: int | None, chat_id: int | None, chat_type: str | None) -> bool:
        """Return True when this sender in this chat may use the bot."""
        if user_id is None:
            return False
        if self.group_chat_id is not None and chat_id == self.group_chat_id:
            return True
        if chat_type != "private":
            return False
        return not self.allowed_user_ids or user_id in self.allowed_user_ids

    def is_rate_limited(self, user_id: int) -> bool:
        """Record one update for ``user_id`` and return True if it is over the limit."""
        if self.max_per_minute <= 0:
            return False
        now = self._clock()
        hits = self._hits.setdefault(user_id, deque())
        while hits and now - hits[0] > self.WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= self.max_per_minute:
            return True
        hits.append(now)
        if len(self._hits) > _MAX_TRACKED_USERS:
            self._prune(now)
        return False

    def _prune(self, now: float) -> None:
        for uid in [u for u, h in self._hits.items() if not h or now - h[-1] > self.WINDOW_SECONDS]:
            del self._hits[uid]

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        chat = data.get("event_chat")
        user_id = getattr(user, "id", None)

        if not self.is_allowed(user_id, getattr(chat, "id", None), getattr(chat, "type", None)):
            logger.info("Dropped update from unauthorised sender (chat_type=%s)", getattr(chat, "type", None))
            return None

        if self.is_rate_limited(user_id):
            logger.warning("Rate limit hit for user_id=%s", user_id)
            callback = getattr(event, "callback_query", None)
            if callback is not None:
                try:
                    await callback.answer("Too many requests, slow down.")
                except Exception:  # noqa: BLE001 - best effort, the update is dropped either way
                    logger.debug("Could not answer rate-limited callback", exc_info=True)
            return None

        return await handler(event, data)
