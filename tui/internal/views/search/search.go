package search

import (
	"context"
	"fmt"
	"strings"

	"paranormal-tui/internal/db"
	"paranormal-tui/internal/styles"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

// SearchMode represents the search mode
type SearchMode int

const (
	ModeText SearchMode = iota
	ModeHybrid
	ModeVector
)

func (m SearchMode) String() string {
	switch m {
	case ModeText:
		return "Text"
	case ModeHybrid:
		return "Hybrid"
	case ModeVector:
		return "Vector"
	default:
		return "Unknown"
	}
}

// Model represents the search view
type Model struct {
	database   *db.DB
	input      textinput.Model
	results    []db.Story
	cursor     int
	mode       SearchMode
	searching  bool
	lastQuery  string
	err        error
	width      int
	height     int
	inputFocus bool
}

// New creates a new search model
func New(database *db.DB) Model {
	ti := textinput.New()
	ti.Placeholder = "Search paranormal stories..."
	ti.Focus()
	ti.CharLimit = 256
	ti.Width = 50

	return Model{
		database:   database,
		input:      ti,
		mode:       ModeText, // Default to text-only (no API key needed)
		inputFocus: true,
	}
}

// Init initializes the model
func (m Model) Init() tea.Cmd {
	return textinput.Blink
}

// SetSize sets the view dimensions
func (m *Model) SetSize(width, height int) {
	m.width = width
	m.height = height
	m.input.Width = width - 20
}

// SetDatabase sets the database connection
func (m *Model) SetDatabase(database *db.DB) {
	m.database = database
}

// Focus gives focus to the search input
func (m *Model) Focus() {
	m.input.Focus()
	m.inputFocus = true
}

// SearchResultsMsg indicates search completed
type SearchResultsMsg struct {
	Results []db.Story
	Query   string
	Err     error
}

// StorySelectedMsg indicates a story was selected
type StorySelectedMsg struct {
	Story db.Story
}

func (m Model) performSearch() tea.Cmd {
	if m.database == nil {
		return nil
	}

	query := m.input.Value()
	if query == "" {
		return nil
	}

	return func() tea.Msg {
		ctx := context.Background()
		// For now, only text search is implemented (no Voyage API in Go)
		results, err := m.database.TextSearch(ctx, query, 20)
		return SearchResultsMsg{Results: results, Query: query, Err: err}
	}
}

// Update handles messages
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case SearchResultsMsg:
		m.searching = false
		if msg.Err != nil {
			m.err = msg.Err
			return m, nil
		}
		m.results = msg.Results
		m.lastQuery = msg.Query
		m.cursor = 0
		m.inputFocus = false
		m.input.Blur()
		return m, nil

	case tea.KeyMsg:
		if m.inputFocus {
			switch msg.String() {
			case "enter":
				if m.input.Value() != "" {
					m.searching = true
					m.err = nil
					return m, m.performSearch()
				}
			case "esc":
				if m.input.Value() != "" {
					m.input.SetValue("")
				} else if len(m.results) > 0 {
					m.inputFocus = false
					m.input.Blur()
				}
			case "tab":
				// Toggle search mode
				m.mode = (m.mode + 1) % 3
			case "down":
				if len(m.results) > 0 {
					m.inputFocus = false
					m.input.Blur()
				}
			default:
				var cmd tea.Cmd
				m.input, cmd = m.input.Update(msg)
				cmds = append(cmds, cmd)
			}
		} else {
			switch {
			case key.Matches(msg, key.NewBinding(key.WithKeys("up", "k"))):
				if m.cursor > 0 {
					m.cursor--
				} else {
					// Go back to input
					m.inputFocus = true
					m.input.Focus()
				}
			case key.Matches(msg, key.NewBinding(key.WithKeys("down", "j"))):
				if m.cursor < len(m.results)-1 {
					m.cursor++
				}
			case key.Matches(msg, key.NewBinding(key.WithKeys("enter"))):
				if len(m.results) > 0 && m.cursor < len(m.results) {
					return m, func() tea.Msg {
						return StorySelectedMsg{Story: m.results[m.cursor]}
					}
				}
			case key.Matches(msg, key.NewBinding(key.WithKeys("/", "i"))):
				m.inputFocus = true
				m.input.Focus()
			case key.Matches(msg, key.NewBinding(key.WithKeys("tab"))):
				m.mode = (m.mode + 1) % 3
			case key.Matches(msg, key.NewBinding(key.WithKeys("esc"))):
				m.inputFocus = true
				m.input.Focus()
			}
		}
	}

	return m, tea.Batch(cmds...)
}

