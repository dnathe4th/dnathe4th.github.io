#!/usr/bin/env python3
"""
Warzone Game Data Fetcher

Fetches game data from the Warzone API and outputs a JSON file
for use with the static dashboard.

Usage:
    # Auto-discover all your games (login with email/password):
    python fetch-games.py --email your@email.com --password YOUR_PASSWORD

    # Or provide game IDs manually (with API token):
    python fetch-games.py --email your@email.com --token YOUR_API_TOKEN --games game_ids.txt

    # Filter to only games with specific players:
    python fetch-games.py --email your@email.com --password YOUR_PASSWORD --filter-players "Player1,Player2,Player3"

Get your API token at: https://www.warzone.com/API/GetAPIToken (while logged in)
"""

import argparse
import json
import re
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin


API_BASE = "https://www.warzone.com"
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def get_api_token(email: str, password: str) -> str | None:
    """Get API token using email and password."""
    print("Getting API token...")
    try:
        response = requests.post(
            f"{API_BASE}/API/GetAPIToken",
            data=f"Email={email}&Password={password}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if "APIToken" in data:
                print("Got API token successfully")
                return data["APIToken"]
            else:
                print(f"Error getting token: {data}")
                return None
    except Exception as e:
        print(f"Error getting API token: {e}")
        return None


def create_session(email: str, password: str) -> requests.Session | None:
    """Create an authenticated session for web scraping."""
    print("Logging in to Warzone...")
    session = requests.Session()

    try:
        # First, get the login page to get any CSRF tokens
        login_page = session.get(f"{API_BASE}/SignIn", timeout=30)

        # Post login credentials
        response = session.post(
            f"{API_BASE}/SignIn",
            data={
                "Email": email,
                "Password": password,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{API_BASE}/SignIn",
            },
            allow_redirects=True,
            timeout=30
        )

        # Check if login was successful by looking for signs of authentication
        if "SignOut" in response.text or "MyGames" in response.text:
            print("Login successful!")
            return session
        else:
            print("Login may have failed - checking anyway...")
            return session

    except Exception as e:
        print(f"Error during login: {e}")
        return None


def scrape_game_ids(session: requests.Session, max_pages: int = 100) -> list[str]:
    """Scrape all game IDs from the My Games page."""
    print("Scraping game IDs from My Games page...")
    all_game_ids = set()
    page = 0

    while page < max_pages:
        url = f"{API_BASE}/MultiPlayer?MyGames=1&Offset={page * 50}"
        print(f"  Fetching page {page + 1} (offset {page * 50})...", end=" ")

        try:
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"HTTP {response.status_code}")
                break

            # Find all game IDs in the page
            game_ids = re.findall(r'GameID=(\d+)', response.text)
            unique_ids = set(game_ids)

            if not unique_ids:
                print("No more games found")
                break

            new_ids = unique_ids - all_game_ids
            if not new_ids:
                print("No new games (reached end)")
                break

            all_game_ids.update(unique_ids)
            print(f"Found {len(new_ids)} new games (total: {len(all_game_ids)})")

            page += 1
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"Error: {e}")
            break

    return list(all_game_ids)


