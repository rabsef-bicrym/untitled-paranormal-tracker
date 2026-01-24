package app

import "github.com/charmbracelet/bubbles/key"

// KeyMap defines all key bindings for the application
type KeyMap struct {
	// Navigation
	Up       key.Binding
	Down     key.Binding
	Left     key.Binding
	Right    key.Binding
	PageUp   key.Binding
	PageDown key.Binding

	// Actions
	Enter  key.Binding
	Escape key.Binding
	Quit   key.Binding
	Help   key.Binding

	// View switching
	View1 key.Binding
	View2 key.Binding
	View3 key.Binding

	// Pagination
	NextPage key.Binding
	PrevPage key.Binding

	// Search modes
	ToggleSearchMode key.Binding

	// Visualization
	ZoomIn    key.Binding
	ZoomOut   key.Binding
	ResetView key.Binding
}

// DefaultKeyMap returns the default key bindings
func DefaultKeyMap() KeyMap {
	return KeyMap{
		Up: key.NewBinding(
			key.WithKeys("up", "k"),
			key.WithHelp("↑/k", "up"),
		),
		Down: key.NewBinding(
			key.WithKeys("down", "j"),
			key.WithHelp("↓/j", "down"),
		),
		Left: key.NewBinding(
			key.WithKeys("left", "h"),
			key.WithHelp("←/h", "left"),
		),
		Right: key.NewBinding(
			key.WithKeys("right", "l"),
			key.WithHelp("→/l", "right"),
		),
		PageUp: key.NewBinding(
			key.WithKeys("pgup", "ctrl+u"),
			key.WithHelp("pgup", "page up"),
		),
		PageDown: key.NewBinding(
			key.WithKeys("pgdown", "ctrl+d"),
			key.WithHelp("pgdn", "page down"),
		),
		Enter: key.NewBinding(
			key.WithKeys("enter"),
			key.WithHelp("enter", "select"),
		),
		Escape: key.NewBinding(
			key.WithKeys("esc"),
			key.WithHelp("esc", "back"),
		),
		Quit: key.NewBinding(
			key.WithKeys("q", "ctrl+c"),
			key.WithHelp("q", "quit"),
		),
		Help: key.NewBinding(
			key.WithKeys("?"),
			key.WithHelp("?", "help"),
		),
		View1: key.NewBinding(
			key.WithKeys("1"),
			key.WithHelp("1", "search"),
		),
		View2: key.NewBinding(
			key.WithKeys("2"),
			key.WithHelp("2", "browse"),
		),
		View3: key.NewBinding(
			key.WithKeys("3"),
			key.WithHelp("3", "visualize"),
		),
		NextPage: key.NewBinding(
			key.WithKeys("n", "]"),
			key.WithHelp("n", "next page"),
		),
		PrevPage: key.NewBinding(
			key.WithKeys("p", "["),
			key.WithHelp("p", "prev page"),
		),
		ToggleSearchMode: key.NewBinding(
			key.WithKeys("tab"),
			key.WithHelp("tab", "toggle mode"),
		),
		ZoomIn: key.NewBinding(
			key.WithKeys("+", "="),
			key.WithHelp("+", "zoom in"),
		),
		ZoomOut: key.NewBinding(
			key.WithKeys("-", "_"),
			key.WithHelp("-", "zoom out"),
		),
		ResetView: key.NewBinding(
			key.WithKeys("r"),
			key.WithHelp("r", "reset view"),
		),
	}
}

// ShortHelp returns a short help text
func (k KeyMap) ShortHelp() []key.Binding {
	return []key.Binding{k.Up, k.Down, k.Enter, k.Escape, k.Quit}
}

// FullHelp returns the full help text
func (k KeyMap) FullHelp() [][]key.Binding {
	return [][]key.Binding{
		{k.Up, k.Down, k.Left, k.Right},
		{k.Enter, k.Escape, k.Help},
		{k.View1, k.View2, k.View3},
		{k.NextPage, k.PrevPage},
		{k.Quit},
	}
}
