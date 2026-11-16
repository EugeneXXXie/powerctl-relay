# powerctl-relay

家里一直开着的中转。手机只访问它。它负责发网络唤醒，并通知电脑上的代关机。

Always-on relay. The phone talks only to this service. It sends Wake-on-LAN and asks each computer agent to shut down.

## What it does

A small Python service, run with Docker Compose on the host network so broadcast wake packets can leave the container.

- `GET /status` probes each agent and returns `on`, `off`, or the reported system
- `POST /power` with `{"id","action":"on"|"off"}`
- The phone password is checked against `password_hash`
- `on` sends a magic packet to the machine MAC
- `off` calls that machine's agent `POST /shutdown`

## Setup

```text
copy .env.example .env
copy config.example.json data/config.json
```

Set `POWER_RELAY_DATA` in `.env`. Put real MAC addresses, agent URLs, and secrets in `data/config.json`. Create the password hash with:

```text
python relay.py --hash
```

Then:

```text
docker compose up -d --build
```

`.env` and `config.json` are not committed.
