package server

import (
	"log/slog"
	"time"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
)

func Ping() func(event *events.ApplicationCommandInteractionCreate) {
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
