import pytest

from backend.brain.master_brain import MasterBrain


@pytest.mark.asyncio
async def test_brain():
    brain = MasterBrain()

    print("\nTesting brain thinking...")

    result = await brain.process_query(
        "Hello AI, test email planning and productivity",
        user_id="test_user",
    )

    print(result)

    assert isinstance(result, dict)
    assert "answer" in result