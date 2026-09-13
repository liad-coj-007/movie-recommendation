import os
import pandas as pd
import kagglehub
from tqdm import tqdm
from src.model.utils import *
from src.data_pipeline.dataset import *


def get_movie_genre_ids(movies_df: pd.DataFrame, genres_df: pd.DataFrame) -> pd.DataFrame:
    """
    return df of (movie_id, genre_id)
    """
    exploded_df = movies_df[['movie_id', 'genres']].copy()
    exploded_df['genre_name'] = exploded_df['genres'].str.split('|')
    exploded_df = exploded_df.explode('genre_name')
    
    exploded_df = exploded_df.dropna(subset=['genre_name'])
    exploded_df = exploded_df[exploded_df['genre_name'] != '(no genres listed)']
    
    result_df = exploded_df.merge(genres_df, on='genre_name', how='inner')
    
    return result_df[['movie_id', 'genre_id']]


def read_movies(path):
    movies = pd.read_csv(os.path.join(path, "movie.csv"))
    movies = movies.rename(columns={
            'movieId': 'movie_id',
            'title': 'title'
    })
    extracted_years = movies['title'].str.extract(r'\((\d{4})\)')[0]
    movies["release_date"] = pd.to_datetime(extracted_years, format='%Y', errors='coerce').dt.date
    movies["release_date"] = movies["release_date"].fillna(pd.to_datetime("1970-01-01").date())

    return movies


def load_movies_to_sql(conn, path):
    print(" Loading movies, genres, and mappings...")
    movies = read_movies(path)
    genre_map = {
        'Action': 1, 'Adventure': 2, 'Animation': 3, 'Children': 4,
        'Comedy': 5, 'Crime': 6, 'Documentary': 7, 'Drama': 8,
        'Fantasy': 9, 'Film-Noir': 10, 'Horror': 11, 'Musical': 12,
        'Mystery': 13, 'Romance': 14, 'Sci-Fi': 15, 'Thriller': 16,
        'War': 17, 'Western': 18, 'IMAX': 19
    }
    genres = pd.DataFrame(list(genre_map.items()), columns=['genre_name', 'genre_id'])

    insert_table(conn, "movies", movies, ["movie_id", "title", "release_date"])
    insert_table(conn, "genres", genres, ["genre_id", "genre_name"])
    
    movies_genres_df = get_movie_genre_ids(movies, genres)

    insert_table(conn, "movie_genres", movies_genres_df, ["movie_id", "genre_id"], conflict_target=["movie_id", "genre_id"])


def load_users_to_sql(conn, path: str, chunk_size=1000000):
    ratings_path = os.path.join(path, "rating.csv")
    print("👤 Generating and inserting synthetic users from rating.csv...")
    chunks = pd.read_csv(ratings_path, chunksize=chunk_size, usecols=['userId'])
    
    
    estimated_chunks = 40  
    
    for i, chunk in enumerate(tqdm(chunks, desc="👥 Processing Users", total=estimated_chunks, unit="chunk")):
        unique_users = chunk['userId'].drop_duplicates().to_frame()
        unique_users = unique_users.rename(columns={'userId': 'user_id'})
        unique_users['user_name'] = 'user_' + unique_users['user_id'].astype(str)
        unique_users['email'] = 'user_' + unique_users['user_id'].astype(str) + '@movielens.dummy'
        unique_users['password'] = 'dummy_password_123'
        unique_users['age'] = 25 
        
        feature_list = ["user_id", "user_name", "email", "password", "age"]
        
        insert_table(
            conn=conn,
            table_name="users",
            df=unique_users,
            feature_list=feature_list,
            conflict_target=["user_id"]
        )
        
    print("✅ Finished loading all synthetic users!")


def load_ratings_to_sql(conn, path, chunk_size=1000000):
    ratings_path = os.path.join(path, "rating.csv")
    
    print("📊 Calculating total rows for ratings progress bar...")
    total_rows_approx = sum(1 for _ in open(ratings_path)) - 1 
    total_chunks = (total_rows_approx // chunk_size) + 1
    
    ratings = pd.read_csv(ratings_path, chunksize=chunk_size)
    total_inserted = 0
    
    print(f"🚀 Starting ratings ingestion ({total_rows_approx:,} rows total)...")
    
    with tqdm(total=total_rows_approx, desc="⭐ Ingesting Ratings", unit="rows") as pbar:
        for i, rating in enumerate(ratings):
            rating = rating.rename(columns={
                'userId': 'user_id',
                'movieId': 'movie_id',
                'rating': 'rating',
                'timestamp': 'rated_at'
            })
            rating['rated_at'] = pd.to_datetime(rating['rated_at'], errors='coerce')
            
            insert_table(
                conn=conn,
                table_name="ratings",
                df=rating,
                feature_list=['user_id', 'movie_id', 'rating', 'rated_at'],
                conflict_target=["user_id, movie_id"]
            )
            
            batch_len = len(rating)
            total_inserted += batch_len
            pbar.update(batch_len)

    print(f"✅ Successfully ingested all {total_inserted:,} ratings!")

    
def main():
    DATASET_PATH = "grouplens/movielens-20m-dataset"
    print("📥 Downloading dataset from Kaggle...")
    path = kagglehub.dataset_download(DATASET_PATH)
    
    conn = connect_db()
    
    load_movies_to_sql(conn, path) 
    print("✨ Finish load movies & genres\n")
    
    load_users_to_sql(conn, path)
    print("✨ Finish load users\n")
    
    load_ratings_to_sql(conn, path)
    insert_avg_genre(conn)
    print("finish load avg genre")
    print("🎉 Finish load Kaggle to SQL completely!")

    


if __name__ == "__main__":
    main()