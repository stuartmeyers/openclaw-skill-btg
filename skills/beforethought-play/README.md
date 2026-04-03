# Before Thought Game (BTG) – OpenClaw Skill

## Purpose
Provides a deterministic OpenClaw skill for Before Thought Game (BTG), allowing agents to run real game commands via the BTG API, track stats, and play 10-game batches using selectable strategies.

## Installation

**New to OpenClaw?** See [SETUP.md](SETUP.md) for complete installation and workspace configuration instructions.

**Quick install:** Copy `beforethought-play` folder to `~/.openclaw/workspace/skills/` and follow the workspace file templates.

## Usage

Use via OpenClaw:

```bash
/skill beforethought_play btg help
/skill beforethought_play btg status
/skill beforethought_play btg stats
/skill beforethought_play btg play
```

Optional direct execution:

```bash
./run_btg.sh btg help
./run_btg.sh btg status
./run_btg.sh btg stats
./run_btg.sh btg play
```

## Output

Typical command output includes help text, summary stats, full profile stats, or a 10-game batch summary.

Example `btg play` output:

```text
Profile stats:
Best score: 6280
Average score: 369
Win rate: 24.5%
Games played: 190
Total wins: 432
Best stage streaks: BW=7, Vehicles=4, Suit=2, Hands=2, Dice=2, Shapes=2, Colour=2
Houses: Full=0, Six=1, Five=1, Half=6, High=3, Low=15, SixSeven=1
Current strategy: cold-avoid

Games: 10
Top score this batch: 4910
Daily bot leaderboard impact: No change (currently #1)
All-time bot leaderboard impact: No change (currently #2)
1/10 score=110 streaks=[1, 0, 1, 0, 0, 0, 0] bonuses={}
...
10/10 score=80 streaks=[0, 0, 1, 0, 0, 0, 0] bonuses={}
```

## Requirements

- Python 3
- Network access to `https://beforethoughtgame.com`
- OpenClaw installed for `/skill` usage

On first real run, the skill will auto-register and create:

- `.api-key`
- `.profile-id`
- `.timezone`

## Notes

- Uses deterministic execution through the OpenClaw skill/plugin path, not a prompt-only flow.
- Runs standard 10-game BTG batches.
- Supports selectable strategies including `random`, `hot-pick-player`, `hot-pick-computer`, `pick-due`, and `cold-avoid`.
- On first registration, stores bot identity locally in the skill folder.
- Includes error handling for missing runtime files, network failures, timeouts, bad responses, unauthorized API access, and rate limits.
- Writes basic logs to `logs/btg.log`.

Built for OpenClaw agents. Adapt to your workspace.

