from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio


def init_scheduler():
    scheduler = AsyncIOScheduler()

    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    init_scheduler()
