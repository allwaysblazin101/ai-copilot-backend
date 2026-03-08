
import asyncio
from backend.brain.master_brain import MasterBrain
from backend.services.email.email_pipeline import EmailPipeline


brain = MasterBrain()
pipeline = EmailPipeline()


async def autonomous_cycle():

    print("🤖 Autonomous AI cycle running...")

    email_summary = pipeline.process_new_email()

    result = await brain.think(
        "system_autonomous_cycle",
        {
            "source": "scheduler",
            "emails": email_summary
        }
    )

    print("🧠 AI Decision:", result)


async def loop_runner():

    while True:

        try:
            await autonomous_cycle()

        except Exception as e:
            print("Cycle error:", e)

        # Run every 10 minutes
        await asyncio.sleep(600)


if name == "main":

    asyncio.run(loop_runner())

