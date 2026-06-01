package services

func tmdbImage(size, path string) string {
	if path == "" {
		return ""
	}
	return "https://image.tmdb.org/t/p/" + size + path
}

func yearFromDate(date string) string {
	if len(date) < 4 {
		return ""
	}
	return date[:4]
}

// isSafePathSegment reports whether `s` is safe to interpolate into a
// URL path component without further escaping. Allows only digits, as
// expected for TMDB numeric IDs. Anything else (letters, '..', '?',
// '&', '/', '%', etc.) is rejected so user input cannot inject query
// parameters, traversal sequences, or percent-encoded payloads.
func isSafePathSegment(s string) bool {
	if s == "" || len(s) > 32 {
		return false
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}
