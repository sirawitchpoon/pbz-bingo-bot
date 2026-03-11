# Bingo Bot

> **Bingo Prediction event bot for the Phantom Blade Zero community.**  
> Users submit prediction images via private tickets; submissions are forwarded to an admin channel.

---

## Overview

| | |
|---|---|
| **Part of** | Phantom Blade Zero (PBZ) — Discord bot ecosystem |
| **Role** | Event submission (ticket-style, image forwarding) |
| **Stack** | Python 3.10+, discord.py, SQLite |

When a Bingo Prediction event is active, users click a **Submit Prediction** button. A private temporary channel is created for them; they upload their image, confirm, and the image is forwarded to an admin-only channel. The temporary channel is deleted after submission or after 10 minutes of inactivity.

---

## Features

- **Event setup** — Admins use `/setup_bingo event_name:"..."` to post the submission button.
- **Ticket system** — One private temporary channel per user per event.
- **Privacy** — Only the submitter and admins see the channel.
- **Auto-cleanup** — Channels removed after submit or 10 min inactivity.
- **Docker** — Stack 7 in multi-stack PBZ deployment.

---

## Quick Start

```bash
# .env: DISCORD_TOKEN, DISCORD_APP_ID, TARGET_CHANNEL_ID
docker compose up -d
```

SQLite (`bingo_data.db`) is bind-mounted; data persists across restarts.

---

## Commands

| Command | Who | Description |
|---------|-----|--------------|
| `/setup_bingo event_name:"..."` | Admin | Post submission button in current channel |

---

## Permissions

Bot role must be **above** user/admin roles in Server Settings → Roles. Category needs: Manage Channels, Manage Permissions. Target channel needs: View Channel, Send Messages, Attach Files, Embed Links.

---

## Project Structure

```
Bingo-bot/
├── main.py
├── bingo_data.db      # SQLite (host-persisted)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## License

ISC
