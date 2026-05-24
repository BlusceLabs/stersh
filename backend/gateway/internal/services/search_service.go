package services

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

type SearchService struct {
	cache *ttlCache
}

type SearchItem struct {
	ID         int    `json:"id"`
	Title      string `json:"title"`
	PosterPath string `json:"posterPath"`
	MediaType  string `json:"mediaType"`
	Year       string `json:"year"`
}

type SearchResponse struct {
	Results []SearchItem `json:"results"`
}

func NewSearchService() *SearchService {
	return &SearchService{
		cache: newTTLCache(5 * time.Minute),
	}
}

func (s *SearchService) Search(ctx context.Context, query string) (*SearchResponse, error) {
	cacheKey := "search:" + query
	if cached, ok := s.cache.Get(cacheKey); ok {
		return cached.(*SearchResponse), nil
	}

	apiKey := os.Getenv("TMDB_API_KEY")
	url := fmt.Sprintf(
		"https://api.themoviedb.org/3/search/multi?api_key=%s&query=%s&include_adult=false",
		apiKey, query,
	)

	req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data struct {
		Results []struct {
			ID          int    `json:"id"`
			Title       string `json:"title"`
			Name        string `json:"name"`
			PosterPath  string `json:"poster_path"`
			MediaType   string `json:"media_type"`
			ReleaseDate string `json:"release_date"`
			FirstAirDate string `json:"first_air_date"`
		} `json:"results"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	var results []SearchItem
	for _, r := range data.Results {
		if r.MediaType != "movie" && r.MediaType != "tv" {
			continue
		}
		title := r.Title
		if title == "" {
			title = r.Name
		}
		year := ""
		if r.MediaType == "tv" && len(r.FirstAirDate) >= 4 {
			year = r.FirstAirDate[:4]
		} else if len(r.ReleaseDate) >= 4 {
			year = r.ReleaseDate[:4]
		}
		results = append(results, SearchItem{
			ID:         r.ID,
			Title:      title,
			PosterPath: "https://image.tmdb.org/t/p/w500" + r.PosterPath,
			MediaType:  r.MediaType,
			Year:       year,
		})
	}

	result := &SearchResponse{Results: results}
	s.cache.Set(cacheKey, result)
	return result, nil
}
