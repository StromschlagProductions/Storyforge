"""Die lokale Markdown-Darstellung erzeugt ausschließlich erlaubte DOM-Knoten."""

import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = r"""
global.window = {};
function element(tag) {
  return {tag, children: [], textContent: '', append(...items) { this.children.push(...items); }};
}
global.document = {
  createElement: element,
  createTextNode: text => ({tag: '#text', textContent: text, children: []})
};
require(process.argv[1]);
const input = '# Titel\n\n**Fett** und *kursiv*\n\n- Punkt\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n> Zitat\n\n```js\n<script>bad()</script>\n```\n\n<img src=x onerror="bad()">';
const root = window.renderMarkdown(input);
function walk(node) { return [node, ...node.children.flatMap(walk)]; }
const all = walk(root);
const tags = new Set(all.map(node => node.tag));
for (const expected of ['h1','strong','em','ul','li','table','blockquote','pre','code']) {
  if (!tags.has(expected)) throw Error('Fehlt: ' + expected);
}
if (tags.has('script') || tags.has('img')) throw Error('HTML aus Modelltext ausgeführt');
if (!all.some(node => node.textContent.includes('<img src=x'))) throw Error('HTML-Text verschwunden');
"""


def test_sicheres_lokales_markdown():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node für den DOM-Test nicht vorhanden')
    renderer = Path(__file__).resolve().parents[1] / 'src/storyforge/web/static/markdown.js'
    result = subprocess.run([node, '-e', SCRIPT, str(renderer)], capture_output=True, text=True,
                            timeout=30, check=False)
    assert result.returncode == 0, result.stderr
