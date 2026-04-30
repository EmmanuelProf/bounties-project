# Superteam Earn Bounty Tracker

A small Python tracker that checks Superteam Earn for new bounties and emails you when fresh opportunities appear.

## What It Does

- Fetches recent bounty listings from Superteam Earn.
- Falls back to the public bounties page if the API request fails.
- Stores seen bounty IDs in `seen_bounties.json`.
- Sends email or Telegram alerts with title, sponsor, reward, deadline, and link.
- Writes run details to `tracker.log`.

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create your local environment file.

```bash
copy .env.example .env
```

4. Edit `.env` with your email settings.

For Gmail, use an App Password, not your normal password. Gmail App Passwords require 2-Step Verification to be enabled.

## Configuration

Required values:

- `ALERT_CHANNELS`: `email`, `telegram`, or `email,telegram`.

For email alerts:

- `EMAIL_FROM`: Gmail address used to send alerts.
- `EMAIL_TO`: Email address that receives alerts.
- `EMAIL_PASS`: Gmail App Password for `EMAIL_FROM`.

For Telegram alerts:

- `TELEGRAM_BOT_TOKEN`: token from BotFather.
- `TELEGRAM_CHAT_ID`: your Telegram chat ID.

Optional values:

- `SMTP_HOST`: defaults to `smtp.gmail.com`.
- `SMTP_PORT`: defaults to `587`.
- `REQUEST_TIMEOUT`: defaults to `20`.
- `LISTING_LIMIT`: defaults to `20`.

## Telegram Setup

1. Open Telegram and message `@BotFather`.
2. Create a bot with `/newbot`.
3. Copy the bot token into `.env` as `TELEGRAM_BOT_TOKEN`.
4. Send any message to your new bot.
5. Get your chat ID by opening this URL in a browser, replacing the token:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

6. Copy the `chat.id` value into `.env` as `TELEGRAM_CHAT_ID`.
7. Set:

```env
ALERT_CHANNELS=telegram
```

Use both email and Telegram with:

```env
ALERT_CHANNELS=email,telegram
```

## First Run

Seed the current bounty list so the first real alert only sends future listings.

```bash
python superteam_tracker.py --seed
```

Then run a normal check:

```bash
python superteam_tracker.py
```

Send a sample alert through the configured channel:

```bash
python superteam_tracker.py --test-alert
```

## Scheduling On Windows

Use Task Scheduler:

- Program/script: path to your Python executable, for example `.venv\Scripts\python.exe`
- Arguments: `superteam_tracker.py`
- Start in: this project folder
- Trigger: repeat every 30 minutes

## Project Files

- `superteam_tracker.py`: main tracker.
- `run_tracker.cmd`: Windows Task Scheduler runner.
- `.env.example`: configuration template.
- `requirements.txt`: Python dependencies.
- `ACHIEVEMENT_PLAN.md`: project goal and roadmap.
- `seen_bounties.json`: generated after seeding or sending alerts.
- `tracker.log`: generated after running the tracker.
