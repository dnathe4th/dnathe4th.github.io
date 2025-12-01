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
import os
import re
import requests
import struct
import time
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin


API_BASE = "https://www.warzone.com"
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def load_env():
    """Load environment variables from .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


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


def create_session(email: str, password: str, debug: bool = False) -> requests.Session | None:
    """Create an authenticated session for web scraping."""
    print("Logging in to Warzone...")
    session = requests.Session()

    try:
        # First, get the login page to examine the form
        print("  Fetching login page...")
        login_page = session.get(f"{API_BASE}/SignIn", timeout=30)

        if debug:
            with open("debug_login_page.html", "w", encoding="utf-8") as f:
                f.write(login_page.text)
            print(f"  Debug: Saved login page to debug_login_page.html")

        # Try to find the form action and any hidden fields
        form_action = "/SignIn"  # Default
        hidden_fields = {}

        # Look for hidden input fields (CSRF tokens, etc.)
        import re
        hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', login_page.text, re.IGNORECASE)
        for hidden in hidden_inputs:
            name_match = re.search(r'name=["\']([^"\']+)["\']', hidden)
            value_match = re.search(r'value=["\']([^"\']*)["\']', hidden)
            if name_match and value_match:
                hidden_fields[name_match.group(1)] = value_match.group(1)
                if debug:
                    print(f"  Debug: Found hidden field: {name_match.group(1)} = {value_match.group(1)[:20]}...")

        # Build login data with hidden fields + credentials
        login_data = {
            **hidden_fields,
            "email": email,
            "password": password,
        }

        # Post login credentials
        print("  Submitting login form...")
        response = session.post(
            f"{API_BASE}{form_action}",
            data=login_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{API_BASE}/SignIn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            allow_redirects=True,
            timeout=30
        )

        if debug:
            with open("debug_login_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  Debug: Saved login response to debug_login_response.html")
            print(f"  Debug: Response URL: {response.url}")
            print(f"  Debug: Response status: {response.status_code}")

        # Check if login was successful
        if response.status_code == 405:
            print("ERROR: Login endpoint returned 405 Method Not Allowed")
            print("This suggests Warzone's login may use JavaScript or a different endpoint.")
            if debug:
                print("Check debug_login_page.html to see the actual login form structure")
            return None
        elif "SignOut" in response.text or "MyGames" in response.text:
            print("Login successful!")
            return session
        elif "error" in response.text.lower() or "incorrect" in response.text.lower():
            print("ERROR: Login failed - incorrect credentials or account issue")
            if debug:
                print("Check debug_login_response.html for details")
            return None
        else:
            print("WARNING: Login may have failed - unable to verify authentication")
            if debug:
                print("Check debug_login_response.html to see what was returned")
            return session

    except Exception as e:
        print(f"Error during login: {e}")
        import traceback
        if debug:
            traceback.print_exc()
        return None


def authenticate_and_get_session(email: str, password: str, debug: bool = False) -> requests.Session | None:
    """Authenticate with Warzone and return a session with valid cookies."""
    print("Authenticating with Warzone...")
    session = requests.Session()

    # Set headers to mimic a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    try:
        # First, visit the main page to get initial cookies
        print("  Getting initial session...")
        home_response = session.get(f"{API_BASE}/", timeout=30)

        if debug:
            print(f"  Debug: Initial cookies: {session.cookies.get_dict()}")

        # Try to find the actual login endpoint by checking the site
        # Warzone likely uses a different login mechanism
        # Let's try posting to common endpoints

        login_endpoints = [
            "/API/Login",
            "/Account/Login",
            "/Login",
            "/api/login",
        ]

        login_data = {
            'email': email,
            'Email': email,
            'password': password,
            'Password': password,
        }

        for endpoint in login_endpoints:
            if debug:
                print(f"  Trying login endpoint: {endpoint}")

            try:
                response = session.post(
                    f"{API_BASE}{endpoint}",
                    data=login_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30,
                    allow_redirects=True
                )

                if debug:
                    print(f"    Status: {response.status_code}")
                    print(f"    Cookies after: {session.cookies.get_dict()}")

                # Check if we got authenticated cookies
                if response.status_code == 200 and session.cookies:
                    # Verify by trying to access My Games
                    test = session.get(f"{API_BASE}/MultiPlayer?MyGames=1", timeout=30)
                    if "Sign In" not in test.text and "GameID=" in test.text:
                        print("  Authentication successful!")
                        return session

            except Exception as e:
                if debug:
                    print(f"    Error: {e}")
                continue

        # If standard login doesn't work, try using the API token to establish a web session
        # Some sites accept API tokens in cookies
        print("  Standard login failed, trying API token approach...")

        # Get API token
        token_response = session.post(
            f"{API_BASE}/API/GetAPIToken",
            data=f"Email={email}&Password={password}",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )

        if token_response.status_code == 200:
            token_data = token_response.json()
            if 'APIToken' in token_data:
                token = token_data['APIToken']

                # Try setting various cookie combinations
                session.cookies.set('WarzoneToken', token, domain='.warzone.com', path='/')
                session.cookies.set('AuthToken', token, domain='.warzone.com', path='/')
                session.cookies.set('APIToken', token, domain='.warzone.com', path='/')
                session.cookies.set('Email', email, domain='.warzone.com', path='/')

                if debug:
                    print(f"  Debug: Set cookies with API token")
                    print(f"  Debug: Cookies: {session.cookies.get_dict()}")

                # Test authentication
                test = session.get(f"{API_BASE}/MultiPlayer?MyGames=1", timeout=30)

                if debug:
                    with open("debug_auth_test.html", "w", encoding="utf-8") as f:
                        f.write(test.text)
                    print(f"  Debug: Saved auth test to debug_auth_test.html")
                    print(f"  Debug: Has 'Sign In': {'Sign In' in test.text}")
                    print(f"  Debug: Has 'GameID=': {'GameID=' in test.text}")

                if "Sign In" not in test.text or "GameID=" in test.text:
                    print("  Authentication with API token successful!")
                    return session

        print("  ERROR: All authentication methods failed")
        return None

    except Exception as e:
        print(f"  Error during authentication: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None


def scrape_game_ids_with_session(session: requests.Session, max_pages: int = 100, debug: bool = False, existing_ids: set = None) -> list[str]:
    """Scrape game IDs from the Past Games page.

    With --merge: Fetches first page only, stops if ANY games are already cached.
    Without --merge: Fetches pages up to max_pages.
    """
    print("Scraping game IDs from Past Games (binary format)...")
    all_game_ids = set()
    per_page = 200  # Max allowed by Warzone

    # Simple logic: if merging, just get first page and stop if we have any cached
    pages_to_fetch = 1 if existing_ids else max_pages

    for page in range(pages_to_fetch):
        offset = page * per_page
        print(f"  Fetching page {page + 1} (offset {offset})...", end=" ")

        try:
            # POST to get hex-encoded binary data
            form_data = {
                'Offset': offset,
                'Sort': 3,
                'PerPage': per_page
            }
            response = session.post(
                f"{API_BASE}/MultiPlayer/PastGames",
                data=form_data,
                timeout=30
            )

            if response.status_code != 200:
                print(f"HTTP {response.status_code}")
                break

            # Response is hex-encoded binary data
            try:
                hex_data = response.text.strip()
                if not hex_data or len(hex_data) < 10:
                    print("Empty response (no more games)")
                    break

                decoded_bytes = bytes.fromhex(hex_data)

                if debug and page == 0:
                    Path("debug_pastgames_page0.bin").write_bytes(decoded_bytes)
                    print(f"\nDebug: Saved decoded binary to debug_pastgames_page0.bin")

                # Extract game IDs: scan for 32-bit integers in expected range
                page_ids = set()
                for i in range(0, len(decoded_bytes) - 4):
                    val = struct.unpack('<I', decoded_bytes[i:i+4])[0]
                    # Game IDs are in the 10M-100M range typically
                    if 10_000_000 <= val <= 100_000_000:
                        page_ids.add(str(val))

                if not page_ids:
                    print("No game IDs found (reached end)")
                    break

                all_game_ids.update(page_ids)

                # For incremental updates: check if we have any cached games
                if existing_ids:
                    cached_count = len(page_ids & existing_ids)
                    new_count = len(page_ids - existing_ids)
                    print(f"Found {new_count} new + {cached_count} cached = {len(page_ids)} total IDs")

                    if cached_count > 0:
                        print(f"  Found cached games - stopping (incremental update)")
                        break
                else:
                    print(f"Found {len(page_ids)} game IDs")

                time.sleep(RATE_LIMIT_DELAY)

            except ValueError as e:
                print(f"Hex decode error: {e}")
                break

        except Exception as e:
            print(f"Error: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            break

    return list(all_game_ids)


def fetch_game(game_id: str, email: str, token: str) -> dict | None:
    """Fetch a single game's data from the Warzone API."""
    # Use dict for proper URL encoding of special characters in token
    data = {
        "Email": email,
        "APIToken": token
    }

    try:
        response = requests.post(
            f"{API_BASE}/API/GameFeed?GameID={game_id}&GetSettings=true",
            data=data,
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


def _build_output(games: list) -> dict:
    """Build output JSON structure with stats."""
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

    return {
        "fetchedAt": datetime.now().isoformat() + "Z",
        "totalGames": len(games),
        "games": games,
        "playerStats": list(player_stats.values()),
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
    # Load .env file first
    load_env()

    parser = argparse.ArgumentParser(
        description="Fetch Warzone game data for the stats dashboard"
    )
    parser.add_argument(
        "--email", "-e",
        default=os.environ.get("WARZONE_EMAIL"),
        help="Your Warzone account email (or set WARZONE_EMAIL in .env)"
    )
    parser.add_argument(
        "--password", "-p",
        default=os.environ.get("WARZONE_PASSWORD"),
        help="Your Warzone account password (or set WARZONE_PASSWORD in .env)"
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
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum number of pages to scrape (default 100, ~5000 games)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode (saves HTML responses to files for troubleshooting)"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge new games with existing data.json (incremental update)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.email:
        print("Error: Email is required (use --email or set WARZONE_EMAIL in .env)")
        sys.exit(1)

    if not args.password and not args.token:
        print("Error: You must provide either --password (or WARZONE_PASSWORD in .env) or --token")
        sys.exit(1)

    # Get API token
    api_token = args.token
    if not api_token and args.password:
        api_token = get_api_token(args.email, args.password)
        if not api_token:
            print("Failed to get API token. Check your credentials.")
            sys.exit(1)

    # Load existing games if merging (do this BEFORE scraping)
    existing_games = {}
    existing_ids = set()
    if args.merge and Path(args.output).exists():
        print(f"Loading existing data from {args.output}...")
        try:
            existing_data = json.loads(Path(args.output).read_text())
            existing_games = {g["id"]: g for g in existing_data.get("games", [])}
            existing_ids = set(existing_games.keys())
            print(f"Found {len(existing_games)} existing games")
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")

    # Get game IDs
    game_ids = []
    if args.games:
        game_ids = load_game_ids(args.games)
        print(f"Loaded {len(game_ids)} game IDs from input")
    else:
        # Auto-discover games by authenticating and scraping
        print("Auto-discovering games...")

        if not args.password:
            print("ERROR: Password required for auto-discovery (or provide --games file)")
            sys.exit(1)

        session = authenticate_and_get_session(args.email, args.password, debug=args.debug)
        if not session:
            print("ERROR: Could not authenticate with Warzone")
            sys.exit(1)

        # Pass existing IDs so scraper can stop early if merging
        game_ids = scrape_game_ids_with_session(
            session,
            max_pages=args.max_pages,
            debug=args.debug,
            existing_ids=existing_ids if args.merge else None
        )
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
    skipped_existing = 0
    save_interval = 50  # Save progress every 50 games

    for i, game_id in enumerate(game_ids, 1):
        # Skip if already have this game
        if game_id in existing_games:
            games.append(existing_games[game_id])
            skipped_existing += 1
            if i % 10 == 0:  # Only print every 10th to avoid spam
                print(f"[{i}/{len(game_ids)}] Skipping existing games... ({skipped_existing} skipped so far)")
            continue

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

        # Incremental save: save progress every N games
        if i % save_interval == 0:
            temp_output = _build_output(games)
            Path(args.output).write_text(json.dumps(temp_output, indent=2))
            print(f"\n  [Progress saved: {len(games)} games so far]\n")

    if skipped_existing > 0:
        print(f"\nReused {skipped_existing} existing games from cache")

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
    output = _build_output(games)

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
