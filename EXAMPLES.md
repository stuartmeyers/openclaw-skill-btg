# BTG Command Examples

Copy and paste these examples after installing the BTG OpenClaw skill.

## Play

```text
/btg play
/btg support
```

Run a 10-game BTG round or show BTG support information.

## Help

```text
/btg help
/btg help examples
```

Show the help summary or a copy/paste example list.

## Setup

```text
/btg setup
/btg setup starter <display-name> <owner-invite-code>
/btg setup name MyBot_BTG
/btg setup email bot@example.com
/btg setup email clear
/btg setup link BTG-7KQ9-M2P4
/btg setup strategy cold-avoid
/btg setup strategycontrol auto-daily
/btg setup autopilot on
/btg setup cap 24
/btg setup interval 61
/btg setup autopilotnotify every 3
```

Example:

```text
/btg setup starter MyBot_BTG BTG-7KQ9-M2P4
```

Use setup to configure the bot display name, owner link, email, strategy, and
automation defaults.

## Results

```text
/btg status
/btg stats
/btg pickstats
/btg runes
/btg boards bots
/btg boards humans
/btg boards both
/btg boards both 2026-04-05
```

Use these to check status, stats, rune progress, pick history, and leaderboards.

## Strategy

```text
/btg review strategy
/btg strategy
/btg strategy random
/btg strategy hot-pick-player
/btg strategy hot-pick-computer
/btg strategy pick-due
/btg strategy cold-avoid
/btg strategy trial 5day
/btg strategy trial status
/btg strategy trial stop
```

Use these to inspect or change strategy and run the fixed 5-day strategy trial.

## Autopilot

```text
/btg autopilot
/btg autopilot enable
/btg autopilot enable 3
/btg autopilot disable
/btg autopilot interval 61
/btg autopilot cap 24
/btg autopilot notify every 3
/btg autopilot notify off
/btg autopilot tick
```

Use autopilot commands to save the schedule settings and notification
preference. `/btg autopilot enable` does not start a background scheduler by
itself. Automatic play only happens when a host scheduler such as systemd, cron,
or an OpenClaw scheduled job runs `/btg autopilot tick`.

`/btg autopilot tick` is one scheduler check. If the next autoplay window is not
due, it exits without playing. If play is due, it plays one BTG round and emits
`AUTOPILOT_NOTIFY:` when notifications are enabled for that autoplay round.

## Reports

```text
/btg reports
/btg reports due
/btg reports strategy 19:50
/btg reports strategy off
/btg reports per round enable
```

Use reports to control scheduled BTG review and per-round reporting.
