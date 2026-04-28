# BTG Autopilot Scheduler

This guide is for an OpenClaw operator who already has the BTG skill installed,
the bot linked, and Telegram or another chat channel working.

## What Autopilot Does

`/btg autopilot enable` saves autopilot settings. It does not start a background
timer, cron job, systemd service, or OpenClaw scheduled job by itself.

`/btg autopilot tick` is a one-shot scheduler check:

- if autopilot is disabled or the next autoplay window is not due, it exits
  without playing
- if play is due, it plays one 10-game BTG round
- if autopilot notifications are enabled, it emits an `AUTOPILOT_NOTIFY:` line

A host scheduler must run `/btg autopilot tick` repeatedly. A common pattern is
to run the tick every 5 minutes and let BTG decide whether the next autoplay
round is due.

If you want Telegram notifications, your scheduler or dispatcher must extract
the text after `AUTOPILOT_NOTIFY:` and send only that notification text to the
bot's Telegram chat.

Each bot/profile needs its own scheduler and its own BTG state paths. Do not
point one bot's scheduler at another bot's `stateDir`, `.api-key`, `.profile-id`,
logs, token file, or chat id.

## Example Paths

The examples below use placeholders:

- `<profile-home>`: the OpenClaw profile home for this bot
- `<btg-state-dir>`: this bot's BTG state directory
- `<telegram-token-file>`: file containing this bot's Telegram token
- `<telegram-chat-id>`: Telegram chat/user id to notify
- `<bot-name>`: a short systemd-safe name for this bot

For example, a BTG2-style setup might use:

```text
<profile-home>      = /home/stubot/.openclaw-btg2
<btg-state-dir>     = /home/stubot/.openclaw-btg2/btg-state-btg2
BTG plugin runner   = /home/stubot/.openclaw-btg2/extensions/btg/run_btg.sh
```

Adjust the paths for your own bot before running any command.

## Dispatcher Script

Create a script such as:

```text
<profile-home>/scripts/<bot-name>-autopilot-dispatcher.sh
```

Example:

```bash
#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_STATE_DIR="<profile-home>"
OPENCLAW_CONFIG_PATH="<profile-home>/openclaw.json"
BTG_STATE_DIR="<btg-state-dir>"
BTG_RUNNER="<profile-home>/extensions/btg/run_btg.sh"
TOKEN_FILE="<telegram-token-file>"
CHAT_ID="<telegram-chat-id>"
LOG_DIR="<profile-home>/logs"
LOCK_FILE="<profile-home>/<bot-name>-autopilot.lock"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/<bot-name>-autopilot-$(date +%Y%m%d).log"
TMP_OUTPUT="$(mktemp "$LOG_DIR/<bot-name>-autopilot.XXXXXX")"

cleanup() {
  rm -f "$TMP_OUTPUT"
}
trap cleanup EXIT

{
  flock -n 9 || {
    echo "[$(date --iso-8601=seconds)] skipped: another autopilot tick is running"
    exit 0
  }

  echo "[$(date --iso-8601=seconds)] starting BTG autopilot tick"

  export OPENCLAW_STATE_DIR
  export OPENCLAW_CONFIG_PATH
  export BTG_STATE_DIR

  set +e
  "$BTG_RUNNER" autopilot tick >"$TMP_OUTPUT" 2>&1
  tick_status=$?
  set -e

  cat "$TMP_OUTPUT"

  if [ "$tick_status" -ne 0 ]; then
    echo "[$(date --iso-8601=seconds)] tick failed with exit code $tick_status"
    exit "$tick_status"
  fi

  notification_text="$(
    awk '
      /^AUTOPILOT_NOTIFY: / {
        sub(/^AUTOPILOT_NOTIFY: /, "")
        print
        in_notify = 1
        next
      }
      in_notify { print }
    ' "$TMP_OUTPUT"
  )"

  if [ -n "$notification_text" ]; then
    if [ ! -r "$TOKEN_FILE" ]; then
      echo "[$(date --iso-8601=seconds)] notification skipped: token file is not readable"
      exit 1
    fi

    telegram_token="$(tr -d '\r\n' < "$TOKEN_FILE")"
    curl --silent --show-error --fail \
      --data-urlencode "chat_id=$CHAT_ID" \
      --data-urlencode "text=$notification_text" \
      "https://api.telegram.org/bot${telegram_token}/sendMessage" >/dev/null
    unset telegram_token
    echo "[$(date --iso-8601=seconds)] sent AUTOPILOT_NOTIFY to Telegram"
  else
    echo "[$(date --iso-8601=seconds)] no AUTOPILOT_NOTIFY emitted"
  fi

  echo "[$(date --iso-8601=seconds)] finished BTG autopilot tick"
} 9>"$LOCK_FILE" >>"$LOG_FILE" 2>&1
```

