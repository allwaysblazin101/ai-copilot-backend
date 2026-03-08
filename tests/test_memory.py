import asyncio
from backend.memory.persistent_memory import PersistentMemoryStore


def test_memory():

    mem = PersistentMemoryStore()

    print(mem.recall_recent())


if __name__ == "__main__":
    test_memory()