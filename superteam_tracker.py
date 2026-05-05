#!/usr/bin/env python3
"""
Superteam Earn bounty tracker.

Polls Superteam Earn for new bounties and emails an alert when fresh listings
appear. Seen bounty IDs are persisted in seen_bounties.json beside this file.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).parent
SEEN_FILE = BASE_DIR / "seen_bounties.json"
LOG_FILE = BASE_DIR / "tracker.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://earn.superteam.fun/",
}


@dataclass(frozen=True)
class Config:
    email_from: str
    email_to: str
    email_pass: str
    telegram_bot_token: str
    telegram_chat_id: str
    alert_channels: tuple[str, ...]
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    request_timeout: int = 20
    listing_limit: int = 20
    seed_only: bool = False
    test_alert: bool = False


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None


def load_dotenv(path: Path = BASE_DIR / ".env") -> None:
    """Load a tiny KEY=VALUE .env file without adding another dependency."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def build_config(seed_only: bool = False, test_alert: bool = False) -> Config:
    load_dotenv()
    channels = tuple(
        channel.strip().lower()
        for channel in os.environ.get("ALERT_CHANNELS", "email").split(",")
        if channel.strip()
    )
    return Config(
        email_from=os.environ.get("EMAIL_FROM", ""),
        email_to=os.environ.get("EMAIL_TO", ""),
        email_pass=os.environ.get("EMAIL_PASS", ""),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        alert_channels=channels or ("email",),
        smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=env_int("SMTP_PORT", 587),
        request_timeout=env_int("REQUEST_TIMEOUT", 20),
        listing_limit=env_int("LISTING_LIMIT", 20),
        seed_only=seed_only,
        test_alert=test_alert,
    )


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


log = setup_logging()


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            log.warning("Could not read %s; starting fresh.", SEEN_FILE)
    return set()