def fetch_game(game_id: str, email: str, token: str) -> dict | None:
    """Fetch a single game's data from the Warzone API."""
    data = f"Email={email}&APIToken={token}"

    try:
        response = requests.post(
            f"{API_BASE}/API/GameFeed?GameID={game_id}&GetSettings=true",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Error fetching game {game_id}: HTTP {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"  Error fetching game {game_id}: {e}")
        return None


def parse_game_data(raw: dict) -> dict | None:
    """Parse raw API response into our simplified format."""
    if "error" in raw:
        return None

    # Extract player info
    players = []
    for p in raw.get("players", []):
        player = {
            "id": p.get("id"),
            "name": p.get("name", "Unknown"),
            "state": p.get("state"),  # Won, Eliminated, Playing, etc.
            "team": p.get("team", "None"),
        }
        players.append(player)

    # Determine winner(s)
    winners = [p["name"] for p in players if p["state"] == "Won"]

    return {
        "id": raw.get("id"),
        "name": raw.get("name", "Unnamed Game"),
        "state": raw.get("state"),  # Finished, Playing, etc.
        "created": raw.get("created"),
        "numberOfTurns": raw.get("numberOfTurns", 0),
        "players": players,
        "winners": winners,
        "templateId": raw.get("templateID"),
    }


def load_game_ids(source: str) -> list[str]:
    """Load game IDs from a file or comma-separated string."""
    path = Path(source)
    if path.exists():
        content = path.read_text()
    else:
        content = source

    # Handle comma-separated, newline-separated, or mixed
    ids = []
    for line in content.replace(",", "\n").split("\n"):
        game_id = line.strip()
        if game_id and game_id.isdigit():
            ids.append(game_id)

    return ids


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Warzone game data for the stats dashboard"
    )
    parser.add_argument(
        "--email", "-e",
        required=True,
        help="Your Warzone account email"
    )
    parser.add_argument(
        "--password", "-p",
        help="Your Warzone account password (for auto-discovery of game IDs)"
    )
    parser.add_argument(
        "--token", "-t",
        help="Your Warzone API token (alternative to password)"
    )
    parser.add_argument(
        "--games", "-g",
        help="File containing game IDs (one per line) or comma-separated list. If not provided, will auto-discover."
    )
    parser.add_argument(
        "--output", "-o",
        default="data.json",
        help="Output JSON file (default: data.json)"
    )
    parser.add_argument(
        "--filter-players", "-f",
        help="Comma-separated list of player names to filter by (only include games with ANY of these players)"
    )
    parser.add_argument(
        "--filter-all-players",
        help="Comma-separated list of player names - only include games with ALL of these players"
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=0,
        help="Maximum number of games to fetch (0 = unlimited)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.password and not args.token:
        print("Error: You must provide either --password or --token")
        sys.exit(1)

    # Get API token
    api_token = args.token
    if not api_token and args.password:
        api_token = get_api_token(args.email, args.password)
        if not api_token:
            print("Failed to get API token. Check your credentials.")
            sys.exit(1)

    # Get game IDs
    game_ids = []
    if args.games:
        game_ids = load_game_ids(args.games)
        print(f"Loaded {len(game_ids)} game IDs from input")
    else:
        # Auto-discover games by scraping
        if not args.password:
            print("Error: --password is required for auto-discovery (or provide --games)")
            sys.exit(1)

        session = create_session(args.email, args.password)
        if not session:
            print("Failed to create session")
            sys.exit(1)

        game_ids = scrape_game_ids(session)
        print(f"\nDiscovered {len(game_ids)} total games")

    if not game_ids:
        print("No game IDs found!")
        sys.exit(1)

    # Apply max games limit
    if args.max_games > 0:
        game_ids = game_ids[:args.max_games]
        print(f"Limited to {len(game_ids)} games")

    # Optional player filters
    filter_any_players = None
    filter_all_players = None

    if args.filter_players:
        filter_any_players = set(name.strip().lower() for name in args.filter_players.split(","))
        print(f"Filtering for games with ANY of: {filter_any_players}")

    if args.filter_all_players:
        filter_all_players = set(name.strip().lower() for name in args.filter_all_players.split(","))
        print(f"Filtering for games with ALL of: {filter_all_players}")

    # Fetch all games
    print(f"\nFetching {len(game_ids)} games from API...")
    games = []
    errors = 0
    skipped = 0

    for i, game_id in enumerate(game_ids, 1):
        print(f"[{i}/{len(game_ids)}] Game {game_id}...", end=" ")

        raw = fetch_game(game_id, args.email, api_token)
        if raw is None:
            errors += 1
            continue

        parsed = parse_game_data(raw)
        if parsed is None:
            print("Parse error")
            errors += 1
            continue

        # Apply player filters
        game_players = set(p["name"].lower() for p in parsed["players"])

        if filter_any_players:
            if not filter_any_players.intersection(game_players):
                print("Skipped (no matching players)")
                skipped += 1
                continue

        if filter_all_players:
            if not filter_all_players.issubset(game_players):
                print("Skipped (missing required players)")
                skipped += 1
                continue

        games.append(parsed)
        print(f"OK - {parsed['name'][:40]}")

        time.sleep(RATE_LIMIT_DELAY)

    # Calculate aggregate stats
    print("\nCalculating stats...")
    player_stats = {}
    for game in games:
        if game["state"] != "Finished":
            continue

        for player in game["players"]:
            name = player["name"]
            if name not in player_stats:
                player_stats[name] = {
                    "name": name,
                    "wins": 0,
                    "losses": 0,
                    "games": 0,
                }

            player_stats[name]["games"] += 1
            if player["state"] == "Won":
                player_stats[name]["wins"] += 1
            elif player["state"] in ("Eliminated", "SurrenderAccepted", "Booted"):
                player_stats[name]["losses"] += 1

    # Build output
    output = {
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "totalGames": len(games),
        "games": games,
        "playerStats": list(player_stats.values()),
    }

    # Write output
    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*50}")
    print(f"Done! Fetched {len(games)} games ({errors} errors, {skipped} skipped)")
    print(f"Output written to: {output_path}")

    # Print quick summary
    if player_stats:
        print(f"\n{'='*50}")
        print("LEADERBOARD")
        print(f"{'='*50}")
        for stat in sorted(player_stats.values(), key=lambda x: x["wins"], reverse=True)[:10]:
            win_rate = (stat["wins"] / stat["games"] * 100) if stat["games"] > 0 else 0
            print(f"  {stat['name']}: {stat['wins']}W / {stat['losses']}L ({win_rate:.1f}%)")


if __name__ == "__main__":
    main()
