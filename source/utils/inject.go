package utils

import (
	"encoding/json"
	"os"
)

// LoadCfg loads config.json and assigns the loaded configuration to
// the Config struct
func LoadCfg() (Config, error) {
	// Load config.json
	file, err := os.Open("config.json")
	if err != nil {
		return Config{}, err
	}
	defer file.Close()

	var config Config
	err = json.NewDecoder(file).Decode(&config)
	if err != nil {
		return Config{}, err
	}

	return config, nil
}
