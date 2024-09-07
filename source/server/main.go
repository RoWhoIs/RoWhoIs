package server

import (
	"github.com/disgoorg/disgo"
)

// RunClient initializes the discord client
func RunClient(Token string) error {
	disgo.New(Token)
	return nil
}
