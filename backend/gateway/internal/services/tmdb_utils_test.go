package services

import "testing"

func TestIsSafePathSegment(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want bool
	}{
		// Happy path: digit-only TMDB IDs.
		{"empty rejected", "", false},
		{"single digit", "1", true},
		{"typical id", "27205", true},
		{"long but valid", "12345678901234567890123456789012", true}, // 32 chars
		{"too long", "123456789012345678901234567890123", false},      // 33 chars

		// Path-traversal attempts.
		{"dotdot", "..", false},
		{"dotdot inside", "1..2", false},
		{"slash inside", "1/2", false},
		{"backslash inside", "1\\2", false},

		// Injection attempts.
		{"percent encoding", "%2e%2e", false},
		{"single percent", "1%", false},
		{"query string", "1?x=1", false},
		{"fragment", "1#x", false},
		{"ampersand", "1&x=2", false},
		{"space", "1 2", false},
		{"letter", "abc", false},
		{"leading minus", "-1", false},
		{"trailing junk", "1abc", false},

		// Whitelisted hostnames that look numeric-ish.
		{"uppercase letter", "A1", false},
		{"unicode digit", "१२३", false}, // Devanagari 1-3, NOT ASCII 0-9
		{"mixed case", "1a", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := isSafePathSegment(tc.in); got != tc.want {
				t.Errorf("isSafePathSegment(%q) = %v, want %v", tc.in, got, tc.want)
			}
		})
	}
}

func TestYearFromDate(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"2024-03-15", "2024"},
		{"2024", "2024"},
		{"20", ""},
		{"", ""},
		{"2024-13-99", "2024"},
	}
	for _, tc := range cases {
		t.Run(tc.in, func(t *testing.T) {
			if got := yearFromDate(tc.in); got != tc.want {
				t.Errorf("yearFromDate(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestTmdbImage(t *testing.T) {
	if got := tmdbImage("w500", "/abc.jpg"); got != "https://image.tmdb.org/t/p/w500/abc.jpg" {
		t.Errorf("tmdbImage = %q", got)
	}
	if got := tmdbImage("original", ""); got != "" {
		t.Errorf("empty path should return empty, got %q", got)
	}
}
