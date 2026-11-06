"""
PlayStation Direct (UK) PS5 Pro stock check for GitHub Actions. Sends Telegram alerts.

Runs once per workflow run. State (last result, alert times, failure streak) is kept in state.json,
which the workflow carries between runs with actions/cache.

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (GitHub repository secrets). Without them it just prints.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from curl_cffi import requests

URL = os.environ.get("PS_DIRECT_URL", "https://direct.playstation.com/en-gb/buy-consoles/playstation5-pro-console-2-tb")
STATE = Path(os.environ.get("STATE_FILE", "state.json"))
REALERT_SECONDS = 30 * 60

IN, OUT, QUEUE, UNKNOWN = "IN STOCK", "out of stock", "QUEUE OPEN", "unknown"


def classify(final_url, status, html):
    """Work out the stock state from the fetched page."""
    host = final_url.lower()
    if "queue-it" in host or "queue." in host:
        return QUEUE, "Waiting room is live: a drop is starting"
    if status in (403, 429) or status >= 500:
        return UNKNOWN, f"PlayStation answered HTTP {status} (likely blocking GitHub's servers)"
    return classify_html(html)


IN_SCHEMA = {"InStock", "LimitedAvailability", "PreOrder", "BackOrder", "OnlineOnly"}
OUT_SCHEMA = {"OutOfStock", "SoldOut", "Discontinued"}


BUY_WORDS = re.compile(r"add to (cart|basket)|buy now|sign in to (order|buy|purchase)|pre-?order|checkout", re.I)


def classify_html(html):
    """
    In stock ONLY when the page shows a working buy button: <button data-qa="mfeCtaMain#cta#action">Add to Cart</button>,
    not disabled. That's the button you'd click, so if the watcher says IN, you can buy.
    The product data (schema.org InStock) and the price slot can flip minutes before the button does, while the
    page still says "Not available for purchase": that's what caused false alerts. They're now only noted.
    """
    schema = set(re.findall(r"schema\.org/(\w+)", html)) & (IN_SCHEMA | OUT_SCHEMA)
    m = re.search(r'data-qa="mfeCtaMain#offer0#finalPrice"[^>]*>([^<]*)<', html)
    price = m.group(1).strip() if m else None
    b = re.search(r'<button\b([^>]*data-qa="mfeCtaMain#cta#action"[^>]*)>(.*?)</button>', html, re.S)
    btn_text = re.sub(r"<[^>]+>|\s+", " ", b.group(2)).strip() if b else ""
    btn_live = bool(b) and not re.search(r'\bdisabled\b|aria-disabled="true"', b.group(1)) and bool(BUY_WORDS.search(btn_text))
    if btn_live:
        return IN, f"'{btn_text}' button is live" + (f" at {price}" if price and "£" in price else "")
    early = []
    if schema & IN_SCHEMA:
        early.append(f"product data says {'/'.join(sorted(schema & IN_SCHEMA))}")
    if price and "£" in price:
        early.append(f"price shows {price}")
    if early:  # stock data is moving but you can't buy yet: logged, not alerted
        return OUT, "not buyable yet, but " + " and ".join(early) + (f"; button says '{btn_text}'" if btn_text else "")
    if schema & OUT_SCHEMA or (price and "not available" in price.lower()) or "mfeCtaMain" in html:
        return OUT, ""
    return UNKNOWN, "couldn't find the stock data or buy button on the page"


def fetch():
    r = requests.get(URL, impersonate="chrome", timeout=40, allow_redirects=True,
                     headers={"Accept-Language": "en-GB,en;q=0.9"})
    return r.url, r.status_code, r.text


def telegram(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    print(f"MESSAGE: {text}")
    if not token or not chat:
        print("(no Telegram secrets set, so nothing sent)")
        return False
    api = os.environ.get("TELEGRAM_API", "https://api.telegram.org")
    try:
        urlopen(f"{api}/bot{token}/sendMessage", data=urlencode({"chat_id": chat, "text": text}).encode(), timeout=20)
        return True
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = time.time()
    first_run = not state

    try:
        final_url, status, html = fetch()
        result, detail = classify(final_url, status, html)
    except Exception as e:
        result, detail = UNKNOWN, f"fetch failed: {str(e)[:100]}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{stamp}] PlayStation Direct PS5 Pro: {result} {detail}")

    if first_run:
        telegram(f"✅ GitHub backup watcher is running. PlayStation Direct PS5 Pro is currently: {result}.")

    if result in (IN, QUEUE):
        if state.get("last") not in (IN, QUEUE) or now - state.get("last_alert", 0) > REALERT_SECONDS:
            telegram(f"🚨 PS5 Pro {result.lower()} at PlayStation Direct (GitHub backup)\n{detail}\n{URL}")
            state["last_alert"] = now
    elif state.get("last") in (IN, QUEUE):
        telegram(f"PlayStation Direct PS5 Pro is now {result} again (GitHub backup).")

    state["unknown_streak"] = state.get("unknown_streak", 0) + 1 if result == UNKNOWN else 0
    if state["unknown_streak"] == 3:
        telegram(f"⚠️ GitHub backup can't read PlayStation Direct (3 runs in a row): {detail}. "
                 "Your VPS and laptop watchers are unaffected.")

    today = datetime.now(timezone.utc).date().isoformat()
    if state.get("heartbeat") != today and datetime.now(timezone.utc).hour >= 8:
        telegram(f"💤 GitHub backup still running. PlayStation Direct PS5 Pro: {result} as of {stamp}.")
        state["heartbeat"] = today

    state["last"], state["checked"] = result, stamp
    STATE.write_text(json.dumps(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
