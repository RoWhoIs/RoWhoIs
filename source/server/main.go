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
	// Might not persist presence on reconnect
	event.Client().SetPresence(context.TODO(), gateway.WithWatchingActivity("over Robloxia"))
	slog.Info(fmt.Sprintf("Initialized RoWhoIs! [%s/%d]", event.User.Username, event.User.ID))
}

var Client bot.Client

func NewServer(token string) (bot.Client, error) {
	var err error
	Client, err = disgo.New(token,
		bot.WithGatewayConfigOpts(
			gateway.WithIntents(
				gateway.IntentsNonPrivileged,
			),
			gateway.WithAutoReconnect(true),
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
		return nil, err
	}

	if err = Client.OpenGateway(context.TODO()); err != nil {
		return nil, err
	}
	return Client, nil
}

func EndServer() {
	if Client == nil {
		return
	}
	Client.Close(context.TODO())
}
