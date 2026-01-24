package db

import (
	"time"

	"github.com/jackc/pgx/v5/pgtype"
)

// Story represents a paranormal story from the database
type Story struct {
	ID        string
	Title     string
	Content   string
	Summary   pgtype.Text
	StoryType pgtype.Text
	Location  pgtype.Text
	AirDate   pgtype.Date
	ShowName  pgtype.Text

	// Scores from search
	Rank       float64
	Similarity float64

	// UMAP coordinates for visualization
	UmapX pgtype.Float8
	UmapY pgtype.Float8
}

// StoryTypes defines all valid story types for filtering
var StoryTypes = []string{
	"ghost",
	"shadow_person",
	"cryptid",
	"ufo",
	"alien_encounter",
	"haunting",
	"poltergeist",
	"precognition",
	"nde",
	"obe",
	"time_slip",
	"doppelganger",
	"sleep_paralysis",
	"possession",
	"other",
}

// StoryTypeColors maps story types to terminal colors
var StoryTypeColors = map[string]string{
	"ghost":           "#8B8BFF", // Light blue
	"shadow_person":   "#4A4A4A", // Dark gray
	"cryptid":         "#228B22", // Forest green
	"ufo":             "#FFD700", // Gold
	"alien_encounter": "#00FF00", // Bright green
	"haunting":        "#9370DB", // Medium purple
	"poltergeist":     "#FF6347", // Tomato red
	"precognition":    "#00CED1", // Dark cyan
	"nde":             "#FFFFFF", // White
	"obe":             "#E6E6FA", // Lavender
	"time_slip":       "#FF69B4", // Hot pink
	"doppelganger":    "#DAA520", // Goldenrod
	"sleep_paralysis": "#483D8B", // Dark slate blue
	"possession":      "#8B0000", // Dark red
	"other":           "#808080", // Gray
}

// FormattedDate returns the air date as a string
func (s *Story) FormattedDate() string {
	if !s.AirDate.Valid {
		return "Unknown"
	}
	return s.AirDate.Time.Format("2006-01-02")
}

// FormattedType returns the story type or "unknown"
func (s *Story) FormattedType() string {
	if !s.StoryType.Valid {
		return "unknown"
	}
	return s.StoryType.String
}

// FormattedLocation returns the location or "Unknown"
func (s *Story) FormattedLocation() string {
	if !s.Location.Valid {
		return "Unknown"
	}
	return s.Location.String
}

// FormattedShow returns the show name or "Unknown"
func (s *Story) FormattedShow() string {
	if !s.ShowName.Valid {
		return "Unknown"
	}
	return s.ShowName.String
}

// Snippet returns a truncated version of the content
func (s *Story) Snippet(maxLen int) string {
	if len(s.Content) <= maxLen {
		return s.Content
	}
	return s.Content[:maxLen] + "..."
}

// UmapPoint represents a story's position in UMAP space
type UmapPoint struct {
	ID        string
	Title     string
	StoryType string
	X         float64
	Y         float64
}

// SearchResult combines a story with its search scores
type SearchResult struct {
	Story       Story
	TextScore   float64
	VectorScore float64
	HybridScore float64
}

// BrowseFilters holds filters for the browse view
type BrowseFilters struct {
	StoryType string
	Location  string
	DateFrom  *time.Time
	DateTo    *time.Time
}

// BrowseSort defines sorting options
type BrowseSort struct {
	Field     string // "date", "title", "type"
	Ascending bool
}
