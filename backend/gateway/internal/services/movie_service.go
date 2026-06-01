package services

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "time"
)

type MovieService struct {
    cache *ttlCache
}

func NewMovieService() *MovieService {
    return &MovieService{
        cache: newTTLCache(10 * time.Minute),
    }
}

type TrendingMovie struct {
    ID           int     `json:"id"`
    Title        string  `json:"title"`
    PosterPath   string  `json:"posterPath"`
    BackdropPath string  `json:"backdropPath"`
    Rating       float64 `json:"rating"`
    Year         string  `json:"year"`
}

type TrendingResponse struct {
    Results []TrendingMovie `json:"results"`
}

func (s *MovieService) GetTrending(ctx context.Context) (*TrendingResponse, error) {
    if cached, ok := s.cache.Get("trending"); ok {
        return cached.(*TrendingResponse), nil
    }

    apiKey := os.Getenv("TMDB_API_KEY")

    url := fmt.Sprintf(
        "https://api.themoviedb.org/3/trending/movie/week?api_key=%s",
        apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode >= 400 {
        return nil, fmt.Errorf("tmdb trending: HTTP %d", resp.StatusCode)
    }

    var data struct {
        Results []struct {
            ID           int     `json:"id"`
            Title        string  `json:"title"`
            PosterPath   string  `json:"poster_path"`
            BackdropPath string  `json:"backdrop_path"`
            ReleaseDate  string  `json:"release_date"`
            VoteAverage  float64 `json:"vote_average"`
        } `json:"results"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, err
    }

    results := make([]TrendingMovie, 0, len(data.Results))
    for _, m := range data.Results {
        results = append(results, TrendingMovie{
            ID:           m.ID,
            Title:        m.Title,
			PosterPath:   tmdbImage("w780", m.PosterPath),
			BackdropPath: tmdbImage("w1280", m.BackdropPath),
			Rating:       m.VoteAverage,
			Year:         yearFromDate(m.ReleaseDate),
		})
	}

    respData := &TrendingResponse{Results: results}
    s.cache.Set("trending", respData)
    return respData, nil
}
