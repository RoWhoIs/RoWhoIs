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

func ClientRunning(client bot.Client) bool {
	return client.Gateway().Status().IsConnected()
}

func onClientReady(event *events.Ready) {
	// Might not persist presence on reconnect
	event.Client().SetPresence(context.TODO(), gateway.WithWatchingActivity("over Robloxia"))
	slog.Info(fmt.Sprintf("Initialized RoWhoIs! [%s/%d]", event.User.Username, event.User.ID))
}

func NewServer(token string) (bot.Client, error) {
	var err error
	client, err := disgo.New(token,
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

	if err = client.OpenGateway(context.TODO()); err != nil {
		return nil, err
	}
	return client, nil
}

func EndServer(client bot.Client) {
	client.Close(context.TODO())
}
