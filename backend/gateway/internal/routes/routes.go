package routes

import (
	"github.com/gofiber/fiber/v2"

	"watchfy/backend/gateway/internal/handlers"
)

type Dependencies struct {
	HomeHandler    *handlers.HomeHandler
	MovieHandler   *handlers.MovieHandler
	DetailsHandler *handlers.DetailsHandler
	WatchHandler   *handlers.WatchHandler
	SearchHandler  *handlers.SearchHandler
}

func Register(app *fiber.App, deps Dependencies) {
	api := app.Group("/api")

	// Home & discovery
	api.Get("/home", deps.HomeHandler.GetHomepage)
	api.Get("/movies/trending", deps.MovieHandler.GetTrending)

	// Search
	api.Get("/search", deps.SearchHandler.Search)

	// Movie details
	api.Get("/details/:id", deps.DetailsHandler.GetDetails)
	api.Get("/details/by-slug/:slug", deps.DetailsHandler.GetDetailsBySlug)
	api.Get("/details/tv/by-slug/:slug", deps.DetailsHandler.GetTVDetailsBySlug)

	// Credits & similar
	api.Get("/details/:id/credits", deps.DetailsHandler.GetCredits)
	api.Get("/details/:id/similar", deps.DetailsHandler.GetSimilar)

	// TV season episodes
	api.Get("/tv/:id/season", deps.DetailsHandler.GetTVSeason)

	// Stream management
	api.Get("/watch/refresh", deps.WatchHandler.RefreshSource)
	api.Get("/watch/prewarm", deps.WatchHandler.Prewarm)
	api.Post("/watch/health/report", deps.WatchHandler.HealthReport)

	// Watch / streaming (use ?mediaType=tv&season=1&episode=1 for TV)
	api.Get("/watch/:id", deps.WatchHandler.GetWatchSource)

	// Subtitles
	api.Get("/subtitles", deps.WatchHandler.GetSubtitles)
}
