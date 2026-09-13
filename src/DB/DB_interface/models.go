package db

import (
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



type user struct {
	userId int64 
	userName string
	email string
	password string 
	age int 
}


type movie struct {
	movieId int64
	title string
	releaseDate time.Time 
}

type genre struct {
	genreId int64
	genreName string
}


