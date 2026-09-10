
from src.model.architectures.two_tower_trainer import TwoTowerTrainer
import kagglehub
import pandas as pd
import os
from src.model.utils.utils import *
 





def learning():
    ratings_path = kagglehub.dataset_download("grouplens/movielens-20m-dataset") + "/rating.csv"
    movies,ratings = load_kaggle()
    user_matrix = build_user_genre_profile_matrix(movies, ratings)
    LIMIT_ROWS = 500_000
    BATCH_SIZE = 2048
    num_batches = LIMIT_ROWS // BATCH_SIZE

    ratings_ds = tf.data.experimental.make_csv_dataset(
        ratings_path,
        batch_size=BATCH_SIZE,
        label_name="rating",
        num_epochs=1,
        ignore_errors=True,
        select_columns=["userId", "movieId", "rating"]
    )
    
    ratings_ds = ratings_ds.take(num_batches)

    model = TwoTowerTrainer(
        user_features=user_matrix,
        movie_features=movies,
        embedding_dim=32,
        learning_rate=3e-3,
        epochs=5,
        batch_size=4 * 1024
    )

    model.fit(ratings_ds, validation_data=None)
    return model





if __name__ == "__main__":
    model = learning()
    print("Training completed successfully.")
    model.save_model(save_dir="artifacts")
    print("Model saved successfully.")