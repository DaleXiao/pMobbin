package main

import (
	"log"
	"net/http"
	"os"

	"github.com/DaleXiao/pMobbin/api"
	"github.com/DaleXiao/pMobbin/mobbin"
)

func main() {
	apiKey := os.Getenv("MOBBIN_API_KEY")
	if apiKey == "" {
		log.Fatal("MOBBIN_API_KEY is required")
	}

	client := mobbin.NewClient(apiKey)
	handler := api.NewHandler(client)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8085"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /", handler.Health)
	mux.HandleFunc("POST /api/login/password", handler.LoginPassword)
	mux.HandleFunc("POST /api/login/send-otp", handler.SendOTP)
	mux.HandleFunc("POST /api/login/verify", handler.VerifyOTP)
	mux.HandleFunc("GET /api/search", handler.Search)
	mux.HandleFunc("GET /api/apps/latest", handler.LatestApps)
	mux.HandleFunc("GET /api/apps", handler.BrowseApps)

	log.Printf("pMobbin listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
