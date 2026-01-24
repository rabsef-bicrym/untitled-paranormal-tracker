package visualize

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"paranormal-tui/internal/db"
	"paranormal-tui/internal/styles"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// PlottedPoint stores a point with its computed screen coordinates
type PlottedPoint struct {
	Point   *db.UmapPoint
	ScreenX int // Integer screen position (0 to width-1)
	ScreenY int // Integer screen position (0 to height-1)
}

// ColorMode determines how points are colored
type ColorMode int

const (
	ColorByStoryType ColorMode = iota
	ColorByCluster
)

// Model represents the visualization view
type Model struct {
	database *db.DB
	points   []db.UmapPoint
	loading  bool
	err      error
	width    int
	height   int

	// View state
	cursorX    int
	cursorY    int
	zoom       float64
	offsetX    float64
	offsetY    float64
	selected   *db.UmapPoint
	selectedID string
	colorMode  ColorMode // Toggle between story_type and cluster coloring

	// Pre-computed screen positions (single source of truth)
	plottedPoints []PlottedPoint
	// Overlap handling: points at cursor position
	pointsAtCursor []*db.UmapPoint
	overlapIndex   int // Which overlapping point is currently selected

	// Computed bounds
	minX, maxX float64
	minY, maxY float64

	// Cached plot dimensions for detecting resize
	lastPlotWidth  int
	lastPlotHeight int
}

// New creates a new visualization model
func New(database *db.DB) Model {
	return Model{
		database: database,
		zoom:     1.0,
	}
}

// Init initializes the model
func (m Model) Init() tea.Cmd {
	return m.loadPoints()
}

// SetSize sets the view dimensions
func (m *Model) SetSize(width, height int) {
	oldWidth, oldHeight := m.width, m.height
	m.width = width
	m.height = height

	// Center cursor only on initial set
	if oldWidth == 0 && oldHeight == 0 {
		m.cursorX = width / 4
		m.cursorY = height / 2
	}

	// Recompute screen positions if we have points loaded
	if len(m.points) > 0 {
		m.computeScreenPositions()
		m.updateSelection()
	}
}

// SetDatabase sets the database connection
func (m *Model) SetDatabase(database *db.DB) {
	m.database = database
}

// UmapPointsLoadedMsg indicates UMAP points have loaded
type UmapPointsLoadedMsg struct {
	Points []db.UmapPoint
	Err    error
}

// StorySelectedMsg indicates a story was selected
type StorySelectedMsg struct {
	StoryID string
}

func (m Model) loadPoints() tea.Cmd {
	if m.database == nil {
		return nil
	}

	return func() tea.Msg {
		ctx := context.Background()
		points, err := m.database.GetUmapPoints(ctx)
		return UmapPointsLoadedMsg{Points: points, Err: err}
	}
}

// Reload refreshes the UMAP points
func (m *Model) Reload() tea.Cmd {
	m.loading = true
	return m.loadPoints()
}

// Update handles messages
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case UmapPointsLoadedMsg:
		m.loading = false
		if msg.Err != nil {
			m.err = msg.Err
			return m, nil
		}
		m.points = msg.Points
		m.computeBounds()
		m.computeScreenPositions()
		m.updateSelection()
		return m, nil

	case tea.KeyMsg:
		switch {
		case key.Matches(msg, key.NewBinding(key.WithKeys("up", "k"))):
			m.cursorY--
			if m.cursorY < 0 {
				m.cursorY = 0
			}
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("down", "j"))):
			plotHeight := m.height - 8
			m.cursorY++
			if m.cursorY >= plotHeight {
				m.cursorY = plotHeight - 1
			}
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("left", "h"))):
			m.cursorX--
			if m.cursorX < 0 {
				m.cursorX = 0
			}
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("right", "l"))):
			plotWidth := m.width/2 - 4
			m.cursorX++
			if m.cursorX >= plotWidth {
				m.cursorX = plotWidth - 1
			}
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("+", "="))):
			m.zoom *= 1.2
			if m.zoom > 5.0 {
				m.zoom = 5.0
			}
			m.computeScreenPositions()
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("-", "_"))):
			m.zoom /= 1.2
			if m.zoom < 0.2 {
				m.zoom = 0.2
			}
			m.computeScreenPositions()
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("r"))):
			m.zoom = 1.0
			m.offsetX = 0
			m.offsetY = 0
			m.computeScreenPositions()
			m.updateSelection()
		case key.Matches(msg, key.NewBinding(key.WithKeys("["))):
			// Cycle backward through overlapping points
			if len(m.pointsAtCursor) > 1 {
				m.overlapIndex--
				if m.overlapIndex < 0 {
					m.overlapIndex = len(m.pointsAtCursor) - 1
				}
				m.selected = m.pointsAtCursor[m.overlapIndex]
				m.selectedID = m.selected.ID
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("]"))):
			// Cycle forward through overlapping points
			if len(m.pointsAtCursor) > 1 {
				m.overlapIndex++
				if m.overlapIndex >= len(m.pointsAtCursor) {
					m.overlapIndex = 0
				}
				m.selected = m.pointsAtCursor[m.overlapIndex]
				m.selectedID = m.selected.ID
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("enter"))):
			if m.selected != nil {
				return m, func() tea.Msg {
					return StorySelectedMsg{StoryID: m.selected.ID}
				}
			}
		case key.Matches(msg, key.NewBinding(key.WithKeys("c"))):
			// Toggle color mode between story_type and cluster
			if m.colorMode == ColorByStoryType {
				m.colorMode = ColorByCluster
			} else {
				m.colorMode = ColorByStoryType
			}
		}
	}

	return m, nil
}

