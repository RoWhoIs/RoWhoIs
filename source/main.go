package main

import (
	"io"
	"log"
	"log/slog"
	"os"

	"rowhois/portal"
)

func main() {
	file, err := os.OpenFile("logs/main.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	multiWriter := io.MultiWriter(file, os.Stdout)
	log.SetOutput(multiWriter)

	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "-d":
			slog.Info("RoWhoIs initializing in development mode")
		case "-p":
			slog.Info("RoWhoIs initializing in production mode")
		default:
			slog.Error("Invalid flag. Use -d for development mode or -p for production mode.")
		}
	} else {
		slog.Error("Invalid flag. Use -d for development mode or -p for production mode.")
	}

	if _, err := os.Stat("config.json"); os.IsNotExist(err) {
		slog.Error("A config.json is required in the root directory")
		return
	}

	if portal.StartServer(os.Args[1]) != nil {
		slog.Error("Failed to start server")
	}
}
