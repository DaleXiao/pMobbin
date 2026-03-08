package api

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/DaleXiao/pMobbin/mobbin"
)

// Handler holds API route handlers.
type Handler struct {
	client *mobbin.Client
}

// NewHandler creates a Handler backed by the given Mobbin client.
func NewHandler(c *mobbin.Client) *Handler {
	return &Handler{client: c}
}

// --- helpers ---

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func errJSON(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func requireAuth(w http.ResponseWriter, c *mobbin.Client) bool {
	if !c.Authenticated() {
		errJSON(w, 403, "Not authenticated. Call login first.")
		return false
	}
	return true
}

// --- routes ---

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]string{
		"status":  "ok",
		"message": "pMobbin (Go) is running",
	})
}

func (h *Handler) LoginPassword(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, 400, "invalid request body")
		return
	}
	if err := h.client.LoginPassword(req.Email, req.Password); err != nil {
		errJSON(w, 401, err.Error())
		return
	}
	writeJSON(w, 200, map[string]string{"message": "Login successful"})
}

func (h *Handler) SendOTP(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email string `json:"email"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, 400, "invalid request body")
		return
	}
	if err := h.client.SendOTP(req.Email); err != nil {
		errJSON(w, 500, err.Error())
		return
	}
	writeJSON(w, 200, map[string]string{"message": "OTP sent to " + req.Email})
}

func (h *Handler) VerifyOTP(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email string `json:"email"`
		OTP   string `json:"otp"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		errJSON(w, 400, "invalid request body")
		return
	}
	if err := h.client.VerifyOTP(req.Email, req.OTP); err != nil {
		errJSON(w, 401, err.Error())
		return
	}
	writeJSON(w, 200, map[string]string{"message": "Login successful"})
}

func (h *Handler) Search(w http.ResponseWriter, r *http.Request) {
	if !requireAuth(w, h.client) {
		return
	}
	q := r.URL.Query().Get("q")
	if q == "" {
		errJSON(w, 400, "query parameter 'q' is required")
		return
	}
	platform := r.URL.Query().Get("platform")

	result, err := h.client.SearchApps(q, platform)
	if err != nil {
		errJSON(w, 502, err.Error())
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write(result)
}

func (h *Handler) LatestApps(w http.ResponseWriter, r *http.Request) {
	if !requireAuth(w, h.client) {
		return
	}
	platform := r.URL.Query().Get("platform")
	limit := 20
	if l := r.URL.Query().Get("limit"); l != "" {
		if v, err := strconv.Atoi(l); err == nil && v > 0 {
			limit = v
		}
	}

	result, err := h.client.LatestApps(platform, limit)
	if err != nil {
		errJSON(w, 502, err.Error())
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write(result)
}

func (h *Handler) BrowseApps(w http.ResponseWriter, r *http.Request) {
	if !requireAuth(w, h.client) {
		return
	}
	category := r.URL.Query().Get("category")
	platform := r.URL.Query().Get("platform")
	pageSize := 20
	if ps := r.URL.Query().Get("pageSize"); ps != "" {
		if v, err := strconv.Atoi(ps); err == nil && v > 0 {
			pageSize = v
		}
	}

	result, err := h.client.BrowseApps(category, platform, pageSize)
	if err != nil {
		errJSON(w, 502, err.Error())
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write(result)
}