func (m *Model) computeBounds() {
	if len(m.points) == 0 {
		return
	}

	// Use percentile-based bounds to handle outliers gracefully
	// Sort X and Y values separately
	n := len(m.points)
	xs := make([]float64, n)
	ys := make([]float64, n)
	for i, p := range m.points {
		xs[i] = p.X
		ys[i] = p.Y
	}

	sort.Float64s(xs)
	sort.Float64s(ys)

	// Use 2nd and 98th percentile to exclude extreme outliers
	lowIdx := n * 2 / 100
	highIdx := n - 1 - lowIdx
	if lowIdx >= highIdx {
		lowIdx = 0
		highIdx = n - 1
	}

	m.minX, m.maxX = xs[lowIdx], xs[highIdx]
	m.minY, m.maxY = ys[lowIdx], ys[highIdx]

	// Ensure we still include all points in bounds if range is too small
	if m.maxX-m.minX < 1 {
		m.minX, m.maxX = xs[0], xs[n-1]
	}
	if m.maxY-m.minY < 1 {
		m.minY, m.maxY = ys[0], ys[n-1]
	}

	// Add padding
	rangeX := m.maxX - m.minX
	rangeY := m.maxY - m.minY
	m.minX -= rangeX * 0.1
	m.maxX += rangeX * 0.1
	m.minY -= rangeY * 0.1
	m.maxY += rangeY * 0.1
}

// computeScreenPositions converts all data points to integer screen coordinates once.
// This is the single source of truth for where points appear on screen.
func (m *Model) computeScreenPositions() {
	plotWidth := m.width/2 - 4
	plotHeight := m.height - 8

	// Store dimensions to detect resize
	m.lastPlotWidth = plotWidth
	m.lastPlotHeight = plotHeight

	if plotWidth <= 0 || plotHeight <= 0 || len(m.points) == 0 {
		m.plottedPoints = nil
		return
	}

	// Compute visible range based on zoom
	rangeX := (m.maxX - m.minX) / m.zoom
	rangeY := (m.maxY - m.minY) / m.zoom
	centerX := (m.minX + m.maxX) / 2
	centerY := (m.minY + m.maxY) / 2
	viewMinX := centerX - rangeX/2
	viewMaxY := centerY + rangeY/2

	// Pre-allocate slice
	m.plottedPoints = make([]PlottedPoint, 0, len(m.points))

	for i := range m.points {
		p := &m.points[i]

		// Convert data coords to integer screen coords (same formula as rendering)
		screenX := int((p.X - viewMinX) / rangeX * float64(plotWidth))
		screenY := int((viewMaxY - p.Y) / rangeY * float64(plotHeight)) // Flip Y

		// Only include points that are within the visible area
		if screenX >= 0 && screenX < plotWidth && screenY >= 0 && screenY < plotHeight {
			m.plottedPoints = append(m.plottedPoints, PlottedPoint{
				Point:   p,
				ScreenX: screenX,
				ScreenY: screenY,
			})
		}
	}
}

