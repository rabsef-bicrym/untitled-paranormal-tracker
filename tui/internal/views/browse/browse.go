package browse

import (
	"context"
	"fmt"
	"strings"

	"paranormal-tui/internal/db"
	"paranormal-tui/internal/styles"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

const pageSize = 15

// Model represents the browse view
type Model struct {
	database *db.DB
	stories  []db.Story
	total    int
	cursor   int
	page     int
	loading  bool
	err      error
	width    int
	height   int

	// Filters
	filters    db.BrowseFilters
	sort       db.BrowseSort
	showFilter bool
	filterIdx  int
	storyTypes []string
}

// New creates a new browse model
func New(database *db.DB) Model {
	return Model{
		database: database,
		sort: db.BrowseSort{
			Field:     "date",
			Ascending: false,
		},
		storyTypes: db.StoryTypes,
	}
}

// Init initializes the model and loads initial data
func (m Model) Init() tea.Cmd {
	return m.loadStories()
}

// SetSize sets the view dimensions
func (m *Model) SetSize(width, height int) {
	m.width = width
	m.height = height
}

// SetDatabase sets the database connection
func (m *Model) SetDatabase(database *db.DB) {
	m.database = database
}

func (m Model) loadStories() tea.Cmd {
	if m.database == nil {
		return nil
	}

	return func() tea.Msg {
		ctx := context.Background()
		offset := m.page * pageSize
		stories, total, err := m.database.ListStories(ctx, pageSize, offset, &m.filters, &m.sort)
		return StoriesLoadedMsg{Stories: stories, Total: total, Err: err}
	}
}

// StoriesLoadedMsg indicates stories have been loaded
type StoriesLoadedMsg struct {
	Stories []db.Story
	Total   int
	Err     error
}

// StorySelectedMsg indicates a story was selected
type StorySelectedMsg struct {
	Story db.Story
}

// Update handles messages
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case StoriesLoadedMsg:
		m.loading = false
		if msg.Err != nil {
			m.err = msg.Err
			return m, nil
		}
		m.stories = msg.Stories
		m.total = msg.Total
		if m.cursor >= len(m.stories) {
			m.cursor = max(0, len(m.stories)-1)
		}
		return m, nil

	case tea.KeyMsg:
		// Handle filter mode
		if m.showFilter {
			return m.handleFilterKeys(msg)
		}

		switch {
		case key.Matches(msg, key.NewBinding(key.WithKeys("up", "k"))):
			if m.cursor > 0 {
				m.cursor--
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("down", "j"))):
			if m.cursor < len(m.stories)-1 {
				m.cursor++
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("n", "]"))):
			// Next page
			maxPage := (m.total - 1) / pageSize
			if m.page < maxPage {
				m.page++
				m.cursor = 0
				m.loading = true
				return m, m.loadStories()
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("p", "["))):
			// Previous page
			if m.page > 0 {
				m.page--
				m.cursor = 0
				m.loading = true
				return m, m.loadStories()
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("enter"))):
			if len(m.stories) > 0 && m.cursor < len(m.stories) {
				return m, func() tea.Msg {
					return StorySelectedMsg{Story: m.stories[m.cursor]}
				}
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("f"))):
			m.showFilter = true
			m.filterIdx = 0
		case key.Matches(msg, key.NewBinding(key.WithKeys("s"))):
			// Cycle sort field
			switch m.sort.Field {
			case "date":
				m.sort.Field = "title"
			case "title":
				m.sort.Field = "type"
			default:
				m.sort.Field = "date"
			}
			m.page = 0
			m.cursor = 0
			m.loading = true
			return m, m.loadStories()
		case key.Matches(msg, key.NewBinding(key.WithKeys("S"))):
			// Toggle sort direction
			m.sort.Ascending = !m.sort.Ascending
			m.page = 0
			m.cursor = 0
			m.loading = true
			return m, m.loadStories()
		case key.Matches(msg, key.NewBinding(key.WithKeys("c"))):
			// Clear filters
			m.filters = db.BrowseFilters{}
			m.page = 0
			m.cursor = 0
			m.loading = true
			return m, m.loadStories()
		}
	}

	return m, nil
}

func (m Model) handleFilterKeys(msg tea.KeyMsg) (Model, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.showFilter = false
		return m, nil
	case "up", "k":
		if m.filterIdx > 0 {
			m.filterIdx--
		}
	case "down", "j":
		if m.filterIdx < len(m.storyTypes) {
			m.filterIdx++
		}
	case "enter":
		if m.filterIdx == 0 {
			// "All" option
			m.filters.StoryType = ""
		} else {
			m.filters.StoryType = m.storyTypes[m.filterIdx-1]
		}
		m.showFilter = false
		m.page = 0
		m.cursor = 0
		m.loading = true
		return m, m.loadStories()
	}
	return m, nil
}

