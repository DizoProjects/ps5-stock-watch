# PS5 Pro stock backup: PlayStation Direct UK → Telegram

A free GitHub job that checks PlayStation Direct every ~5 minutes and messages your Telegram when the
PS5 Pro comes into stock, or when the queue opens (that's how drops start). It's a backup for the VPS
watcher: it only covers PlayStation Direct, because Smyths blocks requests that don't come from a real browser.

## Setup (about 10 minutes, all in the browser)

**1. Make a GitHub account** at <https://github.com/signup> if you don't have one.

**2. Create a repository**
- Go to <https://github.com/new>
- Name: `ps5-stock-watch` (anything works)
- Choose **Public**. Public repos get unlimited free run minutes, and your Telegram token still stays secret
  (step 4). A private repo would run out of free minutes at this frequency.
- Tick **Add a README file**, then click **Create repository**.

**3. Add the files** (repeat for each one: **Add file → Create new file**, type the name, paste, **Commit changes**)

| File name to type (including folders) | Paste the contents of |
|---|---|
| `ps_direct_check.py` | `ps_direct_check.py` from this folder |
| `requirements.txt` | `requirements.txt` |
| `.gitignore` | `.gitignore` |
| `.github/workflows/ps-direct-watch.yml` | `.github/workflows/ps-direct-watch.yml` |

Typing the slashes in the name creates the folders automatically.

**4. Add your Telegram details as secrets** (encrypted: nobody can read them, even though the repo is public)
- In the repository: **Settings → Secrets and variables → Actions → New repository secret**
- Name `TELEGRAM_BOT_TOKEN`, value = your bot token (the same one you used for the VPS)
- Name `TELEGRAM_CHAT_ID`, value = your chat ID (SETUP-TELEGRAM.bat prints it at the end, or it's the
  `telegram_chat_id` value in `stock_watch.json` on the VPS)

**5. Start it**
- Open the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
- Click **PS Direct PS5 Pro watch → Run workflow**. Within a minute you should get
  "✅ GitHub backup watcher is running" on Telegram.
- From then on it runs by itself every ~5 minutes, 24/7, with your laptop off.

## What you'll get
- 🚨 when PS Direct shows the PS5 Pro in stock or opens its queue (repeats every 30 minutes while in stock)
- a note when it sells out again
- ⚠️ if it can't read the page 3 runs in a row (e.g. Sony starts blocking GitHub's servers)
- 💤 one "still running" message a day

## Good to know
- GitHub's 5-minute schedule is "best effort": when GitHub is busy, runs can be 10–20 minutes late or skipped.
  That's why this is the backup and the VPS is the main watcher.
- Stock is read from the page's product data and buy button, not the description text, which Sony can
  leave saying "out of stock" after a restock.
- To pause it: **Actions → PS Direct PS5 Pro watch → ⋯ → Disable workflow**.
