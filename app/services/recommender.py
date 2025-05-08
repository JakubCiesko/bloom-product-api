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
    @abstractmethod
    def recommend(self, *args, **kwargs) -> list[int]: 
        """Recommends products""" 
        pass
    
    @abstractmethod
    async def _initialize(self, *args, **kwargs):
        """Async initializer of recommender. Used for periodic reinizialitazion"""
        pass

class CoOccurenceRecommender(RecommenderBase):
    def __init__(self, alpha_smoothing:float=1.0):
        self.alpha_smoothing = alpha_smoothing
        self.n_products = 0
        self.matrix = np.array([])
        self.probability_matrix = np.array([])
        self.i_to_product_id = dict()

    async def _initialize(self):
        self.n_products = await self._get_distinct_products_count()
        self.matrix = np.zeros((self.n_products, self.n_products))
        await self._aggregate_data()
        self.calculate_probability_matrix()

    async def _get_distinct_products_count(self) -> int:
        distinct_ids = await products_collection.distinct("id")
        self.i_to_product_id = {
            i: product_id for i, product_id in enumerate(distinct_ids)
        }
        self.product_id_to_i = {
            product_id: i for i, product_id in enumerate(distinct_ids)
        }
        return len(distinct_ids)

    async def _aggregate_data(self):
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
        for i in range(len(products)):
            for j in range(i + 1, len(products)):
                p1, p2 = products[i], products[j]
                self.matrix[p1, p2] += 1
                self.matrix[p2, p1] += 1

    def calculate_probability_matrix(self) -> np.array:
        """
        Returns a smoothed probability matrix P(j|i) using additive smoothing
        """
        prob_matrix = np.zeros_like(self.matrix)
        for i in range(self.n_products):
            row = self.matrix[i]
            total_interactions = np.sum(row)
            prob_matrix[i] = (row + self.alpha_smoothing) / (total_interactions + self.alpha_smoothing * self.n_products)
        self.probability_matrix = prob_matrix
        return prob_matrix
    
    def get_probability_matrix(self) -> np.array:
        return self.probability_matrix

    async def recommend(self, product_id: int, top_n=5, sample:bool=False, user_id:int=None) -> list[int]:
        """
        Recommend top_n products given a product_id based on the smoothed probability matrix
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
        await self._load_users_and_products()
        await self._build_user_item_matrix()
        self._compute_similarity_matrix()
    
    async def _load_users_and_products(self):
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
        async for event in events_collection.find({}):
            user_id = event["user_id"]
            product_id = event["product_id"]
            if user_id in self.user_to_i and product_id in self.product_to_i:
                i = self.user_to_i[user_id]
                j = self.product_to_i[product_id]
                self.user_item_matrix[i, j] += 1
    
    def _compute_similarity_matrix(self):
        self.similarity_matrix = cosine_similarity(self.user_item_matrix)
    
    @cached(ttl=300, cache=SimpleMemoryCache)
    async def recommend(self, user_id: int, top_n: int = 5, sample: bool=False, product_id: int=None) -> list[int]:
        """
        Recommend products for a given user based on user similarity.
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