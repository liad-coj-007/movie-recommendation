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

func CreateTables(conn *pgxpool.Pool) error {
	tables := []string{`
	CREATE TABLE IF NOT EXISTS users
	(
		userId BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
		user_name VARCHAR(20) CHECK (user_name ~ '^[a-zA-Z][a-zA-Z0-9]*$') UNIQUE NOT NULL,
		email TEXT CHECK (email ~* '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$') UNIQUE NOT NULL,
		password TEXT NOT NULL,
		age INT CHECK (age >= 0 AND age <= 120) NOT NULL
	);`,
	`
	CREATE TABLE IF NOT EXISTS movies (
		movieId  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
		movieName VARCHAR(20) UNIQUE NOT NULL,
		releseDate DATE NOT NULL
	);`,
	`
	CREATE TABLE IF NOT EXISTS generes
	(
		genreId  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
		genreName VARCHAR(20) UNIQUE NOT NULL

	);`,
	}

	err := executeQueries(conn,tables)
	if err != nil {
		return err
	}


	relations := []string{
		`
	CREATE TABLE IF NOT EXISTS ratings (
		userId BIGINT NOT NULL REFERENCES users(userId) ON DELETE CASCADE,
		movieId BIGINT NOT NULL REFERENCES movies(movieId) ON DELETE CASCADE,
		rating DECIMAL CHECK (rating >=0 AND rating<=5) NOT NULL,
		PRIMARY KEY (userId,movieId)
	);`,
	`
	CREATE TABLE IF NOT EXISTS UserGenreRating (
		userId BIGINT NOT NULL REFERENCES users(userId) ON DELETE CASCADE,
		genreId BIGINT NOT NULL REFERENCES generes(genreId) ON DELETE CASCADE,
		avgRating DECIMAL CHECK (avgRating >=0 AND avgRating<=5) NOT NULL,
		PRIMARY KEY (userId,genreId)
	);`,

	`	
	CREATE TABLE IF NOT EXISTS UserGenreRating (
		movieId BIGINT NOT NULL REFERENCES movies(movieId) ON DELETE CASCADE,
		genreId BIGINT NOT NULL REFERENCES generes(genreId) ON DELETE CASCADE,
		PRIMARY KEY (movieID,genreId)
	);`,
	}

	return executeQueries(conn,relations)
}