def save_seen(ids: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")


def fetch_via_api(config: Config) -> list[dict[str, Any]] | None:
    url = "https://earn.superteam.fun/api/listings/"
    params = {"type": "bounty", "take": config.listing_limit, "order": "desc"}

    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=config.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log.warning("API fetch failed (%s); trying HTML fallback.", exc)
        return None

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        listings = data.get("data") or data.get("bounties") or data.get("listings") or []
        if isinstance(listings, list):
            return listings

    log.warning("Unexpected API response shape: %s", type(data).__name__)
    return []


def fetch_via_scrape(config: Config) -> list[dict[str, Any]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("beautifulsoup4 is not installed. Run: pip install -r requirements.txt")
        return []

    url = "https://earn.superteam.fun/bounties/"
    try:
        response = requests.get(
            url,
            headers={**HEADERS, "Accept": "text/html"},
            timeout=config.request_timeout,
        )
        response.raise_for_status()
    except Exception as exc:
        log.error("HTML scrape request failed: %s", exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        log.error("__NEXT_DATA__ tag not found. Site structure may have changed.")
        return []

    try:
        blob = json.loads(tag.string or "{}")
        props = blob.get("props", {}).get("pageProps", {})
        result = props.get("bounties") or props.get("listings") or props.get("data") or []
    except Exception as exc:
        log.error("Failed to parse __NEXT_DATA__: %s", exc)
        return []

    if not isinstance(result, list):
        log.warning("Unexpected shape in __NEXT_DATA__. Keys: %s", list(props.keys()))
        return []

    return result[: config.listing_limit]


def fetch_bounties(config: Config) -> list[dict[str, Any]]:
    bounties = fetch_via_api(config)
    if bounties is None:
        log.info("Falling back to HTML scrape.")
        bounties = fetch_via_scrape(config)
    log.info("Fetched %d bounties total.", len(bounties))
    return bounties


def fmt_deadline(raw: Any) -> str:
    if not raw:
        return "Not specified"
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return str(raw)


def bounty_link(bounty: dict[str, Any]) -> str:
    slug = bounty.get("slug", "")
    return f"https://earn.superteam.fun/listing/{slug}/"


def bounty_id(bounty: dict[str, Any]) -> str:
    value = bounty.get("id") or bounty.get("slug") or bounty.get("title")
    return str(value or "")


def sponsor_name(bounty: dict[str, Any]) -> str:
    sponsor = bounty.get("sponsor") or {}
    if isinstance(sponsor, dict):
        return str(sponsor.get("name") or "Unknown")
    return "Unknown"


def reward_value(bounty: dict[str, Any]) -> str:
    reward = bounty.get("usdValue") or bounty.get("rewardAmount") or "?"
    return str(reward)


def build_html(bounties: list[dict[str, Any]]) -> str:
    count = len(bounties)
    cards = ""

    for bounty in bounties:
        title = bounty.get("title", "Untitled")
        sponsor = sponsor_name(bounty)
        reward = reward_value(bounty)
        bounty_type = str(bounty.get("type") or "Bounty").capitalize()
        deadline = fmt_deadline(bounty.get("deadline"))
        link = bounty_link(bounty)

        cards += f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;
                    padding:20px 24px;margin-bottom:16px;">
          <p style="margin:0 0 4px;font-size:11px;color:#7c3aed;font-weight:700;
                    text-transform:uppercase;letter-spacing:.07em;">{bounty_type}</p>
          <h2 style="margin:0 0 4px;font-size:17px;font-weight:700;color:#111827;">{title}</h2>
          <p style="margin:0 0 12px;font-size:13px;color:#6b7280;">by {sponsor}</p>
          <table style="width:100%;font-size:13px;color:#374151;border-collapse:collapse;">
            <tr>
              <td style="padding:4px 0;color:#9ca3af;width:90px;">Reward</td>
              <td style="padding:4px 0;font-weight:700;color:#059669;">${reward}</td>
            </tr>
            <tr>
              <td style="padding:4px 0;color:#9ca3af;">Deadline</td>
              <td style="padding:4px 0;">{deadline}</td>
            </tr>
          </table>
          <a href="{link}" style="display:inline-block;margin-top:14px;padding:9px 20px;
             background:#7c3aed;color:#fff;font-size:13px;font-weight:600;
             border-radius:6px;text-decoration:none;">View Bounty &rarr;</a>
        </div>"""

    plural = "bounty" if count == 1 else "bounties"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:system-ui,sans-serif;">
  <div style="max-width:600px;margin:32px auto;padding:0 16px 32px;">
    <div style="background:#7c3aed;border-radius:8px 8px 0 0;padding:24px 28px;">
      <h1 style="margin:0;font-size:20px;color:#fff;font-weight:700;">
        Superteam Earn Tracker</h1>
      <p style="margin:4px 0 0;font-size:14px;color:#ddd6fe;">
        {count} new {plural} posted</p>
    </div>
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-top:none;
                border-radius:0 0 8px 8px;padding:24px 28px;">
      {cards}
      <p style="font-size:12px;color:#9ca3af;margin:24px 0 0;text-align:center;">
        Sent by your Superteam Earn tracker &middot;
        <a href="https://earn.superteam.fun/bounties/"
           style="color:#7c3aed;text-decoration:none;">Browse all</a>
      </p>
    </div>
  </div>
</body></html>"""


def build_plain(bounties: list[dict[str, Any]]) -> str:
    lines = ["New Superteam Earn bounties:\n"]
    for bounty in bounties:
        lines.append(
            f"- {bounty.get('title', 'Untitled')}\n"
            f"  Sponsor:  {sponsor_name(bounty)}\n"
            f"  Reward:   ${reward_value(bounty)}\n"
            f"  Deadline: {fmt_deadline(bounty.get('deadline'))}\n"
            f"  Link:     {bounty_link(bounty)}\n"
        )
    return "\n".join(lines)


def build_telegram_message(bounties: list[dict[str, Any]]) -> str:
    count = len(bounties)
    plural = "bounty" if count == 1 else "bounties"
    lines = [f"New Superteam Earn {plural}: {count}", ""]

    for bounty in bounties:
        lines.extend(
            [
                f"{bounty.get('title', 'Untitled')}",
                f"Sponsor: {sponsor_name(bounty)}",
                f"Reward: ${reward_value(bounty)}",
                f"Deadline: {fmt_deadline(bounty.get('deadline'))}",
                bounty_link(bounty),
                "",
            ]
        )

    return "\n".join(lines).strip()


def validate_email_config(config: Config) -> bool:
    missing = []
    if not config.email_from:
        missing.append("EMAIL_FROM")
    if not config.email_to:
        missing.append("EMAIL_TO")
    if not config.email_pass:
        missing.append("EMAIL_PASS")

    if missing:
        log.error("Missing email config: %s", ", ".join(missing))
        return False

    return True


def validate_telegram_config(config: Config) -> bool:
    missing = []
    if not config.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not config.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        log.error("Missing Telegram config: %s", ", ".join(missing))
        return False

    return True


def send_email(config: Config, bounties: list[dict[str, Any]]) -> bool:
    if not validate_email_config(config):
        return False

    count = len(bounties)
    subject = (
        f"New Superteam Bounty: {bounties[0].get('title', 'Untitled')}"
        if count == 1
        else f"{count} New Superteam Bounties"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.email_from
    msg["To"] = config.email_to
    msg.attach(MIMEText(build_plain(bounties), "plain", "utf-8"))
    msg.attach(MIMEText(build_html(bounties), "html", "utf-8"))

    try:
        with smtplib.SMTP(
            config.smtp_host,
            config.smtp_port,
            timeout=config.request_timeout,
        ) as server:
            server.ehlo()
            server.starttls()
            server.login(config.email_from, config.email_pass)
            server.send_message(msg)
        log.info("Alert sent for %d new %s.", count, "bounty" if count == 1 else "bounties")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error("Gmail auth failed. Use a Gmail App Password, not your regular password.")
    except smtplib.SMTPException as exc:
        log.error("SMTP error: %s", exc)
    return False


def send_telegram(config: Config, bounties: list[dict[str, Any]]) -> bool:
    if not validate_telegram_config(config):
        return False

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": config.telegram_chat_id,
        "text": build_telegram_message(bounties),
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=config.request_timeout)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        log.error("Telegram alert failed with HTTP status %s.", status)
        return False
    except requests.RequestException:
        log.error("Telegram alert failed due to a network error.")
        return False

    log.info("Telegram alert sent for %d new bounty/bounties.", len(bounties))
    return True


def send_alerts(config: Config, bounties: list[dict[str, Any]]) -> bool:
    senders = {
        "email": send_email,
        "telegram": send_telegram,
    }
    results = []

    for channel in config.alert_channels:
        sender = senders.get(channel)
        if not sender:
            log.error("Unknown alert channel: %s", channel)
            results.append(False)
            continue
        results.append(sender(config, bounties))

    return bool(results) and all(results)


def seed_seen(bounties: list[dict[str, Any]]) -> None:
    ids = {bounty_id(bounty) for bounty in bounties if bounty_id(bounty)}
    save_seen(ids)
    log.info("Seeded %d bounty IDs. Future runs will alert only on newer listings.", len(ids))


def sample_bounty() -> dict[str, Any]:
    return {
        "id": "test-alert",
        "slug": "test-alert",
        "title": "Test Alert from Superteam Earn Tracker",
        "sponsor": {"name": "Local Test"},
        "usdValue": "0",
        "type": "bounty",
        "deadline": None,
    }


def run(config: Config) -> int:
    log.info("=== Superteam Earn bounty check ===")

    if config.test_alert:
        ok = send_alerts(config, [sample_bounty()])
        return 0 if ok else 1

    bounties = fetch_bounties(config)
    if not bounties:
        log.warning("No bounties returned. Check the logs above.")
        return 1

    if config.seed_only:
        seed_seen(bounties)
        return 0

    seen = load_seen()
    new_bounties = [bounty for bounty in bounties if bounty_id(bounty) not in seen]

    if not new_bounties:
        log.info("No new bounties. Nothing to send.")
        return 0

    log.info("%d new bounty/bounties found.", len(new_bounties))
    if not send_alerts(config, new_bounties):
        log.error("No alerts were sent. Seen list was not updated.")
        return 1

    seen.update(bounty_id(bounty) for bounty in new_bounties if bounty_id(bounty))
    save_seen(seen)
    log.info("Done. Tracking %d total bounty IDs.", len(seen))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track new Superteam Earn bounties.")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Save current bounties as seen without sending an email.",
    )
    parser.add_argument(
        "--test-alert",
        action="store_true",
        help="Send a sample alert through the configured alert channels.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = build_config(seed_only=args.seed, test_alert=args.test_alert)
    except ValueError as exc:
        log.error(str(exc))
        return 1
    return run(config)


if __name__ == "__main__":
    raise SystemExit(main())
