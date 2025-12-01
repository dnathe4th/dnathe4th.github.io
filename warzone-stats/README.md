# Warzone Stats Dashboard

A static dashboard showing game statistics for your Warzone gaming group over 9 years of gameplay.

## Features

- **Leaderboard** with wins, losses, win rate, and last win date
- **Head-to-Head records** between players
- **Game history** with search and filter
- **Standalone HTML** - no server needed, works offline

## Quick Start

Just open `index.html` in your browser!

## Updating the Dashboard

### Option 1: Quick Update (Recommended)

Check for new games and update incrementally:

```bash
cd warzone-stats
python fetch-games.py --filter-all-players "ajnard,Dauntless" --merge
python build_standalone.py
```

This will:
- Fetch only the most recent 200 games
- Stop immediately if any are already in your cache
- Only add brand new games
- Takes ~30 seconds if no new games

### Option 2: Full Re-scan

To rebuild from scratch or if you think games were missed:

```bash
cd warzone-stats
python fetch-games.py --filter-all-players "ajnard,Dauntless" --max-pages 60
python build_standalone.py
```

This will:
- Scan all 60 pages (~12,000 game IDs)
- Re-fetch everything (but reuses cached games with --merge)
- Takes 30-60 minutes

## Configuration

### Credentials

Create a `.env` file (already in .gitignore):

```
WARZONE_EMAIL=your@email.com
WARZONE_PASSWORD=your_password
```

### Filter Options

**Filter for specific players:**
```bash
# Games with ANY of these players
python fetch-games.py --filter-players "ajnard,Dauntless,Moriarty"

# Games with ALL of these players (your core group)
python fetch-games.py --filter-all-players "ajnard,Dauntless"
```

### Other Options

```bash
# Limit number of games fetched
python fetch-games.py --max-games 100

# Limit number of pages scraped
python fetch-games.py --max-pages 10

# Enable debug mode (saves HTML/binary files for troubleshooting)
python fetch-games.py --debug
```

## How It Works

1. **Authentication**: Script logs into Warzone using your credentials
2. **Game ID Discovery**: Scrapes Past Games page which returns hex-encoded binary data
3. **Binary Decoding**: Extracts game IDs from the binary format (scans for 32-bit integers)
4. **Data Fetching**: Queries Warzone API for each valid game ID
5. **Filtering**: Keeps only games matching your player criteria
6. **Stats Calculation**: Aggregates wins, losses, head-to-head records
7. **Dashboard Generation**: Embeds all data into standalone index.html

## Technical Details

- **Binary Format**: Warzone's Past Games endpoint returns hex-encoded binary data
- **Game ID Extraction**: Scans binary for 32-bit integers in the 10M-100M range
- **False Positives**: ~50% of extracted IDs are invalid (other numbers in binary), filtered out during API fetch
- **Caching**: With `--merge`, previously fetched games are reused to avoid redundant API calls
- **Rate Limiting**: 0.5 second delay between API requests
- **Incremental Saves**: Progress saved every 50 games to prevent data loss

## File Structure

```
warzone-stats/
├── index.html           # Standalone dashboard (open this!)
├── data.json            # Game data (DO NOT commit)
├── style.css            # Styling (source file)
├── fetch-games.py       # Data fetching script
├── build_standalone.py  # Embeds CSS+data into index.html
├── .env                 # Your credentials (DO NOT commit)
├── .env.example         # Template for credentials
└── README.md            # This file
```

## Troubleshooting

**No data found:**
- Make sure you've run `fetch-games.py` first
- Run `python build_standalone.py` to embed the data

**Login fails:**
- Check your credentials in `.env`
- Try with `--debug` flag to see what's happening

**Missing games:**
- Remove `--merge` flag to do a full re-scan
- Increase `--max-pages` if you have more than 60 pages of game history

**API errors:**
- Many "Parse error" messages are normal (false positive IDs from binary scan)
- Real games will parse successfully

## Future Enhancements

Possible additions:
- Win streaks / losing streaks
- Most common maps played
- Team game analysis
- Timeline/chart of wins over time
- Export to CSV
