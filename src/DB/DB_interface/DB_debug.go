package db

import "fmt"

func (s Status) String() string {
	switch s {
	case Success:
		return "Success"
	case UnknownError:
		return "UnknownError"
	case Unauthorized:
		return "Unauthorized"
	case Forbidden:
		return "Forbidden"
	case InvalidToken:
		return "InvalidToken"
	case BadParam:
		return "BadParam"
	case NotExists:
		return "NotExists"
	case AlreadyExists:
		return "AlreadyExists"
	case ValidationError:
		return "ValidationError"
	case DatabaseError:
		return "DatabaseError"
	case InternalError:
		return "InternalError"
	case ServiceUnavailable:
		return "ServiceUnavailable"
	case RateLimitExceeded:
		return "RateLimitExceeded"
	case Timeout:
		return "Timeout"
	default:
		return fmt.Sprintf("UnknownStatus(%d)", s)
	}
}

func ErrorStatus(expected Status, actual Status) string {
	if expected != actual {
		return fmt.Sprintf("Status mismatch: expected '%s' (%d), got '%s' (%d)", 
			expected.String(), expected, actual.String(), actual)
	}

	return ""
}