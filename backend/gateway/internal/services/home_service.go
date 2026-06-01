package services

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "sync"
    "time"
)

type HomeService struct {
    cache *ttlCache
}

func NewHomeService() *HomeService {
    return &HomeService{
        cache: newTTLCache(10 * time.Minute),
    }
}

type HomepageResponse struct {
    Hero []HeroMovie `json:"hero"`
    Rows []MovieRow  `json:"rows"`
}

type HeroMovie struct {
    ID           int    `json:"id"`
    Title        string `json:"title"`
    Overview     string `json:"overview"`
    BackdropPath string `json:"backdropPath"`
    LogoPath     string `json:"logoPath"`
    TrailerKey   string `json:"trailerKey"`
}

type MovieRow struct {
    ID    string      `json:"id"`
    Title string      `json:"title"`
    Items []MovieCard `json:"items"`
}

type MovieCard struct {
    ID         int    `json:"id"`
    Title      string `json:"title"`
    PosterPath string `json:"posterPath"`
    MediaType  string `json:"mediaType,omitempty"`
}

var httpClient = &http.Client{
    Timeout: 10 * time.Second,
}

func (s *HomeService) GetHomepage(ctx context.Context) (*HomepageResponse, error) {
    if cached, ok := s.cache.Get("homepage"); ok {
        return cached.(*HomepageResponse), nil
    }

    var wg sync.WaitGroup
    var hero []HeroMovie
    var topRated, popular, upcoming []MovieCard
    var trendingTV, popularTV, topRatedTV []MovieCard
    var heroErr, trErr, pErr, uErr, ttErr, ptErr, trtErr error

    wg.Add(7)

    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        hero, heroErr = s.getHeroMovies(ctx)
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        topRated, trErr = s.getItems(ctx, "movie/top_rated", "movie")
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        popular, pErr = s.getItems(ctx, "movie/popular", "movie")
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        upcoming, uErr = s.getItems(ctx, "movie/upcoming", "movie")
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        trendingTV, ttErr = s.getItems(ctx, "trending/tv/week", "tv")
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        popularTV, ptErr = s.getItems(ctx, "tv/popular", "tv")
    }()
    go func() {
        defer func() { _ = recover() }()
        defer wg.Done()
        topRatedTV, trtErr = s.getItems(ctx, "tv/top_rated", "tv")
    }()

    wg.Wait()

    if heroErr != nil {
        return nil, heroErr
    }

    rows := make([]MovieRow, 0, 6)
    if trErr == nil {
        rows = append(rows, MovieRow{ID: "top-rated", Title: "Top Rated Movies", Items: topRated})
    }
    if pErr == nil {
        rows = append(rows, MovieRow{ID: "popular", Title: "Popular Movies", Items: popular})
    }
    if uErr == nil {
        rows = append(rows, MovieRow{ID: "upcoming", Title: "Upcoming Movies", Items: upcoming})
    }
    if ttErr == nil {
        rows = append(rows, MovieRow{ID: "trending-tv", Title: "Trending TV Shows", Items: trendingTV})
    }
    if ptErr == nil {
        rows = append(rows, MovieRow{ID: "popular-tv", Title: "Popular TV Shows", Items: popularTV})
    }
    if trtErr == nil {
        rows = append(rows, MovieRow{ID: "top-rated-tv", Title: "Top Rated TV Shows", Items: topRatedTV})
    }

    resp := &HomepageResponse{Hero: hero, Rows: rows}
    s.cache.Set("homepage", resp)
    return resp, nil
}

func (s *HomeService) getItems(ctx context.Context, path, mediaType string) ([]MovieCard, error) {
    apiKey := os.Getenv("TMDB_API_KEY")

    url := fmt.Sprintf(
        "https://api.themoviedb.org/3/%s?api_key=%s",
        path, apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode >= 400 {
        return nil, fmt.Errorf("tmdb %s: HTTP %d", path, resp.StatusCode)
    }

    var data struct {
        Results []struct {
            ID           int    `json:"id"`
            Title        string `json:"title"`
            Name         string `json:"name"`
            PosterPath   string `json:"poster_path"`
        } `json:"results"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, err
    }

    items := make([]MovieCard, 0, len(data.Results))
    for _, item := range data.Results {
        title := item.Title
        if title == "" {
            title = item.Name
        }

        items = append(items, MovieCard{
            ID:         item.ID,
            Title:      title,
			PosterPath: tmdbImage("w780", item.PosterPath),
			MediaType:  mediaType,
		})
    }

    return items, nil
}

func (s *HomeService) getHeroMovies(ctx context.Context) ([]HeroMovie, error) {
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
            ID           int    `json:"id"`
            Title        string `json:"title"`
            Overview     string `json:"overview"`
            BackdropPath string `json:"backdrop_path"`
        } `json:"results"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, err
    }

    hero := make([]HeroMovie, len(data.Results))
    var wg sync.WaitGroup

    for i, movie := range data.Results {
        wg.Add(1)

        go func(idx int, m struct {
            ID           int    `json:"id"`
            Title        string `json:"title"`
            Overview     string `json:"overview"`
            BackdropPath string `json:"backdrop_path"`
        }) {
            // Without recover(), a panic in any hero goroutine crashes
            // the gateway. A single bad TMDB response shouldn't take
            // down the whole homepage.
            defer func() {
                _ = recover()
                wg.Done()
            }()
            logo, trailer := s.getMovieAssets(ctx, m.ID)

            hero[idx] = HeroMovie{
                ID:           m.ID,
                Title:        m.Title,
                Overview:     m.Overview,
				BackdropPath: tmdbImage("w1280", m.BackdropPath),
				LogoPath:     logo,
				TrailerKey:   trailer,
            }
        }(i, movie)
    }

    wg.Wait()
    return hero, nil
}

func (s *HomeService) getMovieAssets(ctx context.Context, id int) (string, string) {
    apiKey := os.Getenv("TMDB_API_KEY")

    url := fmt.Sprintf(
        "https://api.themoviedb.org/3/movie/%d/images?api_key=%s",
        id, apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return "", ""
    }
    defer resp.Body.Close()

    var data struct {
        Logos []struct {
            FilePath string `json:"file_path"`
        } `json:"logos"`
    }

    json.NewDecoder(resp.Body).Decode(&data)

    logo := ""
    if len(data.Logos) > 0 {
        logo = tmdbImage("w780", data.Logos[0].FilePath)
    }

    trailer := s.getMovieTrailer(ctx, id)
    return logo, trailer
}

func (s *HomeService) getMovieTrailer(ctx context.Context, id int) string {
    apiKey := os.Getenv("TMDB_API_KEY")

    url := fmt.Sprintf(
        "https://api.themoviedb.org/3/movie/%d/videos?api_key=%s",
        id, apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return ""
    }
    defer resp.Body.Close()

    var data struct {
        Results []struct {
            Key  string `json:"key"`
            Type string `json:"type"`
            Site string `json:"site"`
        } `json:"results"`
    }

    json.NewDecoder(resp.Body).Decode(&data)

    for _, video := range data.Results {
        if video.Site == "YouTube" && video.Type == "Trailer" {
            return video.Key
        }
    }

    return ""
}
