package db

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
	"time"
)

type Status int


const (
	// Success and General Statuses
	Success Status = iota // 0: Operation completed successfully
	UnknownError          // 1: Unhandled or unexpected internal error

	// Authentication & Authorization Statuses
	Unauthorized // 2: User is not authenticated or missing token
	Forbidden    // 3: User lacks necessary permissions
	InvalidToken // 4: Token is expired, malformed, or invalid

	// Validation & Resource Statuses
	BadParam        // 5: Provided parameters are invalid or missing
	NotExists       // 6: Requested resource was not found
	AlreadyExists   // 7: Resource already exists (e.g., duplicate username)
	ValidationError // 8: Request payload failed business validation rules

	// Database & System Infrastructure Statuses
	DatabaseError      // 9: Database query failure or connection loss
	InternalError      // 10: Server internal execution error
	ServiceUnavailable // 11: Dependent external service is unreachable

	// Rate Limiting & Execution Statuses
	RateLimitExceeded // 12: Client exceeded request limit threshold
	Timeout           // 13: Operation timed out before completion
)



func mapErrorToStatus(err error) Status {
	if err == nil {
		return Success
	}

	// 1. Check for Context Timeout
	if errors.Is(err, context.DeadlineExceeded) {
		return Timeout
	}

	// 2. Check for pgx No Rows found
	if errors.Is(err, pgx.ErrNoRows) {
		return NotExists
	}

	// 3. Check for PostgreSQL specific driver errors
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "23505": // unique_violation
			return AlreadyExists
		case "23503": // foreign_key_violation
			return BadParam
		case "23514": // check_violation
			return ValidationError
		case "40P01": // deadlock_detected
			return InternalError
		default:
			fmt.Println("ERROR:",err)
			return DatabaseError
		}
	}
	
	fmt.Println("ERROR:",err)
	return UnknownError
}



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
        title VARCHAR(20) CHECK( LENGTH(title) > 0) UNIQUE NOT NULL,
        release_date DATE NOT NULL
    );`,
    `
    CREATE TABLE IF NOT EXISTS genres
    (
        genre_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        genre_name VARCHAR(20) CHECK( LENGTH(genre_name) > 0) UNIQUE NOT NULL
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

func ClearTable(conn *pgxpool.Pool ,tableName string ) error {
	query := fmt.Sprintf("DELETE FROM %s;", tableName)
	_, err := conn.Exec(context.Background(), query)
	return err
}

func ClearTables(conn *pgxpool.Pool) error {
	for _, table := range tables {
		err := ClearTable(conn,table)
		if err != nil {
			return err
		}
	}

	for _, relation := range relations {
		err := ClearTable(conn,relation)
		if err != nil {
			return err
		}
	}

	return nil
}



type user struct {
	userId int64 
	userName string
	email string
	password string 
	age int 
}

func AddUser(conn *pgxpool.Pool, user user) Status {
	query := "INSERT INTO users (user_name,email,password,age) VALUES ($1,$2,$3,$4)"
	_, err := conn.Exec(context.Background(),query,user.userName,user.email,user.password,user.age)
	return mapErrorToStatus(err)
}


func GetUserByID(conn *pgxpool.Pool , userId int64) (*user,Status) {
	query := "SELECT * FROM users WHERE user_id = $1"
	var user user
	err := conn.QueryRow(context.Background(),query,userId).Scan(&user.userId,&user.userName,&user.email,&user.password,&user.age)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &user,Success
}

func GetUserByName(conn *pgxpool.Pool , userName string) (*user,Status){
	query := "SELECT * FROM users WHERE user_name = $1"
	var user user
	err := conn.QueryRow(context.Background(),query,userName).Scan(&user.userId,&user.userName,&user.email,&user.password,&user.age)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &user,Success
}

type movie struct {
	movieId int64
	title string
	releaseDate time.Time 
}


func AddMovie(conn  *pgxpool.Pool, movie movie) Status {
	query := "INSERT INTO movies (title ,release_date) VALUES ($1,$2)"
	_, err := conn.Exec(context.Background(),query,movie.title,movie.releaseDate)
	return mapErrorToStatus(err)
}

func GetMovieByID(conn *pgxpool.Pool, movieId int64) (*movie,Status) {
	query := "SELECT * FROM movies WHERE movie_id = $1"
	var movie movie 
	err := conn.QueryRow(context.Background(),query,movieId).Scan(&movie.movieId,&movie.title,&movie.releaseDate)
	if err != nil {
		return nil,mapErrorToStatus(err)
	}
	
	return &movie,Success
}

func GetMovieByTitle(conn  *pgxpool.Pool, title string ) (*movie,Status) {
	query := "SELECT * FROM movies WHERE title = $1"
	var movie movie 
	err := conn.QueryRow(context.Background(),query,title).Scan(&movie.movieId,&movie.title,&movie.releaseDate)
	if err != nil {
		return nil,mapErrorToStatus(err)
	}

	return &movie,Success
}

type genre struct {
	genreId int64
	genreName string
}

func AddGenre(conn  *pgxpool.Pool, genre genre) Status {
	query := "INSERT INTO genres (genre_name) VALUES ($1)"
	_, err := conn.Exec(context.Background(),query,genre.genreName)
	return mapErrorToStatus(err)
}

func GetGenreByID(conn  *pgxpool.Pool , genreId int64) (*genre, Status) {
	query := "SELECT * FROM genres WHERE genre_id = $1 "
	var genre genre
	err := conn.QueryRow(context.Background(),query,genreId).Scan(&genre.genreId,&genre.genreName)
	if err != nil {
		return nil,mapErrorToStatus(err)
	}
	return &genre,Success
}


func GetGenreByName(conn  *pgxpool.Pool,genreName string) (*genre,Status) {
	query := "SELECT * FROM genres WHERE genre_name = $1 "
	var genre genre
	err := conn.QueryRow(context.Background(),query,genreName).Scan(&genre.genreId,&genre.genreName)
	if err != nil {
		return nil,mapErrorToStatus(err)
	}
	return &genre,Success
}


