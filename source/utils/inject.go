package utils

import (
	"encoding/json"
	"os"
)

// LoadCfg loads config.json and assigns the loaded configuration to
// the Config struct
func LoadCfg() (struct{}, error) {
	// Load config.json
	file, err := os.Open("config.json")
	if err != nil {
		return struct{}{}, err
	}
	defer file.Close()

	var config struct{}
	err = json.NewDecoder(file).Decode(&config)
	if err != nil {
		return struct{}{}, err
	}

	return config, nil
}
