# backend/cron/daily_briefing.py
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.brain.master_brain import MasterBrain
from backend.services.email.email_pipeline import EmailPipeline
from backend.tools.tool_router import ToolRouter
from backend.config.settings import settings
from backend.utils.logger import logger

async def run_morning_briefing():
    """The automated 8:00 AM routine."""
    logger.info("🌅 Starting Daily Morning Briefing...")
    
    brain = MasterBrain()
    email_pipe = EmailPipeline()
    router = ToolRouter()
    
    # 1. Process Emails (Trash spam, find important ones)
    email_data = email_pipe.process_new_email()
    
    # 2. Get AI Insights (Calendar + Proactive Plan)
    # We send a 'dummy' message to trigger the Brain's planning logic
    brain_result = await brain.think("Give me my morning briefing.")
    
    # 3. Construct the SMS
    agenda = "\n".join(brain_result.get("proactive_plan", ["No events today."]))
    email_summary = f"📧 Emails: {email_data['important_count']} important messages."
    
    final_sms = (
        f"☀️ GOOD MORNING CO-PILOT\n\n"
        f"{agenda}\n\n"
        f"{email_summary}\n"
        f"Check your inbox for details."
    )
    
    # 4. Send via Twilio
    router.execute("send_sms", {
        "to": settings.owner_number,
        "body": final_sms
    })
    logger.success("Morning Briefing SMS sent!")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Schedule for 8:00 AM every day
    scheduler.add_job(run_morning_briefing, 'cron', hour=8, minute=0)
    scheduler.start()
    logger.info("Scheduler started: Daily Briefing set for 08:00")

if __name__ == "__main__":
    # For manual testing
    asyncio.run(run_morning_briefing())
