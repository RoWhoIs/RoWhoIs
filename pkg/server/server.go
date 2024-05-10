package server

import (
	"context"
	"fmt"

	"github.com/RoWhoIs/RoWhoIs/pkg/proxypool"
	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/gateway"
)

type Server struct {
	Config        *Config
	discordClient bot.Client
}

func NewServer(config *Config) (*Server, error) {
	pool := proxypool.NewProxyPool(config.Proxies)
	commands := slashCommands(pool)

	client, err := disgo.New(config.DiscordToken,
		bot.WithGatewayConfigOpts(
			gateway.WithIntents(),
		),
		bot.WithEventListenerFunc(slashCommandHandler(commands)),
	)
	if err != nil {
		return nil, fmt.Errorf("error while creating discord client: %v", err)
	}
	if err := registerSlashCommands(client, commands); err != nil {
		return nil, fmt.Errorf("registering slash commands: %v", err)
	}
	return &Server{
		Config:        config,
		discordClient: client,
	}, nil
}

func (s *Server) Serve(ctx context.Context) error {
	if err := s.discordClient.OpenGateway(ctx); err != nil {
		return fmt.Errorf("errors opening gateway: %v", err)
	}
	return nil
}

func (s *Server) Close(ctx context.Context) {
	s.discordClient.Close(ctx)
}
