from src.model.training.two_tower_recommender import TwoTowerRecommender
import kagglehub
import pandas as pd
import os
from src.model.utils.utils import *
from datetime import date  
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

def evaluate_predictions(predictor, ratings_df, sample_size=100_000):
    sample = ratings_df.sample(n=min(sample_size, len(ratings_df)), random_state=42)
    
    user_ids = sample["userId"].values
    movie_ids = sample["movieId"].values
    y_true = sample["rating"].values

    y_pred = predictor.predict(user_ids, movie_ids).flatten()

    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))

    return {"RMSE": rmse, "MAE": mae}


import numpy as np
import pandas as pd

def evaluate_hit_rate(predictor, train_df, test_df, num_users=500, top_k=20, min_rating=4.0):
    """
    evaluate_hit_rate: Evaluates the hit rate of the recommender system.
    A hit is counted if at least one of the top_k recommended movies for a user is
    present in the user's liked movies in the test set (movies with rating >= min_rating).
    The function returns the hit rate, which is the ratio of users with at least one hit
    to the total number of evaluated users.
    """
    test_high = test_df[test_df["rating"] >= min_rating]
    
    eval_users = np.intersect1d(train_df["userId"].unique(), test_high["userId"].unique())
    if len(eval_users) > num_users:
        eval_users = eval_users[:num_users]

    hits = 0
    total = len(eval_users)

    raw_recommendations = predictor.get_top_recommendations(eval_users, top_k=top_k + 150)

    train_seen_map = train_df.groupby("userId")["movieId"].apply(set).to_dict()
    test_liked_map = test_high.groupby("userId")["movieId"].apply(set).to_dict()

    for user_id in eval_users:
        seen_in_train = train_seen_map.get(user_id, set())
        actual_test_liked = test_liked_map.get(user_id, set())

        user_recs = [m for m in raw_recommendations[user_id] if m not in seen_in_train][:top_k]

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