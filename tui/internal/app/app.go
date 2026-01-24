package app

import (
	"context"
	"fmt"
	"strings"

	"paranormal-tui/internal/db"
	"paranormal-tui/internal/styles"
	"paranormal-tui/internal/views/browse"
	"paranormal-tui/internal/views/detail"
	"paranormal-tui/internal/views/search"
	"paranormal-tui/internal/views/visualize"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Model is the root application model
type Model struct {
	// Database connection
	database   *db.DB
	storyCount int
	dbErr      error
	connecting bool

	// Views
	searchView    search.Model
	browseView    browse.Model
	visualizeView visualize.Model
	detailView    detail.Model

	// State
	currentView View
	showDetail  bool
	showHelp    bool
	width       int
	height      int
	keys        KeyMap
}

// New creates a new application model
func New() Model {
	return Model{
		keys:       DefaultKeyMap(),
		connecting: true,
	}
}

// Init initializes the application
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		m.connectDB(),
		tea.SetWindowTitle("Paranormal Tracker"),
	)
}

func (m Model) connectDB() tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		database, err := db.New(ctx)
		if err != nil {
			return DBConnectedMsg{Err: err}
		}

		count, err := database.GetStoryCount(ctx)
		if err != nil {
			database.Close()
			return DBConnectedMsg{Err: err}
		}

		return DBConnectedMsg{DB: database, StoryCount: count}
	}
}

// Update handles messages
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.updateViewSizes()
		return m, nil

	case DBConnectedMsg:
		m.connecting = false
		if msg.Err != nil {
			m.dbErr = msg.Err
			return m, nil
		}
		m.database = msg.DB
		m.storyCount = msg.StoryCount

		// Initialize views with database
		m.searchView = search.New(m.database)
		m.browseView = browse.New(m.database)
		m.visualizeView = visualize.New(m.database)
		m.detailView = detail.New()

		m.updateViewSizes()

		// Start on browse view and load data
		m.currentView = ViewBrowse
		return m, m.browseView.Init()

	case tea.KeyMsg:
		// Global keys (when not in detail mode)
		if m.showHelp {
			if msg.String() == "?" || msg.String() == "esc" {
				m.showHelp = false
				return m, nil
			}
			return m, nil
		}

		if m.showDetail {
			if msg.String() == "esc" || msg.String() == "q" {
				m.showDetail = false
				return m, nil
			}
			var cmd tea.Cmd
			m.detailView, cmd = m.detailView.Update(msg)
			return m, cmd
		}

		// Global quit
		if key.Matches(msg, m.keys.Quit) {
			if m.database != nil {
				m.database.Close()
			}
			return m, tea.Quit
		}

		// Help toggle
		if key.Matches(msg, m.keys.Help) {
			m.showHelp = true
			return m, nil
		}

		// View switching
		if key.Matches(msg, m.keys.View1) {
			m.currentView = ViewSearch
			m.searchView.Focus()
			return m, nil
		}
		if key.Matches(msg, m.keys.View2) {
			if m.currentView != ViewBrowse {
				m.currentView = ViewBrowse
				return m, m.browseView.Reload()
			}
			return m, nil
		}
		if key.Matches(msg, m.keys.View3) {
			if m.currentView != ViewVisualize {
				m.currentView = ViewVisualize
				return m, m.visualizeView.Reload()
			}
			return m, nil
		}

	// Handle story selection from any view
	case browse.StorySelectedMsg:
		m.showDetail = true
		m.detailView.SetStory(&msg.Story)
		m.detailView.SetSize(m.width-4, m.height-6)
		return m, nil

	case search.StorySelectedMsg:
		m.showDetail = true
		m.detailView.SetStory(&msg.Story)
		m.detailView.SetSize(m.width-4, m.height-6)
		return m, nil

	case visualize.StorySelectedMsg:
		// Load full story from DB
		return m, func() tea.Msg {
			ctx := context.Background()
			story, err := m.database.GetStoryByID(ctx, msg.StoryID)
			if err != nil {
				return ErrorMsg{Err: err}
			}
			return StorySelectedMsg{Story: story}
		}

	case StorySelectedMsg:
		if msg.Story != nil {
			m.showDetail = true
			m.detailView.SetStory(msg.Story)
			m.detailView.SetSize(m.width-4, m.height-6)
		}
		return m, nil
	}

	// Route to current view
	var cmd tea.Cmd
	switch m.currentView {
	case ViewSearch:
		m.searchView, cmd = m.searchView.Update(msg)
	case ViewBrowse:
		m.browseView, cmd = m.browseView.Update(msg)
	case ViewVisualize:
		m.visualizeView, cmd = m.visualizeView.Update(msg)
	}
	cmds = append(cmds, cmd)

	return m, tea.Batch(cmds...)
}

