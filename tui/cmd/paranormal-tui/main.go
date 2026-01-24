package main

import (
	"fmt"
	"os"

	"paranormal-tui/internal/app"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	// Create and run the application
	p := tea.NewProgram(
		app.New(),
		tea.WithAltScreen(),
		tea.WithMouseCellMotion(),
	)

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running TUI: %v\n", err)
		os.Exit(1)
	}
}