// updateSelection finds all points at the cursor position using exact int matching.
// No threshold, no float/int mismatch - cursor must be exactly on a dot.
func (m *Model) updateSelection() {
	// Reset overlap tracking
	m.pointsAtCursor = nil
	m.overlapIndex = 0

	if len(m.plottedPoints) == 0 {
		m.selected = nil
		m.selectedID = ""
		return
	}

	// Find all points at exact cursor position
	for i := range m.plottedPoints {
		pp := &m.plottedPoints[i]
		if pp.ScreenX == m.cursorX && pp.ScreenY == m.cursorY {
			m.pointsAtCursor = append(m.pointsAtCursor, pp.Point)
		}
	}

	// Update selection based on what we found
	if len(m.pointsAtCursor) > 0 {
		m.selected = m.pointsAtCursor[0]
		m.selectedID = m.selected.ID
	} else {
		m.selected = nil
		m.selectedID = ""
	}
}

// View renders the visualization
func (m Model) View() string {
	if m.loading {
		return "  Loading UMAP visualization..."
	}

	if m.err != nil {
		return styles.ErrorStyle.Render(fmt.Sprintf("  Error: %v", m.err))
	}

	if len(m.points) == 0 {
		return "  No UMAP coordinates available.\n  Run UMAP computation to generate visualization data."
	}

	// Layout: plot on left, legend + info on right
	plotWidth := m.width/2 - 4
	plotHeight := m.height - 8
	infoWidth := m.width/2 - 4

	if plotWidth < 20 || plotHeight < 10 {
		return "  Terminal too small for visualization"
	}

	// Build the plot
	plot := m.renderPlot(plotWidth, plotHeight)

	// Build the info panel
	info := m.renderInfoPanel(infoWidth, plotHeight)

	// Combine horizontally
	combined := lipgloss.JoinHorizontal(lipgloss.Top, plot, "  ", info)

	// Header
	colorModeLabel := "by type"
	if m.colorMode == ColorByCluster {
		colorModeLabel = "by cluster"
	}
	header := styles.HeaderStyle.Width(m.width - 4).Render(
		fmt.Sprintf("UMAP Visualization (%d stories) [colored %s]", len(m.points), colorModeLabel),
	)

	// Footer
	colorModeHint := "c: color by cluster"
	if m.colorMode == ColorByCluster {
		colorModeHint = "c: color by type"
	}
	footer := styles.DimStyle.Render(
		fmt.Sprintf("  ←↑↓→: move • +/-: zoom • r: reset • [/]: cycle overlap • %s • enter: view", colorModeHint),
	)

	return lipgloss.JoinVertical(lipgloss.Left, header, "", combined, "", footer)
}

func (m Model) renderPlot(width, height int) string {
	// Create empty grid
	grid := make([][]rune, height)
	pointRefs := make([][]*db.UmapPoint, height) // Store point refs for color lookup
	for y := 0; y < height; y++ {
		grid[y] = make([]rune, width)
		pointRefs[y] = make([]*db.UmapPoint, width)
		for x := 0; x < width; x++ {
			grid[y][x] = ' '
			pointRefs[y][x] = nil
		}
	}

	// Plot points using pre-computed screen coordinates (single source of truth)
	for _, pp := range m.plottedPoints {
		x := pp.ScreenX
		y := pp.ScreenY

		if x >= 0 && x < width && y >= 0 && y < height {
			if grid[y][x] == ' ' {
				grid[y][x] = '●'
			} else if grid[y][x] == '●' {
				grid[y][x] = '◉' // Overlap (2 points)
			} else {
				grid[y][x] = '◆' // Cluster (3+ points)
			}
			pointRefs[y][x] = pp.Point
		}
	}

	// Mark cursor position
	if m.cursorY >= 0 && m.cursorY < height && m.cursorX >= 0 && m.cursorX < width {
		if m.selected != nil {
			grid[m.cursorY][m.cursorX] = '█'
		} else {
			grid[m.cursorY][m.cursorX] = '+'
		}
	}

	// Render grid with colors
	var b strings.Builder
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			ch := string(grid[y][x])
			if x == m.cursorX && y == m.cursorY {
				// Cursor
				b.WriteString(lipgloss.NewStyle().
					Foreground(lipgloss.Color("#FFFFFF")).
					Background(lipgloss.Color("#FF6B6B")).
					Render(ch))
			} else if pointRefs[y][x] != nil {
				// Color based on current mode
				var color lipgloss.Color
				if m.colorMode == ColorByCluster {
					color = styles.GetClusterColor(pointRefs[y][x].ClusterID)
				} else {
					color = styles.GetTypeColor(pointRefs[y][x].StoryType)
				}
				b.WriteString(lipgloss.NewStyle().Foreground(color).Render(ch))
			} else {
				b.WriteString(ch)
			}
		}
		if y < height-1 {
			b.WriteString("\n")
		}
	}

	return lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(styles.Muted).
		Render(b.String())
}

