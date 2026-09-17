import numpy as np
import pandas as pd
import tensorflow as tf
from src.model.architectures.production_architectures.two_tower import TwoTower
import pickle
import os 

class TwoTowerRecommender:
    def __init__(self, path):
        weights_path = os.path.join(path, "weights.weights.h5")
        metadata_path = os.path.join(path, "metadata.pkl")

        if not os.path.isfile(weights_path) or not os.path.isfile(metadata_path):
            raise FileNotFoundError("Model artifacts not found.")

        with open(metadata_path, "rb") as f:
            self.metadata = pickle.load(f)

        self.user_bucket = self.metadata["user_bucket"]
        self.movie_bucket = self.metadata["movie_bucket"]
        self.genre_bucket = self.metadata["genre_bucket"]
        self.embedding_dim = self.metadata["embedding_dim"]

        self.model = TwoTower(
            user_bucket=self.metadata["user_bucket"],
            movie_bucket=self.metadata["movie_bucket"],
            genre_buckets=self.metadata["genre_bucket"],
            embedding_dim=self.metadata["embedding_dim"]
        )

        # for buiding the model
        dummy_inputs = {
            "user_id": tf.zeros([1], dtype=tf.int32),
            "movie_id": tf.zeros([1], dtype=tf.int32),
            "genre_ids": tf.ragged.constant([[1]], dtype=tf.int64),
            "avg_rating_arr": tf.ragged.constant([[3.0]], dtype=tf.float32)
        }
        self.model(dummy_inputs)

        self.model.load_weights(weights_path)

    def predict(self, users_data, movies_data):
        user_emb, movie_emb = self.model.get_embeddings(users_data, movies_data)
        scores = tf.reduce_sum(user_emb * movie_emb, axis=1)
        return scores.numpy()


    def score_recommendations(self,users_data,movies_data):
        user_embeddings, movie_embeddings = self.model.get_embeddings(users_data,movies_data)
        return np.dot(user_embeddings.numpy(), movie_embeddings.numpy().T)

    def get_top_recommendations(self, users_data,movies_data, top_k=20):
        scores = self.score_recommendations(users_data,movies_data)

        recommendations = {}
        movie_ids = movies_data["movie_id"].numpy() if hasattr(movies_data["movie_id"], "numpy") else np.array(movies_data["movie_id"])
        user_ids = users_data["user_id"].numpy() if hasattr(users_data["user_id"], "numpy") else np.array(users_data["user_id"])
        for i, user_id in enumerate(user_ids):
            user_scores = scores[i]
            
            top_indices = np.argsort(user_scores)[::-1][:top_k]
            
            top_movie_ids = movie_ids[top_indices]
            top_scores = user_scores[top_indices]
            
            recommendations[user_id] = list(zip(top_movie_ids, top_scores))
            
        return recommendations
    