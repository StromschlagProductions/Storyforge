/* Kleine, erlaubnisbasierte Markdown-Darstellung. Modelltext wird nie als HTML interpretiert. */
(function () {
  function node(tag, text) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function inline(parent, text) {
    const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g;
    let from = 0;
    for (const match of text.matchAll(pattern)) {
      parent.append(document.createTextNode(text.slice(from, match.index)));
      const value = match[0];
      const tag = value.startsWith('`') ? 'code' : value.startsWith('**') ? 'strong' : 'em';
      parent.append(node(tag, value.slice(tag === 'strong' ? 2 : 1, tag === 'strong' ? -2 : -1)));
      from = match.index + value.length;
    }
    parent.append(document.createTextNode(text.slice(from)));
  }
  function cells(line) { return line.replace(/^\||\|$/g, '').split('|').map(x => x.trim()); }
  function render(text) {
    const root = node('div'); root.className = 'markdown';
    const lines = String(text).replace(/\r\n?/g, '\n').split('\n');
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (!line.trim()) { i++; continue; }
      if (/^```/.test(line)) {
        const code = []; i++;
        while (i < lines.length && !/^```\s*$/.test(lines[i])) code.push(lines[i++]);
        if (i < lines.length) i++;
        const pre = node('pre'); pre.append(node('code', code.join('\n'))); root.append(pre); continue;
      }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) { const h = node('h' + heading[1].length); inline(h, heading[2]); root.append(h); i++; continue; }
      if (line.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
        const table = node('table'); const head = node('thead'); const row = node('tr');
        cells(line).forEach(value => { const th = node('th'); inline(th, value); row.append(th); });
        head.append(row); table.append(head); i += 2; const body = node('tbody');
        while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
          const tr = node('tr'); cells(lines[i++]).forEach(value => { const td = node('td'); inline(td, value); tr.append(td); }); body.append(tr);
        }
        table.append(body); root.append(table); continue;
      }
      if (/^>\s?/.test(line)) {
        const quote = []; while (i < lines.length && /^>\s?/.test(lines[i])) quote.push(lines[i++].replace(/^>\s?/, ''));
        const block = node('blockquote'); inline(block, quote.join('\n')); root.append(block); continue;
      }
      const list = line.match(/^\s*(?:[-*+]\s+|\d+\.\s+)/);
      if (list) {
        const ordered = /^\s*\d+\./.test(line); const group = node(ordered ? 'ol' : 'ul');
        while (i < lines.length && /^\s*(?:[-*+]\s+|\d+\.\s+)/.test(lines[i])) {
          const item = node('li'); inline(item, lines[i++].replace(/^\s*(?:[-*+]\s+|\d+\.\s+)/, '')); group.append(item);
        }
        root.append(group); continue;
      }
      const paragraph = [];
      while (i < lines.length && lines[i].trim() && !/^\s*(?:#{1,6}\s|```|>\s?|[-*+]\s+|\d+\.\s+)/.test(lines[i])) paragraph.push(lines[i++]);
      if (!paragraph.length) paragraph.push(lines[i++]);
      const p = node('p'); inline(p, paragraph.join('\n')); root.append(p);
    }
    return root;
  }
  window.renderMarkdown = render;
})();
