import tensorflow as tf


class UserTower(tf.keras.layers.Layer):
    def __init__(self, num_buckets=50000, embedding_dim=64, **kwargs):
        super().__init__(**kwargs)
        self.hashing = tf.keras.layers.Hashing(num_bins=num_buckets)
        self.user_embedding = tf.keras.layers.Embedding(num_buckets, embedding_dim)

        self.network = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(embedding_dim)
        ])

    def call(self, inputs):
        user_ids = inputs["user_id"]
        hashed_ids = self.hashing(user_ids)
        x = self.user_embedding(hashed_ids)
        return self.network(x)


class MovieTower(tf.keras.layers.Layer):
    def __init__(self, movie_buckets=20000, genre_buckets=100, embedding_dim=64, **kwargs):        
        super().__init__(**kwargs)
        self.movie_hashing = tf.keras.layers.Hashing(num_bins=movie_buckets)
        self.genre_hashing = tf.keras.layers.Hashing(num_bins=genre_buckets)
        
        self.movie_embedding = tf.keras.layers.Embedding(movie_buckets, embedding_dim)
        self.genre_embedding = tf.keras.layers.Embedding(genre_buckets, embedding_dim)
        
        self.network = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(embedding_dim)
        ])

    def call(self, inputs):
        hashed_movie_ids = self.movie_hashing(inputs["movie_id"])
        movie_emb = self.movie_embedding(hashed_movie_ids)

        hashed_genre_ids = self.genre_hashing(inputs["genre_ids"])
        genre_emb = self.genre_embedding(hashed_genre_ids)
        genre_emb_mean = tf.reduce_mean(genre_emb, axis=1)
        combined = movie_emb + genre_emb_mean
        return self.network(combined)


class TwoTower(tf.keras.Model):
    def __init__(self, user_bucket=50000, movie_bucket=20000, genre_buckets=100, embedding_dim=64, **kwargs):
        super().__init__(**kwargs)
        self.user_tower = UserTower(user_bucket, embedding_dim)
        self.movie_tower = MovieTower(movie_bucket, genre_buckets, embedding_dim)

    def call(self, inputs):
        user_embedding = self.user_tower(inputs)
        movie_embedding = self.movie_tower(inputs)

        score = tf.reduce_sum(user_embedding * movie_embedding, axis=1)
        return score