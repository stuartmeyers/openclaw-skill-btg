#!/usr/bin/env python3
import sys, json, random, requests, os, time
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://beforethoughtgame.com"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.environ.get("BTG_STATE_DIR") or os.path.join(os.path.expanduser("~"), ".openclaw", "btg-state")
CONFIG_DIR = os.path.join(STATE_DIR, ".config")
API_KEY_FILE = os.path.join(STATE_DIR, ".api-key")
PROFILE_ID_FILE = os.path.join(STATE_DIR, ".profile-id")
TIMEZONE_FILE = os.path.join(STATE_DIR, ".timezone")
DISPLAY_NAME_FILE = os.path.join(STATE_DIR, ".display-name")
PERSONALITY_FILE = os.path.join(CONFIG_DIR, "personality.json")
STRATEGY_FILE = os.path.join(CONFIG_DIR, "strategy.json")
LOG_DIR = os.path.join(STATE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "btg.log")
LAST_PLAY_FILE = os.path.join(STATE_DIR, ".last-play-at")
BATCH_HISTORY_FILE = os.path.join(STATE_DIR, ".batch-history.json")
STATS_CACHE_FILE = os.path.join(STATE_DIR, ".last-stats.json")
SUPPORT_UNAVAILABLE = "Support information is unavailable right now."
PLAY_COOLDOWN_MINUTES = 60

def ensure_state_dirs():
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

def copy_if_missing(target_path, legacy_path, chmod_mode=None):
    if os.path.exists(target_path) or not os.path.exists(legacy_path):
        return

    with open(legacy_path, "rb") as src:
        content = src.read()
    with open(target_path, "wb") as dst:
        dst.write(content)
    if chmod_mode is not None:
        os.chmod(target_path, chmod_mode)

def migrate_legacy_state():
    ensure_state_dirs()
    copy_if_missing(API_KEY_FILE, os.path.join(SCRIPT_DIR, ".api-key"), 0o600)
    copy_if_missing(PROFILE_ID_FILE, os.path.join(SCRIPT_DIR, ".profile-id"), 0o600)
    copy_if_missing(TIMEZONE_FILE, os.path.join(SCRIPT_DIR, ".timezone"), 0o600)
    copy_if_missing(STRATEGY_FILE, os.path.join(SCRIPT_DIR, ".config", "strategy.json"))

def log_event(message):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

def append_batch_history(entry):
    ensure_state_dirs()
    history = load_batch_history()
    history.append(entry)
    history = history[-50:]
    with open(BATCH_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=True, indent=2)
    os.chmod(BATCH_HISTORY_FILE, 0o600)

def load_batch_history():
    migrate_legacy_state()
    if not os.path.exists(BATCH_HISTORY_FILE):
        return []

    try:
        with open(BATCH_HISTORY_FILE) as f:
            data = json.load(f)
    except Exception:
        return []

    return data if isinstance(data, list) else []

def save_stats_cache(stats):
    if not isinstance(stats, dict):
        return
    ensure_state_dirs()
    with open(STATS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=True, indent=2)
    os.chmod(STATS_CACHE_FILE, 0o600)

def load_stats_cache():
    migrate_legacy_state()
    if not os.path.exists(STATS_CACHE_FILE):
        return {}

    try:
        with open(STATS_CACHE_FILE) as f:
            data = json.load(f)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}

def load_display_name():
    env_name = os.environ.get("BTG_DISPLAY_NAME")
    if isinstance(env_name, str) and env_name.strip():
        return env_name.strip()

    migrate_legacy_state()
    if os.path.exists(DISPLAY_NAME_FILE):
        with open(DISPLAY_NAME_FILE) as f:
            value = f.read().strip()
            if value:
                return value
    return None

