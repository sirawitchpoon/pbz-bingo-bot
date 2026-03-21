<p align="center">
  <strong>Bingo Bot</strong>
</p>
<p align="center">
  <em>Bingo Prediction event bot for the Phantom Blade Zero community.</em>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/discord.py-2.x-5865F2?logo=discord" alt="discord.py" />
  <img src="https://img.shields.io/badge/license-ISC-green" alt="License" />
  <img src="https://img.shields.io/badge/Phantom%20Blade%20Zero-PBZ%20Ecosystem-8b0000" alt="PBZ" />
</p>

---

Users submit prediction images via private tickets; submissions are forwarded to an admin channel. One button, one temporary channel per user.

## 📋 Overview

| | |
|---|---|
| **Part of** | Phantom Blade Zero (PBZ) — Discord bot ecosystem |
| **Role** | Event submission (ticket-style, image forwarding) |
| **Stack** | Python 3.10+, discord.py, SQLite |

---

## ✨ Features

- **Event setup** — Admins use `/setup_bingo event_name:"..."` to post the submission button.
- **Ticket system** — One private temporary channel per user per event.
- **Privacy** — Only the submitter and admins see the channel.
- **Auto-cleanup** — Channels removed after submit or 10 min inactivity.
- **Docker** — Stack 7 in multi-stack PBZ deployment.

---

## 🚀 Quick Start

```bash
# .env: DISCORD_TOKEN, DISCORD_APP_ID, TARGET_CHANNEL_ID
docker compose up -d
```

SQLite (`bingo_data.db`) is bind-mounted; data persists across restarts.

---

## 📜 Commands

| Command | Who | Description |
|---------|-----|--------------|
| `/setup_bingo event_name:"..."` | Admin | Post submission button in current channel |

---

## 🔐 Permissions

Bot role must be **above** user/admin roles in **Server Settings** → **Roles**. Category needs: **Manage Channels**, **Manage Permissions**. Target channel needs: **View Channel**, **Send Messages**, **Attach Files**, **Embed Links**.

---

## 📁 Project Structure

```
Bingo-bot/
├── main.py
├── bingo_data.db      # SQLite (host-persisted)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🔗 Ecosystem

Other PBZ stacks include **honor-points-service**, **honorbot-pbz**, **Shadow Duel** ([`wuxia-bobozan`](../wuxia-bobozan)), **pbz-dashboard**, etc. Overview: [`docs/README.md`](../docs/README.md).

---

## 📄 License

ISC · Part of the **Phantom Blade Zero** community ecosystem.
