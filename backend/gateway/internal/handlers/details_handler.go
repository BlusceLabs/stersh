package handlers

import (
    "context"
    "time"

    "github.com/gofiber/fiber/v2"

    "stersh/backend/gateway/internal/services"
)

type DetailsHandler struct {
    service *services.DetailsService
}

func NewDetailsHandler(
    service *services.DetailsService,
) *DetailsHandler {
    return &DetailsHandler{
        service: service,
    }
}

func (h *DetailsHandler) GetDetails(
    c *fiber.Ctx,
) error {

    id := c.Params("id")

    ctx, cancel := context.WithTimeout(
        context.Background(),
        10*time.Second,
    )

    defer cancel()

    data, err := h.service.GetMovieDetails(
        ctx,
        id,
    )

    if err != nil {
        return fiber.NewError(
            fiber.StatusInternalServerError,
            err.Error(),
        )
    }

    return c.JSON(data)
}

func (h *DetailsHandler) GetDetailsBySlug(
    c *fiber.Ctx,
) error {

    slug := c.Params("slug")

    ctx, cancel := context.WithTimeout(
        context.Background(),
        15*time.Second,
    )

    defer cancel()

    data, err := h.service.GetMovieDetailsBySlug(
        ctx,
        slug,
    )

    if err != nil {
        return fiber.NewError(
            fiber.StatusInternalServerError,
            err.Error(),
        )
    }

    return c.JSON(data)
}

func (h *DetailsHandler) GetTVDetailsBySlug(
	c *fiber.Ctx,
) error {

	slug := c.Params("slug")

	ctx, cancel := context.WithTimeout(
		context.Background(),
		15*time.Second,
	)

	defer cancel()

	data, err := h.service.GetTVDetailsBySlug(
		ctx,
		slug,
	)

	if err != nil {
		return fiber.NewError(
			fiber.StatusInternalServerError,
			err.Error(),
		)
	}

	return c.JSON(data)
}

func (h *DetailsHandler) GetCredits(
	c *fiber.Ctx,
) error {
	id := c.Params("id")
	mediaType := c.Query("mediaType", "movie")

	ctx, cancel := context.WithTimeout(
		context.Background(),
		10*time.Second,
	)
	defer cancel()

	data, err := h.service.GetCredits(ctx, id, mediaType)
	if err != nil {
		return fiber.NewError(
			fiber.StatusInternalServerError,
			err.Error(),
		)
	}

	return c.JSON(data)
}

func (h *DetailsHandler) GetSimilar(
	c *fiber.Ctx,
) error {
	id := c.Params("id")
	mediaType := c.Query("mediaType", "movie")

	ctx, cancel := context.WithTimeout(
		context.Background(),
		10*time.Second,
	)
	defer cancel()

	data, err := h.service.GetSimilar(ctx, id, mediaType)
	if err != nil {
		return fiber.NewError(
			fiber.StatusInternalServerError,
			err.Error(),
		)
	}

	return c.JSON(data)
}

func (h *DetailsHandler) GetTVSeason(
	c *fiber.Ctx,
) error {
	id := c.Params("id")
	season := c.QueryInt("season", 1)

	ctx, cancel := context.WithTimeout(
		context.Background(),
		10*time.Second,
	)
	defer cancel()

	data, err := h.service.GetTVSeason(ctx, id, season)
	if err != nil {
		return fiber.NewError(
			fiber.StatusInternalServerError,
			err.Error(),
		)
	}

	return c.JSON(data)
}