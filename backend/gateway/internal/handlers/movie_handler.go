package handlers

import (
    "context"
    "time"

    "github.com/gofiber/fiber/v2"

    "watchfy/backend/gateway/internal/services"
)

type MovieHandler struct {
    service *services.MovieService
}

func NewMovieHandler(
    service *services.MovieService,
) *MovieHandler {
    return &MovieHandler{
        service: service,
    }
}

func (h *MovieHandler) GetTrending(
    c *fiber.Ctx,
) error {

    ctx, cancel := context.WithTimeout(
        context.Background(),
        10*time.Second,
    )

    defer cancel()

    data, err := h.service.GetTrending(ctx)

    if err != nil {
        return fiber.NewError(
            fiber.StatusInternalServerError,
            err.Error(),
        )
    }

    return c.JSON(data)
}
