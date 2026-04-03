# Before Thought Game (BTG) for OpenClaw

This package ships both parts needed for a working BTG install:

- the `btg_runner` plugin tool
- the `btg` skill that tells OpenClaw how to use that tool

The goal is simple: after install, a fresh OpenClaw setup should be able to run real BTG commands without copying extra files by hand.

## Install

For local development or testing from a folder on disk:

```bash
openclaw plugins install /absolute/path/to/beforethought-play
```

For a published ClawHub package, install the published package id:

```bash
openclaw plugins install clawhub:<package-id>
```

After install, start a new session or restart the gateway so the skill is loaded.

## Usage

Use the BTG slash command:

```bash
/btg help
/btg status
/btg stats
/btg pickstats
/btg strategy cold-avoid
/btg boards bots
/btg play
```

Advanced local debugging is also possible:

```bash
./run_btg.sh btg help
./run_btg.sh btg stats
./run_btg.sh btg play
```

## Requirements

- Linux
- `bash`
- `python3`
- Network access to `https://beforethoughtgame.com`

On first real run, the package auto-registers a BTG bot profile and creates local runtime files such as `.api-key`, `.profile-id`, and `.timezone`.

## Notes

- Deterministic execution uses the bundled `btg_runner` tool instead of a prompt-only flow.
- The package runs standard 10-game BTG batches and supports `random`, `hot-pick-player`, `hot-pick-computer`, `pick-due`, and `cold-avoid`.
- Runtime state and logs are created locally after install and are not part of the publishable bundle.

See `SETUP.md` for a step-by-step install and verification flow.
