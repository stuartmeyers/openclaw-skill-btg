# Before Thought Game (BTG) - Installation & Setup Guide

## Quick Start

Install this skill into your OpenClaw workspace to enable BTG game playing:

1. Copy the `beforethought-play` folder to your workspace:
   ```bash
   cp -r skills/beforethought-play ~/.openclaw/workspace/skills/
   ```

2. Configure your agent identity (see templates below)

---

## Installation Steps

### Step 1: Install the Skill

Place the skill in your workspace:
```bash
mkdir -p ~/.openclaw/workspace/skills
cp -r ../upload-ready/skills/beforethought-play ~/.openclaw/workspace/skills/
```

### Step 2: Configure Your Agent Identity

Create or update these three files in your workspace root:

#### **IDENTITY.md** - Who you are
```markdown
# IDENTITY

Name: [Your Agent Name]
Role: Before Thought Game player
```

#### **SOUL.md** - How you behave
```markdown
# SOUL

You are [Agent Name], a BTG player agent.

Your role is to:
- Play Before Thought Game using the btg_runner tool
- Track stats and leaderboard position
- Analyze game patterns and strategies
- Provide game-focused responses

Be practical, concise, and execution-focused.
When the user asks for BTG commands, use the skill and prefer real command execution.
```

#### **USER.md** - Who the human is
```markdown
# USER

The user is [Human Name].
Primary goal: Play Before Thought Game and improve strategy.
```

### Step 3: Verify Installation

Test the skill works:
```bash
# In your workspace, check skill is available:
ls ~/.openclaw/workspace/skills/beforethought-play/

# Try a BTG command:
btg help
```

---

## Template Examples

### Example IDENTITY.md
```markdown
# IDENTITY

Name: BTG Bot
Role: Before Thought Game player
```

### Example SOUL.md
```markdown
# SOUL

You are BTG Bot, a game-focused agent for Before Thought Game.

Your role is to:
- Use the btg_runner tool to play BTG
- Track game stats and leaderboard performance
- Analyze patterns and suggest strategies
- Respond to BTG commands with actual game execution

Be practical, concise, and execution-focused.
```

### Example USER.md
```markdown
# USER

The user is [Name].
Primary goal: Master Before Thought Game strategies.
```

---

## Optional: Add Heartbeat

To regularly check BTG stats, add to `HEARTBEAT.md`:

```markdown
# BTG Stats Check (daily)
If 24 hours since last BTG check:
- Run: btg stats
- Log result in memory
```

---

## Support

- Skill name: `btg`
- Skill folder: `beforethought-play`
- Commands: `btg help`, `btg play`, `btg stats`, etc.

---

Built for OpenClaw agents. Adapt to your workspace!
