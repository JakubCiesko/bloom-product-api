import random
import numpy as np 
from abc import ABC, abstractmethod
from aiocache import cached, SimpleMemoryCache
from sklearn.metrics.pairwise import cosine_similarity
from app.db import (
    events_collection, 
    products_collection
)


class RecommenderBase(ABC):
    """Abstract base class for all recommenders.""" 
    @abstractmethod
    def recommend(self, *args, **kwargs) -> list[int]: 
        """Generate a list of recommended product IDs.""" 
        pass
    
    @abstractmethod
    async def _initialize(self, *args, **kwargs):
        """Asynchronously initialize the recommender. Typically used for loading data or building matrices required for recommendation logic."""
        pass

class CoOccurenceRecommender(RecommenderBase):
    """Recommender that suggests products based on co-occurrence frequency in user sessions. Uses a smoothed probability matrix to generate recommendations."""
    def __init__(self, alpha_smoothing:float=1.0):
        self.alpha_smoothing = alpha_smoothing
        self.n_products = 0
        self.matrix = np.array([])
        self.probability_matrix = np.array([])
        self.i_to_product_id = dict()

    async def _initialize(self):
        """Initialize the co-occurrence matrix and probability matrix based on event data."""
        self.n_products = await self._get_distinct_products_count()
        self.matrix = np.zeros((self.n_products, self.n_products))
        await self._aggregate_data()
        self.calculate_probability_matrix()

    async def _get_distinct_products_count(self) -> int:
        """Get the number of distinct products from the database."""
        distinct_ids = await products_collection.distinct("id")
        self.i_to_product_id = {
            i: product_id for i, product_id in enumerate(distinct_ids)
        }
        self.product_id_to_i = {
            product_id: i for i, product_id in enumerate(distinct_ids)
        }
        return len(distinct_ids)

    async def _aggregate_data(self):
        """Aggregate event data to compute product co-occurrence."""
        pipeline = [
            {"$group": {
                "_id": "$user_id",  
                "products": {"$push": "$product_id"}
            }}
        ]
        cursor = events_collection.aggregate(pipeline)
        async for user_data in cursor:
            products = user_data["products"]
            self._update_matrix(products)

    def _update_matrix(self, products: list[int]):
        """Update the co-occurrence matrix with product pairs from a user session.

        Args:
            products (list[int]): List of product IDs viewed by the user."""
        for i in range(len(products)):
            for j in range(i + 1, len(products)):
                p1, p2 = products[i], products[j]
                self.matrix[p1, p2] += 1
                self.matrix[p2, p1] += 1

    def calculate_probability_matrix(self) -> np.array:
        """Returns a smoothed probability matrix P(j|i) using additive smoothing."""
        prob_matrix = np.zeros_like(self.matrix)
        for i in range(self.n_products):
            row = self.matrix[i]
            total_interactions = np.sum(row)
            prob_matrix[i] = (row + self.alpha_smoothing) / (total_interactions + self.alpha_smoothing * self.n_products)
        self.probability_matrix = prob_matrix
        return prob_matrix
    
    def get_probability_matrix(self) -> np.array:
        """Return the current probability matrix."""
        return self.probability_matrix

    async def recommend(self, product_id: int, top_n=5, sample:bool=False, **kwargs) -> list[int]:
        """
        Recommend products based on co-occurrence with a given product.

        Args:
            product_id (int): Reference product ID.
            top_n (int): Number of recommendations to return.
            sample (bool): If True, return random recommendations.

        Returns:
            list[int]: List of recommended product IDs.
        """
        prob_matrix = self.get_probability_matrix()
        product_i = self.product_id_to_i[product_id]
        product_probs = prob_matrix[product_i]
        if sample: 
            idx = random.sample(range(self.n_products), top_n)
            return [self.i_to_product_id[i] for i in idx]
        recommended_ids = np.argsort(product_probs)[::-1]
        recommendations = []
        for rec_id in recommended_ids:
            if rec_id != product_i:
                recommendations.append(rec_id)
            if len(recommendations) >= top_n:
                break
        return [self.i_to_product_id[i] for i in recommendations]


class UserBasedCollaborativeRecommender(RecommenderBase):
    """Recommender based on user-user collaborative filtering.
    Computes similarity between users based on their interactions and recommends
    products preferred by similar users."""

    def __init__(self):
        self.user_ids = []
        self.product_ids = []
        self.user_to_i = {}
        self.product_to_i = {}
        self.i_to_user = {}
        self.i_to_product = {}
        self.user_item_matrix = np.array([])
        self.similarity_matrix = np.array([])

    async def _initialize(self):
        """Load user and product data, construct the user-item interaction matrix, and compute the user similarity matrix."""
        await self._load_users_and_products()
        await self._build_user_item_matrix()
        self._compute_similarity_matrix()
    
    async def _load_users_and_products(self):
        """Load distinct users and products from the database and prepare index mappings."""
        user_ids = await events_collection.distinct("user_id")
        product_ids = await products_collection.distinct("id")

        self.user_ids = user_ids
        self.product_ids = product_ids

        self.user_to_i = {uid: i for i, uid in enumerate(user_ids)}
        self.product_to_i = {pid: i for i, pid in enumerate(product_ids)}
        self.i_to_user = {i: uid for uid, i in self.user_to_i.items()}
        self.i_to_product = {i: pid for pid, i in self.product_to_i.items()}

        self.user_item_matrix = np.zeros((len(user_ids), len(product_ids)))

    async def _build_user_item_matrix(self):
        """Populate the user-item matrix based on interaction events."""
        async for event in events_collection.find({}):
            user_id = event["user_id"]
            product_id = event["product_id"]
            if user_id in self.user_to_i and product_id in self.product_to_i:
                i = self.user_to_i[user_id]
                j = self.product_to_i[product_id]
                self.user_item_matrix[i, j] += 1
    
    def _compute_similarity_matrix(self):
        """Compute cosine similarity between all user vectors."""
        try: 
            self.similarity_matrix = cosine_similarity(self.user_item_matrix)
        except Exception as e: 
            pass

    @cached(ttl=300, cache=SimpleMemoryCache)
    async def recommend(self, user_id: int, top_n: int = 5, **kwargs) -> list[int]:
        """Recommend products for a user based on user similarity scores.
        Args:
            user_id (int): The user ID to generate recommendations for.
            top_n (int): Number of products to return.
            sample (bool): If True, sample recommendations randomly (currently unused).
            product_id (int): Not used in this model.

        Returns:
            list[int]: List of recommended product IDs.
        """
        if user_id not in self.user_to_i:
            return []
        
        user_i = self.user_to_i[user_id]
        user_similarities = self.similarity_matrix[user_i]

        # Get top similar users (excluding self)
        similar_users = np.argsort(user_similarities)[::-1]
        similar_users = [i for i in similar_users if i != user_i]

        scores = np.zeros(len(self.product_ids))
        for sim_i in similar_users:
            sim_score = user_similarities[sim_i]
            scores += sim_score * self.user_item_matrix[sim_i]
        interacted_items = self.user_item_matrix[user_i] > 0
        scores[interacted_items] = -1  

        top_items = np.argsort(scores)[::-1][:top_n]
        return [self.i_to_product[i] for i in top_items if scores[i] > 0]
