package services

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
)

type WatchService struct{}

func NewWatchService() *WatchService {
	return &WatchService{}
}

type Source struct {
	URL        string `json:"url"`
	Quality    string `json:"quality"`
	Resolution int    `json:"resolution"`
	Bandwidth  int    `json:"bandwidth,omitempty"`
}

type WatchResponse struct {
	Sources  []Source `json:"sources"`
	Cached   bool     `json:"cached"`
	Stale    bool     `json:"stale"`
	EmbedUrl *string  `json:"embedUrl"`
}

type SubtitleTrack struct {
	Label    string `json:"label"`
	Language string `json:"language"`
	URL      string `json:"url"`
	Format   string `json:"format"`
}

type SubtitleResponse struct {
	Subtitles []SubtitleTrack `json:"subtitles"`
}

type RefreshResponse struct {
	Sources   []Source `json:"sources"`
	Refreshed bool     `json:"refreshed"`
}

type PrewarmResponse struct {
	Status string `json:"status"`
}

type HealthReportResponse struct {
	Status string `json:"status"`
}

func (s *WatchService) getSourceURL() string {
	if value := strings.TrimRight(os.Getenv("WATCHFY_EXTRACTOR_URL"), "/"); value != "" {
		return value + "/api"
	}
	if value := strings.TrimRight(os.Getenv("VIDKING_EXTRACTOR_URL"), "/"); value != "" {
		return value + "/api"
	}
	return "http://localhost:8000/api"
}

func (s *WatchService) resolveServerPrefix(server string) string {
	switch strings.ToLower(strings.TrimSpace(server)) {
	case "white":
		return "/white"
	case "black", "vidking":
		return "/black"
	default:
		return "/white"
	}
}

func (s *WatchService) GetSource(ctx context.Context, id string, server ...string) (*WatchResponse, error) {
	srv := "White"
	if len(server) > 0 && server[0] != "" {
		srv = server[0]
	}
	prefix := s.resolveServerPrefix(srv)
	u := fmt.Sprintf("%s%s/source?tmdbId=%s&mediaType=movie", s.getSourceURL(), prefix, url.QueryEscape(id))

	req, _ := http.NewRequestWithContext(ctx, "GET", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data WatchResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *WatchService) GetSourceTV(ctx context.Context, id string, season, episode int, server ...string) (*WatchResponse, error) {
	srv := "White"
	if len(server) > 0 && server[0] != "" {
		srv = server[0]
	}
	prefix := s.resolveServerPrefix(srv)
	u := fmt.Sprintf("%s%s/source?tmdbId=%s&mediaType=tv&season=%d&episode=%d",
		s.getSourceURL(), prefix, url.QueryEscape(id), season, episode)

	req, _ := http.NewRequestWithContext(ctx, "GET", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data WatchResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *WatchService) RefreshSource(ctx context.Context, id string, mediaType string, season, episode int, server ...string) (*RefreshResponse, error) {
	srv := "White"
	if len(server) > 0 && server[0] != "" {
		srv = server[0]
	}
	prefix := s.resolveServerPrefix(srv)
	u := fmt.Sprintf("%s%s/refresh?tmdbId=%s&mediaType=%s&season=%d&episode=%d",
		s.getSourceURL(), prefix, url.QueryEscape(id), url.QueryEscape(mediaType), season, episode)

	req, _ := http.NewRequestWithContext(ctx, "GET", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data RefreshResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *WatchService) GetSubtitles(ctx context.Context, imdbId string) (*SubtitleResponse, error) {
	u := fmt.Sprintf("%s/subtitles?imdbId=%s", s.getSourceURL(), url.QueryEscape(imdbId))

	req, _ := http.NewRequestWithContext(ctx, "GET", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data SubtitleResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *WatchService) Prewarm(ctx context.Context, id string, mediaType string, season, episode int, server ...string) (*PrewarmResponse, error) {
	srv := "White"
	if len(server) > 0 && server[0] != "" {
		srv = server[0]
	}
	prefix := s.resolveServerPrefix(srv)
	u := fmt.Sprintf("%s%s/prewarm?tmdbId=%s&mediaType=%s&season=%d&episode=%d",
		s.getSourceURL(), prefix, url.QueryEscape(id), url.QueryEscape(mediaType), season, episode)

	req, _ := http.NewRequestWithContext(ctx, "GET", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data PrewarmResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}

func (s *WatchService) HealthReport(ctx context.Context, server ...string) (*HealthReportResponse, error) {
	srv := "White"
	if len(server) > 0 && server[0] != "" {
		srv = server[0]
	}
	prefix := s.resolveServerPrefix(srv)
	u := fmt.Sprintf("%s%s/health/report", s.getSourceURL(), prefix)

	req, _ := http.NewRequestWithContext(ctx, "POST", u, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("extractor returned HTTP %d", resp.StatusCode)
	}

	var data HealthReportResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}
	return &data, nil
}
