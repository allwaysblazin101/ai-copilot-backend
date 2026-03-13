import pytest

from backend.memory.persistent_memory import PersistentMemoryStore


@pytest.mark.asyncio
async def test_memory():
    mem = PersistentMemoryStore()

    result = await mem.recall_recent(user_id="test_user")
    print(result)

    assert result is not None