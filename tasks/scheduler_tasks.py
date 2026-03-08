import asyncio
import schedule
import time

from backend.brain.master_brain import MasterBrain
from backend.services.email.email_pipeline import EmailPipeline

brain = MasterBrain()
pipeline = EmailPipeline()


async def autonomous_cycle():

    print("🤖 Running autonomous AI cycle...")

    # Observe world
    email_summary = pipeline.process_new_email()

    # Think
    result = await brain.think(
        "autonomous_system_cycle",
        {
            "source": "scheduler",
            "emails": email_summary
        }
    )

    print("🧠 Brain Decision:", result)


def start_scheduler():

    print("✅ AI Scheduler Started")

async def loop_runner():
    MAX_CYCLES = 1000

    for _ in range(MAX_CYCLES):
        try:
            await autonomous_cycle()
        except Exception as e:
            print("Scheduler error:", e)

        await asyncio.sleep(600)


if __name__ == "__main__":
    start_scheduler()