def save_display_name(display_name):
    ensure_state_dirs()
    with open(DISPLAY_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(display_name.strip())
    os.chmod(DISPLAY_NAME_FILE, 0o600)

def require_display_name():
    display_name = load_display_name()
    if display_name:
        return display_name

    print("BTG setup required: no BTG display name is configured.", file=sys.stderr)
    print(f"Create {DISPLAY_NAME_FILE} with the bot name you want to register, or set BTG_DISPLAY_NAME.", file=sys.stderr)
    print("Example names: MyBot or MyBot_BTG", file=sys.stderr)
    sys.exit(1)

def register_bot():
    ensure_state_dirs()
    display_name = require_display_name()
    try:
        resp = requests.post(
            f"{BASE_URL}/api/bot/register",
            json={"displayName": display_name, "timezone": "Australia/Sydney"},
            timeout=10
        )
        resp.raise_for_status()
        d = resp.json()
    except requests.exceptions.ConnectionError:
        print("BTG error: network unavailable during registration.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("BTG error: registration timed out.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"BTG error: registration failed: {e}", file=sys.stderr)
        sys.exit(1)

    ak, pid = d.get("apiKey"), d.get("profileId")
    if not ak or not pid:
        print("BTG error: registration failed (missing apiKey or profileId).", file=sys.stderr)
        sys.exit(1)

    for path, val in [(API_KEY_FILE, ak), (PROFILE_ID_FILE, pid)]:
        with open(path, "w") as f:
            f.write(val)
        os.chmod(path, 0o600)

    with open(TIMEZONE_FILE, "w") as f:
        f.write("Australia/Sydney")
    os.chmod(TIMEZONE_FILE, 0o600)

    return ak, pid

def get_bot_timezone():
    migrate_legacy_state()
    if os.path.exists(TIMEZONE_FILE):
        with open(TIMEZONE_FILE) as f:
            value = f.read().strip()
            if value:
                return value
    return "Australia/Sydney"

def load_bot_tz():
    return pytz.timezone(get_bot_timezone())

def load_last_play_at():
    migrate_legacy_state()
    if not os.path.exists(LAST_PLAY_FILE):
        return None

    try:
        with open(LAST_PLAY_FILE) as f:
            raw = f.read().strip()
    except Exception:
        return None

    if not raw:
        return None

    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return load_bot_tz().localize(dt)

    return dt

def save_last_play_at(dt):
    ensure_state_dirs()
    with open(LAST_PLAY_FILE, "w", encoding="utf-8") as f:
        f.write(dt.isoformat())
    os.chmod(LAST_PLAY_FILE, 0o600)

def format_retry_time(last_play_at):
    if not last_play_at:
        return "Retry after the hourly BTG cooldown resets."

    next_allowed_at = last_play_at + timedelta(minutes=PLAY_COOLDOWN_MINUTES)
    now = datetime.now(next_allowed_at.tzinfo)
    remaining = next_allowed_at - now

    if remaining.total_seconds() <= 0:
        return "Retry now."

    total_minutes = int((remaining.total_seconds() + 59) // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0 and minutes > 0:
        remaining_text = f"in about {hours}h {minutes}m"
    elif hours > 0:
        remaining_text = f"in about {hours}h"
    else:
        remaining_text = f"in about {minutes}m"

    local_time = next_allowed_at.astimezone(load_bot_tz()).strftime("%Y-%m-%d %H:%M")
    return f"Retry {remaining_text} at approximately {local_time}."

def stage_label(stage):
    return (
        stage.replace("BlackWhite", "Black/White")
        .replace("Vehicles", "Vehicles")
        .replace("Suit", "Suit")
        .replace("Hands", "Hands")
        .replace("Dice", "Dice")
        .replace("Shapes", "Shapes")
        .replace("Colour", "Colour")
    )

def safe_int(value, default=0):
    return int(value) if isinstance(value, (int, float)) else default

def fetch_daily_rank_safe(profile_id):
    tz = load_bot_tz()
    now = datetime.now(tz).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/api/leaderboard/daily"
    try:
        resp = requests.get(
            url,
            params={"date": now, "type": "bots", "limit": 10},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None

    for i, entry in enumerate(data):
        if isinstance(entry, dict) and entry.get("profileId") == profile_id:
            return {
                "rank": i + 1,
                "score": entry.get("bestScore", 0)
            }
    return None

def select_recent_batches():
    history = load_batch_history()
    if not history:
        return []

    today = datetime.now(load_bot_tz()).date().isoformat()
    todays_batches = [
        entry for entry in history
        if isinstance(entry, dict) and entry.get("localDate") == today
    ]
    if todays_batches:
        return todays_batches

    latest = history[-1] if history else None
    return [latest] if isinstance(latest, dict) else []

def summarize_recent_play():
    batches = select_recent_batches()
    if not batches:
        return "Recent play: I do not have a completed local batch to review yet."

    latest = batches[-1]
    batch_count = len(batches)
    best_top_score = max(safe_int(entry.get("topScore", 0)) for entry in batches)
    latest_top_score = safe_int(latest.get("topScore", 0))
    latest_avg_score = safe_int(latest.get("averageScore", 0))
    latest_games = safe_int(latest.get("gamesCompleted", 0))

    if batch_count > 1:
        return (
            f"Recent play: I finished {batch_count} batch{'es' if batch_count != 1 else ''} today. "
            f"My best batch top score was {best_top_score}, and my latest batch averaged {latest_avg_score} over {latest_games} games."
        )

    return (
        f"Recent play: My latest completed batch reached {latest_top_score} "
        f"and averaged {latest_avg_score} over {latest_games} games."
    )

def best_batch_today():
    batches = select_recent_batches()
    if not batches:
        return None

    return max(safe_int(entry.get("topScore", 0)) for entry in batches)

def derive_daily_observation(current_strategy, stats):
    scoreboard = stats.get("scoreboard", {}) if isinstance(stats, dict) else {}
    best_score = safe_int(scoreboard.get("bestScore", 0))
    average_score = safe_int(scoreboard.get("averageScore", 0))
    games_played = safe_int(scoreboard.get("gamesPlayed", 0))

    if best_score >= 5000:
        return f"{current_strategy} is starting to show real breakthrough upside."
    if games_played < 10:
        return f"{current_strategy} is still early, so I would treat today as signal-gathering."
    if average_score >= 800:
        return f"{current_strategy} looks steady enough to keep pushing for deeper runs."
    if average_score >= 300:
        return f"{current_strategy} looks stable, but I am not breaking through consistently yet."
    return f"{current_strategy} is keeping me active, but I may need a different angle to go deeper."

def suggest_next_strategy(current_strategy, stats):
    my_picks = stats.get("myPicks", {}) if isinstance(stats, dict) else {}
    comp_picks = stats.get("computerPicks", {}) if isinstance(stats, dict) else {}
    scoreboard = stats.get("scoreboard", {}) if isinstance(stats, dict) else {}

    best_player_avg = 0
    player_signal = 0
    for options in my_picks.values():
        if not isinstance(options, dict):
            continue
        for data in options.values():
            if not isinstance(data, dict):
                continue
            picks = safe_int(data.get("picks", 0))
            avg = safe_int(data.get("avg", 0))
            if picks > 0:
                player_signal += 1
                if avg > best_player_avg:
                    best_player_avg = avg

    hot_pick_dominance = 0
    due_pick_signal = 0
    for options in comp_picks.values():
        if not isinstance(options, dict) or not options:
            continue
        pick_counts = [safe_int(data.get("picks", 0)) for data in options.values() if isinstance(data, dict)]
        positive = [count for count in pick_counts if count > 0]
        if not positive:
            continue
        if max(positive) >= 2 * min(positive):
            hot_pick_dominance += 1
        if len(set(positive)) > 1:
            due_pick_signal += 1

    best_score = safe_int(scoreboard.get("bestScore", 0))

    if player_signal >= 3 and best_player_avg >= 500 and current_strategy != "hot-pick-player":
        return "hot-pick-player", "your own pick history is starting to show some strong average winners"
    if due_pick_signal >= 3 and current_strategy != "pick-due":
        return "pick-due", "computer pick history shows some underused options worth testing for a deeper run"
    if hot_pick_dominance >= 3 and current_strategy != "cold-avoid":
        return "cold-avoid", "computer pick patterns look concentrated enough that avoiding the hottest choices may help"
    if hot_pick_dominance >= 3 and current_strategy != "hot-pick-computer":
        return "hot-pick-computer", "computer pick trends are clear enough to try riding the hottest lanes"
    if best_score < 500 and current_strategy != "random":
        return "random", "a reset to a neutral baseline could help before the next experiment"

    return current_strategy, "the current approach still looks like the best baseline for now"

def build_daily_review_lines(api_key, profile_id):
    stats = fetch_player_stats_for_review(api_key, profile_id)
    scoreboard = stats.get("scoreboard", {})
    current_strategy = load_strategy()
    best_score = safe_int(scoreboard.get("bestScore", 0))
    today_best = best_batch_today()
    rank_info = fetch_daily_rank_safe(profile_id)
    observation = derive_daily_observation(current_strategy, stats)
    next_strategy, reason = suggest_next_strategy(current_strategy, stats)

    lines = [
        f"I am currently using {current_strategy}."
    ]

    if today_best is not None:
        lines.append(f"My best batch today was {today_best}.")
        lines.append(f"My best score overall is {best_score}.")
    else:
        lines.append(f"My best score overall is {best_score}.")

    if rank_info and rank_info.get("rank") is not None:
        lines.append(f"My current daily bot rank is #{rank_info['rank']}.")

    lines.append(summarize_recent_play())
    lines.append(f"Observation: {observation}")

    if next_strategy == current_strategy:
        lines.append("Optional next move if you want to guide me: I can stay with this strategy and keep pressing for a deeper run.")
    else:
        lines.append(
            f"Optional next move if you want to change: I could try {next_strategy} next, because {reason}."
        )

    return lines

def describe_working_signals(stats):
    scoreboard = stats.get("scoreboard", {})
    streaks = stats.get("streaks", {}).get("byStage", {})
    best_score = safe_int(scoreboard.get("bestScore", 0))
    average_score = safe_int(scoreboard.get("averageScore", 0))

    strongest_stage = None
    strongest_value = -1
    for stage, value in streaks.items():
        stage_value = safe_int(value, -1)
        if stage_value > strongest_value:
            strongest_value = stage_value
            strongest_stage = stage

    if best_score >= 5000:
        return f"I am showing breakthrough upside now, with a best score of {best_score}."
    if strongest_stage and strongest_value > 0:
        return f"My strongest stage depth so far is {stage_label(strongest_stage)} at {strongest_value}, and my average score is {average_score}."
    return f"My best score is {best_score} and I am still building reliable depth."

def describe_limits(stats):
    scoreboard = stats.get("scoreboard", {})
    houses = stats.get("houses", {})
    average_score = safe_int(scoreboard.get("averageScore", 0))
    games_played = safe_int(scoreboard.get("gamesPlayed", 0))
    house_total = sum(safe_int(value, 0) for value in houses.values() if isinstance(value, (int, float)))

    if games_played < 10:
        return "I do not have much sample size yet, so the current read is still soft."
    if house_total == 0:
        return "I am not converting enough deep runs into houses yet, so the ceiling is still limited."
    if average_score < 500:
        return "My average score is still modest, so I am not going deep often enough yet."
    return "I have some traction, but I still need more repeatable deep runs to really press the leaderboard."

def build_strategy_review_lines(api_key, profile_id):
    stats = fetch_player_stats_for_review(api_key, profile_id)
    current_strategy = load_strategy()
    recommended_strategy, reason = suggest_next_strategy(current_strategy, stats)

    lines = [
        f"Current strategy: {current_strategy}.",
        f"What seems to be working: {describe_working_signals(stats)}",
        f"What seems limited: {describe_limits(stats)}",
        f"Recommended next strategy: {recommended_strategy}, because {reason}.",
    ]

    if recommended_strategy == current_strategy:
        lines.append(f"Question: Do you want me to stay with {current_strategy} for stability, or try an experiment anyway?")
    else:
        lines.append(f"Question: Do you want me to stay with {current_strategy}, or switch to {recommended_strategy} for the next batch?")

    return lines

def load_key(path, idx):
    migrate_legacy_state()
    if os.path.exists(path):
        with open(path) as f:
            v = f.read().strip()
            if v:
                return v
    return register_bot()[idx]

def load_api_key():
    return load_key(API_KEY_FILE, 0)

def load_profile_id():
    return load_key(PROFILE_ID_FILE, 1)

def load_personality():
    return "balanced"

def save_personality(mode):
    pass

def load_strategy():
    migrate_legacy_state()
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE) as f:
                return json.load(f).get("mode", "random")
        except Exception:
            pass
    return "random"

def save_strategy(mode):
    if mode not in ["random", "hot-pick-player", "hot-pick-computer", "pick-due", "cold-avoid"]:
        print("Invalid strategy. Options: random, hot-pick-player, hot-pick-computer, pick-due, cold-avoid", file=sys.stderr)
        sys.exit(1)
    ensure_state_dirs()
    with open(STRATEGY_FILE, "w") as f:
        json.dump({"mode": mode}, f)

def fetch(endpoint, params):
    url = f"{BASE_URL}/{endpoint}"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                print("Network unavailable. Batch cancelled.")
                sys.exit(1)
            print("Network error contacting beforethoughtgame.com. Retrying in 30 seconds.")
            time.sleep(30)
    return None

def fetch_support_info():
    url = f"{BASE_URL}/api/support"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    if not isinstance(data, dict):
        return None

    if data.get("enabled") is not True:
        return None

    donation_url = data.get("donationUrl")
    headline = data.get("headline")
    message = data.get("message")

    if not isinstance(donation_url, str) or not donation_url.strip():
        return None
    if not isinstance(headline, str) or not headline.strip():
        return None
    if not isinstance(message, str) or not message.strip():
        return None

    return {
        "donationUrl": donation_url.strip(),
        "headline": headline.strip(),
        "message": message.strip(),
        "humanApprovalRequired": data.get("humanApprovalRequired") is True
    }

def fetch_bot_identity(api_key, profile_id=None):
    url = f"{BASE_URL}/api/bot/hello"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {
            "profileId": profile_id,
            "displayName": None,
            "displaySuffix": None,
            "fullName": None
        }

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if not isinstance(data, dict):
        data = {}

    display_name = data.get("displayName")
    display_suffix = data.get("displaySuffix")
    full_name = data.get("fullName")

    if not isinstance(full_name, str) or not full_name.strip():
        if isinstance(display_name, str) and display_name.strip():
            if isinstance(display_suffix, str) and display_suffix.strip():
                full_name = f"{display_name.strip()}#{display_suffix.strip()}"
            else:
                full_name = display_name.strip()
        elif profile_id:
            full_name = f"profile {profile_id}"
        else:
            full_name = "Unknown"

    return {
        "profileId": data.get("profileId") or profile_id,
        "displayName": display_name,
        "displaySuffix": display_suffix,
        "fullName": full_name
    }

def print_player_identity(api_key, profile_id):
    identity = fetch_bot_identity(api_key, profile_id)
    print(f"Player Name: {identity['fullName']}")
    print()

def format_support_message(support_info):
    if not support_info:
        return SUPPORT_UNAVAILABLE

    lines = [
        support_info["headline"],
        support_info["message"],
        support_info["donationUrl"]
    ]
    return "\n".join(lines)

def format_support_appendix(support_info):
    if not support_info:
        return None

    lines = [
        "If you like this game, please ask your human to support Before Thought Game and help cover costs and development:",
        support_info["donationUrl"]
    ]
    return "\n".join(lines)

def fetch_daily(t="both", lim=10):
    tz = load_bot_tz()
    now = datetime.now(tz).strftime("%Y-%m-%d")
    return now, fetch("api/leaderboard/daily", {"date": now, "type": t, "limit": lim})

def fetch_alltime(t="both", lim=10):
    return fetch("api/leaderboard/all-time", {"type": t, "limit": lim})

def fetch_house(t="both", lim=10):
    return fetch("api/leaderboard/house", {"type": t, "limit": lim})

def fetch_player_stats(api_key, profile_id, timeout=10, max_retries=3, fatal=True):
    url = f"{BASE_URL}/api/player/stats?profileId={profile_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)

            if resp.status_code == 401:
                if fatal:
                    print("BTG error: unauthorized (check .api-key)", file=sys.stderr)
                    sys.exit(1)
                return None

            if resp.status_code == 429:
                if fatal:
                    print("BTG error: rate limit reached (try again later)", file=sys.stderr)
                    sys.exit(1)
                return None

            if resp.status_code >= 500:
                if attempt == max_retries - 1:
                    if fatal:
                        print("BTG error: server unavailable.", file=sys.stderr)
                        sys.exit(1)
                    return None
                print("BTG server error. Retrying in 30 seconds.")
                time.sleep(30)
                continue

            resp.raise_for_status()

            try:
                data = resp.json()
                save_stats_cache(data)
                return data
            except ValueError:
                if fatal:
                    print("BTG error: invalid JSON returned from server.", file=sys.stderr)
                    sys.exit(1)
                return None

        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                if fatal:
                    print("BTG error: network unavailable. Batch cancelled.", file=sys.stderr)
                    sys.exit(1)
                return None
            print("Network error contacting beforethoughtgame.com. Retrying in 30 seconds.")
            time.sleep(30)

        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                if fatal:
                    print("BTG error: request timed out.", file=sys.stderr)
                    sys.exit(1)
                return None
            print("BTG request timed out. Retrying in 30 seconds.")
            time.sleep(30)

    if fatal:
        print("BTG error: unable to fetch player stats.", file=sys.stderr)
        sys.exit(1)
    return None

def fetch_player_stats_for_review(api_key, profile_id):
    live = fetch_player_stats(api_key, profile_id, timeout=5, max_retries=1, fatal=False)
    if isinstance(live, dict):
        return live

    cached = load_stats_cache()
    if cached:
        return cached

    return {}

def fetch_player_stats_after_play(api_key, profile_id, previous_stats, batch_top_score, games_completed):
    previous_scoreboard = previous_stats.get("scoreboard", {}) if isinstance(previous_stats, dict) else {}
    previous_games_played = score_or_zero(previous_scoreboard.get("gamesPlayed", 0))
    previous_best_score = score_or_zero(previous_scoreboard.get("bestScore", 0))
    expected_games_played = previous_games_played + games_completed
    expected_best_score = max(previous_best_score, batch_top_score)

    latest = previous_stats
    for _ in range(5):
        latest = fetch_player_stats(api_key, profile_id)
        scoreboard = latest.get("scoreboard", {}) if isinstance(latest, dict) else {}
        latest_games_played = score_or_zero(scoreboard.get("gamesPlayed", 0))
        latest_best_score = score_or_zero(scoreboard.get("bestScore", 0))

        if latest_games_played >= expected_games_played or latest_best_score >= expected_best_score:
            return latest

        time.sleep(2)

    return latest

def play_one_game(api_key, strategy_data):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(
            f"{BASE_URL}/api/game/start",
            headers=headers,
            json={"timezone": "Australia/Sydney"},
            timeout=10
        )
    except requests.exceptions.ConnectionError:
        return {"error": "network unavailable"}
    except requests.exceptions.Timeout:
        return {"error": "start timeout"}
    except Exception as e:
        return {"error": f"start exception: {e}"}

    if resp.status_code == 401:
        return {"error": "unauthorized"}

    if resp.status_code == 429:
        try:
            error_resp = resp.json()
        except ValueError:
            return {"error": "rate limit"}
        if error_resp.get("error") == "bot_rate_limit":
            return {"error": "bot_rate_limit"}
        return {"error": "rate limit"}

    if resp.status_code != 201:
        return {"error": f"start {resp.status_code}"}

    try:
        data = resp.json()
    except ValueError:
        return {"error": "invalid start response"}

    gid = data.get("gameId")
    if not gid:
        return {"error": "no gameId"}

    strategy = load_strategy()

    while not data.get("isComplete"):
        stage = data.get("currentStage") or data.get("stage")
        if not stage or not stage.get("options"):
            return {"error": "bad stage"}

        if strategy == "random":
            chosen = random.choice(stage["options"])

        elif strategy == "hot-pick-player":
            my_picks = strategy_data["myPicks"]
            stage_key = stage.get("type", "")
            if stage_key and stage_key in my_picks:
                options_stats = my_picks[stage_key]
                best = None
                best_avg = -1
                for opt in stage["options"]:
                    opt_id = opt["id"]
                    opt_data = options_stats.get(opt_id)
                    if opt_data:
                        avg = opt_data.get("avg", 0)
                        if avg > best_avg:
                            best_avg = avg
                            best = opt
                chosen = best if best else random.choice(stage["options"])
            else:
                chosen = random.choice(stage["options"])

        elif strategy == "hot-pick-computer":
            comp_picks = strategy_data["computerPicks"]
            stage_key = stage.get("stageName", stage.get("type", stage.get("stage", "")))
            comp_data = comp_picks.get(stage_key, {})

            option_list = []
            for opt in stage["options"]:
                opt_key = opt.get("key", opt.get("label", "").lower())
                picks = comp_data.get(opt_key, {}).get("picks", 0)
                option_list.append({"option": opt, "picks": picks})

            valid_opts = [o for o in option_list if o["picks"] > 0]
            if valid_opts:
                max_picks = max(o["picks"] for o in valid_opts)
                tied_opts = [o["option"] for o in valid_opts if o["picks"] == max_picks]
                chosen = random.choice(tied_opts)
            else:
                chosen = random.choice(stage["options"])

        elif strategy == "pick-due":
            recency = strategy_data["computerPickRecency"]
            stage_key = stage.get("stageName", stage.get("type", stage.get("stage", "")))
            recency_data = recency.get(stage_key, {})

            if not recency_data:
                chosen = random.choice(stage["options"])
            else:
                best_recency = -1
                best_option = None
                for opt in stage["options"]:
                    opt_key = opt.get("key", opt.get("label", "").lower())
                    opt_recency = recency_data.get(opt_key, {})
                    plays_since_seen = opt_recency.get("playsSinceSeen", 0)
                    if opt_recency.get("lastSeenAt") is None:
                        chosen = opt
                        break
                    if plays_since_seen > best_recency:
                        best_recency = plays_since_seen
                        best_option = opt
                else:
                    chosen = best_option if best_option else random.choice(stage["options"])

        elif strategy == "cold-avoid":
            comp_picks = strategy_data["computerPicks"]
            stage_key = stage.get("stageName", stage.get("type", stage.get("stage", "")))
            comp_data = comp_picks.get(stage_key, {})

            if not comp_data:
                chosen = random.choice(stage["options"])
            else:
                max_picks = max(
                    comp_data.get(opt.get("key", opt.get("label", "").lower()), {}).get("picks", 0)
                    for opt in stage["options"]
                )
                hottest_opts = [
                    opt for opt in stage["options"]
                    if comp_data.get(opt.get("key", opt.get("label", "").lower()), {}).get("picks", 0) == max_picks
                ]
                candidates = [opt for opt in stage["options"] if opt not in hottest_opts]
                chosen = random.choice(candidates) if candidates else random.choice(stage["options"])

        else:
            chosen = random.choice(stage["options"])

        try:
            mr = requests.post(
                f"{BASE_URL}/api/game/{gid}/move",
                headers=headers,
                json={"optionId": chosen["id"]},
                timeout=10
            )
        except requests.exceptions.ConnectionError:
            return {"error": "network unavailable during move"}
        except requests.exceptions.Timeout:
            return {"error": "move timeout"}
        except Exception as e:
            return {"error": f"move exception: {e}"}

        if mr.status_code == 401:
            return {"error": "unauthorized"}

        if mr.status_code == 429:
            return {"error": "bot_rate_limit"}

        if mr.status_code != 200:
            return {"error": f"move {mr.status_code}"}

        try:
            data = mr.json()
        except ValueError:
            return {"error": "invalid move response"}

    return {
        "finalScore": data.get("finalScore", 0),
        "streaks": data.get("streaksByStage", [0] * 7),
        "bonuses": data.get("bonusesEarned", {}),
    }
def fmt_bonuses(b):
    if not isinstance(b, dict):
        return "{}"
    nz = {k: v for k, v in b.items() if v > 0}
    if not nz:
        return "{}"
    return repr(nz)

def cmd_help():
    print("btg help")
    print(" Show this help summary")
    print()
    print("btg boards [both|humans|bots] [YYYY-MM-DD optional for daily]")
    print(" Show leaderboards. With a date, shows the daily board for that date.")
    print()
    print("btg stats")
    print(" Show full profile stats, including best score, win rate, streaks, and houses.")
    print()
    print("btg status")
    print(" Show a shorter stats summary.")
    print()
    print("btg pickstats")
    print(" Show player picks, computer picks, and due-pick analysis used by strategies.")
    print()
    print("btg strategy [random|hot-pick-player|hot-pick-computer|pick-due|cold-avoid]")
    print(" Show or set the active play strategy.")
    print()
    print("btg play")
    print(" Run the standard 10-game batch using the current strategy.")
    print()
    print("btg review daily")
    print(" Show a short daily review using live rank if available and local batch history.")
    print()
    print("btg review strategy")
    print(" Show a concise strategy review and suggest the next strategy to consider.")
    print()
    print("btg support")
    print(" Show how humans can support BTG and keep bot play online.")

def cmd_support():
    support_info = fetch_support_info()
    print(format_support_message(support_info))

def cmd_review_daily(api_key, profile_id):
    print_player_identity(api_key, profile_id)
    print("BTG Review Daily")
    print()
    for line in build_daily_review_lines(api_key, profile_id):
        print(line)

def cmd_review_strategy(api_key, profile_id):
    print_player_identity(api_key, profile_id)
    print("BTG Review Strategy")
    print()
    for line in build_strategy_review_lines(api_key, profile_id):
        print(line)

def cmd_boards(api_key, profile_id, type_arg, date_str, limit):
    type_arg = "bots"
    limit = 10
    print_player_identity(api_key, profile_id)

    if date_str is not None:
        daily_date, daily_list = fetch_daily(type_arg, limit)
        if not isinstance(daily_list, list):
            print("Error: daily endpoint returned unexpected shape", file=sys.stderr)
            sys.exit(1)

        print(f"DAILY type={type_arg} date={date_str} limit={limit}")
        for i, e in enumerate(daily_list[:limit]):
            parts = [f"{e.get('displayName','?')}#{e.get('displaySuffix','')} score={e['bestScore']}"]
            if 'games' in e:
                parts.append(f"games={e['games']}")
            print(f"{i+1}. {' '.join(parts)}")
        return

    alltime = fetch_alltime(type_arg, limit)
    house = fetch_house(type_arg, limit)
    streaks_data = fetch_streaks(type_arg, limit)

    if not isinstance(alltime, list):
        print("Error: all-time endpoint returned unexpected shape", file=sys.stderr)
        sys.exit(1)
    if not isinstance(house, dict):
        print("Error: house endpoint returned unexpected shape", file=sys.stderr)
        sys.exit(1)
    if not isinstance(streaks_data, dict):
        print("Error: streaks endpoint returned unexpected shape", file=sys.stderr)
        sys.exit(1)

    print(f"ALL_TIME type={type_arg} limit={limit}")
    for i, e in enumerate(alltime[:limit]):
        parts = [f"{e.get('displayName','?')}#{e.get('displaySuffix','')} score={e['bestScore']}"]
        if 'games' in e:
            parts.append(f"games={e['games']}")
        print(f"{i+1}. {' '.join(parts)}")

    print()
    print(f"HOUSE type={type_arg} limit={limit}")
    cat_map = [
        ("fullHouse", "FULL_HOUSE"),
        ("sixHouse", "SIX_HOUSE"),
        ("fiveHouse", "FIVE_HOUSE"),
        ("halfHouse", "HALF_HOUSE"),
        ("highHouse", "HIGH_HOUSE"),
        ("lowHouse", "LOW_HOUSE"),
        ("sixSeven", "SIX_SEVEN"),
    ]
    for key, label in cat_map:
        print(label)
        entries = house.get(key, [])
        if not entries:
            print("(none)")
            continue
        for e in entries[:limit]:
            print(f"{e['displayName']}#{e['displaySuffix']} value={e['value']}")

    print()
    print(f"STREAKS type={type_arg} limit={limit}")

    streak_sections = [
        ("BLACK_WHITE", "blackWhite"),
        ("VEHICLES", "vehicles"),
        ("SUIT", "suit"),
        ("HANDS", "hands"),
        ("DICE", "dice"),
        ("SHAPES", "shapes"),
        ("COLOUR", "colour"),
    ]

    for label, api_key in streak_sections:
        print(label)
        entries = streaks_data.get(api_key, [])
        if not entries:
            print("(none)")
            continue
        for e in entries[:limit]:
            print(f"{e['displayName']}#{e['displaySuffix']} value={e['value']}")

def fetch_streaks(type_arg, limit):
    url = f"{BASE_URL}/api/leaderboard/streaks?type={type_arg}&limit={limit}"
    headers = {"Authorization": f"Bearer {load_api_key()}", "Accept": "application/json", "User-Agent": "OpenClaw-Bot/1.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def find_leaderboard_entry(entries, profile_id):
    if not isinstance(entries, list):
        return None, None

    for i, entry in enumerate(entries):
        if entry.get("profileId") == profile_id:
            return i + 1, entry.get("bestScore", 0)

    return None, None

def score_or_zero(value):
    return value if isinstance(value, (int, float)) else 0

def cmd_play(api_key, profile_id):
    n = 10
    results = []
    lines = []
    best = 0
    games_completed = 0

    pre_play_stats = fetch_player_stats(api_key, profile_id)
    profile_best_score = pre_play_stats.get("scoreboard", {}).get("bestScore", 0)
    pre_daily_list = fetch_daily("bots", 10)[1]
    pre_alltime_list = fetch_alltime("bots", 10)
    pre_daily_rank, pre_daily_best = find_leaderboard_entry(pre_daily_list, profile_id)
    pre_alltime_rank, pre_alltime_board_score = find_leaderboard_entry(pre_alltime_list, profile_id)
    pre_alltime_best = profile_best_score

    post_daily_best_from_response = score_or_zero(pre_daily_best)
    post_alltime_best_from_response = score_or_zero(pre_alltime_best)

    for i in range(n):
        r = play_one_game(api_key, pre_play_stats)

        if "error" in r and r["error"] == "bot_rate_limit":
            support_info = fetch_support_info()
            retry_message = format_retry_time(load_last_play_at())
            if i == 0:
                print("Batch blocked by server limit. Maximum 10 games per 60 minutes for this bot.")
            else:
                print(f"Batch interrupted by server limit. Games completed: {games_completed}/{n}")
            print(retry_message)
            appendix = format_support_appendix(support_info)
            if appendix:
                print()
                print(appendix)
            return

        if "error" in r and r["error"] == "unauthorized":
            print("BTG error: saved bot credentials were rejected. Do not re-register unless you intend to create a new bot identity.", file=sys.stderr)
            print(f"BTG state dir: {STATE_DIR}", file=sys.stderr)
            return

        if "error" in r:
            lines.append(f"{i+1}/{n} score=0 streaks=[0,0,0,0,0,0,0] bonuses={{}}")
            continue

        sc = r["finalScore"] if r["finalScore"] is not None else 0
        st = r["streaks"] if isinstance(r["streaks"], list) else [0] * 7
        bn = fmt_bonuses(r["bonuses"])
        if sc > best:
            best = sc
        lines.append(f"{i+1}/{n} score={sc} streaks={st} bonuses={bn}")
        results.append(r)
        games_completed = i + 1

        if sc > post_daily_best_from_response:
            post_daily_best_from_response = sc
        if sc > post_alltime_best_from_response:
            post_alltime_best_from_response = sc

    post_play_stats = fetch_player_stats_after_play(
        api_key,
        profile_id,
        pre_play_stats,
        best,
        games_completed
    )
    scoreboard = post_play_stats.get("scoreboard", {})
    streaks = post_play_stats.get("streaks", {}).get("byStage", {})
    houses = post_play_stats.get("houses", {})

    print_player_identity(api_key, profile_id)
    print("Profile stats:")
    print(f"Best score: {scoreboard.get('bestScore', 0)}")
    print(f"Average score: {scoreboard.get('averageScore', 0)}")
    print(f"Win rate: {scoreboard.get('winRate', 0)}%")
    print(f"Games played: {scoreboard.get('gamesPlayed', 0)}")
    print(f"Total wins: {scoreboard.get('totalWins', 0)}")
    print(f"Best stage streaks: BW={streaks.get('blackWhite', 0)}, Vehicles={streaks.get('vehicles', 0)}, Suit={streaks.get('suit', 0)}, Hands={streaks.get('hands', 0)}, Dice={streaks.get('dice', 0)}, Shapes={streaks.get('shapes', 0)}, Colour={streaks.get('colour', 0)}")
    print(f"Houses: Full={houses.get('fullHouse', 0)}, Six={houses.get('sixHouse', 0)}, Five={houses.get('fiveHouse', 0)}, Half={houses.get('halfHouse', 0)}, High={houses.get('highHouse', 0)}, Low={houses.get('lowHouse', 0)}, SixSeven={houses.get('sixSeven', 0)}")
    print(f"Current strategy: {load_strategy()}")
    print()
    print(f"Games: {n}")
    print(f"Top score this batch: {best}")

    d_date_post, d_list_post = fetch_daily("bots", 10)
    a_list_post = fetch_alltime("bots", 10)

    post_daily_rank, post_daily_board_score = find_leaderboard_entry(d_list_post, profile_id)
    post_alltime_rank, post_alltime_board_score = find_leaderboard_entry(a_list_post, profile_id)

    baseline_daily_best = score_or_zero(pre_daily_best)
    daily_score_improved = post_daily_best_from_response > baseline_daily_best
    daily_board_improved = (
        post_daily_board_score is not None and
        (pre_daily_best is None or post_daily_board_score > pre_daily_best)
    )
    daily_rank_improved = (
        post_daily_rank is not None and
        (pre_daily_rank is None or post_daily_rank < pre_daily_rank)
    )

    if daily_score_improved or daily_board_improved or daily_rank_improved:
        if post_daily_rank is not None:
            daily_score = post_daily_board_score if post_daily_board_score is not None else post_daily_best_from_response
            if pre_daily_rank is None:
                print(f"Daily bot leaderboard impact: Now ranked #{post_daily_rank} with score {daily_score}")
            else:
                print(f"Daily bot leaderboard impact: Rank #{post_daily_rank}, score improved ({baseline_daily_best} → {daily_score})")
        else:
            print("Daily bot leaderboard impact: Score improved, outside top 10")
    else:
        if post_daily_rank is not None:
            print(f"Daily bot leaderboard impact: No change (currently #{post_daily_rank})")
        else:
            print("Daily bot leaderboard impact: No change")

    baseline_alltime_best = score_or_zero(pre_alltime_best)
    alltime_score_improved = post_alltime_best_from_response > baseline_alltime_best
    alltime_board_improved = (
        post_alltime_board_score is not None and
        (pre_alltime_board_score is None or post_alltime_board_score > pre_alltime_board_score)
    )
    alltime_rank_improved = (
        post_alltime_rank is not None and
        (pre_alltime_rank is None or post_alltime_rank < pre_alltime_rank)
    )

    if alltime_score_improved or alltime_board_improved or alltime_rank_improved:
        if post_alltime_rank is not None:
            alltime_score = post_alltime_board_score if post_alltime_board_score is not None else post_alltime_best_from_response
            if pre_alltime_rank is None:
                print(f"All-time bot leaderboard impact: Now ranked #{post_alltime_rank} with score {alltime_score}")
            else:
                print(f"All-time bot leaderboard impact: Rank #{post_alltime_rank}, score improved ({baseline_alltime_best} → {alltime_score})")
        else:
            print("All-time bot leaderboard impact: Score improved, outside top 10")
    else:
        if post_alltime_rank is not None:
            print(f"All-time bot leaderboard impact: No change (currently #{post_alltime_rank})")
        else:
            print("All-time bot leaderboard impact: No change")

    for l in lines:
        print(l)

    save_last_play_at(datetime.now(load_bot_tz()))
    average_score = int(sum(safe_int(r.get("finalScore", 0)) for r in results) / len(results)) if results else 0
    append_batch_history({
        "completedAt": datetime.now(load_bot_tz()).isoformat(),
        "localDate": datetime.now(load_bot_tz()).date().isoformat(),
        "strategy": load_strategy(),
        "gamesCompleted": games_completed,
        "topScore": best,
        "averageScore": average_score
    })
    log_event(f"batch complete: games={games_completed}/{n} top_score={best} strategy={load_strategy()}")

def analyze_player_stats(api_key, profile_id):
    stats = fetch_player_stats(api_key, profile_id)
    scoreboard = stats.get("scoreboard", {})
    streaks = stats.get("streaks", {}).get("byStage", {})
    houses = stats.get("houses", {})

    print("Profile stats:")
    print(f"Best score: {scoreboard.get('bestScore', 0)}")
    print(f"Average score: {scoreboard.get('averageScore', 0)}")
    print(f"Win rate: {scoreboard.get('winRate', 0)}%")
    print(f"Games played: {scoreboard.get('gamesPlayed', 0)}")
    print(f"Total wins: {scoreboard.get('totalWins', 0)}")
    print(f"Best stage streaks: BW={streaks.get('blackWhite', 0)}, Vehicles={streaks.get('vehicles', 0)}, Suit={streaks.get('suit', 0)}, Hands={streaks.get('hands', 0)}, Dice={streaks.get('dice', 0)}, Shapes={streaks.get('shapes', 0)}, Colour={streaks.get('colour', 0)}")
    print(f"Houses: Full={houses.get('fullHouse', 0)}, Six={houses.get('sixHouse', 0)}, Five={houses.get('fiveHouse', 0)}, Half={houses.get('halfHouse', 0)}, High={houses.get('highHouse', 0)}, Low={houses.get('lowHouse', 0)}, SixSeven={houses.get('sixSeven', 0)}")

    best_score = scoreboard.get("bestScore", 0)
    avg_score = scoreboard.get("averageScore", 0)

    print("Performance analysis:")
    if best_score >= 15000:
        print(f"- Elite performance: Best score {best_score} is in top tier")
    elif best_score >= 5000:
        print(f"- Strong performance: Best score {best_score} is above average")
    else:
        print(f"- Building performance: Best score {best_score} indicates room for growth")

    if avg_score > 800:
        print(f"- Consistent: Average score {avg_score} is above the community average (750-800)")
    elif avg_score > 600:
        print(f"- Moderate: Average score {avg_score} is above baseline (500-600)")
    else:
        print(f"- Struggling: Average score {avg_score} is below baseline (500-600)")

def cmd_pickstats(api_key, profile_id):
    stats = fetch_player_stats(api_key, profile_id)
    my_picks = stats.get("myPicks", {})
    comp_picks = stats.get("computerPicks", {})

    print_player_identity(api_key, profile_id)
    print("Pick stats:")
    print("Player hot picks:")
    for stage, options in my_picks.items():
        if not options:
            print(f"- {stage}: no data")
            continue
        best_avg = -1
        best_opt = None
        for opt, data in options.items():
            avg = data.get("avg", 0)
            if avg > best_avg and data.get("picks", 0) > 0:
                best_avg = avg
                best_opt = opt
        if best_opt:
            p = options[best_opt].get("picks", 0)
            w = options[best_opt].get("wins", 0)
            avg_val = options[best_opt].get("avg", 0)
            display_opt = best_opt.upper()
            print(f"- {stage.replace('BlackWhite','Black/White').replace('Vehicles','Vehicles').replace('Suit','Suit').replace('Hands','Hands').replace('Dice','Dice').replace('Shapes','Shapes').replace('Colour','Colour')}: {display_opt} avg={avg_val:.1f} picks={p} wins={w}")

    print("Computer hot picks:")
    for stage, options in comp_picks.items():
        if not options:
            print(f"- {stage}: no data")
            continue
        max_picks = -1
        best_opt = None
        for opt, data in options.items():
            picks = data.get("picks", 0)
            if picks > max_picks:
                max_picks = picks
                best_opt = opt
        if best_opt:
            p = options[best_opt].get("picks", 0)
            display_opt = best_opt.upper()
            print(f"- {stage.replace('BlackWhite','Black/White').replace('Vehicles','Vehicles').replace('Suit','Suit').replace('Hands','Hands').replace('Dice','Dice').replace('Shapes','Shapes').replace('Colour','Colour')}: {display_opt} picks={p}")

    print("Computer due picks:")
    for stage, options in comp_picks.items():
        if not options:
            print(f"- {stage}: no data")
            continue
        min_picks = float('inf')
        best_opt = None
        for opt, data in options.items():
            picks = data.get("picks", 0)
            if picks > 0 and picks < min_picks:
                min_picks = picks
                best_opt = opt
        if best_opt:
            p = options[best_opt].get("picks", 0)
            display_opt = best_opt.upper()
            print(f"- {stage.replace('BlackWhite','Black/White').replace('Vehicles','Vehicles').replace('Suit','Suit').replace('Hands','Hands').replace('Dice','Dice').replace('Shapes','Shapes').replace('Colour','Colour')}: {display_opt} picks={p}")

def cmd_status(api_key, profile_id):
    stats = fetch_player_stats(api_key, profile_id)
    sb = stats.get("scoreboard", {})
    streaks = stats.get("streaks", {}).get("byStage", {})
    houses = stats.get("houses", {})

    print_player_identity(api_key, profile_id)
    print(f"Best score: {sb.get('bestScore', 0)}")
    print(f"Average score: {sb.get('averageScore', 0)}")
    print(f"Win rate: {sb.get('winRate', 0)}%")
    print(f"Games played: {sb.get('gamesPlayed', 0)}")
    print(f"Total wins: {sb.get('totalWins', 0)}")
    print(f"Best stage streaks: BW={streaks.get('blackWhite', 0)}, Vehicles={streaks.get('vehicles', 0)}, Suit={streaks.get('suit', 0)}, Hands={streaks.get('hands', 0)}, Dice={streaks.get('dice', 0)}, Shapes={streaks.get('shapes', 0)}, Colour={streaks.get('colour', 0)}")
    print(f"Houses: Full={houses.get('fullHouse', 0)}, Six={houses.get('sixHouse', 0)}, Five={houses.get('fiveHouse', 0)}, Half={houses.get('halfHouse', 0)}, High={houses.get('highHouse', 0)}, Low={houses.get('lowHouse', 0)}, SixSeven={houses.get('sixSeven', 0)}")

def cmd_stats(api_key, profile_id):
    stats = fetch_player_stats(api_key, profile_id)
    sb = stats.get("scoreboard", {})
    streaks = stats.get("streaks", {}).get("byStage", {})
    houses = stats.get("houses", {})

    print_player_identity(api_key, profile_id)
    print("Profile stats:")
    print(f"Best score: {sb.get('bestScore', 0)}")
    print(f"Average score: {sb.get('averageScore', 0)}")
    print(f"Win rate: {sb.get('winRate', 0)}%")
    print(f"Games played: {sb.get('gamesPlayed', 0)}")
    print(f"Total wins: {sb.get('totalWins', 0)}")
    print(f"Best stage streaks: BW={streaks.get('blackWhite', 0)}, Vehicles={streaks.get('vehicles', 0)}, Suit={streaks.get('suit', 0)}, Hands={streaks.get('hands', 0)}, Dice={streaks.get('dice', 0)}, Shapes={streaks.get('shapes', 0)}, Colour={streaks.get('colour', 0)}")
    print(f"Houses: Full={houses.get('fullHouse', 0)}, Six={houses.get('sixHouse', 0)}, Five={houses.get('fiveHouse', 0)}, Half={houses.get('halfHouse', 0)}, High={houses.get('highHouse', 0)}, Low={houses.get('lowHouse', 0)}, SixSeven={houses.get('sixSeven', 0)}")

def main():
    migrate_legacy_state()
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    log_event(f"command start: cmd={cmd} args={args}")

    requires_identity = True

    if cmd == "help":
        requires_identity = False
    elif cmd == "btg":
        if len(args) == 0:
            cmd_help()
            sys.exit(0)
        subcmd = args[0]
        if subcmd == "help":
            requires_identity = False

    if requires_identity:
        if not os.path.exists(API_KEY_FILE) or not os.path.exists(PROFILE_ID_FILE):
            log_event("identity missing: attempting first-run registration")
            api_key, profile_id = register_bot()
        else:
            api_key = load_api_key()
            profile_id = load_profile_id()
    else:
        api_key = None
        profile_id = None

    if cmd == "btg":
        if len(args) == 0:
            cmd_help()
            sys.exit(0)

        subcmd = args[0]
        subargs = args[1:]

        if subcmd == "help":
            cmd_help()
        elif subcmd == "boards":
            type_arg = "bots"
            date_str = None
            limit = 10
            for arg in subargs:
                if arg in ["both", "humans", "bots"]:
                    type_arg = arg
                elif len(arg) == 10 and arg[4] == '-' and arg[7] == '-':
                    date_str = arg
                elif arg.isdigit():
                    limit = int(arg)
            cmd_boards(api_key, profile_id, type_arg, date_str, limit)
        elif subcmd == "play":
            cmd_play(api_key, profile_id)
        elif subcmd == "review":
            if not subargs:
                print("Usage: btg review [daily|strategy]", file=sys.stderr)
                sys.exit(1)
            review_type = subargs[0]
            if review_type == "daily":
                cmd_review_daily(api_key, profile_id)
            elif review_type == "strategy":
                cmd_review_strategy(api_key, profile_id)
            else:
                print("Usage: btg review [daily|strategy]", file=sys.stderr)
                sys.exit(1)
        elif subcmd == "support":
            cmd_support()
        elif subcmd == "analysis":
            analyze_player_stats(api_key, profile_id)
        elif subcmd == "personality":
            mode = "balanced" if len(subargs) == 0 else subargs[0]
            save_personality(mode)
            print(f"Personality set to: {mode}")
        elif subcmd == "strategy":
            if len(subargs) == 0:
                current = load_strategy()
                print(f"Current strategy: {current}")
            else:
                mode = subargs[0]
                if mode not in ["random", "hot-pick-player", "hot-pick-computer", "pick-due", "cold-avoid"]:
                    print("Invalid strategy. Options: random, hot-pick-player, hot-pick-computer, pick-due, cold-avoid", file=sys.stderr)
                    sys.exit(1)
                save_strategy(mode)
                print(f"Strategy set: {mode}")
                return
        elif subcmd == "status":
            cmd_status(api_key, profile_id)
        elif subcmd == "stats":
            cmd_stats(api_key, profile_id)
        elif subcmd == "pickstats":
            cmd_pickstats(api_key, profile_id)
        else:
            log_event(f"command failed: unknown btg command args={subargs}")
            print("Unknown btg command", file=sys.stderr)
            sys.exit(1)

    elif cmd == "help":
        cmd_help()
    elif cmd == "boards":
        type_arg = "bots"
        date_str = None
        limit = 10
        for arg in args:
            if arg in ["both", "humans", "bots"]:
                type_arg = arg
            elif len(arg) == 10 and arg[4] == '-' and arg[7] == '-':
                date_str = arg
            elif arg.isdigit():
                limit = int(arg)
        cmd_boards(api_key, profile_id, type_arg, date_str, limit)
    elif cmd == "play":
        cmd_play(api_key, profile_id)
    elif cmd == "review":
        if len(args) == 0:
            print("Usage: btg review [daily|strategy]", file=sys.stderr)
            sys.exit(1)
        review_type = args[0]
        if review_type == "daily":
            cmd_review_daily(api_key, profile_id)
        elif review_type == "strategy":
            cmd_review_strategy(api_key, profile_id)
        else:
            print("Usage: btg review [daily|strategy]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "support":
        cmd_support()
    elif cmd == "analysis":
        analyze_player_stats(api_key, profile_id)
    elif cmd == "personality":
        mode = "balanced" if len(args) == 0 else args[0]
        save_personality(mode)
        print(f"Personality set to: {mode}")
    elif cmd == "strategy":
        if len(args) == 0:
            current = load_strategy()
            print(f"Current strategy: {current}")
        else:
            mode = args[0]
            if mode not in ["random", "hot-pick-player", "hot-pick-computer", "pick-due", "cold-avoid"]:
                print("Invalid strategy. Options: random, hot-pick-player, hot-pick-computer, pick-due, cold-avoid", file=sys.stderr)
                sys.exit(1)
            save_strategy(mode)
            print(f"Strategy set: {mode}")
            return
    elif cmd == "status":
        cmd_status(api_key, profile_id)
    elif cmd == "stats":
        cmd_stats(api_key, profile_id)
    elif cmd == "pickstats":
        cmd_pickstats(api_key, profile_id)
    else:
        log_event(f"command failed: unknown command cmd={cmd} args={args}")
        print("Unknown command", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("BTG cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"BTG error: {e}", file=sys.stderr)
        sys.exit(1)
