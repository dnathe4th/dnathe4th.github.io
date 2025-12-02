#!/usr/bin/env python3
"""Build standalone dashboard with race chart"""

import json
from pathlib import Path

# Read source files
html = Path('index.html').read_text(encoding='utf-8')
css = Path('style.css').read_text(encoding='utf-8')
data_text = Path('data.json').read_text(encoding='utf-8')

# 1. Add race chart HTML section after header
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

html = html.replace(
    '        <section class="stats-overview"',
    race_html + '        <section class="stats-overview"'
)

# 2. Add race chart variables
html = html.replace(
    '        let gamesData = null;',
    '''        let gamesData = null;
        let raceTimeline = [];
        let raceCurrentFrame = 0;
        let raceAnimationId = null;'''
)

# 3. Add race chart initialization
html = html.replace(
    '''            // Event listeners
            setupEventListeners();
        }''',
    '''            // Race chart
            buildRaceTimeline();
            renderRaceChart(0);

            // Event listeners
            setupEventListeners();
            setupRaceControls();
        }'''
)

# 4. Add race chart functions before loadData()
race_js = Path('race_chart.js').read_text(encoding='utf-8')
# Remove the variable declarations and reindent to match script scope
race_js = race_js.replace('let raceTimeline = [];\nlet raceCurrentFrame = 0;\nlet raceAnimationId = null;\n\n', '')
race_js = race_js.replace('// Race Chart Animation\n', '')
# Add proper indentation
race_js = '\n'.join('        ' + line if line.strip() else '' for line in race_js.split('\n'))

html = html.replace(
    '        // Load data on page load\n        loadData();',
    race_js + '\n        // Load data on page load\n        loadData();'
)

# 5. Embed CSS
html = html.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')

# 6. Embed data
html = html.replace(
    "const response = await fetch('data.json');",
    "const response = { ok: true, json: async () => EMBEDDED_DATA };"
)

html = html.replace(
    '<script>',
    f'<script>\n        const EMBEDDED_DATA = {data_text};\n',
    1
)

# Write output
Path('index.html').write_text(html, encoding='utf-8')
print(f'Built standalone index.html: {len(html) / 1024:.1f} KB')
