# Subscriber Setup

Use this when other people want to receive the same bounty notifications.

## Recommended: Telegram Channel

The easiest subscriber model is a Telegram channel.

1. Create a Telegram channel, for example `Superteam Bounty Alerts`.
2. Add the bot to the channel as an admin.
3. Give the channel a public username, for example:

```text
@superteam_bounty_alerts
```

4. In GitHub Actions secrets, update:

```text
TELEGRAM_CHAT_ID=@superteam_bounty_alerts
```

5. Share the channel invite link in the engagement post.

Anyone who joins the channel will receive the bounty alerts automatically. No code changes are needed for each new subscriber.

## Optional: Email Group

For email subscribers, use a mailing list or Google Group.

Set the GitHub Actions secret:

```text
EMAIL_TO=your-group-email@googlegroups.com
```

Then people can subscribe through the email group instead of editing the tracker each time.

## Best Engagement Flow

For public engagement, use Telegram as the main subscription path:

```text
Join the Telegram channel to get automatic Superteam bounty alerts.
```

This is easier than collecting individual chat IDs or email addresses.
