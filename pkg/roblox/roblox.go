package roblox

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"github.com/RoWhoIs/RoWhoIs/pkg/proxypool"
)

func avatarHeadShotURL(userID int, size string, headshot, circular bool) string {
	endpoint := "avatar"
	if headshot {
		endpoint = "avatar-headshot"
	}
	return fmt.Sprintf("https://thumbnails.roblox.com/v1/users/%s?userIds=%d&size=%s&format=Png&isCircular=%t", endpoint, userID, size, circular)
}

type BlockedErr struct{}
type NotOKErr struct{ StatusCode int }

func (e BlockedErr) Error() string { return "blocked" }
func (e NotOKErr) Error() string   { return fmt.Sprintf("request returned: %d", e.StatusCode) }

func GetPlayerBust(ctx context.Context, pool *proxypool.ProxyPool, userID int) (string, error) {
	return GetPlayerImage(ctx, pool, userID, "420x420", true, false)
}

func GetPlayerHeadShot(ctx context.Context, pool *proxypool.ProxyPool, userID int) (string, error) {
	return GetPlayerImage(ctx, pool, userID, "60x60", true, true)
}

// GetPlayerImage returns the URL to the bust of the passed player.
// An error is returned when something unexpected happens, for example if the
// response is not as expected.
func GetPlayerImage(ctx context.Context, pool *proxypool.ProxyPool, userID int, size string, headshot, circular bool) (string, error) {
	url := avatarHeadShotURL(userID, size, headshot, circular)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("creating request with context: %v", err)
	}

	resp, err := pool.Do(req)
	if err != nil {
		return "", fmt.Errorf("client do: %v", err)
	}
	if resp.StatusCode != 200 {
		return "", &NotOKErr{}
	}

	avatarResp := &AvatarHeadShotResponse{}
	jsonPayload, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("reading body: %v", err)
	}
	if err := json.Unmarshal(jsonPayload, avatarResp); err != nil {
		return "", fmt.Errorf("unmarshalling resp: %v", err)
	}
	if len(avatarResp.Data) == 0 {
		return "", fmt.Errorf("no data in response")
	}
	if avatarResp.Data[0].State == "Blocked" {
		return "", &BlockedErr{}
	}
	if avatarResp.Data[0].State == "Completed" {
		return avatarResp.Data[0].ImageURL, nil
	}
	return "", fmt.Errorf("unknown")
}

func UserIDToUser(ctx context.Context, pool *proxypool.ProxyPool, userID int) (*User, error) {
	requestBody := struct {
		UserIds            []int `json:"userIds"`
		ExcludeBannedUsers bool  `json:"excludeBannedUsers"`
	}{
		UserIds:            []int{userID},
		ExcludeBannedUsers: false,
	}
	req, err := postRequestWithJSON(ctx, "https://users.roblox.com/v1/users", requestBody)
	if err != nil {
		return nil, fmt.Errorf("creating post request: %v", err)
	}

	resp, err := pool.Do(req)
	if err != nil {
		return nil, fmt.Errorf("creating post request: %v", err)
	}
	if resp.StatusCode != 200 {
		return nil, &NotOKErr{resp.StatusCode}
	}

	users := &UserIDToUsernameResponse{}
	err = unmarshalHTTPResponseIntoStruct(resp, users)
	if err != nil {
		return nil, fmt.Errorf("unmarshalling resp: %v", err)
	}
	if users.Users == nil || len(users.Users) == 0 {
		return nil, fmt.Errorf("no users returned")
	}
	return &users.Users[0], nil
}

type AvatarHeadShotResponse struct {
	Data []struct {
		TargetID int    `json:"targetId"`
		State    string `json:"state"`
		ImageURL string `json:"imageUrl"`
		Version  string `json:"version"`
	} `json:"data"`
}
type UserIDToUsernameResponse struct {
	Users []User `json:"data"`
}

type User struct {
	ID               int    `json:"id"`
	Name             string `json:"name"`
	DisplayName      string `json:"displayName"`
	HasVerifiedBadge bool   `json:"hasVerifiedBadge"`
}

func postRequestWithJSON(ctx context.Context, url string, v any) (*http.Request, error) {
	rawJSON, err := json.Marshal(v)
	if err != nil {
		return nil, fmt.Errorf("marshalling JSON: %v", err)
	}
	log.Println("rawJSON")
	log.Println(string(rawJSON))
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(rawJSON))
	if err != nil {
		return nil, fmt.Errorf("creating request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	return req, nil
}

func unmarshalHTTPResponseIntoStruct(resp *http.Response, v any) error {
	jsonPayload, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading body: %v", err)
	}
	if err := json.Unmarshal(jsonPayload, v); err != nil {
		return fmt.Errorf("unmarshalling resp: %v", err)
	}
	return nil
}
