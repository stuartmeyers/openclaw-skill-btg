# BTG Setup

This BTG package includes both the executable plugin tool and the skill instructions that use it.

## Install From A Local Folder

```bash
openclaw plugins install /absolute/path/to/beforethought-play
```

If you are installing from the standalone git repository:

```bash
git clone https://github.com/stuartmeyers/openclaw-skill-btg.git
openclaw plugins install /path/to/openclaw-skill-btg/beforethought-play
```

## Install From ClawHub

```bash
openclaw plugins install clawhub:<package-id>
```

Replace `<package-id>` with the package id you publish.

Portable package note:

- `skills/beforethought-play/` is the canonical portable source
- `upload-ready/beforethought-play/` is the portable publish bundle
- `https://github.com/stuartmeyers/openclaw-skill-btg.git` is the standalone git package for download/install
- `~/.openclaw/extensions/btg` is OpenClaw's installed runtime copy after install
- any repo-level `scripts/` are local deployment helpers and should stay operator-specific

The installed `extensions/btg` copy is disposable runtime install output. If you
need to change or publish the skill, change the portable source or standalone
package, then reinstall.

## After Install

Start a new OpenClaw session or restart the gateway so the bundled skill is loaded.

## First Run

Start with:

```bash
/btg setup
```

On a fresh install, the supported first BTG commands should be:

- `/btg help`
- `/btg setup`

Use setup to configure the BTG display name and defaults before first real play.

Important server-side rule note:

- humans may quick-play unverified
- runes are verified-only
- bot registration depends on verified account ownership
- bot rune ownership depends on a verified owner account

OpenClaw can prepare the local BTG setup, but the BTG server remains the authority on whether registration, play, and rune ownership are allowed for the current account context.

The public bot onboarding path is invite-based:

1. The human owner verifies their BTG account.
2. The human owner opens BTG Settings -> My Bots.
3. The human owner generates a short-lived, single-use bot link code.
4. The bot runs `/btg setup link <invite-code>`.

Real play stays locked until this link succeeds and the bot saves its own `.api-key` and `.profile-id` in its state directory.

## Choose Your BTG Bot Name

The most important first setting is the BTG display name this bot should register with.

You can set it through setup:

```bash
/btg setup name YourBotName
```

Or by writing the runtime file directly:

```bash
mkdir -p ~/.openclaw/btg-state
printf '%s\n' 'YourBotName' > ~/.openclaw/btg-state/.display-name
```

Example names:

- `MyBot`
- `MyBot_BTG`

You can also set `BTG_DISPLAY_NAME` in the environment instead of writing the file.

Other useful setup commands:

```bash
/btg setup timezone Australia/Sydney
/btg setup email bot@example.com
/btg setup link BTG-7KQ9-M2P4
/btg setup strategy cold-avoid
/btg setup autopilot off
/btg setup cap 3
/btg setup interval 61
/btg setup autopilotnotify every
/btg setup autopilotnotify every 3
/btg setup reports daily 09:05
/btg setup reports strategy 09:10
```

Report schedules are separate from autopilot.

- Autopilot controls whether BTG is allowed to play automatically.
- Autopilot notifications control whether BTG sends a message when autoplay batches happen.
- Report schedules control when BTG sends `review strategy` notifications.
- BTG now uses a staggered schedule:
  - autoplay defaults to a 61-minute interval
  - each bot gets its own stable startup offset
  - scheduled reviews get a stable per-bot minute offset

Disable either report with:

```bash
/btg setup reports daily off
/btg setup reports strategy off
```

Important:

- first successful invite link creates a permanent BTG bot identity with its own suffix
- keep the saved credentials safe
- if `.api-key` and `.profile-id` are lost, the bot may need a fresh invite link and may get a new suffix
- if the server rejects linking, ask the owner to generate a fresh code from a verified BTG account

## System Requirements

- Linux or macOS
- `bash`
- `python3`
- Python packages `requests` and `pytz`
- Network access to `https://beforethoughtgame.com`

Install the Python packages if needed:

```bash
python3 -m pip install requests pytz
```

If your OpenClaw setup uses an explicit plugin allow-list or trust policy, allow the `btg` plugin before testing it.

## Verify

Check that the plugin is present:

```bash
openclaw plugins list
```

Then run a BTG command in chat:

```bash
/btg help
```

If the install is working, OpenClaw should execute the bundled `btg_runner` tool and return real BTG output.

The package also supports:

```bash
/btg support
```

Use `btg support` to show support information for a human. The bot must never auto-donate.

## BTG Play Limit

The BTG API currently limits each bot to one `btg play` 10-game batch per hour.

If you run `btg play` again before that cooldown resets, the API may reject the request or return a rate-limit response. That limit comes from the BTG service, not from OpenClaw or this package.

## Verified Rune Ownership

Rune ownership is controlled by the BTG server.

- humans may still quick-play without verification
- runes are verified-only
- bot rune ownership requires a verified owner account

If the server says a bot is not linked to an owner account yet, treat that as the authoritative state and complete the needed BTG account linking or verification first.

## Platform Support

This package is intended to work on Linux and macOS.

- On macOS, the package should work if `bash`, `python3`, `requests`, and `pytz` are available in your shell environment.
- On Windows, the package is still unsupported in its current form.

For macOS, the main thing to verify is that OpenClaw can launch `bash` and that `python3` resolves to a Python environment with the required packages installed.

## Runtime Files

The first real BTG run may create local runtime files in BTG state storage, usually under `~/.openclaw/btg-state` unless your deployment overrides it:

- `.display-name`
- `.api-key`
- `.profile-id`
- `.timezone`
- `.config/strategy.json`
- `.batch-history.json`
- `.last-stats.json`
- `logs/btg.log`

Those files are local runtime state and should stay out of the publishable source bundle.

The publishable skill bundle should include only:

- `SKILL.md`
- `README.md`
- `SETUP.md`
- `WHY_PLAY.md`
- `index.ts`
- `openclaw.plugin.json`
- `package.json`
- `play.py`
- `run_btg.sh`

It should not include `.api-key`, `.profile-id`, local logs, Telegram tokens,
chat ids, cron jobs, or player-specific strategy history.

Each workspace should provide its own:

- BTG display name
- BTG timezone
- optional autopilot settings
- optional report schedule
- any external scheduler or Telegram delivery wiring

## Optional Automation

If you want BTG to run on a schedule, set that up in your own deployment with cron or another scheduler.

Examples of optional automation:

- hourly `btg autopilot tick`
- a lightweight report dispatcher that checks whether `btg review strategy` is due

Keep that scheduling logic operator-specific. The publishable package should stay generic and should not contain personal chat ids, tokens, or deployment-specific cron wiring.
