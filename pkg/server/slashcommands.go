package server

import (
	"context"
	"fmt"
	"log"
	"log/slog"
	"time"

	"github.com/RoWhoIs/RoWhoIs/pkg/proxypool"
	"github.com/RoWhoIs/RoWhoIs/pkg/roblox"
	"github.com/disgoorg/disgo/bot"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
)

type RoWhoIsSlashCommand struct {
	discord.SlashCommandCreate

	Handler                func(event *events.ApplicationCommandInteractionCreate)
	Intensity              Intensity
	PremiumOnly            bool
	RobloxConnectionNeeded bool
}

func registerSlashCommands(client bot.Client, commands []RoWhoIsSlashCommand) error {
	slashCommands := []discord.ApplicationCommandCreate{}
	for _, command := range commands {
		slashCommands = append(slashCommands, command.SlashCommandCreate)
	}
	if _, err := client.Rest().SetGlobalCommands(client.ApplicationID(), slashCommands); err != nil {
		return fmt.Errorf("cannot create commands: %v", err)
	}
	return nil
}

func slashCommandHandler(slashCommands []RoWhoIsSlashCommand) func(event *events.ApplicationCommandInteractionCreate) {
	// Generate commands once
	slashCommandsMap := map[string]RoWhoIsSlashCommand{}
	for _, command := range slashCommands {
		slashCommandsMap[command.Name] = command
	}

	return func(event *events.ApplicationCommandInteractionCreate) {
		log.Println("start: ", time.Now())
		data := event.SlashCommandInteractionData()
		commandName := data.CommandName()
		command, ok := slashCommandsMap[commandName]
		if !ok {
			log.Printf("unknown slash command: %s", commandName)
			return
		}
		command.Handler(event)
		log.Println("done: ", time.Now())
	}
}

type Intensity string

var (
	Low     Intensity = "low"
	Medium  Intensity = "medium"
	High    Intensity = "high"
	Extreme Intensity = "extreme"
)

func slashCommands(pool *proxypool.ProxyPool) []RoWhoIsSlashCommand {
	return []RoWhoIsSlashCommand{
		{
			Handler:     whois(pool),
			PremiumOnly: false,
			Intensity:   High,
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
		{
			Handler:     username(pool),
			PremiumOnly: false,
			Intensity:   Low,
			SlashCommandCreate: discord.SlashCommandCreate{
				Name:        "username",
				Description: "Get a username from a User ID",
				Options: []discord.ApplicationCommandOption{
					discord.ApplicationCommandOptionString{
						Name:        "userid",
						Description: "userid of a player",
						Required:    true,
					},
				},
			},
		},
	}
}

func whois(pool *proxypool.ProxyPool) func(event *events.ApplicationCommandInteractionCreate) {
	return func(event *events.ApplicationCommandInteractionCreate) {
		data := event.SlashCommandInteractionData()
		err := event.CreateMessage(discord.NewMessageCreateBuilder().
			SetContent(time.Now().String()).
			SetEphemeral(data.Bool("ephemeral")).
			Build(),
		)
		if err != nil {
			slog.Error("error on sending response", slog.Any("err", err))
		}
	}
}

func username(pool *proxypool.ProxyPool) func(event *events.ApplicationCommandInteractionCreate) {
	return func(event *events.ApplicationCommandInteractionCreate) {
		log.Println("about to fetch img at : ", time.Now())
		img, err := roblox.GetPlayerBust(context.Background(), pool, "12345", "60x60")
		if err != nil {
			log.Printf("err getting player bust: %v", err)
			return
		}
		log.Println("got player bust, responding to discord message: ", time.Now())
		data := event.SlashCommandInteractionData()
		err = event.CreateMessage(discord.NewMessageCreateBuilder().
			SetContent(img).
			SetEphemeral(data.Bool("ephemeral")).
			Build(),
		)
		if err != nil {
			slog.Error("error on sending response", slog.Any("err", err))
		}
		log.Println("successful response: ", time.Now())
	}
}
