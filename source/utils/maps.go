package utils

import (
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/events"
)

type Config struct {
	Authentication struct {
		ProdBot       string `json:"prod-bot"`
		DevBot        string `json:"dev-bot"`
		Webhook       string `json:"webhook"`
		RobloSecurity string `json:"roblosecurity"`
		TopGGAuth     string `json:"topgg-auth"`
	} `json:"authentication"`
	Moderation struct {
		OptOut             []string `json:"opt_out"`
		BannedUsers        []string `json:"banned_users"`
		BannedAssets       []string `json:"banned_assets"`
		AdminIDs           []string `json:"admin_ids"`
		Donors             []string `json:"donors"`
		SubscriptionBypass []string `json:"subscription_bypass"`
	} `json:"moderation"`
	Proxying struct {
		Enabled   bool     `json:"enabled"`
		ProxyURLs []string `json:"proxy_urls"`
		Username  string   `json:"username"`
		Password  string   `json:"password"`
	} `json:"proxying"`
}

type StatusResponse struct {
	Status    bool `json:"status"`
	Users     int  `json:"users"`
	Servers   int  `json:"servers"`
	Shards    int  `json:"shards"`
	CacheSize int  `json:"cache_size"`
	Uptime    int  `json:"uptime"`
}

type SlashCommand struct {
	discord.SlashCommandCreate

	Handler     func(event *events.ApplicationCommandInteractionCreate)
	Name        string
	Description string
	Intensity   int
	Plus        bool
}
