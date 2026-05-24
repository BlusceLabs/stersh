package services

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "os"
    "strings"
    "sync"
    "time"
)

type DetailsService struct {
    cache   *ttlCache
    slugMap map[string]int
    slugMu  sync.RWMutex
}

func NewDetailsService() *DetailsService {
    return &DetailsService{
        cache:   newTTLCache(10 * time.Minute),
        slugMap: make(map[string]int),
    }
}

type SeasonInfo struct {
	SeasonNumber int `json:"seasonNumber"`
	EpisodeCount int `json:"episodeCount"`
}

type ProductionCompany struct {
	ID        int    `json:"id"`
	Name      string `json:"name"`
	LogoPath  string `json:"logoPath"`
	OriginCountry string `json:"originCountry"`
}

type MovieDetails struct {
	ID                 int                 `json:"id"`
	Title              string              `json:"title"`
	Overview           string              `json:"overview"`
	BackdropPath       string              `json:"backdropPath"`
	PosterPath         string              `json:"posterPath"`
	LogoPath           string              `json:"logoPath"`
	Rating             float64             `json:"rating"`
	Runtime            string              `json:"runtime,omitempty"`
	Year               string              `json:"year"`
	Genres             []string            `json:"genres"`
	MediaType          string              `json:"mediaType"`
	ImdbID             string              `json:"imdbId,omitempty"`
	Seasons            []SeasonInfo        `json:"seasons,omitempty"`
	NumberOfSeasons    int                 `json:"numberOfSeasons,omitempty"`
	ProductionCompanies []ProductionCompany `json:"productionCompanies,omitempty"`
}

