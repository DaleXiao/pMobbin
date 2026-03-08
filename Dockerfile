FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /pmobbin .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /pmobbin /pmobbin
EXPOSE 8085
ENV PORT=8085
ENTRYPOINT ["/pmobbin"]
