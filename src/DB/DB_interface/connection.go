package db

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
)

func ConnectDB() *pgxpool.Pool {
	_ = godotenv.Load()


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

func BuildTxn(conn *pgxpool.Pool,ctx context.Context ) (pgx.Tx,Status) {
	tx,err := conn.Begin(ctx)
	return tx,mapErrorToStatus(err)
}

func commit(tx pgx.Tx, ctx context.Context) Status {
	// commit
	if err := tx.Commit(ctx); err != nil {
		return mapErrorToStatus(err)
	}

	return Success
}