import pytest
from backend.brain.master_brain import MasterBrain


@pytest.mark.asyncio
async def test_brain():

    brain = MasterBrain()

    print("\nTesting brain thinking...")

    result = await brain.think(
        "Hello AI, test email planning and productivity",
        {
            "sentiment": 0.7
        }
    )

    print(result)

    assert "reply_text" in result