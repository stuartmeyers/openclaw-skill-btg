#!/usr/bin/env python3
import sys, json, random, requests, os, time
from datetime import datetime
import pytz

BASE_URL = "https://beforethoughtgame.com"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY_FILE = os.path.join(SCRIPT_DIR, ".api-key")
PROFILE_ID_FILE = os.path.join(SCRIPT_DIR, ".profile-id")
PERSONALITY_FILE = os.path.join(SCRIPT_DIR, ".config", "personality.json")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "btg.log")

def log_event(message):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

def register_bot():
    try:
        resp = requests.post(
            f"{BASE_URL}/api/bot/register",
            json={"displayName": "BTG Bot", "timezone": "Australia/Sydney"},
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

    timezone_path = os.path.join(os.path.dirname(PROFILE_ID_FILE), ".timezone")
    with open(timezone_path, "w") as f:
        f.write("Australia/Sydney")
    os.chmod(timezone_path, 0o600)

    return ak, pid

def load_key(path, idx):
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
    path = os.path.join(SCRIPT_DIR, ".config", "strategy.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f).get("mode", "random")
        except Exception:
            pass
    return "random"

def save_strategy(mode):
    if mode not in ["random", "hot-pick-player", "hot-pick-computer", "pick-due", "cold-avoid"]:
        print("Invalid strategy. Options: random, hot-pick-player, hot-pick-computer, pick-due, cold-avoid", file=sys.stderr)
        sys.exit(1)
    path = os.path.join(SCRIPT_DIR, ".config", "strategy.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
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

def fetch_daily(t="both", lim=10):
    timezone_file = os.path.join(os.path.dirname(PROFILE_ID_FILE), ".timezone")
    if os.path.exists(timezone_file):
        with open(timezone_file) as f:
            bot_timezone = f.read().strip()
    else:
        bot_timezone = "Australia/Sydney"
    tz = pytz.timezone(bot_timezone)
    now = datetime.now(tz).strftime("%Y-%m-%d")
    return now, fetch("api/leaderboard/daily", {"date": now, "type": t, "limit": lim})

def fetch_alltime(t="both", lim=10):
    return fetch("api/leaderboard/all-time", {"type": t, "limit": lim})

def fetch_house(t="both", lim=10):
    return fetch("api/leaderboard/house", {"type": t, "limit": lim})

def fetch_player_stats(api_key, profile_id):
    url = f"{BASE_URL}/api/player/stats?profileId={profile_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    max_retries = 3

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 401:
                print("BTG error: unauthorized (check .api-key)", file=sys.stderr)
                sys.exit(1)

            if resp.status_code == 429:
                print("BTG error: rate limit reached (try again later)", file=sys.stderr)
                sys.exit(1)

            if resp.status_code >= 500:
                if attempt == max_retries - 1:
                    print("BTG error: server unavailable.", file=sys.stderr)
                    sys.exit(1)
                print("BTG server error. Retrying in 30 seconds.")
                time.sleep(30)
                continue

            resp.raise_for_status()

            try:
                return resp.json()
            except ValueError:
                print("BTG error: invalid JSON returned from server.", file=sys.stderr)
                sys.exit(1)

        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                print("BTG error: network unavailable. Batch cancelled.", file=sys.stderr)
                sys.exit(1)
            print("Network error contacting beforethoughtgame.com. Retrying in 30 seconds.")
            time.sleep(30)

        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                print("BTG error: request timed out.", file=sys.stderr)
                sys.exit(1)
            print("BTG request timed out. Retrying in 30 seconds.")
            time.sleep(30)

    print("BTG error: unable to fetch player stats.", file=sys.stderr)
    sys.exit(1)

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
        api_key = register_bot()[0]
        headers["Authorization"] = f"Bearer {api_key}"
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
            api_key = register_bot()[0]
            headers["Authorization"] = f"Bearer {api_key}"
            continue

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

def cmd_boards(type_arg, date_str, limit):
    type_arg = "bots"
    limit = 10

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

def cmd_play(api_key, profile_id):
    n = 10
    results = []
    lines = []
    best = 0
    games_completed = 0

    strategy_data = fetch_player_stats(api_key, profile_id)
    profile_best_score = strategy_data.get("scoreboard", {}).get("bestScore", 0)
    pre_daily_list = fetch_daily("bots", 10)[1]
    pre_alltime_list = fetch_alltime("bots", 10)
    pre_daily_rank, pre_daily_best = find_leaderboard_entry(pre_daily_list, profile_id)
    pre_alltime_rank, pre_alltime_board_score = find_leaderboard_entry(pre_alltime_list, profile_id)
    pre_alltime_best = profile_best_score

    post_daily_best_from_response = pre_daily_best
    post_alltime_best_from_response = pre_alltime_best

    for i in range(n):
        r = play_one_game(api_key, strategy_data)

        if "error" in r and r["error"] == "bot_rate_limit":
            if i == 0:
                print("Batch blocked by server limit. Maximum 10 games per 60 minutes for this bot. Retry in 30 minutes.")
            else:
                print(f"Batch interrupted by server limit. Games completed: {games_completed}/{n}")
                print("Retry in 30 minutes.")
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

    print("Profile stats:")
    print(f"Best score: {profile_best_score}")
    print(f"Average score: {strategy_data.get('scoreboard', {}).get('averageScore', 0)}")
    print(f"Win rate: {strategy_data.get('scoreboard', {}).get('winRate', 0)}%")
    print(f"Games played: {strategy_data.get('scoreboard', {}).get('gamesPlayed', 0)}")
    print(f"Total wins: {strategy_data.get('scoreboard', {}).get('totalWins', 0)}")
    print(f"Best stage streaks: BW={strategy_data.get('streaks', {}).get('byStage', {}).get('blackWhite', 0)}, Vehicles={strategy_data.get('streaks', {}).get('byStage', {}).get('vehicles', 0)}, Suit={strategy_data.get('streaks', {}).get('byStage', {}).get('suit', 0)}, Hands={strategy_data.get('streaks', {}).get('byStage', {}).get('hands', 0)}, Dice={strategy_data.get('streaks', {}).get('byStage', {}).get('dice', 0)}, Shapes={strategy_data.get('streaks', {}).get('byStage', {}).get('shapes', 0)}, Colour={strategy_data.get('streaks', {}).get('byStage', {}).get('colour', 0)}")
    print(f"Houses: Full={strategy_data.get('houses', {}).get('fullHouse', 0)}, Six={strategy_data.get('houses', {}).get('sixHouse', 0)}, Five={strategy_data.get('houses', {}).get('fiveHouse', 0)}, Half={strategy_data.get('houses', {}).get('halfHouse', 0)}, High={strategy_data.get('houses', {}).get('highHouse', 0)}, Low={strategy_data.get('houses', {}).get('lowHouse', 0)}, SixSeven={strategy_data.get('houses', {}).get('sixSeven', 0)}")
    print(f"Current strategy: {load_strategy()}")
    print()
    print(f"Games: {n}")
    print(f"Top score this batch: {best}")

    d_date_post, d_list_post = fetch_daily("bots", 10)
    a_list_post = fetch_alltime("bots", 10)

    post_daily_rank, post_daily_board_score = find_leaderboard_entry(d_list_post, profile_id)
    post_alltime_rank, post_alltime_board_score = find_leaderboard_entry(a_list_post, profile_id)

    daily_score_improved = post_daily_best_from_response > pre_daily_best
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
                print(f"Daily bot leaderboard impact: Rank #{post_daily_rank}, score improved ({pre_daily_best} → {daily_score})")
        else:
            print("Daily bot leaderboard impact: Score improved, outside top 10")
    else:
        if post_daily_rank is not None:
            print(f"Daily bot leaderboard impact: No change (currently #{post_daily_rank})")
        else:
            print("Daily bot leaderboard impact: No change")

    alltime_score_improved = post_alltime_best_from_response > pre_alltime_best
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
                print(f"All-time bot leaderboard impact: Rank #{post_alltime_rank}, score improved ({pre_alltime_best} → {alltime_score})")
        else:
            print("All-time bot leaderboard impact: Score improved, outside top 10")
    else:
        if post_alltime_rank is not None:
            print(f"All-time bot leaderboard impact: No change (currently #{post_alltime_rank})")
        else:
            print("All-time bot leaderboard impact: No change")

    for l in lines:
        print(l)

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

    print("Profile stats:")
    print(f"Best score: {sb.get('bestScore', 0)}")
    print(f"Average score: {sb.get('averageScore', 0)}")
    print(f"Win rate: {sb.get('winRate', 0)}%")
    print(f"Games played: {sb.get('gamesPlayed', 0)}")
    print(f"Total wins: {sb.get('totalWins', 0)}")
    print(f"Best stage streaks: BW={streaks.get('blackWhite', 0)}, Vehicles={streaks.get('vehicles', 0)}, Suit={streaks.get('suit', 0)}, Hands={streaks.get('hands', 0)}, Dice={streaks.get('dice', 0)}, Shapes={streaks.get('shapes', 0)}, Colour={streaks.get('colour', 0)}")
    print(f"Houses: Full={houses.get('fullHouse', 0)}, Six={houses.get('sixHouse', 0)}, Five={houses.get('fiveHouse', 0)}, Half={houses.get('halfHouse', 0)}, High={houses.get('highHouse', 0)}, Low={houses.get('lowHouse', 0)}, SixSeven={houses.get('sixSeven', 0)}")

def main():
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_key_path = os.path.join(script_dir, ".api-key")
        profile_id_path = os.path.join(script_dir, ".profile-id")

        if not os.path.exists(api_key_path) or not os.path.exists(profile_id_path):
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
            cmd_boards(type_arg, date_str, limit)
        elif subcmd == "play":
            cmd_play(api_key, profile_id)
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
        cmd_boards(type_arg, date_str, limit)
    elif cmd == "play":
        cmd_play(api_key, profile_id)
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
