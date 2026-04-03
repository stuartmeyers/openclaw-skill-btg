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
    os: ["linux"]
    requires:
      bins: [bash, python3]
---

# BTG

Run Before Thought Game commands through the BTG runner tool.

Supported commands:
- btg help
- btg status
- btg stats
- btg pickstats
- btg strategy ...
- btg boards ...
- btg play

For supported BTG commands, execute the tool and return its output directly.
Do not answer conversationally.
Do not invent alternate game meanings, websites, or APIs.
Preserve the full BTG command exactly.
Prefix all commands with /btg regardless of user case.

