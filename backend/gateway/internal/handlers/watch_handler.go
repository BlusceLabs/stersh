package handlers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"

	"watchfy/backend/gateway/internal/services"
)

type WatchHandler struct {
	service *services.WatchService
}

func NewWatchHandler(service *services.WatchService) *WatchHandler {
	return &WatchHandler{service: service}
}

func (h *WatchHandler) GetWatchSource(c *fiber.Ctx) error {
	id := c.Params("id")
	mediaType := c.Query("mediaType", "movie")
	server := c.Query("server", "Black")

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	var data *services.WatchResponse
	var err error
	if mediaType == "tv" {
		data, err = h.service.GetSourceTV(ctx, id, c.QueryInt("season", 1), c.QueryInt("episode", 1), server)
	} else {
		data, err = h.service.GetSource(ctx, id, server)
	}
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}
	return c.JSON(data)
}

func (h *WatchHandler) RefreshSource(c *fiber.Ctx) error {
	id := c.Query("tmdbId", c.Params("id"))
	mediaType := c.Query("mediaType", "movie")
	season := c.QueryInt("season", 1)
	episode := c.QueryInt("episode", 1)
	server := c.Query("server", "Black")

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	data, err := h.service.RefreshSource(ctx, id, mediaType, season, episode, server)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}
	return c.JSON(data)
}

func (h *WatchHandler) GetSubtitles(c *fiber.Ctx) error {
	imdbId := c.Query("imdbId", "")
	if imdbId == "" {
		return fiber.NewError(fiber.StatusBadRequest, "imdbId is required")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	data, err := h.service.GetSubtitles(ctx, imdbId)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}
	return c.JSON(data)
}

func (h *WatchHandler) Prewarm(c *fiber.Ctx) error {
	id := c.Query("tmdbId", c.Params("id"))
	mediaType := c.Query("mediaType", "movie")
	season := c.QueryInt("season", 1)
	episode := c.QueryInt("episode", 1)
	server := c.Query("server", "Black")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	data, err := h.service.Prewarm(ctx, id, mediaType, season, episode, server)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}
	return c.JSON(data)
}

func (h *WatchHandler) HealthReport(c *fiber.Ctx) error {
	server := c.Query("server", "Black")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	data, err := h.service.HealthReport(ctx, server)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}
	return c.JSON(data)
}
