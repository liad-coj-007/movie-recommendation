
import os

from sklearn.preprocessing import MultiLabelBinarizer
import pandas as pd
import kagglehub
import numpy as np

def read_movies(movies):
    mlb = MultiLabelBinarizer()
    genre_features = mlb.fit_transform(movies['genres'].str.split('|'))
    genre_df = pd.DataFrame(
        genre_features,
        columns=mlb.classes_,
        index=movies["movieId"]
    )
    return genre_df


def build_user_genre_profile_matrix(movies, ratings):
    """
    building a user-genre profile matrix where each row corresponds to 
    a user and each column corresponds to a genre. 
    The values in the matrix represent the average rating given 
    by the user to movies of that genre.
    """
    
    genre_cols = movies.columns.tolist()
    
    merged = ratings[['userId', 'movieId', 'rating']].merge(
        movies[genre_cols], left_on='movieId', right_index=True, how='inner'
    )
    
    weighted_genres = merged[genre_cols].values * merged['rating'].values[:, None]
    
    grouped_sum = pd.DataFrame(weighted_genres, index=merged['userId'], columns=genre_cols).groupby('userId').sum()
    grouped_count = merged.groupby('userId')[genre_cols].sum()
    
    user_genre_matrix = grouped_sum / grouped_count.replace(0, np.nan)
    
    genre_means = user_genre_matrix.mean()
    user_genre_matrix = user_genre_matrix.fillna(genre_means)
    
    return user_genre_matrix


def load_kaggle(sample_size_for_matrix=500_000):
    PATH = kagglehub.dataset_download("grouplens/movielens-20m-dataset")

    movies_raw = pd.read_csv(os.path.join(PATH, "movie.csv"))
    movies = read_movies(movies_raw)
    ratings = pd.read_csv(os.path.join(PATH, "rating.csv"),
                          nrows=sample_size_for_matrix,
                          usecols=["userId", "movieId", "rating"])

    return movies, ratings


  