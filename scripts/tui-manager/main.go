package main

import (
	"fmt"
	"os"

	"apicortex-manager/config"
	"apicortex-manager/ui"
)

func main() {

	cfg, err := config.LoadConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading config: %v\n", err)
		os.Exit(1)
	}

	app := ui.NewApp(cfg)

	if err := app.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running application: %v\n", err)
		os.Exit(1)
	}
}
