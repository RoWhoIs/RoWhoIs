package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/RoWhoIs/RoWhoIs/pkg/server"
)

func errAndExit(format string, args ...interface{}) {
	log.Printf(format, args...)
	os.Exit(1)
}

func main() {
	ctx := context.Background()

	config, err := server.ReadConfig("ROWHOIS_CONFIG")
	if err != nil {
		errAndExit("reading config: %v", err)
	}

	rowhoisServer, err := server.NewServer(config)
	if err != nil {
		errAndExit("creating server: %v", err)
	}

	if err := rowhoisServer.Serve(ctx); err != nil {
		errAndExit("serving requests: %v", err)
	}
	defer rowhoisServer.Close(ctx)

	log.Println("RoWhoIs server running and ready to receive discord requests. Press CTRL-C to exit.")
	s := make(chan os.Signal, 1)
	signal.Notify(s, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-s
}
