package handlers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"

	"stersh/backend/gateway/internal/services"
)

type SearchHandler struct {
	service *services.SearchService
}

func NewSearchHandler(service *services.SearchService) *SearchHandler {
	return &SearchHandler{service: service}
}

func (h *SearchHandler) Search(c *fiber.Ctx) error {
	query := c.Query("q", "")
	if query == "" {
		return c.JSON(fiber.Map{"results": []any{}})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	data, err := h.service.Search(ctx, query)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, err.Error())
	}

	return c.JSON(data)
}
