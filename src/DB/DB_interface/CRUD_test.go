package db

import (
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

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

func TestDeleteMovie(t *testing.T) {
	defer ClearTables(testPool)

	m1 := movie{title: "Matrix", releaseDate: time.Now().UTC()}
	m2 := movie{title: "Interstellar", releaseDate: time.Now().UTC()}

	_ = AddMovie(testPool, m1)
	_ = AddMovie(testPool, m2)

	fetchedM1, _ := GetMovieByTitle(testPool, m1.title)

	st := DeleteMovieByID(testPool, fetchedM1.movieId)
	if st != Success {
		t.Fatalf("DeleteMovieByID failed | %s", ErrorStatus(Success, st))
	}

	_, stVerify := GetMovieByID(testPool, fetchedM1.movieId)
	if stVerify != NotExists {
		t.Errorf("Movie still exists after DeleteMovieByID | %s", ErrorStatus(NotExists, stVerify))
	}

	stTitle := DeleteMovieByTitle(testPool, m2.title)
	if stTitle != Success {
		t.Fatalf("DeleteMovieByTitle failed | %s", ErrorStatus(Success, stTitle))
	}

	_, stVerifyTitle := GetMovieByTitle(testPool, m2.title)
	if stVerifyTitle != NotExists {
		t.Errorf("Movie still exists after DeleteMovieByTitle | %s", ErrorStatus(NotExists, stVerifyTitle))
	}

	stNotFound := DeleteMovieByID(testPool, 9999)
	if stNotFound != NotExists {
		t.Errorf("DeleteMovieByID expected NotExists | %s", ErrorStatus(NotExists, stNotFound))
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

func TestDeleteGenre(t *testing.T) {
	defer ClearTables(testPool)

	g1 := genre{genreName: "Comedy"}
	g2 := genre{genreName: "Drama"}

	_ = AddGenre(testPool, g1)
	_ = AddGenre(testPool, g2)

	fetchedG1, _ := GetGenreByName(testPool, g1.genreName)

	st := DeleteGenreByID(testPool, fetchedG1.genreId)
	if st != Success {
		t.Fatalf("DeleteGenreByID failed | %s", ErrorStatus(Success, st))
	}

	_, stVerify := GetGenreByID(testPool, fetchedG1.genreId)
	if stVerify != NotExists {
		t.Errorf("Genre still exists after DeleteGenreByID | %s", ErrorStatus(NotExists, stVerify))
	}

	stName := DeleteGenreByName(testPool, g2.genreName)
	if stName != Success {
		t.Fatalf("DeleteGenreByName failed | %s", ErrorStatus(Success, stName))
	}

	_, stVerifyName := GetGenreByName(testPool, g2.genreName)
	if stVerifyName != NotExists {
		t.Errorf("Genre still exists after DeleteGenreByName | %s", ErrorStatus(NotExists, stVerifyName))
	}

	stNotFound := DeleteGenreByName(testPool, "NonExistingGenre")
	if stNotFound != NotExists {
		t.Errorf("DeleteGenreByName expected NotExists | %s", ErrorStatus(NotExists, stNotFound))
	}
}