package server

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/events"
	"github.com/disgoorg/disgo/gateway"
)

func onMessageCreate(event *events.InteractionCreate) {
	slog.Info(fmt.Sprint(event.Interaction.User()))

}

func onClientReady(event *events.Ready) {
	slog.Info("RoWhoIs initialized! Running as " + event.User.Username)
}

func NewServer(token string) {
	client, err := disgo.New(token,

		bot.WithGatewayConfigOpts(

			gateway.WithIntents(
				gateway.IntentGuilds,
				gateway.IntentGuildMessages,
				gateway.IntentDirectMessages,
			),
		),

		bot.WithEventListenerFunc(
			func(e *events.InteractionCreate) {
				onMessageCreate(e)
			},
		),
		bot.WithEventListenerFunc(
			func(e *events.Ready) {
				onClientReady(e)
			},
		),
	)
	if err != nil {
		panic(err)
	}

	if err = client.OpenGateway(context.TODO()); err != nil {
		panic(err)
	}

}
