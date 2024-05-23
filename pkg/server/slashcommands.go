package server

import (
	"context"
	"errors"
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

const Red = 0xFF0000
const Green = 0x00FF00

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
					discord.ApplicationCommandOptionInt{
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
		userID, ok := event.SlashCommandInteractionData().OptInt("userid") // TODO: get keyname from SSOT
		if !ok {
			log.Println("no user id provided")
		}

		user, err := roblox.UserIDToUser(context.TODO(), pool, userID)
		if err != nil {
			log.Printf("problem getting username %v", err) // TODO: log error to db
			embed := discord.NewEmbedBuilder().SetColor(Red).SetDescription("User doesn't exist.").Build()
			event.CreateMessage(discord.NewMessageCreateBuilder().SetEmbeds(embed).Build())
			return
		}

		headshot, err := roblox.GetPlayerHeadShot(context.TODO(), pool, userID)
		switch {
		case errors.As(err, &roblox.BlockedErr{}):
			headshot = "https://rowhois.com/blocked.png"
		case errors.As(err, &roblox.NotOKErr{}) || err != nil:
			headshot = "https://rowhois.com/not-available.png"
		}

		bust, err := roblox.GetPlayerBust(context.Background(), pool, userID)
		switch {
		case errors.As(err, &roblox.BlockedErr{}):
			bust = "https://rowhois.com/blocked.png"
		case errors.As(err, &roblox.NotOKErr{}) || err != nil:
			bust = "https://rowhois.com/not-available.png"
		}

		// Show both names if username is not the display/nick name
		authorName := user.Name
		if user.Name != user.DisplayName {
			authorName = fmt.Sprintf("%s (%s)", user.Name, user.DisplayName)
		}

		inline := false
		linkToProfile := fmt.Sprintf("https://www.roblox.com/users/%d/profile", userID)
		embed := discord.NewEmbedBuilder().
			SetAuthor(authorName, linkToProfile, headshot).
			SetThumbnail(bust).
			SetColor(Green).
			SetFields(discord.EmbedField{
				Name:   "Username:",
				Value:  fmt.Sprintf("`%s`", user.Name),
				Inline: &inline,
			}).
			Build()
		err = event.CreateMessage(
			discord.NewMessageCreateBuilder().
				SetEmbeds(embed).
				Build())
		if err != nil {
			log.Printf("could not create message: %v", err) // TODO: log to db
		}
	}
}
