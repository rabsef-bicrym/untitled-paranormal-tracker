package detail

import (
	"fmt"
	"strings"

	"paranormal-tui/internal/db"
	"paranormal-tui/internal/styles"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Model represents the detail view for a single story
type Model struct {
	story    *db.Story
	viewport viewport.Model
	width    int
	height   int
	ready    bool
}

// New creates a new detail view model
func New() Model {
	return Model{}
}

// SetStory sets the story to display
func (m *Model) SetStory(story *db.Story) {
	m.story = story
	if m.ready {
		m.updateContent()
	}
}

// SetSize sets the dimensions of the detail view
func (m *Model) SetSize(width, height int) {
	m.width = width
	m.height = height

	// Account for border and padding
	contentWidth := width - 6
	contentHeight := height - 4

	if !m.ready {
		m.viewport = viewport.New(contentWidth, contentHeight)
		m.viewport.Style = lipgloss.NewStyle()
		m.ready = true
	} else {
		m.viewport.Width = contentWidth
		m.viewport.Height = contentHeight
	}

	if m.story != nil {
		m.updateContent()
	}
}

func (m *Model) updateContent() {
	if m.story == nil {
		return
	}

	var b strings.Builder

	// Title
	b.WriteString(styles.BoldStyle.Foreground(styles.Primary).Render(m.story.Title))
	b.WriteString("\n\n")

	// Metadata
	metaStyle := styles.DimStyle

	b.WriteString(fmt.Sprintf("%s %s\n",
		metaStyle.Render("Show:"),
		m.story.FormattedShow()))

	b.WriteString(fmt.Sprintf("%s %s\n",
		metaStyle.Render("Date:"),
		m.story.FormattedDate()))

	b.WriteString(fmt.Sprintf("%s %s\n",
		metaStyle.Render("Type:"),
		styles.TypeBadge(m.story.FormattedType())))

	b.WriteString(fmt.Sprintf("%s %s\n",
		metaStyle.Render("Location:"),
		m.story.FormattedLocation()))

	b.WriteString("\n")
	b.WriteString(styles.HeaderStyle.Render("Story"))
	b.WriteString("\n\n")

	// Content - wrap to viewport width
	content := m.story.Content
	wrapped := wrapText(content, m.viewport.Width-2)
	b.WriteString(wrapped)

	m.viewport.SetContent(b.String())
}

// wrapText wraps text to the specified width
func wrapText(text string, width int) string {
	if width <= 0 {
		width = 80
	}

	var result strings.Builder
	lines := strings.Split(text, "\n")

	for i, line := range lines {
		if i > 0 {
			result.WriteString("\n")
		}

		// Handle speaker labels specially
		if strings.HasPrefix(line, "[Speaker") {
			result.WriteString(styles.DimStyle.Render(line[:strings.Index(line, "]")+1]))
			line = line[strings.Index(line, "]")+1:]
		}

		words := strings.Fields(line)
		currentLine := ""

		for _, word := range words {
			if len(currentLine)+len(word)+1 <= width {
				if currentLine != "" {
					currentLine += " "
				}
				currentLine += word
			} else {
				if currentLine != "" {
					result.WriteString(currentLine + "\n")
				}
				currentLine = word
			}
		}
		if currentLine != "" {
			result.WriteString(currentLine)
		}
	}

	return result.String()
}

// Init initializes the model
func (m Model) Init() tea.Cmd {
	return nil
}

// Update handles messages
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "up", "k":
			m.viewport.LineUp(1)
		case "down", "j":
			m.viewport.LineDown(1)
		case "pgup", "ctrl+u":
			m.viewport.HalfViewUp()
		case "pgdown", "ctrl+d":
			m.viewport.HalfViewDown()
		case "home", "g":
			m.viewport.GotoTop()
		case "end", "G":
			m.viewport.GotoBottom()
		}
	}

	m.viewport, cmd = m.viewport.Update(msg)
	return m, cmd
}

// View renders the detail view
func (m Model) View() string {
	if m.story == nil {
		return styles.ModalStyle.
			Width(m.width - 4).
			Height(m.height - 2).
			Render("No story selected")
	}

	// Scroll indicator
	scrollPercent := 0
	if m.viewport.TotalLineCount() > 0 {
		scrollPercent = int(float64(m.viewport.YOffset) / float64(m.viewport.TotalLineCount()-m.viewport.Height) * 100)
		if scrollPercent < 0 {
			scrollPercent = 0
		}
		if scrollPercent > 100 {
			scrollPercent = 100
		}
	}

	footer := styles.DimStyle.Render(fmt.Sprintf(
		"↑↓ scroll • esc close • %d%%",
		scrollPercent,
	))

	content := lipgloss.JoinVertical(
		lipgloss.Left,
		m.viewport.View(),
		footer,
	)

	return styles.ModalStyle.
		Width(m.width - 4).
		Render(content)
}

// HasStory returns true if a story is loaded
func (m Model) HasStory() bool {
	return m.story != nil
}