// View renders the search view
func (m Model) View() string {
	var b strings.Builder

	// Header
	b.WriteString(styles.HeaderStyle.Width(m.width - 4).Render("Search Stories"))
	b.WriteString("\n\n")

	// Search input with mode indicator
	modeStyle := styles.DimStyle
	if m.mode == ModeText {
		modeStyle = styles.SuccessStyle
	}
	modeIndicator := modeStyle.Render(fmt.Sprintf("[%s]", m.mode.String()))

	inputStyle := styles.InputStyle
	if m.inputFocus {
		inputStyle = styles.FocusedInputStyle
	}

	b.WriteString(fmt.Sprintf("  %s %s\n",
		inputStyle.Width(m.width-20).Render(m.input.View()),
		modeIndicator,
	))
	b.WriteString(styles.DimStyle.Render("  tab: toggle mode (Text/Hybrid/Vector)"))
	b.WriteString("\n\n")

	if m.searching {
		b.WriteString("  Searching...")
		return b.String()
	}

	if m.err != nil {
		b.WriteString(styles.ErrorStyle.Render(fmt.Sprintf("  Error: %v", m.err)))
		return b.String()
	}

	if m.lastQuery != "" && len(m.results) == 0 {
		b.WriteString(fmt.Sprintf("  No results for: %s", m.lastQuery))
		return b.String()
	}

	if len(m.results) == 0 {
		b.WriteString(styles.DimStyle.Render("  Enter a search query and press Enter"))
		return b.String()
	}

	// Results header
	b.WriteString(fmt.Sprintf("  Found %d results for: %s\n\n",
		len(m.results), m.lastQuery))

	// Calculate available height for results
	listHeight := m.height - 12

	// Results list
	for i, story := range m.results {
		if i >= listHeight {
			break
		}

		cursor := "  "
		if !m.inputFocus && i == m.cursor {
			cursor = "▸ "
		}

		// Format result line
		typeStr := story.FormattedType()
		dateStr := story.FormattedDate()

		// Truncate title
		maxTitleLen := m.width - 45
		title := story.Title
		if len(title) > maxTitleLen {
			title = title[:maxTitleLen-3] + "..."
		}

		// Score display
		scoreStr := ""
		if story.Rank > 0 {
			scoreStr = styles.DimStyle.Render(fmt.Sprintf(" (%.2f)", story.Rank))
		}

		line := fmt.Sprintf("%s%s%s  %s  %s",
			cursor,
			title,
			scoreStr,
			styles.TypeBadge(typeStr),
			styles.DimStyle.Render(dateStr),
		)

		if !m.inputFocus && i == m.cursor {
			b.WriteString(styles.SelectedItemStyle.Width(m.width - 4).Render(line))
		} else {
			b.WriteString(line)
		}
		b.WriteString("\n")

		// Show snippet for selected item
		if !m.inputFocus && i == m.cursor {
			snippet := story.Snippet(100)
			snippet = strings.ReplaceAll(snippet, "\n", " ")
			b.WriteString(styles.DimStyle.Render(fmt.Sprintf("    \"%s\"", snippet)))
			b.WriteString("\n")
		}
	}

	// Help
	b.WriteString("\n")
	b.WriteString(styles.DimStyle.Render("  ↑↓: navigate • /: search • enter: view • esc: back to input"))

	return b.String()
}

// SelectedStory returns the currently selected story
func (m Model) SelectedStory() *db.Story {
	if !m.inputFocus && len(m.results) > 0 && m.cursor < len(m.results) {
		return &m.results[m.cursor]
	}
	return nil
}
