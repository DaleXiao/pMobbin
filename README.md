# pMobbin (Go)

Unofficial Mobbin API proxy. Login with your Mobbin account, then search/browse app designs.

Rewritten from Python/FastAPI to Go — single binary, ~8MB Docker image, zero dependencies.

## Quick Start

```bash
# Clone
git clone https://github.com/DaleXiao/pMobbin
cd pMobbin

# Set your API key (get it from Mobbin browser devtools → Network → look for apikey header)
cp .env.example .env
# Edit .env and add your MOBBIN_API_KEY

# Run with Docker
docker compose up -d --build

# Or run directly
go build -o pmobbin . && MOBBIN_API_KEY=your_key ./pmobbin
```

## API

### Auth

```bash
# Password login
curl -X POST http://localhost:8085/api/login/password \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "xxx"}'

# OTP login (two steps)
curl -X POST http://localhost:8085/api/login/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'

curl -X POST http://localhost:8085/api/login/verify \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "otp": "123456"}'
```

### Data

```bash
# Search apps
curl "http://localhost:8085/api/search?q=uber"
curl "http://localhost:8085/api/search?q=uber&platform=android"

# Latest apps
curl "http://localhost:8085/api/apps/latest"
curl "http://localhost:8085/api/apps/latest?limit=10&platform=ios"

# Browse by category
curl "http://localhost:8085/api/apps?category=Travel%20%26%20Transportation"
```

## Architecture

- `main.go` — entry point, routes
- `mobbin/client.go` — Mobbin/Supabase API client (auth + data)
- `api/handler.go` — HTTP handlers

Auth goes through Supabase (Mobbin's backend). The JWT from login is used for both the Supabase REST API and Mobbin's first-party `/api/` endpoints.
