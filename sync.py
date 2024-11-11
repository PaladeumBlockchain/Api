from datetime import datetime
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.sync import sync_chain


def init_scheduler():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        sync_chain, "interval", minutes=1, next_run_time=datetime.now()
    )

    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    init_scheduler()
