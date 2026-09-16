from model.architectures.research_architectures.two_tower_model import TwoTowerModel
import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from src.model.utils.utils import *


def learning():
    
    movies,ratings = load_kaggle()

    users_features = build_user_genre_profile_matrix(movies, ratings)

    X_train, X_test, y_train, y_test = train_test_split(
        ratings[["userId", "movieId"]],
        ratings["rating"],
        test_size=0.2,
        random_state=42
    )

    embedding_dim = 32
    batch_size = 4 * 1024
    epochs = 7
    learning_rate = 3e-3

    print("Training Two-Tower Model...")
    model = TwoTowerModel(
        user_features=users_features,
        movie_features=movies,
        epochs=epochs,
        batch_size=batch_size,
        embedding_dim=embedding_dim,
        learning_rate=learning_rate
    )
    model.fit(X_train, y_train)
    testing(model, X_train, y_train, X_test, y_test)
    return model, users_features.index.to_numpy()

def testing(model, X_train,y_train, X_test, y_test):
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
    
    train_rmse = np.sqrt(np.mean((train_predictions - y_train) ** 2))
    test_rmse = np.sqrt(np.mean((test_predictions - y_test) ** 2))

    print(f"Train RMSE: {train_rmse:.4f}")
    print(f"Test RMSE: {test_rmse:.4f}")


def benchmark_throughput(model, available_user_ids, batch_size=64, num_batches=200):
    """
    Benchmark the throughput of the model by simulating multiple requests for recommendations.

    """
    print("\n===========================================================================")
    print(f"Starting Benchmark: {num_batches} requests | Batch size: {batch_size} users/request")
    print("===========================================================================\n")

    latencies_ms = []
    total_users_processed = 0

    dummy_users = np.random.choice(available_user_ids, size=batch_size, replace=True)
    _ = model.find_recommendations(dummy_users)

    global_start_time = time.perf_counter()

    for _ in range(num_batches):
        # 1. sample users
        batch_users = np.random.choice(available_user_ids, size=batch_size, replace=True)

        # 2. time the request
        req_start = time.perf_counter()
        _ = model.find_recommendations(batch_users)
        req_end = time.perf_counter()

        latency = (req_end - req_start) * 1000  # convert to ms
        latencies_ms.append(latency)
        total_users_processed += batch_size

    global_end_time = time.perf_counter()
    total_duration_sec = global_end_time - global_start_time

    # compute throughput metrics
    rps = num_batches / total_duration_sec
    users_per_sec = total_users_processed / total_duration_sec

    # compute latency percentiles
    p50 = np.percentile(latencies_ms, 50)
    p95 = np.percentile(latencies_ms, 95)
    p99 = np.percentile(latencies_ms, 99)
    avg_lat = np.mean(latencies_ms)

    # print the results
    print("📊 PERFORMANCES REPORT:")
    print(f"  • Total Time Elapsed     : {total_duration_sec:.2f} seconds")
    print(f"  • Total Requests Processed: {num_batches}")
    print(f"  • Total Users Served      : {total_users_processed:,}")
    print(f"--------------------------------------------------")
    print(f"🚀 THROUGHPUT:")
    print(f"  • Requests Per Second (RPS): {rps:.2f} req/sec")
    print(f"  • Users Per Second (UPS)   : {users_per_sec:.2f} users/sec")
    print(f"--------------------------------------------------")
    print(f"⏱️ LATENCY DISTRIBUTION:")
    print(f"  • Average Latency : {avg_lat:.2f} ms")
    print(f"  • P50 (Median)    : {p50:.2f} ms")
    print(f"  • P95             : {p95:.2f} ms")
    print(f"  • P99 (Tail)      : {p99:.2f} ms")
    print("===========================================================================")


def main():
    model, available_user_ids = learning()
    batch_sizes = [32,64,128,256]
    for batch_size in batch_sizes:
        print(f"\n\nBenchmarking with batch size: {batch_size}")
        print("--------------------------------------------------")
        benchmark_throughput(model, available_user_ids, batch_size=batch_size, num_batches=200)
    


if __name__ == "__main__":
    main()