from src.model.training.two_tower_recommender import TwoTowerRecommender
from src.model.utils.utils import *
from datetime import date  
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf

def evaluate_predictions(predictor, ratings_df, sample_size=100_000, max_movies_for_eval=10000):
    sample = ratings_df.sample(n=min(sample_size, len(ratings_df)), random_state=42)
    
    unique_movies = sample.drop_duplicates(subset=["movieId"]).head(max_movies_for_eval)
    sample = sample[sample["movieId"].isin(unique_movies["movieId"])].reset_index(drop=True)
    
    if len(sample) == 0:
        sample = ratings_df.head(100) 

    users_data = {
        "user_id": sample["userId"].values.astype(np.int64),
        "genre_ids": tf.ragged.constant(sample.get("user_genre_ids", [[1]] * len(sample)), dtype=tf.int64),
        "avg_rating_arr": tf.ragged.constant(sample.get("avg_rating_arr", [[3.0]] * len(sample)), dtype=tf.float32)
    }
    
    movies_data = {
        "movie_id": sample["movieId"].values.astype(np.int64),
        "genre_ids": tf.ragged.constant(sample.get("movie_genre_ids", [[1]] * len(sample)), dtype=tf.int64)
    }

    y_true = sample["rating"].values

    y_pred = predictor.predict(users_data, movies_data).flatten()

    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))

    return {"RMSE": rmse, "MAE": mae}


def evaluate_hit_rate(predictor, train_df, test_df, num_users=500, top_k=20, min_rating=4.0, max_eval_movies=1000):
    """
    evaluate_hit_rate: Evaluates the hit rate of the recommender system.
    """
    test_high = test_df[test_df["rating"] >= min_rating]
    
    eval_users_ids = np.intersect1d(train_df["userId"].unique(), test_high["userId"].unique())
    if len(eval_users_ids) > num_users:
        eval_users_ids = eval_users_ids[:num_users]

    users_subset = train_df[train_df["userId"].isin(eval_users_ids)].drop_duplicates(subset=["userId"])
    
    users_data = {
        "user_id": users_subset["userId"].values.astype(np.int64),
        "genre_ids": tf.ragged.constant(users_subset.get("user_genre_ids", [[1]] * len(users_subset)), dtype=tf.int64),
        "avg_rating_arr": tf.ragged.constant(users_subset.get("avg_rating_arr", [[3.0]] * len(users_subset)), dtype=tf.float32)
    }

    movies_subset = test_df.drop_duplicates(subset=["movieId"]).head(max_eval_movies)
    movies_data = {
        "movie_id": movies_subset["movieId"].values.astype(np.int64),
        "genre_ids": tf.ragged.constant(movies_subset.get("movie_genre_ids", [[1]] * len(movies_subset)), dtype=tf.int64)
    }

    hits = 0
    total = len(eval_users_ids)

    raw_recommendations = predictor.get_top_recommendations(users_data, movies_data, top_k=top_k + 150)

    train_seen_map = train_df.groupby("userId")["movieId"].apply(set).to_dict()
    test_liked_map = test_high.groupby("userId")["movieId"].apply(set).to_dict()

    for user_id in eval_users_ids:
        seen_in_train = train_seen_map.get(user_id, set())
        actual_test_liked = test_liked_map.get(user_id, set())

        user_recs_raw = raw_recommendations.get(user_id, [])
        user_recs = [m_id for m_id, score in user_recs_raw if m_id not in seen_in_train][:top_k]

        if set(user_recs).intersection(actual_test_liked):
            hits += 1

    hit_rate = hits / total if total > 0 else 0.0
    return hit_rate


def testing(dir="artifacts"):
    today = date.today().strftime("%Y-%m-%d")
    model_path = f"{dir}/two_tower_model_{today}/"
    recommender = TwoTowerRecommender(model_path)
    _ , ratings = load_kaggle()
    
    start_time = time.time()
    evaluation_metrics = evaluate_predictions(recommender, ratings)
    end_time = time.time()
    print(f"Evaluation Metrics: {evaluation_metrics}")
    print(f"Evaluation Time: {end_time - start_time:.2f} seconds")
    
    train_df, test_df = train_test_split(ratings, test_size=0.2, random_state=42)
    
    start_time = time.time()
    evaluation_hit_rate = evaluate_hit_rate(
            predictor=recommender,
            train_df=train_df,
            test_df=test_df,
            num_users=500,
            top_k=20
        )    
    end_time = time.time()
    print(f"Hit Rate @ 20: {evaluation_hit_rate:.4f}")
    print(f"Hit Rate Time: {end_time - start_time:.2f} seconds")

    
if __name__ == "__main__":
    testing()