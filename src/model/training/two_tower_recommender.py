import numpy as np
import pandas as pd
import tensorflow as tf
from model.architectures.research_architectures.two_tower import TwoTower
import pickle
import os 

class TwoTowerRecommender:
    def __init__(self, path):
        weights_path = os.path.join(path, "weights.weights.h5")
        metadata_path = os.path.join(path, "metadata.pkl")

        if not os.path.isfile(weights_path) or not os.path.isfile(metadata_path):
            raise FileNotFoundError("Model artifacts not found.")

        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)

        self.user_features = metadata["user_features"]
        self.movie_features = metadata["movie_features"]
        self.embedding_dim = metadata["embedding_dim"]

        default_user_vec = np.mean(self.user_features.values, axis=0, keepdims=True)
        default_movie_vec = np.mean(self.movie_features.values, axis=0, keepdims=True)

        full_user_matrix = np.vstack([default_user_vec, self.user_features.values])
        full_movie_matrix = np.vstack([default_movie_vec, self.movie_features.values])

        self._user_tensor = tf.Variable(full_user_matrix, dtype=tf.float32)
        self._movie_tensor = tf.Variable(full_movie_matrix, dtype=tf.float32)

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

        self._movie_id_list = [-1] + list(movie_keys)

        self._user_lookup = tf.lookup.experimental.MutableHashTable(
            key_dtype=tf.int32, value_dtype=tf.int32, default_value=0
        )
        self._user_lookup.insert(
            tf.constant(user_keys, dtype=tf.int32),
            tf.constant(np.arange(1, len(self.user_features) + 1), dtype=tf.int32)
        )
        
        self._movie_lookup = tf.lookup.experimental.MutableHashTable(
            key_dtype=tf.int32, value_dtype=tf.int32, default_value=0
        )
        self._movie_lookup.insert(
            tf.constant(movie_keys, dtype=tf.int32),
            tf.constant(np.arange(1, len(self.movie_features) + 1), dtype=tf.int32)
        )

        self.model = TwoTower(embedding_dim=self.embedding_dim)
        self.model.build({
            "user": (None, self.user_features.shape[1]),
            "movie": (None, self.movie_features.shape[1])
        })
        self.model.load_weights(weights_path)

    def get_user_embedding(self, user_ids, new_users_features=None):
        if new_users_features is not None:
            user_feats = tf.convert_to_tensor(new_users_features, dtype=tf.float32)
        else:
            u_idx = self._user_lookup.lookup(tf.constant(user_ids, dtype=tf.int32))
            user_feats = tf.gather(self._user_tensor, u_idx)

        return self.model.user_tower(user_feats)

    def add_new_movie(self, movie_id: int, movie_features: np.ndarray):
        """ add a new movie to the recommender system with its features. """
        movie_feat_tensor = tf.convert_to_tensor([movie_features], dtype=tf.float32)

        self._movie_tensor = tf.concat([self._movie_tensor, movie_feat_tensor], axis=0)
        
        new_idx = tf.shape(self._movie_tensor)[0] - 1

        self._movie_lookup.insert(
            keys=tf.constant([movie_id], dtype=tf.int32),
            values=tf.constant([new_idx], dtype=tf.int32)
        )

        self._movie_id_list.append(int(movie_id))

    def predict(self, user_ids, movie_ids):
        user_ids = tf.cast(user_ids, tf.int32)
        movie_ids = tf.cast(movie_ids, tf.int32)

        u_idx = self._user_lookup.lookup(user_ids)
        m_idx = self._movie_lookup.lookup(movie_ids)

        inputs = {
            "user": tf.gather(self._user_tensor, u_idx),
            "movie": tf.gather(self._movie_tensor, m_idx)
        }
        return self.model(inputs, training=False).numpy()

    def get_top_recommendations(self, user_ids, top_k=20):
        user_ids_arr = np.array(user_ids, dtype=np.int32)
        
        u_idx = self._user_lookup.lookup(tf.constant(user_ids_arr, dtype=tf.int32))
        user_feats = tf.gather(self._user_tensor, u_idx)

        user_embeddings = self.model.user_tower(user_feats)
        movie_embeddings = self.model.movie_tower(self._movie_tensor)

        scores = tf.matmul(user_embeddings, movie_embeddings, transpose_b=True)

        oov_mask = tf.one_hot(0, depth=tf.shape(scores)[1], on_value=-1e9, off_value=0.0)
        scores = scores + oov_mask

        _, top_indices = tf.math.top_k(scores, k=top_k)
        top_indices_np = top_indices.numpy()

        all_movie_ids = np.array(self._movie_id_list)

        recommendations = {}
        for i, user_id in enumerate(user_ids_arr):
            recommendations[int(user_id)] = all_movie_ids[top_indices_np[i]].tolist()
        return recommendations