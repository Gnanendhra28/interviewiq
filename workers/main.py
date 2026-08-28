import asyncio

from apps.api.app.core.logging import logger, setup_logging
from workers.tasks import process_queued_jobs

setup_logging()


async def main():
    logger.info("Starting InterviewIQ Background Worker Process...")
    while True:
        try:
            await process_queued_jobs()
        except Exception as e:
            logger.error(f"Error in worker main loop: {e}")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
