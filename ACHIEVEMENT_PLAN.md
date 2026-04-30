# Superteam Earn Tracker: What We Want To Achieve

## Main Goal

Build a simple tracker that watches Superteam Earn for newly posted bounties and alerts us by email so we can discover opportunities early and act before they become crowded.

## Desired Outcome

The tracker should:

- Check Superteam Earn on a regular schedule.
- Find new bounty listings that have not been seen before.
- Send a clean email alert when new bounties appear.
- Include the bounty title, sponsor, reward, deadline, and direct link.
- Remember already-seen bounties so duplicate emails are not sent.
- Keep logs so we can confirm whether each check worked.

## Current Tracker Behavior

The existing `superteam_tracker.py` script already aims to:

- Fetch recent Superteam Earn bounty listings from the internal API.
- Fall back to scraping the public bounties page if the API request fails.
- Store seen bounty IDs in `seen_bounties.json`.
- Build both plain-text and HTML email versions.
- Send alerts through Gmail SMTP.
- Log activity to `tracker.log`.

## User Flow

1. The script runs automatically every 30 minutes.
2. It fetches the newest bounty listings from Superteam Earn.
3. It compares each listing ID against the saved seen list.
4. If there are no new bounties, it logs the result and stops.
5. If there are new bounties, it emails the details.
6. After sending the email, it saves the new bounty IDs.

## Setup Needed

Before the tracker can run properly, we need to:

- Install dependencies:

```bash
pip install requests beautifulsoup4
```

- Set the sender and receiver emails in `superteam_tracker.py`.
- Create a Gmail App Password for the sender email.
- Set the password as an environment variable named `EMAIL_PASS`.
- Run the script once to seed the seen bounty list.
- Schedule the script to run automatically.

## Success Criteria

The project is successful when:

- The script runs without manual intervention.
- New Superteam bounties trigger an email alert.
- Old bounties do not trigger repeated alerts.
- Logs clearly show fetch results, email status, and tracked bounty count.
- The tracker can recover gracefully if the API fails by using the HTML fallback.

## Nice-To-Have Improvements

Future improvements could include:

- Support Telegram, Discord, or Slack alerts in addition to email.
- Filter alerts by prize amount, sponsor, region, skill, or deadline.
- Send a daily digest instead of one email per check.
- Add a `.env` file for easier local configuration.
- Clean up the current text encoding artifacts in the script comments and messages.
- Add tests for bounty parsing, seen-list storage, and email formatting.
- Package the tracker with a clearer setup guide for reuse on another machine.

## Short Version

We want a reliable Superteam bounty radar: it checks often, spots fresh opportunities, sends useful alerts, avoids duplicates, and gives us enough logging to trust that it is working.
