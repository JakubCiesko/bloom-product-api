import asyncio 
import logging
from app.stats import compute_and_store_stats
from app.services.recommender import RecommenderBase

logger = logging.getLogger('uvicorn.info')

class Updater:
    def __init__(self, stats_refresh_time:int=300, recommender_refresh_time:int=500):
        self.stats_refresh_time = stats_refresh_time
        self.recommender_refresh_time = recommender_refresh_time
    
    async def periodic_stats_update(self):
        while True:
            await self.update_stats()
            await asyncio.sleep(self.stats_refresh_time) 
    
    async def periodic_recommender_update(self, recommender: RecommenderBase):
        while True:
            await self.update_recommender(recommender)
            await asyncio.sleep(self.stats_refresh_time) 
    
    async def update_recommender(self, recommender: RecommenderBase):
        try:
            logger.info(f"Reinitializing recommender: {type(recommender).__name__}")
            await recommender._initialize()
            logger.info(f"Reinitialization finished [{type(recommender).__name__}].")
        except Exception as e:
            logger.error(f"Recommender could not be updated: {e}")
    
    async def update_stats(self): 
        try:
            logger.info("Updating stats.")
            await compute_and_store_stats()
            logger.info("Stats updated.")
        except Exception as e:
            logger.error(f"Stats could not be updated: {e}")

