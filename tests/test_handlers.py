import asyncio
import html
import pytest
from types import SimpleNamespace

from bot import handlers


class DummyMessage:
    def __init__(self):
        self.sent = None

    async def reply_html(self, text):
        # store reply for assertions
        self.sent = text


class DummyUpdate:
    def __init__(self):
        self.message = DummyMessage()
        self.effective_chat = SimpleNamespace(id=12345)
        self.effective_user = SimpleNamespace(id=67890)


class DummyContext:
    def __init__(self):
        self.args = []
        self.user_data = {}


@pytest.mark.asyncio
async def test_start_command_sends_help_message():
    update = DummyUpdate()
    context = DummyContext()
    await handlers.start_command(update, context)
    assert update.message.sent is not None
    assert "Привет" in update.message.sent
    assert "/find_net" in update.message.sent or "find_net" in update.message.sent
    assert "/add_data" in update.message.sent or "add_data" in update.message.sent
