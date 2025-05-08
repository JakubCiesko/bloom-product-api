import asyncio 
import logging
from app.stats import compute_and_store_stats

logger = logging.getLogger('uvicorn.info')

async def periodic_stats_updater():
    while True:
        try:
            logger.info("Updating stats.")
            await compute_and_store_stats()
            logger.info("Stats updated.")
        except Exception as e:
            logger.error(f"Stats could not be updated: {e}")
        await asyncio.sleep(300) 