import tensorflow as tf


class UserTower(tf.keras.Model):

    def __init__(self, embedding_dim=64):
        super().__init__()

        self.network = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(embedding_dim)
        ])

    def call(self, x):
        return self.network(x)


class MovieTower(tf.keras.Model):

    def __init__(self, embedding_dim=64):
        super().__init__()

        self.network = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(embedding_dim)
        ])

    def call(self, x):
        return self.network(x)

    
class TwoTower(tf.keras.Model):

    def __init__(self, embedding_dim=64):
        super().__init__()

        self.user_tower = UserTower(embedding_dim)
        self.movie_tower = MovieTower(embedding_dim)

    def call(self, inputs):

        user_features = inputs["user"]
        movie_features = inputs["movie"]

        user_embedding = self.user_tower(user_features)
        movie_embedding = self.movie_tower(movie_features)

        score = tf.reduce_sum(
            user_embedding * movie_embedding,
            axis=1
        )

        return score