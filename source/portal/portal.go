package portal

import (
	"encoding/json"
	"log/slog"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"rowhois/server"
	"rowhois/utils"

	"github.com/disgoorg/disgo/bot"
)

var Client bot.Client

func InjectClient(client bot.Client) {
	Client = client
}

// fileExists checks if a file exists
func fileExists(filePath string) bool {
	_, err := os.Stat(filePath)
	return !os.IsNotExist(err)
}

// handler is a web server handler for the internal management portal
func handler(w http.ResponseWriter, r *http.Request) {
	requestedPath := "portal" + r.URL.Path
	cleanPath := requestedPath
	if filepath.Ext(requestedPath) == "" {
		cleanPath += ".html"
		if !fileExists(cleanPath) && r.URL.Path == "/" {
			cleanPath = "portal"
		}
	}
	switch r.URL.Path {
	case "/api/stats":
		w.Header().Set("Content-Type", "application/json")
		status := utils.StatusResponse{
			Status:    server.ClientRunning(Client),
			Users:     0,
			Servers:   0,
			Shards:    0,
			CacheSize: 0,
			Uptime:    0,
		}

		jsonData, err := json.Marshal(status)
		if err != nil {
			// Handle the error
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write(jsonData)
	case "/api/shutdown":
		w.Header().Set("Content-Type", "application/json")
		if !server.ClientRunning(Client) {
			http.Error(w, "Server already down", http.StatusBadRequest)
			return
		}
		server.EndServer(Client)
		w.Write([]byte(`{"status":"ok"}`))
	case "/api/start":
		w.Header().Set("Content-Type", "application/json")
		if !server.ClientRunning(Client) {
			http.Error(w, "Server already up", http.StatusBadRequest)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
	default:
		if fileExists(cleanPath) {
			w.Header().Set("Content-Type", mime.TypeByExtension(filepath.Ext(cleanPath)))
			http.ServeFile(w, r, cleanPath)
		} else if fileExists(requestedPath) {
			w.Header().Set("Content-Type", mime.TypeByExtension(filepath.Ext(requestedPath)))
			http.ServeFile(w, r, requestedPath)
		} else if fileExists("portal/404.html") {
			http.ServeFile(w, r, "portal/404.html")
		} else {
			http.NotFound(w, r)
		}
	}
}

// StartServer initializes the internal management portal
func StartServer() error {
	http.HandleFunc("/", handler)
	slog.Info("Initialized Internal Management Portal! [http://localhost:63415]")
	go func() {
		err := http.ListenAndServe(":63415", nil)
		if err != nil {
			slog.Error(err.Error())
		}
	}()
	return nil
}
