package app

import (
	"paranormal-tui/internal/db"

	tea "github.com/charmbracelet/bubbletea"
)

// View represents which view is currently active
type View int

const (
	ViewSearch View = iota
	ViewBrowse
	ViewVisualize
)

// Messages for async operations

// StoriesLoadedMsg is sent when stories are loaded from the database
type StoriesLoadedMsg struct {
	Stories []db.Story
	Total   int
	Err     error
}

// SearchResultsMsg is sent when search completes
type SearchResultsMsg struct {
	Results []db.Story
	Query   string
	Err     error
}

// StorySelectedMsg is sent when a story is selected for detail view
type StorySelectedMsg struct {
	Story *db.Story
	Err   error
}

// UmapPointsMsg is sent when UMAP points are loaded
type UmapPointsMsg struct {
	Points []db.UmapPoint
	Err    error
}

// DBConnectedMsg is sent when database connection succeeds
type DBConnectedMsg struct {
	DB         *db.DB
	StoryCount int
	Err        error
}

// ErrorMsg represents an error that occurred
type ErrorMsg struct {
	Err error
}

// SwitchViewMsg requests a view switch
type SwitchViewMsg struct {
	View View
}

// ShowDetailMsg shows the detail modal for a story
type ShowDetailMsg struct {
	StoryID string
}

// CloseDetailMsg closes the detail modal
type CloseDetailMsg struct{}

// Commands

// LoadStoriesCmd creates a command to load stories
func LoadStoriesCmd(database *db.DB, limit, offset int, filters *db.BrowseFilters, sort *db.BrowseSort) tea.Cmd {
	return func() tea.Msg {
		stories, total, err := database.ListStories(nil, limit, offset, filters, sort)
		return StoriesLoadedMsg{Stories: stories, Total: total, Err: err}
	}
}

// SearchCmd creates a command to perform a search
func SearchCmd(database *db.DB, query string, limit int) tea.Cmd {
	return func() tea.Msg {
		results, err := database.TextSearch(nil, query, limit)
		return SearchResultsMsg{Results: results, Query: query, Err: err}
	}
}

// LoadStoryCmd creates a command to load a single story
func LoadStoryCmd(database *db.DB, id string) tea.Cmd {
	return func() tea.Msg {
		story, err := database.GetStoryByID(nil, id)
		return StorySelectedMsg{Story: story, Err: err}
	}
}

// LoadUmapPointsCmd creates a command to load UMAP points
func LoadUmapPointsCmd(database *db.DB) tea.Cmd {
	return func() tea.Msg {
		points, err := database.GetUmapPoints(nil)
		return UmapPointsMsg{Points: points, Err: err}
	}
}
