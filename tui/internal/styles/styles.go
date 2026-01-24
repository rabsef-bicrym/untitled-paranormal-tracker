package styles

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// Colors
	Primary   = lipgloss.Color("#7D56F4")
	Secondary = lipgloss.Color("#5A4FCF")
	Accent    = lipgloss.Color("#FF6B6B")
	Muted     = lipgloss.Color("#626262")
	Success   = lipgloss.Color("#73D216")
	Warning   = lipgloss.Color("#F5A623")
	Error     = lipgloss.Color("#FF4757")

	// Background colors
	BgDark   = lipgloss.Color("#1a1a2e")
	BgMedium = lipgloss.Color("#16213e")
	BgLight  = lipgloss.Color("#0f3460")

	// Text colors
	TextPrimary   = lipgloss.Color("#FAFAFA")
	TextSecondary = lipgloss.Color("#A0A0A0")
	TextMuted     = lipgloss.Color("#666666")

	// Base styles
	BaseStyle = lipgloss.NewStyle().
			Foreground(TextPrimary)

	// Title bar
	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Primary).
			Padding(0, 1)

	// Tab styles
	ActiveTabStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(TextPrimary).
			Background(Primary).
			Padding(0, 2)

	InactiveTabStyle = lipgloss.NewStyle().
				Foreground(TextSecondary).
				Padding(0, 2)

	// Status bar
	StatusBarStyle = lipgloss.NewStyle().
			Foreground(TextSecondary).
			Background(BgMedium).
			Padding(0, 1)

	// List styles
	SelectedItemStyle = lipgloss.NewStyle().
				Foreground(TextPrimary).
				Background(Primary).
				Bold(true).
				Padding(0, 1)

	NormalItemStyle = lipgloss.NewStyle().
			Foreground(TextPrimary).
			Padding(0, 1)

	// Story type badge
	TypeBadgeStyle = lipgloss.NewStyle().
			Padding(0, 1).
			MarginRight(1)

	// Input styles
	InputStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(Primary).
			Padding(0, 1)

	FocusedInputStyle = lipgloss.NewStyle().
				BorderStyle(lipgloss.RoundedBorder()).
				BorderForeground(Accent).
				Padding(0, 1)

	// Modal/detail view
	ModalStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(Primary).
			Padding(1, 2)

	// Help text
	HelpStyle = lipgloss.NewStyle().
			Foreground(TextMuted)

	// Error style
	ErrorStyle = lipgloss.NewStyle().
			Foreground(Error).
			Bold(true)

	// Success style
	SuccessStyle = lipgloss.NewStyle().
			Foreground(Success)

	// Dim style
	DimStyle = lipgloss.NewStyle().
			Foreground(TextMuted)

	// Bold style
	BoldStyle = lipgloss.NewStyle().
			Bold(true)

	// Header style for sections
	HeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Primary).
			BorderStyle(lipgloss.NormalBorder()).
			BorderBottom(true).
			BorderForeground(Muted).
			MarginBottom(1)
)

// GetTypeColor returns the color for a story type
func GetTypeColor(storyType string) lipgloss.Color {
	colors := map[string]lipgloss.Color{
		"ghost":           lipgloss.Color("#8B8BFF"),
		"shadow_person":   lipgloss.Color("#A0A0A0"),
		"cryptid":         lipgloss.Color("#228B22"),
		"ufo":             lipgloss.Color("#FFD700"),
		"alien_encounter": lipgloss.Color("#00FF00"),
		"haunting":        lipgloss.Color("#9370DB"),
		"poltergeist":     lipgloss.Color("#FF6347"),
		"precognition":    lipgloss.Color("#00CED1"),
		"nde":             lipgloss.Color("#FFFFFF"),
		"obe":             lipgloss.Color("#E6E6FA"),
		"time_slip":       lipgloss.Color("#FF69B4"),
		"doppelganger":    lipgloss.Color("#DAA520"),
		"sleep_paralysis": lipgloss.Color("#6A5ACD"),
		"possession":      lipgloss.Color("#DC143C"),
		"other":           lipgloss.Color("#808080"),
	}

	if c, ok := colors[storyType]; ok {
		return c
	}
	return lipgloss.Color("#808080")
}

// TypeBadge creates a colored badge for a story type
func TypeBadge(storyType string) string {
	color := GetTypeColor(storyType)
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#000000")).
		Background(color).
		Padding(0, 1).
		Render(storyType)
}
