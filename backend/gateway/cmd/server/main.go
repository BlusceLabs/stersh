package main

import (
    "io"
    "log"
    "net/http"
    "net/url"
    "strings"

    "github.com/gofiber/fiber/v2"
    "github.com/gofiber/fiber/v2/middleware/cors"
    "github.com/gofiber/fiber/v2/middleware/compress"
    "github.com/joho/godotenv"

    "watchfy/backend/gateway/internal/handlers"
    "watchfy/backend/gateway/internal/routes"
    "watchfy/backend/gateway/internal/services"
)

func main() {

    _ = godotenv.Load("../.env", ".env")

    app := fiber.New(
        fiber.Config{
            AppName: "Watch!fy Gateway",
        },
    )

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

    // Proxy /api/vidking/* and /api/white/* to Python streaming service
    app.All("/api/vidking/*", reverseProxy("http://localhost:8000", "/api/vidking/"))
    app.All("/api/white/*", reverseProxy("http://localhost:8000", "/api/white/"))

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
        app.Listen(":8080"),
    )
}

func reverseProxy(target, prefix string) fiber.Handler {
    targetURL, _ := url.Parse(target)

    return func(c *fiber.Ctx) error {
        suffix := strings.TrimPrefix(c.Params("*"), "/")
        path := prefix + suffix
        qs := string(c.Request().URI().QueryString())

        u := *targetURL
        u.Path = path
        u.RawQuery = qs

        body := io.NopCloser(strings.NewReader(string(c.Body())))
        req, err := http.NewRequest(c.Method(), u.String(), body)
        if err != nil {
            return c.Status(http.StatusInternalServerError).SendString(err.Error())
        }

        c.Request().Header.VisitAll(func(key, value []byte) {
            req.Header.Set(string(key), string(value))
        })
        req.Header.Set("X-Forwarded-Host", req.Host)

        resp, err := http.DefaultClient.Do(req)
        if err != nil {
            return c.Status(http.StatusBadGateway).SendString(err.Error())
        }
        defer resp.Body.Close()

        for k, vals := range resp.Header {
            for _, v := range vals {
                c.Response().Header.Set(k, v)
            }
        }

        c.Status(resp.StatusCode)
        respBody, _ := io.ReadAll(resp.Body)
        return c.Send(respBody)
    }
}