func (m *Model) updateViewSizes() {
	contentHeight := m.height - 4 // Account for tab bar and status bar
	contentWidth := m.width - 2

	m.searchView.SetSize(contentWidth, contentHeight)
	m.browseView.SetSize(contentWidth, contentHeight)
	m.visualizeView.SetSize(contentWidth, contentHeight)
	m.detailView.SetSize(m.width-4, m.height-6)
}

// View renders the application
func (m Model) View() string {
	if m.connecting {
		return m.renderConnecting()
	}

	if m.dbErr != nil {
		return m.renderError()
	}

	if m.showHelp {
		return m.renderHelp()
	}

	var content string

	// Render detail modal overlay
	if m.showDetail {
		content = m.detailView.View()
	} else {
		// Render current view
		switch m.currentView {
		case ViewSearch:
			content = m.searchView.View()
		case ViewBrowse:
			content = m.browseView.View()
		case ViewVisualize:
			content = m.visualizeView.View()
		}
	}

	// Compose full screen
	return lipgloss.JoinVertical(
		lipgloss.Left,
		m.renderTabBar(),
		content,
		m.renderStatusBar(),
	)
}

func (m Model) renderConnecting() string {
	return lipgloss.Place(
		m.width,
		m.height,
		lipgloss.Center,
		lipgloss.Center,
		styles.BoldStyle.Render("Connecting to database..."),
	)
}

func (m Model) renderError() string {
	errBox := lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(styles.Error).
		Padding(2, 4).
		Render(fmt.Sprintf(
			"%s\n\n%s\n\n%s",
			styles.ErrorStyle.Render("Database Connection Failed"),
			m.dbErr.Error(),
			styles.DimStyle.Render("Make sure PostgreSQL is running:\n  docker-compose up -d"),
		))

	return lipgloss.Place(
		m.width,
		m.height,
		lipgloss.Center,
		lipgloss.Center,
		errBox,
	)
}

func (m Model) renderTabBar() string {
	tabs := []string{"Search", "Browse", "Visualize"}
	var renderedTabs []string

	for i, tab := range tabs {
		style := styles.InactiveTabStyle
		if View(i) == m.currentView {
			style = styles.ActiveTabStyle
		}
		renderedTabs = append(renderedTabs, style.Render(fmt.Sprintf("%d %s", i+1, tab)))
	}

	tabBar := lipgloss.JoinHorizontal(lipgloss.Top, renderedTabs...)

	title := styles.TitleStyle.Render("Paranormal Tracker")

	return lipgloss.JoinHorizontal(
		lipgloss.Top,
		title,
		"  ",
		tabBar,
	)
}

func (m Model) renderStatusBar() string {
	left := fmt.Sprintf(" %d stories", m.storyCount)

	viewHelp := ""
	switch m.currentView {
	case ViewSearch:
		viewHelp = "enter: search • ↑↓: results"
	case ViewBrowse:
		viewHelp = "n/p: page • f: filter • enter: view"
	case ViewVisualize:
		viewHelp = "arrows: move • +/-: zoom • enter: view"
	}

	right := fmt.Sprintf("%s • 1/2/3: views • ?: help • q: quit ", viewHelp)

	gap := m.width - lipgloss.Width(left) - lipgloss.Width(right)
	if gap < 0 {
		gap = 0
	}

	return styles.StatusBarStyle.Width(m.width).Render(
		left + strings.Repeat(" ", gap) + right,
	)
}

func (m Model) renderHelp() string {
	help := `
PARANORMAL TRACKER - Keyboard Shortcuts

NAVIGATION
  1           Switch to Search view
  2           Switch to Browse view
  3           Switch to Visualize view
  ↑/k ↓/j     Move up/down
  ←/h →/l     Move left/right (Visualize)
  Enter       Select/view story
  Esc         Close modal / go back

BROWSE VIEW
  n / ]       Next page
  p / [       Previous page
  f           Filter by story type
  s           Cycle sort field
  S           Toggle sort direction
  c           Clear filters

SEARCH VIEW
  Tab         Toggle search mode (Text/Hybrid/Vector)
  /           Focus search input

VISUALIZE VIEW
  + / =       Zoom in
  - / _       Zoom out
  r           Reset view

GENERAL
  ?           Toggle this help
  q           Quit

Press ? or Esc to close this help.
`
	helpBox := lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(styles.Primary).
		Padding(1, 3).
		Render(help)

	return lipgloss.Place(
		m.width,
		m.height,
		lipgloss.Center,
		lipgloss.Center,
		helpBox,
	)
}
