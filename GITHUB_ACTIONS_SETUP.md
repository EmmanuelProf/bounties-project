# GitHub Actions Setup

Use this when you want the tracker to run in the cloud even when your PC is off.

## 1. Create A GitHub Repository

From this project folder:

```powershell
git init
git add .
git commit -m "Create Superteam tracker"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Do not commit `.env`. It is ignored by `.gitignore`.

## 2. Add GitHub Secrets

In GitHub:

```text
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret
```

Add these secrets:

```text
ALERT_CHANNELS=telegram
TELEGRAM_BOT_TOKEN=your bot token
TELEGRAM_CHAT_ID=your chat id
```

Optional email secrets if you want both channels:

```text
ALERT_CHANNELS=email,telegram
EMAIL_FROM=your sender email
EMAIL_TO=your receiver email
EMAIL_PASS=your Gmail app password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

Optional runtime secrets:

```text
REQUEST_TIMEOUT=20
LISTING_LIMIT=20
```

## 3. Seed The Cloud Tracker

Because `seen_bounties.json` is included in the repo, your current local seen list can seed GitHub.

If you ever need to seed from GitHub directly:

```text
Repo -> Actions -> Superteam Earn Tracker -> Run workflow -> mode: seed
```

## 4. Test The Telegram Alert

Run a manual test:

```text
Repo -> Actions -> Superteam Earn Tracker -> Run workflow -> mode: test-alert
```

If that succeeds, Telegram is connected from the cloud.

## 5. Live Schedule

The workflow runs every 30 minutes:

```yaml
cron: "*/30 * * * *"
```

GitHub cron uses UTC time.

## How It Remembers Seen Bounties

GitHub Actions runners are temporary. After every run, the workflow commits `seen_bounties.json` back to the repository if it changed. That file contains bounty IDs only, not secrets.
