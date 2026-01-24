package db

import (
	"context"
	"fmt"
	"strings"
)

// GetStoryByID retrieves a single story by ID
func (db *DB) GetStoryByID(ctx context.Context, id string) (*Story, error) {
	query := `
		SELECT
			s.id, s.title, s.content, s.summary, s.story_type, s.location,
			e.air_date, e.podcast_name,
			s.umap_x, s.umap_y
		FROM stories s
		LEFT JOIN episodes e ON s.episode_id = e.id
		WHERE s.id = $1
	`

	var story Story
	err := db.pool.QueryRow(ctx, query, id).Scan(
		&story.ID, &story.Title, &story.Content, &story.Summary,
		&story.StoryType, &story.Location, &story.AirDate, &story.ShowName,
		&story.UmapX, &story.UmapY,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get story: %w", err)
	}

	return &story, nil
}

// ListStories retrieves stories with pagination and optional filters
func (db *DB) ListStories(ctx context.Context, limit, offset int, filters *BrowseFilters, sort *BrowseSort) ([]Story, int, error) {
	// Build WHERE clause
	var conditions []string
	var args []interface{}
	argNum := 1

	if filters != nil {
		if filters.StoryType != "" {
			conditions = append(conditions, fmt.Sprintf("s.story_type = $%d", argNum))
			args = append(args, filters.StoryType)
			argNum++
		}
		if filters.Location != "" {
			conditions = append(conditions, fmt.Sprintf("s.location ILIKE $%d", argNum))
			args = append(args, "%"+filters.Location+"%")
			argNum++
		}
		if filters.DateFrom != nil {
			conditions = append(conditions, fmt.Sprintf("e.air_date >= $%d", argNum))
			args = append(args, filters.DateFrom)
			argNum++
		}
		if filters.DateTo != nil {
			conditions = append(conditions, fmt.Sprintf("e.air_date <= $%d", argNum))
			args = append(args, filters.DateTo)
			argNum++
		}
	}

	whereClause := ""
	if len(conditions) > 0 {
		whereClause = "WHERE " + strings.Join(conditions, " AND ")
	}

	// Build ORDER BY clause
	orderClause := "ORDER BY e.air_date DESC NULLS LAST, s.title"
	if sort != nil {
		direction := "DESC"
		if sort.Ascending {
			direction = "ASC"
		}
		switch sort.Field {
		case "date":
			orderClause = fmt.Sprintf("ORDER BY e.air_date %s NULLS LAST", direction)
		case "title":
			orderClause = fmt.Sprintf("ORDER BY s.title %s", direction)
		case "type":
			orderClause = fmt.Sprintf("ORDER BY s.story_type %s NULLS LAST", direction)
		}
	}

	// Get total count
	countQuery := fmt.Sprintf(`
		SELECT COUNT(*)
		FROM stories s
		LEFT JOIN episodes e ON s.episode_id = e.id
		%s
	`, whereClause)

	var total int
	err := db.pool.QueryRow(ctx, countQuery, args...).Scan(&total)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to count stories: %w", err)
	}

	// Get stories
	query := fmt.Sprintf(`
		SELECT
			s.id, s.title, s.content, s.summary, s.story_type, s.location,
			e.air_date, e.podcast_name,
			s.umap_x, s.umap_y
		FROM stories s
		LEFT JOIN episodes e ON s.episode_id = e.id
		%s
		%s
		LIMIT $%d OFFSET $%d
	`, whereClause, orderClause, argNum, argNum+1)

	args = append(args, limit, offset)

	rows, err := db.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to list stories: %w", err)
	}
	defer rows.Close()

	var stories []Story
	for rows.Next() {
		var story Story
		err := rows.Scan(
			&story.ID, &story.Title, &story.Content, &story.Summary,
			&story.StoryType, &story.Location, &story.AirDate, &story.ShowName,
			&story.UmapX, &story.UmapY,
		)
		if err != nil {
			return nil, 0, fmt.Errorf("failed to scan story: %w", err)
		}
		stories = append(stories, story)
	}

	return stories, total, nil
}

// TextSearch performs full-text search
func (db *DB) TextSearch(ctx context.Context, query string, limit int) ([]Story, error) {
	sqlQuery := `
		SELECT
			s.id, s.title, s.content, s.summary, s.story_type, s.location,
			e.air_date, e.podcast_name,
			s.umap_x, s.umap_y,
			ts_rank(s.search_vector, plainto_tsquery('english', $1)) as rank
		FROM stories s
		LEFT JOIN episodes e ON s.episode_id = e.id
		WHERE s.search_vector @@ plainto_tsquery('english', $1)
		ORDER BY rank DESC
		LIMIT $2
	`

	rows, err := db.pool.Query(ctx, sqlQuery, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to search: %w", err)
	}
	defer rows.Close()

	var stories []Story
	for rows.Next() {
		var story Story
		err := rows.Scan(
			&story.ID, &story.Title, &story.Content, &story.Summary,
			&story.StoryType, &story.Location, &story.AirDate, &story.ShowName,
			&story.UmapX, &story.UmapY, &story.Rank,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan story: %w", err)
		}
		stories = append(stories, story)
	}

	return stories, nil
}

// GetUmapPoints retrieves all stories with UMAP coordinates
func (db *DB) GetUmapPoints(ctx context.Context) ([]UmapPoint, error) {
	query := `
		SELECT id, title, COALESCE(story_type, 'other'), umap_x, umap_y
		FROM stories
		WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
	`

	rows, err := db.pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to get UMAP points: %w", err)
	}
	defer rows.Close()

	var points []UmapPoint
	for rows.Next() {
		var p UmapPoint
		err := rows.Scan(&p.ID, &p.Title, &p.StoryType, &p.X, &p.Y)
		if err != nil {
			return nil, fmt.Errorf("failed to scan point: %w", err)
		}
		points = append(points, p)
	}

	return points, nil
}

// GetStoryTypes returns all distinct story types in the database
func (db *DB) GetStoryTypes(ctx context.Context) ([]string, error) {
	query := `
		SELECT DISTINCT story_type
		FROM stories
		WHERE story_type IS NOT NULL
		ORDER BY story_type
	`

	rows, err := db.pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to get story types: %w", err)
	}
	defer rows.Close()

	var types []string
	for rows.Next() {
		var t string
		if err := rows.Scan(&t); err != nil {
			return nil, fmt.Errorf("failed to scan type: %w", err)
		}
		types = append(types, t)
	}

	return types, nil
}

// GetStoryCount returns the total number of stories
func (db *DB) GetStoryCount(ctx context.Context) (int, error) {
	var count int
	err := db.pool.QueryRow(ctx, "SELECT COUNT(*) FROM stories").Scan(&count)
	return count, err
}
