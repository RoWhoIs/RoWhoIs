package server

import (
	"context"
	"fmt"
	"log"
	"log/slog"
	"rowhois/utils"

	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
	"github.com/disgoorg/disgo/gateway"
	"github.com/disgoorg/disgo/sharding"
)

func onMessageCreate(event *events.InteractionCreate) {
	slog.Info(fmt.Sprint(event.Interaction.User()))

}

func registerSlashCommands(client bot.Client, commands []utils.SlashCommand) error {
	slashCommands := []discord.ApplicationCommandCreate{}
	for _, command := range commands {
		slashCommands = append(slashCommands, command.SlashCommandCreate)
	}
	if _, err := client.Rest().SetGlobalCommands(client.ApplicationID(), slashCommands); err != nil {
		return fmt.Errorf("cannot create commands: %v", err)
	}
	return nil
}

func slashCommandHandler(slashCommands []utils.SlashCommand) func(event *events.ApplicationCommandInteractionCreate) {
	// Generate commands once
	slashCommandsMap := map[string]utils.SlashCommand{}
	for _, command := range slashCommands {
		slashCommandsMap[command.Name] = command
	}

	return func(event *events.ApplicationCommandInteractionCreate) {
		data := event.SlashCommandInteractionData()
		commandName := data.CommandName()
		command, ok := slashCommandsMap[commandName]
		if !ok {
			log.Printf("unknown slash command: %s", commandName)
			return
		}
		command.Handler(event)
		// TODO: capture start/finish time for command in db
	}
}

func slashCommands(server *Server) []utils.SlashCommand {
	return []utils.SlashCommand{
		{
			Handler:   ping(server),
			Plus:      false,
			Intensity: 0,
			SlashCommandCreate: discord.SlashCommandCreate{
				Name:        "whois",
				Description: "Get detailed profile information from a User ID/Username",
				Options: []discord.ApplicationCommandOption{
					discord.ApplicationCommandOptionString{
						Name:        "user",
						Description: "the username of a player",
						Required:    true,
					},
				},
			},
		},
	}
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
	slog.Info("New discord client created")
	client, err := disgo.New(token,
		bot.WithGatewayConfigOpts(
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
		bot.WithShardManagerConfigOpts(
			sharding.WithAutoScaling(true),
			sharding.WithGatewayConfigOpts(
				gateway.WithIntents(gateway.IntentGuilds, gateway.IntentGuildMessages, gateway.IntentDirectMessages),
				gateway.WithCompress(true),
			),
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
