package portal

import (
	"log/slog"
	"mime"
	"net/http"
	"os"
	"path/filepath"
)

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
	if fileExists(cleanPath) {
		w.Header().Set("Content-Type", mime.TypeByExtension(filepath.Ext(cleanPath)))
		http.ServeFile(w, r, cleanPath)
	} else if fileExists(requestedPath) {
		w.Header().Set("Content-Type", mime.TypeByExtension(filepath.Ext(requestedPath)))
		http.ServeFile(w, r, requestedPath)
	} else {
		if fileExists("portal/404.html") {
			http.ServeFile(w, r, "portal/404.html")
		} else {
			http.NotFound(w, r)
		}
	}
}

// StartServer initializes the internal management portal
func StartServer() error {
	http.HandleFunc("/", handler)
	slog.Info("Initialized Internal Management Portal on http://localhost:63415")
	go func() {
		err := http.ListenAndServe(":63415", nil)
		if err != nil {
			slog.Error(err.Error())
		}
	}()
	return nil
}
