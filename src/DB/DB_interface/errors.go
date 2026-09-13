package db

import (
	"fmt"
	"errors"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"context"
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


func mapExecToStatus(tag pgconn.CommandTag, err error) Status {
	if err != nil {
		return mapErrorToStatus(err)
	}
	if tag.RowsAffected() == 0 {
		return NotExists
	}
	return Success
}
