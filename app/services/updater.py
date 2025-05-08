import asyncio 
import logging
from app.stats import compute_and_store_stats
from app.services.recommender import RecommenderBase

logger = logging.getLogger('uvicorn.info')



class Updater:
    def __init__(self, stats_refresh_time:int=300, recommender_refresh_time:int=500):
        self.stats_refresh_time = stats_refresh_time
        self.recommender_refresh_time = recommender_refresh_time
    
    async def periodic_stats_updater(self):
        while True:
            try:
                logger.info("Updating stats.")
                await compute_and_store_stats()
                logger.info("Stats updated.")
            except Exception as e:
                logger.error(f"Stats could not be updated: {e}")
            await asyncio.sleep(self.stats_refresh_time) 
    
    async def periodic_recommender_updater(self, recommender: RecommenderBase):
        while True:
            try:
                logger.info(f"Reinitializing recommender: {type(recommender).__name__}")
                await recommender._initialize()
                logger.info(f"Reinitialization finished [{type(recommender).__name__}].")
            except Exception as e:
                logger.error(f"Recommender could not be updated: {e}")
            await asyncio.sleep(self.stats_refresh_time) 