package main

import (
	"bytes"
	"errors"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/compress"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"github.com/joho/godotenv"

	"watchfy/backend/gateway/internal/handlers"
	"watchfy/backend/gateway/internal/routes"
	"watchfy/backend/gateway/internal/services"
)

func main() {

	_ = godotenv.Load("../.env", ".env")

	extractorURL := env("WATCHFY_EXTRACTOR_URL", env("VIDKING_EXTRACTOR_URL", "http://localhost:8000"))
	listenAddr := env("WATCHFY_GATEWAY_ADDR", ":8080")

	app := fiber.New(
		fiber.Config{
			AppName:      "Watch!fy Gateway",
			ReadTimeout:  15 * time.Second,
			WriteTimeout: 60 * time.Second,
			IdleTimeout:  90 * time.Second,
			ErrorHandler: func(c *fiber.Ctx, err error) error {
				code := fiber.StatusInternalServerError
				var fiberErr *fiber.Error
				if errors.As(err, &fiberErr) {
					code = fiberErr.Code
				}
				return c.Status(code).JSON(fiber.Map{
					"error":      http.StatusText(code),
					"detail":     err.Error(),
					"request_id": c.Locals("requestid"),
				})
			},
		},
	)

	app.Use(recover.New())
	app.Use(requestid.New())
	app.Use(logger.New(logger.Config{
		Format: `{"time":"${time}","status":${status},"latency":"${latency}","method":"${method}","path":"${path}","request_id":"${locals:requestid}"}` + "\n",
	}))

	app.Use(compress.New(compress.Config{
		Level: compress.LevelBestSpeed,
	}))

	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept",
	}))

	// SERVICES

	homeService :=
		services.NewHomeService()

	movieService :=
		services.NewMovieService()

	detailsService :=
		services.NewDetailsService()

	watchService :=
		services.NewWatchService()

	searchService :=
		services.NewSearchService()

	// HANDLERS

	homeHandler :=
		handlers.NewHomeHandler(
			homeService,
		)

	movieHandler :=
		handlers.NewMovieHandler(
			movieService,
		)

	detailsHandler :=
		handlers.NewDetailsHandler(
			detailsService,
		)

	watchHandler :=
		handlers.NewWatchHandler(
			watchService,
		)

	searchHandler :=
		handlers.NewSearchHandler(
			searchService,
		)

	app.Get("/api/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":        "ok",
			"service":       "watchfy-gateway",
			"extractor_url": extractorURL,
		})
	})

	app.All("/api/black/*", reverseProxy(extractorURL, "/api/black/"))
	app.All("/api/white/*", reverseProxy(extractorURL, "/api/white/"))
	app.All("/api/proxy/*", reverseProxy(extractorURL, "/api/proxy/"))

	// ROUTES

	routes.Register(
		app,
		routes.Dependencies{
			HomeHandler:    homeHandler,
			MovieHandler:   movieHandler,
			DetailsHandler: detailsHandler,
			WatchHandler:   watchHandler,
			SearchHandler:  searchHandler,
		},
	)

	log.Fatal(
		app.Listen(listenAddr),
	)
}

func env(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func reverseProxy(target, prefix string) fiber.Handler {
	targetURL, err := url.Parse(target)
	if err != nil {
		log.Fatalf("invalid proxy target %q: %v", target, err)
	}

	return func(c *fiber.Ctx) error {
		suffix := strings.TrimPrefix(c.Params("*"), "/")
		path := prefix + suffix
		qs := string(c.Request().URI().QueryString())

		u := *targetURL
		u.Path = path
		u.RawQuery = qs

		req, err := http.NewRequestWithContext(c.Context(), c.Method(), u.String(), bytes.NewReader(c.Body()))
		if err != nil {
			return c.Status(http.StatusInternalServerError).SendString(err.Error())
		}

		c.Request().Header.VisitAll(func(key, value []byte) {
			header := string(key)
			if isHopByHop(header) {
				return
			}
			req.Header.Set(header, string(value))
		})
		req.Header.Set("X-Forwarded-Host", c.Hostname())
		req.Header.Set("X-Forwarded-Proto", c.Protocol())
		if id, ok := c.Locals("requestid").(string); ok && id != "" {
			req.Header.Set("X-Request-ID", id)
		}

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			return c.Status(http.StatusBadGateway).SendString(err.Error())
		}
		defer resp.Body.Close()

		for k, vals := range resp.Header {
			if isHopByHop(k) {
				continue
			}
			for _, v := range vals {
				c.Append(k, v)
			}
		}

		c.Status(resp.StatusCode)
		return c.SendStream(resp.Body)
	}
}

func isHopByHop(header string) bool {
	switch strings.ToLower(header) {
	case "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
		"te", "trailer", "transfer-encoding", "upgrade":
		return true
	default:
		return false
	}
}