// Reload refreshes the story list
func (m *Model) Reload() tea.Cmd {
	m.loading = true
	return m.loadStories()
}

// View renders the browse view
func (m Model) View() string {
	if m.showFilter {
		return m.renderFilterView()
	}

	var b strings.Builder

	// Header
	header := styles.HeaderStyle.Width(m.width - 4).Render(
		fmt.Sprintf("Browse Stories (%d total)", m.total),
	)
	b.WriteString(header)
	b.WriteString("\n")

	if m.loading {
		b.WriteString("\n  Loading...")
		return b.String()
	}

	if m.err != nil {
		b.WriteString("\n")
		b.WriteString(styles.ErrorStyle.Render(fmt.Sprintf("  Error: %v", m.err)))
		return b.String()
	}

	if len(m.stories) == 0 {
		b.WriteString("\n  No stories found.")
		return b.String()
	}

	// Calculate available height for list
	listHeight := m.height - 8 // Header, footer, margins

	// Story list
	for i, story := range m.stories {
		if i >= listHeight {
			break
		}

		// Cursor indicator
		cursor := "  "
		itemStyle := styles.NormalItemStyle
		if i == m.cursor {
			cursor = "▸ "
			itemStyle = styles.SelectedItemStyle
		}

		// Format story line
		typeStr := story.FormattedType()
		dateStr := story.FormattedDate()

		// Truncate title if needed
		maxTitleLen := m.width - 40
		title := story.Title
		if len(title) > maxTitleLen {
			title = title[:maxTitleLen-3] + "..."
		}

		line := fmt.Sprintf("%s%-*s  %s  %s",
			cursor,
			maxTitleLen,
			title,
			styles.TypeBadge(typeStr),
			styles.DimStyle.Render(dateStr),
		)

		if i == m.cursor {
			b.WriteString(itemStyle.Width(m.width - 4).Render(line))
		} else {
			b.WriteString(line)
		}
		b.WriteString("\n")
	}

	// Footer with pagination and help
	b.WriteString("\n")

	// Pagination info
	currentPage := m.page + 1
	totalPages := (m.total + pageSize - 1) / pageSize
	if totalPages == 0 {
		totalPages = 1
	}

	// Active filters
	filterInfo := ""
	if m.filters.StoryType != "" {
		filterInfo = fmt.Sprintf(" | Filter: %s", m.filters.StoryType)
	}

	// Sort info
	sortDir := "↓"
	if m.sort.Ascending {
		sortDir = "↑"
	}
	sortInfo := fmt.Sprintf(" | Sort: %s%s", m.sort.Field, sortDir)

	footer := styles.DimStyle.Render(
		fmt.Sprintf("Page %d/%d%s%s | n/p: page • f: filter • s/S: sort • c: clear • enter: view",
			currentPage, totalPages, filterInfo, sortInfo),
	)
	b.WriteString(footer)

	return b.String()
}

func (m Model) renderFilterView() string {
	var b strings.Builder

	b.WriteString(styles.HeaderStyle.Render("Filter by Story Type"))
	b.WriteString("\n\n")

	// "All" option
	cursor := "  "
	if m.filterIdx == 0 {
		cursor = "▸ "
	}
	style := styles.NormalItemStyle
	if m.filterIdx == 0 {
		style = styles.SelectedItemStyle
	}
	allLabel := "All Types"
	if m.filters.StoryType == "" {
		allLabel += " (current)"
	}
	b.WriteString(style.Render(cursor + allLabel))
	b.WriteString("\n")

	// Story types
	for i, t := range m.storyTypes {
		cursor := "  "
		if i+1 == m.filterIdx {
			cursor = "▸ "
		}
		style := styles.NormalItemStyle
		if i+1 == m.filterIdx {
			style = styles.SelectedItemStyle
		}

		label := fmt.Sprintf("%s %s", styles.TypeBadge(t), t)
		if m.filters.StoryType == t {
			label += " (current)"
		}
		b.WriteString(style.Render(cursor + label))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(styles.DimStyle.Render("↑↓: navigate • enter: select • esc: cancel"))

	return lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(styles.Primary).
		Padding(1, 2).
		Render(b.String())
}

// SelectedStory returns the currently selected story, if any
func (m Model) SelectedStory() *db.Story {
	if len(m.stories) > 0 && m.cursor < len(m.stories) {
		return &m.stories[m.cursor]
	}
	return nil
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
