package db

import (
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// --- Helper Formatting Functions ---


var testPool *pgxpool.Pool

func TestMain(m *testing.M) {
	testPool = ConnectDB()
	if err := CreateTables(testPool); err != nil {
		panic("Failed to create tables for testing: " + err.Error())
	}

	_ = ClearTables(testPool)

	code := m.Run()

	_ = ClearTables(testPool)
	testPool.Close()

	os.Exit(code)
}

// --- User Tests ---

func TestAddAndGetUser(t *testing.T) {
	defer ClearTables(testPool)

	u := user{
		userName: "JohnDoe",
		email:    "john@example.com",
		password: "securepassword",
		age:      25,
	}

	st := AddUser(testPool, u)
	if st != Success {
		t.Fatalf("AddUser failed | %s", ErrorStatus(Success, st))
	}

	fetchedUser, st := GetUserByName(testPool, u.userName)
	if st != Success {
		t.Fatalf("GetUserByName failed | %s", ErrorStatus(Success, st))
	}
	if fetchedUser.email != u.email {
		t.Errorf("Expected email %s, got %s", u.email, fetchedUser.email)
	}

	fetchedByID, st := GetUserByID(testPool, fetchedUser.userId)
	if st != Success {
		t.Fatalf("GetUserByID failed | %s", ErrorStatus(Success, st))
	}
	if fetchedByID.userName != u.userName {
		t.Errorf("Expected username %s, got %s", u.userName, fetchedByID.userName)
	}

	stDuplicate := AddUser(testPool, u)
	if stDuplicate != AlreadyExists {
		t.Errorf("AddUser duplicate check failed | %s", ErrorStatus(AlreadyExists, stDuplicate))
	}

	_, stNotFound := GetUserByName(testPool, "NonExistingUser")
	if stNotFound != NotExists {
		t.Errorf("GetUserByName non-existing check failed | %s", ErrorStatus(NotExists, stNotFound))
	}
}

// --- Movie Tests ---

func TestAddAndGetMovie(t *testing.T) {
	defer ClearTables(testPool)

	releaseDate := time.Date(2023, time.May, 25, 0, 0, 0, 0, time.UTC)
	m := movie{
		title:       "Inception",
		releaseDate: releaseDate,
	}

	st := AddMovie(testPool, m)
	if st != Success {
		t.Fatalf("AddMovie failed | %s", ErrorStatus(Success, st))
	}

	fetchedMovie, st := GetMovieByTitle(testPool, m.title)
	if st != Success {
		t.Fatalf("GetMovieByTitle failed | %s", ErrorStatus(Success, st))
	}
	if fetchedMovie.title != m.title {
		t.Errorf("Expected title %s, got %s", m.title, fetchedMovie.title)
	}

	fetchedByID, st := GetMovieByID(testPool, fetchedMovie.movieId)
	if st != Success {
		t.Fatalf("GetMovieByID failed | %s", ErrorStatus(Success, st))
	}
	if !fetchedByID.releaseDate.Equal(m.releaseDate) {
		t.Errorf("Expected release date %v, got %v", m.releaseDate, fetchedByID.releaseDate)
	}

	_, stNotFound := GetMovieByID(testPool, 9999)
	if stNotFound != NotExists {
		t.Errorf("GetMovieByID non-existing check failed | %s", ErrorStatus(NotExists, stNotFound))
	}
}

// --- Genre Tests ---

func TestAddAndGetGenre(t *testing.T) {
	defer ClearTables(testPool)

	g := genre{
		genreName: "Action",
	}

	st := AddGenre(testPool, g)
	if st != Success {
		t.Fatalf("AddGenre failed | %s", ErrorStatus(Success, st))
	}

	fetchedGenre, st := GetGenreByName(testPool, g.genreName)
	if st != Success {
		t.Fatalf("GetGenreByName failed | %s", ErrorStatus(Success, st))
	}
	if fetchedGenre.genreName != g.genreName {
		t.Errorf("Expected genre name %s, got %s", g.genreName, fetchedGenre.genreName)
	}

	fetchedByID, st := GetGenreByID(testPool, fetchedGenre.genreId)
	if st != Success {
		t.Fatalf("GetGenreByID failed | %s", ErrorStatus(Success, st))
	}
	if fetchedByID.genreName != g.genreName {
		t.Errorf("Expected genre name %s, got %s", g.genreName, fetchedByID.genreName)
	}

	invalidGenre := genre{genreName: ""}
	stInvalid := AddGenre(testPool, invalidGenre)
	if stInvalid != ValidationError {
		t.Errorf("AddGenre empty name check failed | %s", ErrorStatus(ValidationError, stInvalid))
	}
}