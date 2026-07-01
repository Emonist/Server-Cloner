<div align="center">

# Server Cloner v2

**Blazing-fast, async-powered Discord server structure cloner**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Discord API](https://img.shields.io/badge/Discord%20API-v10-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/developers/docs)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)]()
[![Author](https://img.shields.io/badge/Author-Irenic-9b59b6?style=for-the-badge&logo=github)](https://github.com/Emonist)

**[GitHub](https://github.com/Emonist)**

</div>

## Overview

**Server Cloner v2** is a blazing-fast, async-powered Discord server cloning tool built with Python. It replicates an entire Discord server's structure — including roles, categories, and channels — into a destination server with surgical precision and zero manual effort.

Built for developers, power users, and community managers who need an exact server structure transferred in seconds.

## Architecture

```
Server Cloner v2
│
├── Token Validation Layer       ← Bot + User token auth via Discord API v10
├── Async HTTP Engine            ← aiohttp-powered with rate-limit handling
├── Semaphore Concurrency        ← Controlled parallelism (10 workers default)
│
├── Clone Pipeline
│   ├── 1. Wipe Destination      ← Optional: nuke channels & deletable roles
│   ├── 2. Clone Roles           ← Position-aware role replication
│   ├── 3. Clone Categories      ← Parent structure with permission overwrite mapping
│   ├── 4. Clone Channels        ← Text, Voice, Forum, Announcement types
│   ├── 5. Apply Server Info     ← Name, icon (with base64 transfer), description
│   └── 6. Verify + Repair       ← Position & parent mismatch auto-fix
│
└── CLI Interface                ← Live progress bars, tables, styled output
```

## Features

| Feature | Description |
|---------|-------------|
| Full Server Clone | Roles, Categories, Channels cloned in correct order |
| Async + Concurrent | 10 parallel workers via asyncio + aiohttp |
| Rate Limit Safe | Auto-detects 429s and waits with precise retry_after |
| Server Icon Transfer | Downloads and re-uploads icon as base64 |
| Permission Overwrites | Role-based permission maps transferred accurately |
| Auto Retry | Exponential backoff on 5xx errors (up to 5 retries) |
| Post-Clone Verify | Checks positions and parents, auto-repairs mismatches |
| Terminal UI | Styled panels, progress bars, live status |
| Smart Wipe Mode | Skips system channels and bot-managed roles |
| Position Ordering | Roles and channels placed in correct hierarchy |

## Requirements

```
Python 3.10+
aiohttp
colorama
```

Install dependencies:

```bash
pip install aiohttp colorama
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Emonist/Server-Cloner.git
cd Server-Cloner
```

### 2. Install Dependencies

```bash
pip install aiohttp colorama
```

### 3. Prepare Your Bot

- Create a bot at [discord.com/developers](https://discord.com/developers/applications)
- Enable **Server Members Intent** and **Message Content Intent**
- Set permissions: `Administrator` (or `Manage Channels` + `Manage Roles`)
- Invite the bot to the **destination** server:

```
https://discord.com/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot
```

### 4. Run the Tool

```bash
python main.py
```

## Usage Walkthrough

```
--- tokens -------------------------------------------------

  Bot Token:  ••••••••••••••••••••
  User Token: ••••••••••••••••••••

  ✓  Bot BotName#0000 authenticated
  ✓  User UserName#0000 authenticated

--- source server -------------------------------------------

  Source Server ID: 123456789012345678

  ✓  SERVER NAME (123456789012345678)
     members: 1500  |  roles: 12  |  channels: 34

--- destination server --------------------------------------

  Destination Server ID: 987654321098765432
  ✓  bot is in DESTINATION SERVER

  Wipe destination before cloning? [Y/n]: Y

--- wiping channels -----------------------------------------
--- wiping roles --------------------------------------------
--- cloning roles -------------------------------------------
--- cloning categories --------------------------------------
--- cloning channels ----------------------------------------
--- applying server info ------------------------------------
--- verification --------------------------------------------
--- summary -------------------------------------------------

  ✓  roles cloned:      12/12
  ✓  categories cloned:  5/5
  ✓  channels cloned:   29/29
  ✓  done — zero errors
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| MAXWORKERS | 10 | Max concurrent API requests |
| BASE | https://discord.com/api/v10 | Discord API base URL |

Adjust MAXWORKERS at the top of main.py to tune speed vs. rate-limit tolerance.

## Channel Types Supported

| Type ID | Type | Support |
|---------|------|---------|
| 0 | Text Channel | ✅ topic, NSFW, slowmode |
| 2 | Voice Channel | ✅ bitrate, user limit |
| 4 | Category | ✅ |
| 5 | Announcement | ✅ |
| 15 | Forum | ✅ |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| bot token rejected | Invalid/expired bot token | Regenerate in Developer Portal |
| bot has no access to destination | Bot not in server | Invite bot with admin perms |
| role creation failed | Bot role below target role | Move bot role to top of hierarchy |
| channel fetch failed | User not in source server | Join source server with your account |
| max retries exceeded | Network instability | Check connection and retry |
| 429 rate limited | Too many requests | Handled automatically by the script |

## Project Structure

```
Server-Cloner/
│
├── main.py          ← Core cloner logic (async, aiohttp, colorama)
└── README.md        ← This file
```

## Security Notice

> **WARNING:** Never share your user token. It grants full access to your Discord account. This tool stores tokens only in memory during runtime — they are never saved to disk.

- Do **not** commit tokens to version control
- This tool uses user tokens only for **read** access (fetching source server structure)

## Legal / ToS Disclaimer

> **CAUTION:** Using self-bot features (user tokens) may violate [Discord's Terms of Service](https://discord.com/terms). Use this tool only on servers you own or have explicit permission to clone. The author holds no responsibility for any account penalties.

## Built With

- **[Python 3.10+](https://python.org)** — Core language
- **[aiohttp](https://docs.aiohttp.org/)** — Async HTTP client
- **[colorama](https://pypi.org/project/colorama/)** — Terminal styling
- **[Discord API v10](https://discord.com/developers/docs/reference)** — Target API

## Support

If this tool helped you, drop a **star** — it helps a lot!

[![Star on GitHub](https://img.shields.io/github/stars/Emonist/Server-Cloner?style=for-the-badge&logo=github&color=yellow)](https://github.com/Emonist/Server-Cloner/stargazers)

---

<div align="center">

**Made by Irenic**

*Server Cloner v2 — precision cloning, zero compromise.*

</div>
