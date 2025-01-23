from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app import sessionmanager, get_settings
from app.sync import sync_chain
from datetime import datetime
import asyncio


async def main():
    scheduler = AsyncIOScheduler()
    settings = get_settings()

    sessionmanager.init(settings.database.endpoint)

    scheduler.add_job(
        sync_chain, "interval", minutes=1, next_run_time=datetime.now()
    )

    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
