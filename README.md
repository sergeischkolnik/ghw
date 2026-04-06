# Telegram Bot Workflow Assistant

A simple Telegram bot that helps workers follow company workflows while collecting data.

## Setup Instructions

### 1. Get a Telegram Bot Token
- Open Telegram and search for `@BotFather`
- Send `/newbot` and follow the instructions
- Copy the token provided (looks like: `123456789:ABCdefGHIjklmnoPQRstuvWXYZ`)

### 2. Install Dependencies
```bash
pip install -r requirements-bot.txt
```

### 3. Configure the Bot
Create a `.env` file with:
```env
TELEGRAM_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

`DATABASE_URL` and `TELEGRAM_TOKEN` are required at startup.

### 4. Run the Bot
```bash
python main.py
```

## Render Deployment Checklist

1. Service type: Web service.
2. Start command: `python -u main.py`.
3. Build command: `bash build.sh`.
4. Required env vars in Render:
	- `TELEGRAM_TOKEN`
	- `DATABASE_URL`
5. Verify health endpoint returns 200:
	- `/health`
6. Verify logs show polling supervisor running continuously.

## Current Features
- `/start` command - Initial greeting
- Replies with "hello" to any message
- `/workflow` command - begin the interactive maintenance workflow

## Workflow Usage
1. Send `/workflow` to the bot.
2. Choose one of the top‑level options (e.g. Taller, Servicio).
3. Pick a subcategory such as _Motor_ or _Mangueras_.
4. In the checklist view you can tap items to toggle them (multi‑select).
5. Press **Hecho** when finished selecting items.
6. Select additional subcategories or press **Finalizar** when done.
7. The bot automatically records start/end timestamps.
8. You will be asked about comments and PANAS; respond yes/no and provide text if requested.

At the end a summary of your entries will be shown.

## Next Steps
We can continue expanding categories and handle storage or reporting of the collected data.
