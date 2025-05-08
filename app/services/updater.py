import asyncio 
import logging
from app.stats import compute_and_store_stats
from app.services.recommender import RecommenderBase

logger = logging.getLogger('uvicorn.info')

class Updater:
    """Handles periodic updating of system components such as statistics and recommenders.
    
    Attributes:
        stats_refresh_time (int): Interval (in seconds) between statistics updates.
        recommender_refresh_time (int): Interval (in seconds) between recommender reinitializations.
    """
    def __init__(self, stats_refresh_time:int=300, recommender_refresh_time:int=500):
        """Initialize the Updater with specified refresh intervals.

        Args:
            stats_refresh_time (int): Time interval between stats updates (default: 300s).
            recommender_refresh_time (int): Time interval between recommender updates (default: 500s).
        """
        self.stats_refresh_time = stats_refresh_time
        self.recommender_refresh_time = recommender_refresh_time
    
    async def periodic_stats_update(self):
        """Periodically update system statistics at the configured interval."""
        while True:
            await self.update_stats()
            await asyncio.sleep(self.stats_refresh_time) 
    
    async def periodic_recommender_update(self, recommender: RecommenderBase):
        """Periodically reinitialize the given recommender at the configured interval.

        Args:
            recommender (RecommenderBase): The recommender instance to update."""
        while True:
            await self.update_recommender(recommender)
            await asyncio.sleep(self.stats_refresh_time) 
    
    async def update_recommender(self, recommender: RecommenderBase):
        """Immediately reinitialize the provided recommender.

        Args:
            recommender (RecommenderBase): The recommender instance to initialize."""
        try:
            logger.info(f"Reinitializing recommender: {type(recommender).__name__}")
            await recommender._initialize()
            logger.info(f"Reinitialization finished [{type(recommender).__name__}].")
        except Exception as e:
            logger.error(f"Recommender could not be updated: {e}")
    
    async def update_stats(self): 
        """Immediately compute and store updated statistics."""
        try:
            logger.info("Updating stats.")
            await compute_and_store_stats()
            logger.info("Stats updated.")
        except Exception as e:
            logger.error(f"Stats could not be updated: {e}")

