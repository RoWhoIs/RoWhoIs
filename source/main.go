package main

import (
	"io"
	"log"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"rowhois/portal"
	"rowhois/server"
	"rowhois/utils"
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
			slog.Info("Starting RoWhoIs in development mode")
		case "-p":
			slog.Info("Starting RoWhoIs in production mode")
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
	config, err := utils.LoadCfg()
	if err != nil {
		slog.Error("Failed to load config")
		return
	}
	slog.Info("Initializing Internal Management Portal...")
	if portal.StartServer() != nil {
		slog.Error("Failed to start server")
	}
	slog.Info("Initializing RoWhoIs...")

	if os.Args[1] == "-p" {
		_, err := server.NewServer(config.Authentication.ProdBot)
		if err != nil {
			slog.Error("Failed to start server")
			return
		}
	} else {
		_, err := server.NewServer(config.Authentication.DevBot)
		if err != nil {
			slog.Error("Failed to start server")
			return
		}
	}

	s := make(chan os.Signal, 1)
	signal.Notify(s, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-s
		if sig == syscall.SIGINT || sig == syscall.SIGTERM {
			slog.Info("Shutting down RoWhoIs...")
			server.EndServer()
			os.Rename("logs/main.log", "logs/"+time.Now().Format("01022006-150405")+".log")
			os.Exit(0)
		}
	}()
	select {}
}
