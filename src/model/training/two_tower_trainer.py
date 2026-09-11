from more_itertools import one
import numpy as np
import pandas as pd
import tensorflow as tf
from src.model.architectures.two_tower import TwoTower
from datetime import date   
import pickle
import os 

class TwoTowerTrainer:
    def __init__(self, user_features, movie_features, embedding_dim=64, learning_rate=0.001,epochs=5,batch_size=1024):
        self.user_features = user_features
        self.movie_features = movie_features
        self.epochs = epochs
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim

        default_user_vec = np.mean(self.user_features.values, axis=0, keepdims=True)
        default_movie_vec = np.mean(self.movie_features.values, axis=0, keepdims=True)

        full_user_matrix = np.vstack([default_user_vec, self.user_features.values])
        full_movie_matrix = np.vstack([default_movie_vec, self.movie_features.values])

        self._user_tensor = tf.constant(full_user_matrix, dtype=tf.float32)
        self._movie_tensor = tf.constant(full_movie_matrix, dtype=tf.float32)

        user_keys = (
            self.user_features.index.values.astype(np.int32)
            if self.user_features.index.name == 'userId' or 'userId' not in self.user_features.columns
            else self.user_features['userId'].values.astype(np.int32)
        )
        movie_keys = (
            self.movie_features.index.values.astype(np.int32)
            if self.movie_features.index.name == 'movieId' or 'movieId' not in self.movie_features.columns
            else self.movie_features['movieId'].values.astype(np.int32)
        )

        self._user_id_to_idx = tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(
                keys=tf.constant(user_keys, dtype=tf.int32),
                values=tf.constant(np.arange(1, len(self.user_features) + 1), dtype=tf.int32)
            ),
            default_value=0
        )
        
        self._movie_id_to_idx = tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(
                keys=tf.constant(movie_keys, dtype=tf.int32),
                values=tf.constant(np.arange(1, len(self.movie_features) + 1), dtype=tf.int32)
            ),
            default_value=0
        )

        self.model = TwoTower(embedding_dim=embedding_dim)
        self.learning_rate = learning_rate

    def _prepare_batch(self, features, label=None):
        """A map function that converts CSV IDs into features during streaming."""
        
        user_ids = tf.cast(features["userId"], tf.int32)
        movie_ids = tf.cast(features["movieId"], tf.int32)

        user_indices = self._user_id_to_idx.lookup(user_ids)
        movie_indices = self._movie_id_to_idx.lookup(movie_ids)

        inputs = {
            "user": tf.gather(self._user_tensor, user_indices),
            "movie": tf.gather(self._movie_tensor, movie_indices)
        }

        if label is not None:
            return inputs, tf.cast(label, tf.float32)
        return inputs

    def fit(self, dataset, validation_data=None):
        """Train the model on the given tf.data.Dataset"""
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=[tf.keras.metrics.RootMeanSquaredError()]
        )

        train_ds = (
            dataset
            .map(self._prepare_batch, num_parallel_calls=tf.data.AUTOTUNE)
            .prefetch(tf.data.AUTOTUNE)
        )

        val_ds = None
        if validation_data is not None:
            val_ds = (
                validation_data
                .map(self._prepare_batch, num_parallel_calls=tf.data.AUTOTUNE)
                .prefetch(tf.data.AUTOTUNE)
            )

        return self.model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=self.epochs,
            batch_size=self.batch_size,
        )



    def save_model(self, save_dir="artifacts"):
        today = date.today().strftime("%Y-%m-%d")
        model_path = f"{save_dir}/two_tower_model_{today}/"
        os.makedirs(model_path, exist_ok=True)
        self.model.save_weights(os.path.join(model_path, "weights.weights.h5"))

        metadata = {
            "user_features": self.user_features,
            "movie_features": self.movie_features,
            "embedding_dim": self.embedding_dim,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size
        }
        metadata_path = os.path.join(model_path, "metadata.pkl")
        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)
