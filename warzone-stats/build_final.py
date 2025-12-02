#!/usr/bin/env python3
"""Build standalone dashboard - always from git sources"""

import json
import subprocess
from pathlib import Path

# Get clean templates from git
subprocess.run(['git', 'show', 'b4fe40f:warzone-stats/index.html'],
               stdout=open('index_clean.html', 'w'), cwd='.')
subprocess.run(['git', 'show', 'b4fe40f:warzone-stats/style.css'],
               stdout=open('style_clean.css', 'w'), cwd='.')

# Read files
html = Path('index_clean.html').read_text(encoding='utf-8')
css = Path('style_clean.css').read_text(encoding='utf-8')
data_text = Path('data.json').read_text(encoding='utf-8')
race_js = Path('race_chart.js').read_text(encoding='utf-8')

# 1. Fix avg turns calculation
html = html.replace(
    'sum + g.numberOfTurns',
    'sum + parseInt(g.numberOfTurns || 0)'
)

# 2. Add race chart HTML
race_html = '''
        <section class="race-chart-section">
            <h2>Win Race Over Time</h2>
            <p class="section-desc">Watch the leaderboard evolve from 2016 to present</p>
            <div class="race-controls">
                <button id="playBtn" class="race-btn">▶ Play</button>
                <button id="pauseBtn" class="race-btn">⏸ Pause</button>
                <button id="resetBtn" class="race-btn">↺ Reset</button>
                <span class="speed-control">
                    Speed: <select id="speedSelect">
                        <option value="1000">Very Slow</option>
                        <option value="500" selected>Slow</option>
                        <option value="200">Normal</option>
                        <option value="50">Fast</option>
                    </select>
                </span>
                <span id="currentDate" class="current-date"></span>
            </div>
            <div id="raceChart" class="race-chart"></div>
        </section>
'''
html = html.replace('        <section class="stats-overview"', race_html + '        <section class="stats-overview"')

# 3. Add race variables
html = html.replace(
    '        let gamesData = null;',
    '        let gamesData = null;\n        let raceTimeline = [];\n        let raceCurrentFrame = 0;\n        let raceAnimationId = null;'
)

# 4. Add race initialization
html = html.replace(
    '            setupEventListeners();\n        }',
    '            buildRaceTimeline();\n            renderRaceChart(0);\n            setupEventListeners();\n            setupRaceControls();\n        }'
)

# 5. Add race functions (with proper indentation)
race_js_clean = race_js.replace('let raceTimeline = [];\nlet raceCurrentFrame = 0;\nlet raceAnimationId = null;\n\n', '')
race_js_clean = race_js_clean.replace('// Race Chart Animation\n', '')
race_js_indented = '\n'.join('        ' + line if line.strip() else '' for line in race_js_clean.split('\n'))

html = html.replace(
    '        // Load data on page load\n        loadData();',
    race_js_indented + '\n        // Load data on page load\n        loadData();'
)

# 6. Add race CSS
race_css = '''
/* Race Chart */
.race-chart-section { margin-bottom: 50px; }
.race-controls { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
.race-btn { background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 1rem; }
.race-btn:hover { background: #c9354e; }
.speed-control select { background: var(--bg-card); color: var(--text-primary); border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
.current-date { color: var(--accent); font-weight: bold; font-size: 1.1rem; }
.race-chart { background: var(--bg-secondary); border-radius: 12px; padding: 30px; min-height: 500px; position: relative; height: 500px; }
.race-bar-container { position: absolute; top: 0; left: 0; right: 0; display: flex; align-items: center; transition: transform 0.5s ease; }
.race-player-name { width: 150px; text-align: right; padding-right: 15px; font-weight: 600; font-size: 1rem; }
.race-bar-wrapper { flex: 1; }
.race-bar { height: 35px; background: linear-gradient(90deg, var(--accent), var(--warning)); border-radius: 6px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; }
.race-bar-value { color: white; font-weight: bold; font-size: 1.1rem; }

'''
css = css.replace('/* Sections */', race_css + '/* Sections */')

# 7. Embed CSS
html = html.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')

# 8. Embed data
html = html.replace(
    "const response = await fetch('data.json');",
    "const response = { ok: true, json: async () => EMBEDDED_DATA };"
)
html = html.replace('<script>', f'<script>\n        const EMBEDDED_DATA = {data_text};\n', 1)

# Write
Path('index.html').write_text(html, encoding='utf-8')
print(f'Built: {len(html) / 1024:.1f} KB')

# Cleanup
Path('index_clean.html').unlink()
Path('style_clean.css').unlink()
