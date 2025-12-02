#!/usr/bin/env python3
"""
Build a standalone HTML file with embedded CSS and data.
"""

import json
from pathlib import Path

def build_standalone():
    # Read files
    html_template = Path('index.html').read_text(encoding='utf-8')
    css = Path('style.css').read_text(encoding='utf-8')
    data = Path('data.json').read_text(encoding='utf-8')

    # Replace the external CSS link with embedded style
    html_with_css = html_template.replace(
        '<link rel="stylesheet" href="style.css">',
        f'<style>{css}</style>'
    )

    # Replace the fetch() call with embedded data
    html_with_data = html_with_css.replace(
        'async function loadData() {\n            try {\n                const response = await fetch(\'data.json\');',
        'async function loadData() {\n            try {\n                // Embedded data\n                const response = { ok: true, json: async () => EMBEDDED_DATA };'
    )

    # Add the data as a variable (only replace first occurrence)
    html_with_data = html_with_data.replace(
        '<script>',
        f'<script>\n        const EMBEDDED_DATA = {data};\n',
        1  # Only replace first occurrence
    )

    # Write standalone file (overwrite index.html to make it standalone)
    output = Path('index.html')
    output.write_text(html_with_data, encoding='utf-8')

    print(f'Updated index.html to standalone version (embedded CSS and data)')
    print(f'File size: {len(html_with_data) / 1024:.1f} KB')
    print(f'\nYou can now open index.html directly in your browser!')

if __name__ == '__main__':
    build_standalone()
