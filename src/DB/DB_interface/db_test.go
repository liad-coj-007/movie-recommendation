package db

import (
	"context"
	"log"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestDB(t *testing.T) *pgxpool.Pool {
	t.Helper()
	conn := ConnectDB()
	assert.NotEqual(t,conn,nil)
	err := CreateTables(conn)	
	if err != nil {
		log.Fatal("ERROR: ",err)
	}
	err = ClearTables(conn)
	if err != nil {
		log.Fatal("ERROR: ",err)
	}
	return conn
}

// -----------------------------------------------------------------------------
// Tests: Users CRUD
// -----------------------------------------------------------------------------



func TestDeleteUserByID(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddUser(conn, user{userName: "user_to_delete", email: "delete@me.com", password: "pwd", age: 30})
	u, u_s := GetUserByName(conn, "user_to_delete")
	if u_s != Success {
		t.Fatalf("TestDeleteUserByID failed | %s",ErrorStatus(Success,u_s))
	}
	status := DeleteUserByID(conn, u.userId)
	assert.Equal(t, Success, status)

	_, status = GetUserByID(conn, u.userId)
	assert.Equal(t, NotExists, status)
}

// -----------------------------------------------------------------------------
// Tests: Movies & Genres
// -----------------------------------------------------------------------------

func TestMoviesCRUD(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	m := movie{
		title:       "Inception",
		releaseDate: time.Now(),
	}

	// הוספה
	assert.Equal(t, Success, AddMovie(conn, m))

	// שליפה לפי כותרת
	fetchedMovie, status := GetMovieByTitle(conn, "Inception")
	assert.Equal(t, Success, status)
	assert.Equal(t, "Inception", fetchedMovie.title)

	// מחיקה
	assert.Equal(t, Success, DeleteMovieByID(conn, fetchedMovie.movieId))
	_, status = GetMovieByID(conn, fetchedMovie.movieId)
	assert.Equal(t, NotExists, status)
}

func TestAddMovieGenres(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddMovie(conn, movie{title: "The Matrix", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "The Matrix")

	AddGenre(conn, genre{genreName: "Action"})
	AddGenre(conn, genre{genreName: "Sci-Fi"})
	g1, _ := GetGenreByName(conn, "Action")
	g2, _ := GetGenreByName(conn, "Sci-Fi")

	status := AddMovieGenres(conn, m.movieId, []int64{g1.genreId, g2.genreId})
	assert.Equal(t, Success, status)

	statusConflict := AddMovieGenres(conn, m.movieId, []int64{g1.genreId})
	assert.Equal(t, Success, statusConflict)
}

// -----------------------------------------------------------------------------
// Tests: Ratings & Aggregations (UpsertRating & BuildUsersEmbedings)
// -----------------------------------------------------------------------------

func TestUpsertRatingAndUserGenreRatings(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddUser(conn, user{userName: "reviewer", email: "rev@test.com", password: "pwd", age: 20})
	u, _ := GetUserByName(conn, "reviewer")

	AddMovie(conn, movie{title: "Interstellar", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "Interstellar")

	AddGenre(conn, genre{genreName: "Sci-Fi"})
	gSciFi, _ := GetGenreByName(conn, "Sci-Fi")

	AddMovieGenres(conn, m.movieId, []int64{gSciFi.genreId})

	status := UpsertRating(conn, u.userId, m.movieId, 5)
	assert.Equal(t, Success, status)

	statusUpdate := UpsertRating(conn, u.userId, m.movieId, 3)
	assert.Equal(t, Success, statusUpdate)

	var avgRating float64
	err := conn.QueryRow(context.Background(),
		"SELECT avg_rating FROM user_genre_ratings WHERE user_id = $1 AND genre_id = $2",
		u.userId, gSciFi.genreId).Scan(&avgRating)

	require.NoError(t, err)
	assert.Equal(t, 3.00, avgRating)
}

func assertStatus(t *testing.T,conn *pgxpool.Pool,actual Status , expected Status,
	name string) {
	t.Helper()
	if actual != expected {
		t.Fatalf("Status failed on %s | %s ",name,ErrorStatus(expected,actual))
	}
}

func TestBuildUsersEmbedings(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddGenre(conn, genre{genreName: "Action"})  // ID 1
	AddGenre(conn, genre{genreName: "Comedy"})  // ID 2
	g1, s1 := GetGenreByName(conn, "Action")
	assertStatus(t,conn,s1,Success,"s1")

	AddUser(conn, user{userName: "embed_user", email: "embed@test.com", password: "pwd", age: 22})
	u, s2 := GetUserByName(conn, "embed_user")
	assertStatus(t,conn,s2,Success,"s2")

	AddMovie(conn, movie{title: "Die Hard", releaseDate: time.Now()})
	m, s3 := GetMovieByTitle(conn, "Die Hard")
	assertStatus(t,conn,s3,Success,"s3")
	AddMovieGenres(conn, m.movieId, []int64{g1.genreId})

	UpsertRating(conn, u.userId, m.movieId, 4)

	embeddingsMap, status := BuildUsersEmbedings(conn, []int64{u.userId})
	assert.Equal(t, Success, status)
	assert.Contains(t, embeddingsMap, u.userId)

	userEmbedding := embeddingsMap[u.userId]
	
	require.Len(t, userEmbedding, 2)
	assert.Equal(t, float32(4.0), userEmbedding[0])
	assert.Equal(t, float32(0.0), userEmbedding[1])
}





// -----------------------------------------------------------------------------
// 1. Edge Cases: BuildUsersEmbedings
// -----------------------------------------------------------------------------

func TestBuildUsersEmbedings_ColdStartUser(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	// יצירת 2 ז'אנרים במערכת
	AddGenre(conn, genre{genreName: "Action"})
	AddGenre(conn, genre{genreName: "Comedy"})

	// יצירת משתמש "קר" שלא דירג אף סרט
	AddUser(conn, user{userName: "colduser", email: "cold@test.com", password: "pwd", age: 25})
	u, _ := GetUserByName(conn, "colduser")

	// הרצת השאילתה עבור המשתמש הקר
	embeddingsMap, status := BuildUsersEmbedings(conn, []int64{u.userId})
	assert.Equal(t, Success, status)
	assert.Contains(t, embeddingsMap, u.userId)

	userEmbedding := embeddingsMap[u.userId]

	// אימות: הווקטור בגודל מלא (2) וכולו 0.0 בלבד (אין NULL)
	require.Len(t, userEmbedding, 2)
	assert.Equal(t, float32(0.0), userEmbedding[0])
	assert.Equal(t, float32(0.0), userEmbedding[1])
}

func TestBuildUsersEmbedings_EmptyArrayAndNonExistingUser(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	// 1. קריאה עם מערך IDs ריק
	emptyMap, status := BuildUsersEmbedings(conn, []int64{})
	assert.Equal(t, Success, status)
	assert.Empty(t, emptyMap)

	// 2. קריאה עם ID של משתמש שלא קיים ב-DB ( למשל 99999)
	nonExistingMap, status := BuildUsersEmbedings(conn, []int64{99999})
	assert.Equal(t, Success, status)
	assert.NotContains(t, nonExistingMap, int64(99999))
}

// -----------------------------------------------------------------------------
// 2. Edge Cases: UpsertRating & Multi-Genre Update
// -----------------------------------------------------------------------------

func TestUpsertRating_MultiGenreMovie(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	// יצירת משתמש
	AddUser(conn, user{userName: "multigener", email: "multi@test.com", password: "pwd", age: 28})
	u, _ := GetUserByName(conn, "multigener")

	// יצירת סרט
	AddMovie(conn, movie{title: "Avengers", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "Avengers")

	// יצירת 2 ז'אנרים ושיוכם לסרט במקביל
	AddGenre(conn, genre{genreName: "Action"})
	AddGenre(conn, genre{genreName: "Sci-Fi"})
	g1, _ := GetGenreByName(conn, "Action")
	g2, _ := GetGenreByName(conn, "Sci-Fi")

	AddMovieGenres(conn, m.movieId, []int64{g1.genreId, g2.genreId})

	// דירוג הסרט ב-5 כוכבים
	status := UpsertRating(conn, u.userId, m.movieId, 5)
	assert.Equal(t, Success, status)

	// אימות ששני הז'אנרים התעדכנו בטרנזקציה ב-user_genre_ratings ל-5.00
	var avg1, avg2 float64
	err1 := conn.QueryRow(context.Background(),
		"SELECT avg_rating FROM user_genre_ratings WHERE user_id = $1 AND genre_id = $2",
		u.userId, g1.genreId).Scan(&avg1)

	err2 := conn.QueryRow(context.Background(),
		"SELECT avg_rating FROM user_genre_ratings WHERE user_id = $1 AND genre_id = $2",
		u.userId, g2.genreId).Scan(&avg2)

	require.NoError(t, err1)
	require.NoError(t, err2)
	assert.Equal(t, 5.00, avg1)
	assert.Equal(t, 5.00, avg2)
}

func TestUpsertRating_TransactionRollbackOnInvalidData(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddUser(conn, user{userName: "rollbackuser", email: "roll@test.com", password: "pwd", age: 30})
	u, _ := GetUserByName(conn, "rollbackuser")

	AddMovie(conn, movie{title: "Test Movie", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "Test Movie")

	status := UpsertRating(conn, u.userId, m.movieId, 10)
	assert.Equal(t, ValidationError, status)

	var count int
	err := conn.QueryRow(context.Background(),
		"SELECT COUNT(*) FROM ratings WHERE user_id = $1 AND movie_id = $2",
		u.userId, m.movieId).Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 0, count, "הדירוג נשמר למרות שהטרנזקציה הייתה אמורה להיכשל")
}

// -----------------------------------------------------------------------------
// 3. Edge Cases: AddMovieGenres
// -----------------------------------------------------------------------------

func TestAddMovieGenres_InvalidGenreID(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddMovie(conn, movie{title: "Lone Movie", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "Lone Movie")

	status := AddMovieGenres(conn, m.movieId, []int64{99999})

	assert.Equal(t, BadParam, status)
}

func TestAddMovieGenres_EmptyList(t *testing.T) {
	conn := setupTestDB(t)
	defer conn.Close()

	AddMovie(conn, movie{title: "Empty Movie", releaseDate: time.Now()})
	m, _ := GetMovieByTitle(conn, "Empty Movie")

	status := AddMovieGenres(conn, m.movieId, []int64{})
	assert.Equal(t, Success, status)
}