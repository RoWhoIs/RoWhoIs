# RoWhoIs

This repository contains code needed to run the RoWhoIs discord bot 

## Running

The server can be configured via environment variable. Before running the
server, set the `ROWHOIS_CONFIG` environment variable with the following
structure.

```bash
export ROWHOIS_CONFIG='{
  "proxies": [
    {
      "Host": "<ip>:<port>",
      "Password": "pass",
      "Username": "user"
    }
  ],
  "discord_token": "token"
}'
```

Run the server with `go run cmd/server`
