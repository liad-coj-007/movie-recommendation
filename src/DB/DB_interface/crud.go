package db

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

func AddUser(conn *pgxpool.Pool, user user) Status {
	query := "INSERT INTO users (user_name,email,password,age) VALUES ($1,$2,$3,$4)"
	tag, err := conn.Exec(context.Background(), query, user.userName, user.email, user.password, user.age)
	return mapExecToStatus(tag, err)
}

func GetUserByID(conn *pgxpool.Pool, userId int64) (*user, Status) {
	query := "SELECT * FROM users WHERE user_id = $1"
	var user user
	err := conn.QueryRow(context.Background(), query, userId).Scan(&user.userId, &user.userName, &user.email, &user.password, &user.age)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &user, Success
}

func GetUserByName(conn *pgxpool.Pool, userName string) (*user, Status) {
	query := "SELECT * FROM users WHERE user_name = $1"
	var user user
	err := conn.QueryRow(context.Background(), query, userName).Scan(&user.userId, &user.userName, &user.email, &user.password, &user.age)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &user, Success
}

func DeleteUserByID(conn *pgxpool.Pool, user_id int64) Status {
	query := "DELETE * FROM users WHERE user_id = $1"
	tag, err := conn.Exec(context.Background(), query, user_id)
	return mapExecToStatus(tag, err)
}

func DeleteUserByName(conn *pgxpool.Pool, userName string) Status {
	query := "DELETE * FROM users WHERE user_name = $1"
	tag, err := conn.Exec(context.Background(), query, userName)
	return mapExecToStatus(tag, err)
}

func AddMovie(conn *pgxpool.Pool, movie movie) Status {
	query := "INSERT INTO movies (title ,release_date) VALUES ($1,$2)"
	tag, err := conn.Exec(context.Background(), query, movie.title, movie.releaseDate)
	return mapExecToStatus(tag, err)
}

func GetMovieByID(conn *pgxpool.Pool, movieId int64) (*movie, Status) {
	query := "SELECT * FROM movies WHERE movie_id = $1"
	var movie movie
	err := conn.QueryRow(context.Background(), query, movieId).Scan(&movie.movieId, &movie.title, &movie.releaseDate)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}

	return &movie, Success
}

func GetMovieByTitle(conn *pgxpool.Pool, title string) (*movie, Status) {
	query := "SELECT * FROM movies WHERE title = $1"
	var movie movie
	err := conn.QueryRow(context.Background(), query, title).Scan(&movie.movieId, &movie.title, &movie.releaseDate)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}

	return &movie, Success
}

func DeleteMovieByID(conn *pgxpool.Pool, movieId int64) Status {
	query := "DELETE FROM movies WHERE movie_id = $1"
	tag, err := conn.Exec(context.Background(), query, movieId)
	return mapExecToStatus(tag, err)
}

func DeleteMovieByTitle(conn *pgxpool.Pool, title string) Status {
	query := "DELETE  FROM movies WHERE title = $1"
	tag, err := conn.Exec(context.Background(), query, title)
	return mapExecToStatus(tag, err)
}

func AddGenre(conn *pgxpool.Pool, genre genre) Status {
	query := "INSERT INTO genres (genre_name) VALUES ($1)"
	tag, err := conn.Exec(context.Background(), query, genre.genreName)
	return mapExecToStatus(tag, err)
}

func GetGenreByID(conn *pgxpool.Pool, genreId int64) (*genre, Status) {
	query := "SELECT * FROM genres WHERE genre_id = $1 "
	var genre genre
	err := conn.QueryRow(context.Background(), query, genreId).Scan(&genre.genreId, &genre.genreName)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &genre, Success
}

func GetGenreByName(conn *pgxpool.Pool, genreName string) (*genre, Status) {
	query := "SELECT * FROM genres WHERE genre_name = $1 "
	var genre genre
	err := conn.QueryRow(context.Background(), query, genreName).Scan(&genre.genreId, &genre.genreName)
	if err != nil {
		return nil, mapErrorToStatus(err)
	}
	return &genre, Success
}

func DeleteGenreByID(conn *pgxpool.Pool, genreId int64) Status {
	query := "DELETE  FROM genres WHERE genre_id = $1"
	tag, err := conn.Exec(context.Background(), query, genreId)
	return mapExecToStatus(tag, err)
}

func DeleteGenreByName(conn *pgxpool.Pool, genreName string) Status {
	query := "DELETE  FROM genres WHERE genre_name = $1"
	tag, err := conn.Exec(context.Background(), query, genreName)
	return mapExecToStatus(tag, err)
}

/*
* insert or update if it already exist rating of a movie
* - conn: the connection model
* - userName: the user name
* - title: the movie title
* - rating: the rating of the movie the user gave
 */
func UpsertRating(conn *pgxpool.Pool, userId int64, movieId int64, rating int) Status {
	ctx := context.Background()
	tx, status := BuildTxn(conn, ctx)
	defer tx.Rollback(ctx)

	if status != Success {
		return status
	}
	query := `
	INSERT INTO ratings (user_id,movie_id,rating) VALUES ($1,$2,$3)
	ON CONFLICT (user_id, movie_id) 
	DO UPDATE SET 
    rating = EXCLUDED.rating, 
    rated_at = NOW();
	`
	_, err := tx.Exec(context.Background(), query, userId, movieId, rating)
	if err != nil {
		return mapErrorToStatus(err)
	}

	genreAvgQuery := `
	INSERT INTO user_genre_ratings (user_id, genre_id, avg_rating)
	SELECT R.user_id AS user_id , MG.genre_id As genre_id , ROUND(AVG(r.rating), 2) AS avg_rating
	FROM ratings AS R JOIN movie_genres AS MG ON R.movie_id = MG.movie_id
	WHERE R.user_id = $1 AND MG.genre_id IN (SELECT genre_id FROM movie_genres WHERE movie_id = $2)
	GROUP BY R.user_id , MG.genre_id
	ON CONFLICT (user_id, genre_id) 
	DO UPDATE SET avg_rating = EXCLUDED.avg_rating;
	`
	_, err = tx.Exec(ctx, genreAvgQuery, userId, movieId)
	if err != nil {
		return mapErrorToStatus(err)
	}

	return commit(tx,ctx)
}

