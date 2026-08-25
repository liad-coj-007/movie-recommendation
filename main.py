import joblib
from two_tower_model import TwoTowerModel
import time
import pandas as pd
import os
import numpy as np

from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
import kagglehub

PATH = kagglehub.dataset_download(
    "grouplens/movielens-20m-dataset"
)


def read_movies(movies):
    mlb = MultiLabelBinarizer()

   

    genre_features = mlb.fit_transform(
        movies['genres'].str.split('|')
    )

    genre_df = pd.DataFrame(
        genre_features,
        columns=mlb.classes_,
        index=movies["movieId"]
    )

    return genre_df


def read_user_matrix(movies,ratings):
    user_genre = ratings.merge(
         movies,
         left_on="movieId",
         right_index=True
     )
    genre_columns = movies.columns.to_list()
    user_genre_matrix = pd.DataFrame(index=user_genre["userId"].unique())
    
    for genre in genre_columns:
        user_genre_matrix[genre] = (
            user_genre[user_genre[genre] == 1]
            .groupby("userId")["rating"]
            .mean()
        )
    genre_means = user_genre_matrix.mean()
    user_genre_matrix = user_genre_matrix.fillna(genre_means)
    return user_genre_matrix




def learning():
    movies_raw = pd.read_csv(
        os.path.join(PATH,"movie.csv")
    )
    
    movies = read_movies(movies_raw)
    ratings = pd.read_csv(os.path.join(PATH,"rating.csv"),nrows=1_000_000)

    users_features = read_user_matrix(movies,ratings)

    X_train, X_test, y_train, y_test = train_test_split(
        ratings[["userId", "movieId"]],
        ratings["rating"],
        test_size=0.2,
        random_state=42
    )
    
    learning_rates = [
        1e-4,
        3e-4,
        1e-3,
        3e-3,
        1e-2
    ]

    embedding_dim = 32
    batch_size = 4*1024
    epochs = 7
    model = TwoTowerModel(user_features=users_features,movie_features=movies,
                        epochs=epochs,batch_size=batch_size,embedding_dim=embedding_dim,
                        learning_rate= learning_rates[3])
    model.fit(X_train,y_train)
    return model
   


def main():
    model = learning()
    start = time.perf_counter()
    result = model.find_recommendations([i for i in range(1,65)])
    end = time.perf_counter()
    print("===========================================================================")
    print(result)
    print(f"Latency: {(end-start)*1000:.2f} ms")

if __name__ == "__main__":
    main()
