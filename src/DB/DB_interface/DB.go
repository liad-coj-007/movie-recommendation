package db

import (
	"context"
	"fmt"
	"log"
	"os"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
)





func ConnectDB() *pgxpool.Pool {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}

	dbUser := os.Getenv("DB_USER")
	dbPassword := os.Getenv("DB_PASSWORD")
	dbHost := os.Getenv("DB_HOST")
	dbPort := os.Getenv("DB_PORT")
	dbName := os.Getenv("DB_NAME")

	connStr := fmt.Sprintf("postgresql://%s:%s@%s:%s/%s", dbUser, dbPassword, dbHost, dbPort, dbName)

	pool, err := pgxpool.New(context.Background(), connStr)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}
	
	if err := pool.Ping(context.Background()); err != nil {
		log.Fatalf("Unable to ping database: %v\n", err)
	}

	return pool
}

func executeQueries(conn  *pgxpool.Pool, queries []string) error {
	ctx := context.Background()
	for _ , query := range queries {
		_, err := conn.Exec(ctx,query)
		if err != nil{
			return err
		}
	}
	return nil
}



var tables = []string{
    "users", "movies", "genres",
}

var relations = []string{
    "ratings", "user_genre_ratings", "movie_genres",
}


func CreateTables(conn *pgxpool.Pool) error {
    tables := []string{`
    CREATE TABLE IF NOT EXISTS users
    (
        user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_name VARCHAR(20) CHECK (user_name ~ '^[a-zA-Z][a-zA-Z0-9]*$') UNIQUE NOT NULL,
        email TEXT CHECK (email ~* '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$') UNIQUE NOT NULL,
        password TEXT NOT NULL,
        age INT CHECK (age >= 0 AND age <= 120) NOT NULL
    );`,
    `
    CREATE TABLE IF NOT EXISTS movies (
        movie_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        movie_name VARCHAR(20) UNIQUE NOT NULL,
        release_date DATE NOT NULL
    );`,
    `
    CREATE TABLE IF NOT EXISTS genres
    (
        genre_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        genre_name VARCHAR(20) UNIQUE NOT NULL
    );`,
    }

    err := executeQueries(conn, tables)
    if err != nil {
        return err
    }

    relations := []string{
        `
    CREATE TABLE IF NOT EXISTS ratings (
        user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        movie_id BIGINT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
        rating DECIMAL CHECK (rating >= 0 AND rating <= 5) NOT NULL,
        rated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
        PRIMARY KEY (user_id, movie_id)
    );`,
    `
    CREATE TABLE IF NOT EXISTS user_genre_ratings (
        user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        genre_id BIGINT NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
        avg_rating DECIMAL CHECK (avg_rating >= 0.0 AND avg_rating <= 5.0) NOT NULL,
        PRIMARY KEY (user_id, genre_id)
    );`,
    `   
    CREATE TABLE IF NOT EXISTS movie_genres (
        movie_id BIGINT NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
        genre_id BIGINT NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
        PRIMARY KEY (movie_id, genre_id)
    );`,
    }

    return executeQueries(conn, relations)
}
