package server

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/RoWhoIs/RoWhoIs/pkg/proxypool"
)

type Config struct {
	Proxies      []proxypool.ProxyConfig `json:"proxies"`
	DiscordToken string                  `json:"discord_token"`
}

func WriteConfig(config *Config) (string, error) {
	bytes, err := json.Marshal(config)
	if err != nil {
		return "", fmt.Errorf("unmarshalling json: %v", err)
	}
	return string(bytes), nil
}

func ReadConfig(envVarName string) (*Config, error) {
	jsonConfig, ok := os.LookupEnv(envVarName)
	if !ok {
		return nil, fmt.Errorf("env var '%s' not set", envVarName)
	}
	config := &Config{}
	err := json.Unmarshal([]byte(jsonConfig), config)
	if err != nil {
		return nil, fmt.Errorf("unmarshalling json: %v", err)
	}
	return config, nil
}
