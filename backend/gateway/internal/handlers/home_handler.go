package handlers

import (
    "context"
    "time"

    "github.com/gofiber/fiber/v2"

    "watchfy/backend/gateway/internal/services"
)

type HomeHandler struct {
    homeService *services.HomeService
}

func NewHomeHandler(
    homeService *services.HomeService,
) *HomeHandler {
    return &HomeHandler{
        homeService: homeService,
    }
}

func (h *HomeHandler) GetHomepage(c *fiber.Ctx) error {
    ctx, cancel := context.WithTimeout(
        context.Background(),
        15*time.Second,
    )
    defer cancel()

    response, err := h.homeService.GetHomepage(ctx)

    if err != nil {
        return fiber.NewError(
            fiber.StatusInternalServerError,
            err.Error(),
        )
    }

    return c.JSON(response)
}
