import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.base import BaseEstimator, RegressorMixin
from src.model.architectures.two_tower import TwoTower


class TwoTowerModel(BaseEstimator, RegressorMixin):

    def __init__(
        self,
        user_features,
        movie_features,
        embedding_dim=64,
        learning_rate=0.001,
        epochs=10,
        batch_size=1024
    ):
        self.user_features = user_features
        self.movie_features = movie_features

        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size

        self.model = TwoTower(
            embedding_dim=embedding_dim
        )

    def _build_inputs(self, X):

        # Get user features according to userId
        user_input = (
            self.user_features
            .loc[X["userId"]]
            .to_numpy(dtype=np.float32)
        )

        # Get movie features according to movieId
        movie_input = (
            self.movie_features
            .loc[X["movieId"]]
            .to_numpy(dtype=np.float32)
        )

        return {
            "user": user_input,
            "movie": movie_input
        }

    def fit(self, X, y):

        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=self.learning_rate
            ),
            loss="mse",
            metrics=[
                tf.keras.metrics.RootMeanSquaredError()
            ]
        )

        inputs = self._build_inputs(X)

        self.model.fit(
            inputs,
            np.asarray(y, dtype=np.float32),
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.2,
            verbose=1
        )

        return self

    def predict(self, X):

        inputs = self._build_inputs(X)

        predictions = self.model(inputs, training=False).numpy()

        return predictions.ravel()
    
    def find_recommendations(self, user_ids, num_of_recomands=20):
        
        user_input = (
            self.user_features
            .loc[user_ids]
            .to_numpy(dtype=np.float32)
        )


        user_embeddings = self.model.user_tower(
            user_input
        )

        movie_embeddings = self.model.movie_tower(
            self.movie_features.to_numpy(dtype=np.float32)
        )

        scores = tf.matmul(
            user_embeddings,
            movie_embeddings,
            transpose_b=True
        )

        top_movies = tf.math.top_k(
            scores,
            k=num_of_recomands
        )

        recommendations = []

        for i, user_id in enumerate(user_ids):

            movie_indices = top_movies.indices[i].numpy()

            movie_ids = self.movie_features.index[
                movie_indices
            ]

            recommendations.append(
                (user_id, movie_ids)
            )

        return recommendations