func (m Model) renderInfoPanel(width, height int) string {
	var b strings.Builder

	// Legend - different based on color mode
	if m.colorMode == ColorByCluster {
		b.WriteString(styles.BoldStyle.Render("Legend (Clusters)"))
		b.WriteString("\n\n")

		// Count stories by cluster
		clusterCounts := make(map[int]int)
		noiseCount := 0
		for _, p := range m.points {
			if p.ClusterID != nil {
				clusterCounts[*p.ClusterID]++
			} else {
				noiseCount++
			}
		}

		// Show clusters in order
		clusterIDs := make([]int, 0, len(clusterCounts))
		for id := range clusterCounts {
			clusterIDs = append(clusterIDs, id)
		}
		sort.Ints(clusterIDs)

		for _, id := range clusterIDs {
			count := clusterCounts[id]
			color := styles.GetClusterColor(&id)
			marker := lipgloss.NewStyle().Foreground(color).Render("●")
			b.WriteString(fmt.Sprintf("%s cluster %-3d %3d\n", marker, id, count))
		}

		if noiseCount > 0 {
			color := styles.GetClusterColor(nil)
			marker := lipgloss.NewStyle().Foreground(color).Render("●")
			b.WriteString(fmt.Sprintf("%s noise       %3d\n", marker, noiseCount))
		}
	} else {
		b.WriteString(styles.BoldStyle.Render("Legend (Types)"))
		b.WriteString("\n\n")

		// Count stories by type
		typeCounts := make(map[string]int)
		for _, p := range m.points {
			typeCounts[p.StoryType]++
		}

		for _, t := range db.StoryTypes {
			count := typeCounts[t]
			if count > 0 {
				color := styles.GetTypeColor(t)
				marker := lipgloss.NewStyle().Foreground(color).Render("●")
				b.WriteString(fmt.Sprintf("%s %-15s %3d\n", marker, t, count))
			}
		}
	}

	b.WriteString("\n")
	b.WriteString(styles.BoldStyle.Render("Symbols"))
	b.WriteString("\n")
	b.WriteString("● single   ◉ overlap   ◆ cluster\n")

	// Zoom info
	b.WriteString("\n")
	b.WriteString(fmt.Sprintf("Zoom: %.1fx\n", m.zoom))

	// Selected story info
	if m.selected != nil {
		b.WriteString("\n")

		// Show overlap count if multiple stories at cursor
		if len(m.pointsAtCursor) > 1 {
			b.WriteString(styles.BoldStyle.Render(
				fmt.Sprintf("Selected Story (%d/%d)", m.overlapIndex+1, len(m.pointsAtCursor)),
			))
			b.WriteString("\n")
			b.WriteString(styles.DimStyle.Render("Use [ ] to cycle"))
		} else {
			b.WriteString(styles.BoldStyle.Render("Selected Story"))
		}
		b.WriteString("\n\n")

		title := m.selected.Title
		if len(title) > width-4 {
			title = title[:width-7] + "..."
		}
		b.WriteString(fmt.Sprintf("%s\n", title))
		b.WriteString(fmt.Sprintf("Type: %s\n", styles.TypeBadge(m.selected.StoryType)))
		if m.selected.ClusterID != nil {
			b.WriteString(fmt.Sprintf("Cluster: %s\n", styles.ClusterBadge(m.selected.ClusterID)))
		} else {
			b.WriteString("Cluster: noise/outlier\n")
		}
		b.WriteString("\n")
		b.WriteString(styles.DimStyle.Render("Press Enter to view"))
	} else {
		b.WriteString("\n")
		b.WriteString(styles.DimStyle.Render("Move cursor to select a story"))
	}

	return lipgloss.NewStyle().
		Width(width).
		Height(height).
		Render(b.String())
}

// SelectedStoryID returns the ID of the selected story
func (m Model) SelectedStoryID() string {
	return m.selectedID
}