func (s *DetailsService) GetMovieDetails(ctx context.Context, id string) (*MovieDetails, error) {
    if cached, ok := s.cache.Get("details:" + id); ok {
        return cached.(*MovieDetails), nil
    }

    apiKey := os.Getenv("TMDB_API_KEY")

    url := fmt.Sprintf(
        "https://api.themoviedb.org/3/movie/%s?api_key=%s&append_to_response=images",
        id, apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var data struct {
        ID           int    `json:"id"`
        Title        string `json:"title"`
        Overview     string `json:"overview"`
        BackdropPath string `json:"backdrop_path"`
        PosterPath   string `json:"poster_path"`
        ReleaseDate  string `json:"release_date"`
        Runtime      int    `json:"runtime"`
        VoteAverage  float64 `json:"vote_average"`
        ImdbID       string `json:"imdb_id"`

        Genres []struct {
            Name string `json:"name"`
        } `json:"genres"`

        ProductionCompanies []struct {
            ID          int    `json:"id"`
            Name        string `json:"name"`
            LogoPath    string `json:"logo_path"`
            OriginCountry string `json:"origin_country"`
        } `json:"production_companies"`

        Images struct {
            Logos []struct {
                FilePath string `json:"file_path"`
            } `json:"logos"`
        } `json:"images"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, err
    }

    var genres []string
    for _, g := range data.Genres {
        genres = append(genres, g.Name)
    }

    var companies []ProductionCompany
    for _, pc := range data.ProductionCompanies {
        if pc.LogoPath == "" {
            continue
        }
        companies = append(companies, ProductionCompany{
            ID:        pc.ID,
            Name:      pc.Name,
            LogoPath:  "https://image.tmdb.org/t/p/w200" + pc.LogoPath,
            OriginCountry: pc.OriginCountry,
        })
    }

    logo := ""
    if len(data.Images.Logos) > 0 {
        logo = "https://image.tmdb.org/t/p/w780" + data.Images.Logos[0].FilePath
    }

    var runtime string
    if data.Runtime > 0 {
        if data.Runtime < 60 {
            runtime = fmt.Sprintf("%dm", data.Runtime)
        } else {
            runtime = fmt.Sprintf("%dh %dm", data.Runtime/60, data.Runtime%60)
        }
    }

    result := &MovieDetails{
        ID:                  data.ID,
        Title:               data.Title,
        Overview:            data.Overview,
        BackdropPath:        "https://image.tmdb.org/t/p/w1280" + data.BackdropPath,
        PosterPath:          "https://image.tmdb.org/t/p/w780" + data.PosterPath,
        LogoPath:            logo,
        Rating:              data.VoteAverage,
        Runtime:             runtime,
        Year:                data.ReleaseDate[:4],
        Genres:              genres,
        MediaType:           "movie",
        ImdbID:              data.ImdbID,
        ProductionCompanies: companies,
    }

    s.cache.Set("details:"+id, result)
    return result, nil
}

func (s *DetailsService) GetMovieDetailsBySlug(ctx context.Context, slug string) (*MovieDetails, error) {
    s.slugMu.RLock()
    if id, ok := s.slugMap[slug]; ok {
        s.slugMu.RUnlock()
        return s.GetMovieDetails(ctx, fmt.Sprintf("%d", id))
    }
    s.slugMu.RUnlock()

    apiKey := os.Getenv("TMDB_API_KEY")
    title := strings.ReplaceAll(slug, "-", " ")

    searchURL := fmt.Sprintf(
        "https://api.themoviedb.org/3/search/movie?api_key=%s&query=%s",
        apiKey, url.QueryEscape(title),
    )

    return s.searchAndGetDetails(ctx, slug, title, searchURL, "movie")
}

func (s *DetailsService) GetTVDetails(ctx context.Context, id string) (*MovieDetails, error) {
    cacheKey := "tv:" + id
    if cached, ok := s.cache.Get(cacheKey); ok {
        return cached.(*MovieDetails), nil
    }

    apiKey := os.Getenv("TMDB_API_KEY")

    detailsURL := fmt.Sprintf(
        "https://api.themoviedb.org/3/tv/%s?api_key=%s&append_to_response=images,external_ids",
        id, apiKey,
    )

    req, _ := http.NewRequestWithContext(ctx, "GET", detailsURL, nil)
    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var data struct {
        ID           int    `json:"id"`
        Name         string `json:"name"`
        Overview     string `json:"overview"`
        BackdropPath string `json:"backdrop_path"`
        PosterPath   string `json:"poster_path"`
        FirstAirDate string `json:"first_air_date"`
        VoteAverage  float64 `json:"vote_average"`

        NumberOfSeasons int `json:"number_of_seasons"`
        Seasons []struct {
            SeasonNumber int `json:"season_number"`
            EpisodeCount int `json:"episode_count"`
        } `json:"seasons"`

        Genres []struct {
            Name string `json:"name"`
        } `json:"genres"`

        ProductionCompanies []struct {
            ID          int    `json:"id"`
            Name        string `json:"name"`
            LogoPath    string `json:"logo_path"`
            OriginCountry string `json:"origin_country"`
        } `json:"production_companies"`

        Images struct {
            Logos []struct {
                FilePath string `json:"file_path"`
            } `json:"logos"`
        } `json:"images"`

        ExternalIDs struct {
            ImdbID string `json:"imdb_id"`
        } `json:"external_ids"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, err
    }

    var genres []string
    for _, g := range data.Genres {
        genres = append(genres, g.Name)
    }

    var companies []ProductionCompany
    for _, pc := range data.ProductionCompanies {
        if pc.LogoPath == "" {
            continue
        }
        companies = append(companies, ProductionCompany{
            ID:        pc.ID,
            Name:      pc.Name,
            LogoPath:  "https://image.tmdb.org/t/p/w200" + pc.LogoPath,
            OriginCountry: pc.OriginCountry,
        })
    }

    logo := ""
    if len(data.Images.Logos) > 0 {
        logo = "https://image.tmdb.org/t/p/w780" + data.Images.Logos[0].FilePath
    }

    year := ""
    if len(data.FirstAirDate) >= 4 {
        year = data.FirstAirDate[:4]
    }

    var seasons []SeasonInfo
    for _, s := range data.Seasons {
        seasons = append(seasons, SeasonInfo{
            SeasonNumber: s.SeasonNumber,
            EpisodeCount: s.EpisodeCount,
        })
    }

    result := &MovieDetails{
        ID:                  data.ID,
        Title:               data.Name,
        Overview:            data.Overview,
        BackdropPath:        "https://image.tmdb.org/t/p/w1280" + data.BackdropPath,
        PosterPath:          "https://image.tmdb.org/t/p/w780" + data.PosterPath,
        LogoPath:            logo,
        Rating:              data.VoteAverage,
        Year:                year,
        Genres:              genres,
        MediaType:           "tv",
        ImdbID:              data.ExternalIDs.ImdbID,
        Seasons:             seasons,
        NumberOfSeasons:     data.NumberOfSeasons,
        ProductionCompanies: companies,
    }

    s.cache.Set(cacheKey, result)
    return result, nil
}

func (s *DetailsService) GetTVDetailsBySlug(ctx context.Context, slug string) (*MovieDetails, error) {
    apiKey := os.Getenv("TMDB_API_KEY")
    title := strings.ReplaceAll(slug, "-", " ")

    searchURL := fmt.Sprintf(
        "https://api.themoviedb.org/3/search/tv?api_key=%s&query=%s",
        apiKey, url.QueryEscape(title),
    )

    return s.searchAndGetDetails(ctx, slug, title, searchURL, "tv")
}

func (s *DetailsService) searchAndGetDetails(ctx context.Context, slug, title, searchURL, mediaType string) (*MovieDetails, error) {
    req, _ := http.NewRequestWithContext(ctx, "GET", searchURL, nil)

    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var searchResult struct {
        Results []struct {
            ID int `json:"id"`
        } `json:"results"`
    }

    if err := json.NewDecoder(resp.Body).Decode(&searchResult); err != nil {
        return nil, err
    }

    if len(searchResult.Results) == 0 {
        return nil, fmt.Errorf("%s not found: %s", mediaType, title)
    }

    tmdbID := searchResult.Results[0].ID

    s.slugMu.Lock()
    s.slugMap[slug] = tmdbID
    s.slugMu.Unlock()

    if mediaType == "tv" {
        return s.GetTVDetails(ctx, fmt.Sprintf("%d", tmdbID))
    }
    return s.GetMovieDetails(ctx, fmt.Sprintf("%d", tmdbID))
}

// ─── CREDITS ─────────────────────────────────────────

type CastMember struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Character   string `json:"character"`
	ProfilePath string `json:"profilePath"`
	Order       int    `json:"order"`
}

