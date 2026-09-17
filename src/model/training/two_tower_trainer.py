
import tensorflow as tf
from src.model.architectures.production_architectures.two_tower import TwoTower
from datetime import date   
import pickle
import os
import pandas as pd
import numpy as np

## generator function
def parquet_generator(data_dir="data_chunks", batch_size=1024):
    """
    get the Parquet files in batches
    """
    files = sorted(
        [
            os.path.join(data_dir, f)
            for f in os.listdir(data_dir)
            if f.endswith(".parquet")
        ]
    )

    for file_path in files:
        df = pd.read_parquet(file_path)
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]

            avg_ratings_float = [[float(val) for val in row_list] for row_list in batch["avg_rating_arr"]]

            features = {
                "user_id": batch["user_id"].values.astype(np.int64),
                "movie_id": batch["movie_id"].values.astype(np.int64),
                "genre_ids": tf.ragged.constant(batch["genre_ids"].tolist(), dtype=tf.int64),
                "avg_rating_arr" : tf.ragged.constant(avg_ratings_float, dtype=tf.float32)
            }
            
            labels = batch["rating"].values.astype(np.float32)
            yield features, labels

class TwoTowerTrainer:
    def __init__(self, user_bucket=50000, movie_bucket=20000, genre_buckets=100,
                 embedding_dim=64, learning_rate=0.001,epochs=5,batch_size=1024):
        self.user_bucket = user_bucket
        self.movie_bucket = movie_bucket
        self.genre_bucket = genre_buckets
        self.epochs = epochs
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim
        self.model = TwoTower(user_bucket,movie_bucket,genre_buckets,embedding_dim=embedding_dim)
        self.learning_rate = learning_rate

    def _process_features(self, features, label=None):
        inputs = {
            "user_id": tf.cast(features["user_id"], tf.int32),
            "movie_id": tf.cast(features["movie_id"], tf.int32),
            "genre_ids": features["genre_ids"],
            "avg_rating_arr" : features["avg_rating_arr"] 
        }

        if label is not None:
            return inputs,tf.cast(label,tf.float32)
        
        return inputs


    def fit(self,generator_fn=parquet_generator):
        """Train the model on the given tf.data.Dataset"""

        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=[tf.keras.metrics.RootMeanSquaredError()]
        )

        output_signature = (
            {
                "user_id": tf.TensorSpec(shape=(None,), dtype=tf.int64),
                "movie_id": tf.TensorSpec(shape=(None,), dtype=tf.int64),
                "genre_ids": tf.RaggedTensorSpec(shape=(None, None), dtype=tf.int64),
                "avg_rating_arr" : tf.RaggedTensorSpec(shape=(None,None),dtype=tf.float32)

            },
            tf.TensorSpec(shape=(None,), dtype=tf.float32)
        )



        train_ds = (
            tf.data.Dataset.from_generator(
                lambda:generator_fn(batch_size=self.batch_size),
                output_signature=output_signature
            )
            .map(self._process_features, num_parallel_calls=tf.data.AUTOTUNE)
            .prefetch(tf.data.AUTOTUNE)  
        )

        return self.model.fit(
            train_ds,
            epochs=self.epochs
        )



    def save_model(self, save_dir="artifacts"):

        today = date.today().strftime("%Y-%m-%d")
        model_path = f"{save_dir}/two_tower_model_{today}/"
        os.makedirs(model_path, exist_ok=True)
        self.model.save_weights(os.path.join(model_path, "weights.weights.h5"))

        metadata = {
            "user_bucket": self.user_bucket,
            "movie_bucket" : self.movie_bucket,
            "genre_bucket" : self.genre_bucket,
            "embedding_dim": self.embedding_dim,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size
        }
        metadata_path = os.path.join(model_path, "metadata.pkl")
        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)
