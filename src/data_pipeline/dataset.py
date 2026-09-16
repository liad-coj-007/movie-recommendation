import os
import psycopg2
from psycopg2.extras import RealDictCursor,execute_values
from psycopg2.extensions import register_adapter

from dotenv import load_dotenv
import pandas as pd
import os

import numpy as np
import shutil
from tqdm import tqdm


register_adapter(np.int64, psycopg2.extensions.AsIs)
register_adapter(np.int32, psycopg2.extensions.AsIs)


load_dotenv()

def connect_db():
    try:
        connection = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "movies_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        return connection
    except Exception as e:
        print(f"ERROR: in connecting PostgreSQL: {e}")
        raise e

def insert_table(conn,table_name : str , df : pd.DataFrame,feature_list : list[str],conflict_target=None):
    
    if conflict_target == None :
        conflict_target = feature_list[0]
    else:
        conflict_target = ", ".join(conflict_target)

    columns_str = ", ".join(feature_list)

    query = f"""
    INSERT INTO {table_name} ({columns_str}) 
    OVERRIDING SYSTEM VALUE 
    VALUES %s 
    ON CONFLICT ({conflict_target}) DO NOTHING;
    """

    records = list(df[feature_list].itertuples(index=False, name=None))    
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, records, page_size=10000)
        conn.commit()
    except Exception as e:
       conn.rollback()
       print(f"ERROR: inserting into {table_name}: {e}")
       raise e

def insert_avg_genre(conn):
    query = """
    INSERT INTO user_genre_ratings 
    SELECT R.user_id AS user_id , MG.genre_id As genre_id , ROUND(AVG(r.rating), 2) AS avg_rating
	FROM ratings AS R JOIN movie_genres AS MG ON R.movie_id = MG.movie_id
	GROUP BY R.user_id , MG.genre_id
	ON CONFLICT (user_id, genre_id) 
	DO UPDATE SET avg_rating = EXCLUDED.avg_rating;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: inserting into user_genre_ratings : {e}")


def build_export_table(conn):
    query = """
    CREATE TABLE IF NOT EXISTS export_ready_ratings AS
                WITH valid_users AS (
                    SELECT user_id
                    FROM ratings
                    GROUP BY user_id
                    HAVING COUNT(*) >= 3 
                    AND COUNT(CASE WHEN rating < 3 THEN 1 END) > 0
                )
                SELECT R.user_id AS user_id, 
                       R.movie_id AS movie_id, 
                       R.rating AS rating, 
                       R.rated_at AS rated_at,
                       ARRAY_AGG(MG.genre_id) AS genre_ids
                FROM ratings AS R  
                JOIN valid_users AS UV ON R.user_id = UV.user_id 
                JOIN movie_genres AS MG ON R.movie_id = MG.movie_id 
                GROUP BY R.user_id, R.movie_id, R.rated_at, R.rating;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_export_composite 
                ON export_ready_ratings(rated_at, user_id);
                
            """)
        conn.commit()
    except Exception as e:
        print(f"{e}")
        raise e

def count_rows_export(conn):
    count_query = """
        SELECT COUNT(*)
        FROM export_ready_ratings
        """
    
    print("📊 Calculating total rows in the database...")
    with conn.cursor() as cur:
        cur.execute(count_query)
        total_rows = cur.fetchone()[0]
    conn.commit()

    return total_rows


def get_chunk(conn,last_rated_at,last_user_id,chunk_size):
    with conn.cursor() as cur:
        if last_rated_at is None:
            query = """
                    SELECT user_id, movie_id, rating, rated_at, genre_ids
                    FROM export_ready_ratings
                    ORDER BY rated_at ASC, user_id ASC
                    LIMIT %s;
                    """
            cur.execute(query, (chunk_size,))
        else:
            query = """
                SELECT user_id, movie_id, rating, rated_at, genre_ids
                FROM export_ready_ratings
                WHERE (rated_at, user_id) > (%s, %s)
                ORDER BY rated_at ASC, user_id ASC
                LIMIT %s;
                """
            cur.execute(query, (last_rated_at, last_user_id, chunk_size))

        conn.commit()
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        return rows,colnames
  


def export_train_df_to_parquet(conn,output_dir="data_chunks", chunk_size=50000):
    """Fast and interactive export of data from PostgreSQL to Parquet chunks.

    - chunk_size defaults to 50,000 rows per file for optimal performance.
    - Uses tqdm for an interactive visual progress bar.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Step A: Calculate total row count for an accurate progress bar

    total_rows = count_rows_export(conn)

    if total_rows == 0:
        print("⚠️ No data found matching the filtering conditions.")
        return
        
    print(
        f"🎯 Found a total of {total_rows:,} rows to export. Starting export process...\n"
    )
    
    
    chunk_idx = 0
    last_rated_at = None
    last_user_id = None

    with tqdm(
        total=total_rows, desc="🚀 Exporting Parquet chunks", unit="rows"
    ) as pbar:
        while True:
            rows, colnames = get_chunk(conn,last_rated_at,last_user_id,chunk_size)            
            if not rows:
                break

            chunk = pd.DataFrame(rows, columns=colnames)

            last_rated_at = chunk.iloc[-1]["rated_at"]
            last_user_id = chunk.iloc[-1]["user_id"]

            chunk["genre_ids"] = chunk["genre_ids"].apply(
                lambda x: list(x) if x is not None else []
            )

            chunk_file = os.path.join(output_dir, f"chunk_{chunk_idx}.parquet")
            chunk.to_parquet(chunk_file, index=False)

            pbar.update(len(chunk))
            chunk_idx += 1
    print(
        f"\n Keyset export completed successfully! Created {chunk_idx} Parquet"
        " files."
    )









    