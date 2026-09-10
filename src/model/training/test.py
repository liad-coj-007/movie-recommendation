from src.model.architectures.two_tower_model import TwoTowerModel
import kagglehub
import pandas as pd
import os
from src.model.utils.utils import *
from datetime import date  
import time
from sklearn.model_selection import train_test_split
import numpy as np
from tensorflow import keras

def loading(dir="artifacts"):
    movies,ratings = load_kaggle()
    user_matrix = build_user_genre_profile_matrix(movies, ratings)
    model = TwoTowerModel(
        user_features=user_matrix,
        movie_features=movies,
        embedding_dim=32,
        learning_rate=3e-3,
        epochs=7,
        batch_size=4 * 1024
    )
    today = date.today().strftime("%Y-%m-%d")
    path = os.path.join(dir, f"two_tower_model_{today}.keras")
    model.model.load_weights(path)
    return model 

def testing():
    model = loading()
    movies,ratings = load_kaggle()
    X_train, X_test, y_train, y_test = train_test_split(
        ratings[["userId", "movieId"]],
        ratings["rating"],
        test_size=0.2,
        random_state=42
    )
    print("Evaluating model on test set...")
    start_train_time = time.time()
    train_predictions = model.predict(X_train)
    end_train_time = time.time()
    train_duration = end_train_time - start_train_time
    print(f"Train prediction time: {train_duration:.2f} seconds")
    start_test_time = time.time()
    test_predictions = model.predict(X_test)
    end_test_time = time.time()
    test_duration = end_test_time - start_test_time
    print(f"Test prediction time: {test_duration:.2f} seconds")
    print(f"Train prediction time: {train_duration:.2f} seconds")

    print(f"Train RMSE: {np.sqrt(np.mean((train_predictions - y_train) ** 2)):.4f}")
    print(f"Test RMSE: {np.sqrt(np.mean((test_predictions - y_test) ** 2)):.4f}")

if __name__ == "__main__":
    testing()