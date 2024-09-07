package portal

import (
	"log/slog"
	"net/http"
)

// StartServer initializes the internal management portal
func StartServer(RunType string) error {
	// RunType "-d" for development mode, "-p" for production mode
	slog.Info("Initializing Internal Management Portal on http://localhost:63415")
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// TODO: Add JSON API routes that trigger the appropriate functions
		switch r.URL.Path {
		case "/css/main.css":
			http.ServeFile(w, r, "portal/css/main.css")
		case "/Sfavicon.ico":
			http.ServeFile(w, r, "portal/favicon.ico")
		case "/":
			http.ServeFile(w, r, "portal/index.html")
		default:
			http.NotFound(w, r)
		}
	})
	slog.Info("Internal Management Portal initialized")
	return http.ListenAndServe(":63415", nil)
}