type CreditsResponse struct {
	Cast []CastMember `json:"cast"`
}

func (s *DetailsService) GetCredits(ctx context.Context, id string, mediaType string) (*CreditsResponse, error) {
	cacheKey := fmt.Sprintf("credits:%s:%s", mediaType, id)
	if cached, ok := s.cache.Get(cacheKey); ok {
		return cached.(*CreditsResponse), nil
	}

	apiKey := os.Getenv("TMDB_API_KEY")
	var endpoint string
	if mediaType == "tv" {
		endpoint = fmt.Sprintf("https://api.themoviedb.org/3/tv/%s/credits?api_key=%s", id, apiKey)
	} else {
		endpoint = fmt.Sprintf("https://api.themoviedb.org/3/movie/%s/credits?api_key=%s", id, apiKey)
	}

	req, _ := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data struct {
		Cast []struct {
			ID          int    `json:"id"`
			Name        string `json:"name"`
			Character   string `json:"character"`
			ProfilePath string `json:"profile_path"`
			Order       int    `json:"order"`
		} `json:"cast"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	var cast []CastMember
	for _, c := range data.Cast {
		cast = append(cast, CastMember{
			ID:          c.ID,
			Name:        c.Name,
			Character:   c.Character,
			ProfilePath: "https://image.tmdb.org/t/p/w200" + c.ProfilePath,
			Order:       c.Order,
		})
	}

	result := &CreditsResponse{Cast: cast}
	s.cache.Set(cacheKey, result)
	return result, nil
}

// ─── SIMILAR ─────────────────────────────────────────

type SimilarItem struct {
	ID           int      `json:"id"`
	Title        string   `json:"title"`
	Overview     string   `json:"overview"`
	PosterPath   string   `json:"posterPath"`
	Year         string   `json:"year"`
	MediaType    string   `json:"mediaType"`
}

type SimilarResponse struct {
	Results []SimilarItem `json:"results"`
}

func (s *DetailsService) GetSimilar(ctx context.Context, id string, mediaType string) (*SimilarResponse, error) {
	cacheKey := fmt.Sprintf("similar:%s:%s", mediaType, id)
	if cached, ok := s.cache.Get(cacheKey); ok {
		return cached.(*SimilarResponse), nil
	}

	apiKey := os.Getenv("TMDB_API_KEY")
	var endpoint string
	if mediaType == "tv" {
		endpoint = fmt.Sprintf("https://api.themoviedb.org/3/tv/%s/similar?api_key=%s", id, apiKey)
	} else {
		endpoint = fmt.Sprintf("https://api.themoviedb.org/3/movie/%s/similar?api_key=%s", id, apiKey)
	}

	req, _ := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
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
			Overview    string `json:"overview"`
			PosterPath  string `json:"poster_path"`
			ReleaseDate string `json:"release_date"`
			FirstAirDate string `json:"first_air_date"`
		} `json:"results"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	var results []SimilarItem
	for _, r := range data.Results {
		title := r.Title
		if title == "" {
			title = r.Name
		}
		year := ""
		if mediaType == "tv" && len(r.FirstAirDate) >= 4 {
			year = r.FirstAirDate[:4]
		} else if len(r.ReleaseDate) >= 4 {
			year = r.ReleaseDate[:4]
		}
		results = append(results, SimilarItem{
			ID:         r.ID,
			Title:      title,
			Overview:   r.Overview,
			PosterPath: "https://image.tmdb.org/t/p/w500" + r.PosterPath,
			Year:       year,
			MediaType:  mediaType,
		})
	}

	result := &SimilarResponse{Results: results}
	s.cache.Set(cacheKey, result)
	return result, nil
}

// ─── TV SEASON EPISODES ────────────────────────────

type Episode struct {
	EpisodeNumber int    `json:"episodeNumber"`
	Name          string `json:"name"`
	Overview      string `json:"overview"`
	StillPath     string `json:"stillPath"`
	AirDate       string `json:"airDate"`
	Runtime       int    `json:"runtime"`
}

type SeasonDetailsResponse struct {
	SeasonNumber int       `json:"seasonNumber"`
	Episodes     []Episode `json:"episodes"`
}

func (s *DetailsService) GetTVSeason(ctx context.Context, id string, season int) (*SeasonDetailsResponse, error) {
	cacheKey := fmt.Sprintf("season:%s:%d", id, season)
	if cached, ok := s.cache.Get(cacheKey); ok {
		return cached.(*SeasonDetailsResponse), nil
	}

	apiKey := os.Getenv("TMDB_API_KEY")
	endpoint := fmt.Sprintf("https://api.themoviedb.org/3/tv/%s/season/%d?api_key=%s", id, season, apiKey)

	req, _ := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data struct {
		SeasonNumber int `json:"season_number"`
		Episodes []struct {
			EpisodeNumber int    `json:"episode_number"`
			Name          string `json:"name"`
			Overview      string `json:"overview"`
			StillPath     string `json:"still_path"`
			AirDate       string `json:"air_date"`
			Runtime       int    `json:"runtime"`
		} `json:"episodes"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	var episodes []Episode
	for _, e := range data.Episodes {
		episodes = append(episodes, Episode{
			EpisodeNumber: e.EpisodeNumber,
			Name:          e.Name,
			Overview:      e.Overview,
			StillPath:     "https://image.tmdb.org/t/p/w500" + e.StillPath,
			AirDate:       e.AirDate,
			Runtime:       e.Runtime,
		})
	}

	result := &SeasonDetailsResponse{
		SeasonNumber: data.SeasonNumber,
		Episodes:     episodes,
	}
	s.cache.Set(cacheKey, result)
	return result, nil
}
