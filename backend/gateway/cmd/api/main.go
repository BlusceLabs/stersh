package main

import (
	"log"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"

	"watchfy/backend/gateway/internal/handlers"
	"watchfy/backend/gateway/internal/routes"
	"watchfy/backend/gateway/internal/services"
)

func main() {
	app := fiber.New()

	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept",
	}))

	deps := routes.Dependencies{
		HomeHandler:    handlers.NewHomeHandler(services.NewHomeService()),
		MovieHandler:   handlers.NewMovieHandler(services.NewMovieService()),
		DetailsHandler: handlers.NewDetailsHandler(services.NewDetailsService()),
		WatchHandler:   handlers.NewWatchHandler(services.NewWatchService()),
	}

	routes.Register(app, deps)

	log.Fatal(app.Listen(":8080"))
}
