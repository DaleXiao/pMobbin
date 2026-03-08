// Package mobbin provides a Go client for the Mobbin API.
//
// Authentication flows through Supabase (OTP or password), which yields a JWT
// access token. That token is then used for both the Supabase REST API and the
// Mobbin first-party browse/search API.
package mobbin

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"sync"
	"time"
)

const (
	supabaseBase = "https://ujasntkfphywizsdaapi.supabase.co"
	mobbinBase   = "https://mobbin.com"
	userAgent    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

// Client holds authentication state and provides methods to call Mobbin APIs.
type Client struct {
	mu           sync.RWMutex
	apiKey       string
	accessToken  string
	refreshToken string
	httpClient   *http.Client
}

// NewClient creates a client with the given Supabase anonymous API key.
func NewClient(apiKey string) *Client {
	return &Client{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: 20 * time.Second,
		},
	}
}

// Authenticated returns true when the client has an access token.
func (c *Client) Authenticated() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.accessToken != ""
}

// --- Auth: Password login ---

func (c *Client) LoginPassword(email, password string) error {
	u := supabaseBase + "/auth/v1/token?grant_type=password"
	body, _ := json.Marshal(map[string]string{"email": email, "password": password})

	resp, err := c.supabasePost(u, body)
	if err != nil {
		return fmt.Errorf("password login request failed: %w", err)
	}
	return c.extractTokens(resp)
}

// --- Auth: OTP ---

func (c *Client) SendOTP(email string) error {
	u := supabaseBase + "/auth/v1/otp"
	body, _ := json.Marshal(map[string]any{"email": email, "create_user": false})

	req, _ := http.NewRequest("POST", u, bytes.NewReader(body))
	req.Header.Set("apikey", c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("send OTP failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("send OTP: status %d: %s", resp.StatusCode, b)
	}
	return nil
}

func (c *Client) VerifyOTP(email, otp string) error {
	u := supabaseBase + "/auth/v1/verify"
	body, _ := json.Marshal(map[string]string{"type": "email", "email": email, "token": otp})

	resp, err := c.supabasePost(u, body)
	if err != nil {
		return fmt.Errorf("verify OTP request failed: %w", err)
	}
	return c.extractTokens(resp)
}

// --- Data: Search apps ---

func (c *Client) SearchApps(query, platform string) (json.RawMessage, error) {
	if platform == "" {
		platform = "ios"
	}

	// Try Mobbin first-party search API first
	result, err := c.mobbinSearch(query, platform)
	if err == nil && len(result) > 2 { // not "[]"
		return result, nil
	}

	// Fallback: Supabase ilike on appName
	log.Printf("Mobbin search returned empty, falling back to Supabase ilike for %q", query)
	u := supabaseBase + "/rest/v1/apps"
	params := url.Values{
		"select":  {"*"},
		"platform": {fmt.Sprintf("eq.%s", platform)},
		"appName":  {fmt.Sprintf("ilike.%%%s%%", query)},
		"limit":   {"50"},
		"order":   {"updatedAt.desc"},
	}

	result, err = c.supabaseGet(u, params)
	if err != nil {
		return nil, err
	}

	// If appName empty, try companyName
	if len(result) <= 2 {
		params.Set("appName", "")
		params.Del("appName")
		params.Set("companyName", fmt.Sprintf("ilike.%%%s%%", query))
		result, err = c.supabaseGet(u, params)
	}
	return result, err
}

// --- Data: Browse apps ---

func (c *Client) BrowseApps(category, platform string, pageSize int) (json.RawMessage, error) {
	if platform == "" {
		platform = "ios"
	}
	if pageSize <= 0 {
		pageSize = 20
	}

	u := fmt.Sprintf("%s/api/browse/%s/apps", mobbinBase, platform)
	params := url.Values{
		"pageSize": {fmt.Sprintf("%d", pageSize)},
		"sortBy":   {"publishedAt"},
	}
	if category != "" {
		params.Set("appCategories[]", category)
		params.Set("filterOperator", "and")
	}

	return c.mobbinGet(u, params)
}

// --- Data: Latest apps ---

func (c *Client) LatestApps(platform string, limit int) (json.RawMessage, error) {
	return c.BrowseApps("", platform, limit)
}

// --- internal helpers ---

func (c *Client) supabasePost(u string, body []byte) (map[string]any, error) {
	req, _ := http.NewRequest("POST", u, bytes.NewReader(body))
	req.Header.Set("apikey", c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	b, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("status %d: %s", resp.StatusCode, b)
	}

	var data map[string]any
	if err := json.Unmarshal(b, &data); err != nil {
		return nil, fmt.Errorf("json decode: %w", err)
	}
	return data, nil
}

func (c *Client) extractTokens(data map[string]any) error {
	at, _ := data["access_token"].(string)
	if at == "" {
		return fmt.Errorf("no access_token in response")
	}
	c.mu.Lock()
	c.accessToken = at
	if rt, ok := data["refresh_token"].(string); ok {
		c.refreshToken = rt
	}
	c.mu.Unlock()
	log.Println("Login successful, access token acquired")
	return nil
}

func (c *Client) supabaseGet(u string, params url.Values) (json.RawMessage, error) {
	c.mu.RLock()
	token := c.accessToken
	c.mu.RUnlock()

	req, _ := http.NewRequest("GET", u+"?"+params.Encode(), nil)
	req.Header.Set("apikey", c.apiKey)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	b, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("supabase status %d: %s", resp.StatusCode, b)
	}
	return json.RawMessage(b), nil
}

func (c *Client) mobbinGet(u string, params url.Values) (json.RawMessage, error) {
	c.mu.RLock()
	token := c.accessToken
	c.mu.RUnlock()

	req, _ := http.NewRequest("GET", u+"?"+params.Encode(), nil)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "application/json, text/plain, */*")
	req.Header.Set("Origin", mobbinBase)
	req.Header.Set("Referer", mobbinBase+"/")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	b, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("mobbin status %d: %s", resp.StatusCode, b)
	}
	return json.RawMessage(b), nil
}

func (c *Client) mobbinSearch(query, platform string) (json.RawMessage, error) {
	// Mobbin's search endpoint (discovered from browser network tab)
	u := fmt.Sprintf("%s/api/search", mobbinBase)
	params := url.Values{
		"query":    {query},
		"platform": {platform},
	}
	return c.mobbinGet(u, params)
}
