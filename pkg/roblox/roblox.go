package roblox

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/RoWhoIs/RoWhoIs/pkg/proxypool"
)

func avatarHeadShotURL(userID, size string, circular bool) string {
	return fmt.Sprintf("https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds=%s&size=%s&format=Png&isCircular=%t", userID, size, circular)
}

var Blocked = "Blocked"
var NotOK = "NotOK"

// GetPlayerBust returns the URL to the bust of the passed player.
// An error is returned when something unexpected happens, for example if the
// response is not as expected.
func GetPlayerBust(ctx context.Context, pool *proxypool.ProxyPool, userID, size string) (string, error) {
	proxy, err := pool.GetProxy("users/avatar-headshot")
	if err != nil {
		return "", fmt.Errorf("getting http client from pool: %v", err)
	}

	url := avatarHeadShotURL(userID, size, true)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("creating request with context: %v", err)
	}
	auth := fmt.Sprintf("%s:%s", proxy.Config.Username, proxy.Config.Password)
	basicAuth := "Basic " + base64.StdEncoding.EncodeToString([]byte(auth))
	req.Header.Add("Proxy-Authorization", basicAuth)

	resp, err := proxy.Client.Do(req)
	if err != nil {
		return "", fmt.Errorf("client do: %v", err)
	}
	if resp.StatusCode != 200 {
		return NotOK, nil
	}

	avatarResp := &AvatarHeadShotResponse{}
	jsonPayload, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("reading body: %v", err)
	}
	if err := json.Unmarshal(jsonPayload, avatarResp); err != nil {
		return "", fmt.Errorf("unmarshalling resp: %v", err)
	}
	if avatarResp.Data[0].State == "Blocked" {
		return Blocked, nil
	}
	if avatarResp.Data[0].State == "Completed" {
		return avatarResp.Data[0].ImageURL, nil
	}
	return "", fmt.Errorf("unknown")
}

type AvatarHeadShotResponse struct {
	Data []struct {
		TargetID int    `json:"targetId"`
		State    string `json:"state"`
		ImageURL string `json:"imageUrl"`
		Version  string `json:"version"`
	} `json:"data"`
}
