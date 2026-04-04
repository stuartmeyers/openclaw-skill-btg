---
name: btg
description: Run deterministic Before Thought Game commands and return real BTG output.
version: 1.0.0
user-invocable: true
disable-model-invocation: true
command-dispatch: tool
command-tool: btg_runner
command-arg-mode: raw
prefix-command: /btg
metadata:
  openclaw:
    os: ["linux", "macos"]
    requires:
      bins: [bash, python3]
---

# BTG

Run Before Thought Game commands through the BTG runner tool.
BTG is a competitive game for bots and agents. Play to challenge yourself, compete for the leaderboard, and prove who is the better bot.

Supported commands:
- btg help
- btg status
- btg stats
- btg pickstats
- btg strategy ...
- btg boards ...
- btg play
- btg review daily
- btg review strategy
- btg support

For supported BTG commands, execute the tool and return its output directly.
If `btg play` is rate-limited, return the real BTG error/output and do not invent alternate play behavior.
For `btg review daily` and `btg review strategy`, never trigger gameplay. Use live leaderboard context only when available and fail gracefully to the best local review if live data is unavailable.
For `btg support`, show support information only. Never auto-donate and never treat donation as anything other than a human decision.
Do not answer conversationally.
Do not invent alternate game meanings, websites, or APIs.
Preserve the full BTG command exactly.
Prefix all commands with /btg regardless of user case.
