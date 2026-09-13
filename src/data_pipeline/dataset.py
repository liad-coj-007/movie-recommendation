import os
import psycopg2
from psycopg2.extras import RealDictCursor,execute_values

from dotenv import load_dotenv
import pandas as pd
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





    