Make it private and executable:

```bash
chmod 700 <profile-home>/scripts/<bot-name>-autopilot-dispatcher.sh
```

Keep the Telegram token file private. Do not paste token contents into logs,
docs, tickets, or chat.

## systemd User Service

Create:

```text
~/.config/systemd/user/openclaw-<bot-name>-autopilot.service
```

Example:

```ini
[Unit]
Description=BTG autopilot scheduler tick for <bot-name>
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
Environment=OPENCLAW_STATE_DIR=<profile-home>
Environment=OPENCLAW_CONFIG_PATH=<profile-home>/openclaw.json
Environment=BTG_STATE_DIR=<btg-state-dir>
ExecStart=<profile-home>/scripts/<bot-name>-autopilot-dispatcher.sh
```

## systemd User Timer

Create:

```text
~/.config/systemd/user/openclaw-<bot-name>-autopilot.timer
```

Example:

```ini
[Unit]
Description=Run BTG autopilot scheduler for <bot-name> every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true
Unit=openclaw-<bot-name>-autopilot.service

[Install]
WantedBy=timers.target
```

## Enable And Start

Reload user systemd, enable the timer, then start only this bot's timer:

```bash
systemctl --user daemon-reload
systemctl --user enable openclaw-<bot-name>-autopilot.timer
systemctl --user start openclaw-<bot-name>-autopilot.timer
```

To run one immediate scheduler check:

```bash
systemctl --user start openclaw-<bot-name>-autopilot.service
```

That service run may play a real 10-game BTG round if the autoplay window is
due.

## Check Status And Logs

Check the timer and service:

```bash
systemctl --user status openclaw-<bot-name>-autopilot.timer
systemctl --user status openclaw-<bot-name>-autopilot.service
systemctl --user list-timers openclaw-<bot-name>-autopilot.timer --all
```

Check the dispatcher log:

```bash
tail -n 120 <profile-home>/logs/<bot-name>-autopilot-$(date +%Y%m%d).log
```

Healthy skipped check:

```text
Decision: no action. Next autoplay window in about 58m.
no AUTOPILOT_NOTIFY emitted
finished BTG autopilot tick
```

Healthy due check:

```text
Decision: play now.
AUTOPILOT_NOTIFY: ...
sent AUTOPILOT_NOTIFY to Telegram
finished BTG autopilot tick
```

## Multi-Bot Safety

For every bot, verify the scheduler points at that bot's own:

- `OPENCLAW_STATE_DIR`
- `OPENCLAW_CONFIG_PATH`
- `BTG_STATE_DIR`
- installed BTG plugin runner
- lock file
- log directory
- Telegram token file
- Telegram chat id

Never point one bot's scheduler at another bot's BTG state directory. Reusing a
state directory can make two bots share credentials, play history, cooldowns,
strategy, or notifications.

Be careful with gateway commands. If you are using a separate OpenClaw profile,
restart only that profile's gateway. Do not stop the default OpenClaw gateway
accidentally while configuring a named or separate bot profile.
