export function $(sel, ctx = document) {
  return ctx.querySelector(sel);
}

export function $$(sel, ctx = document) {
  return [...ctx.querySelectorAll(sel)];
}

export function show(el, display = '') {
  if (el) {
    el.hidden = false;
    if (display) {
      el.style.display = display;
    } else if (el.style.display === 'none') {
      el.style.display = '';
    }
  }
}

export function hide(el) {
  if (el) {
    el.hidden = true;
    el.style.display = 'none';
  }
}

export function showToast(message, type = 'info') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `toast ${type}`;
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => toast.classList.remove('show'), 3500);
}

export function markdownToHtml(md) {
  if (!md) return '';

  let lines = md.split('\n');
  let html = '';
  let inList = null;
  let listItems = [];

  function flushList() {
    if (listItems.length === 0) return;
    const tag = inList === 'ul' ? 'ul' : 'ol';
    html += `<${tag}>${listItems.join('')}</${tag}>\n`;
    listItems = [];
    inList = null;
  }

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    let processed = false;

    let hrMatch = line.match(/^---+$/);
    if (hrMatch) {
      flushList();
      html += '<hr>\n';
      continue;
    }

    let codeStart = line.match(/^```(\w*)/);
    if (codeStart) {
      flushList();
      let lang = codeStart[1];
      let codeLines = [];
      i++;
      while (i < lines.length && !lines[i].match(/^```/)) {
        codeLines.push(lines[i]);
        i++;
      }
      let code = codeLines.join('\n');
      code = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      html += `<pre><code>${code}</code></pre>\n`;
      continue;
    }

    let h1Match = line.match(/^# (.+)/);
    let h2Match = line.match(/^## (.+)/);
    let h3Match = line.match(/^### (.+)/);
    if (h3Match) { flushList(); html += '<h3>' + inlineMarkdown(h3Match[1]) + '</h3>\n'; continue; }
    if (h2Match) { flushList(); html += '<h2>' + inlineMarkdown(h2Match[1]) + '</h2>\n'; continue; }
    if (h1Match) { flushList(); html += '<h1>' + inlineMarkdown(h1Match[1]) + '</h1>\n'; continue; }

    let bqMatch = line.match(/^> (.+)/);
    if (bqMatch) {
      flushList();
      let bqLines = [inlineMarkdown(bqMatch[1])];
      i++;
      while (i < lines.length && lines[i].match(/^> /)) {
        bqLines.push(inlineMarkdown(lines[i].slice(2)));
        i++;
      }
      i--;
      html += '<blockquote>' + bqLines.join('<br>') + '</blockquote>\n';
      continue;
    }

    let tableMatch = line.match(/^\|(.+)\|/);
    if (tableMatch) {
      flushList();
      let rows = [];
      let headers = parseTableRow(line);
      i++;
      let dividerLine = i < lines.length ? lines[i] : '';
      if (dividerLine.match(/^\|[-:| ]+\|/)) {
        i++;
      }
      if (headers.length > 0) {
        let headerRow = '<thead><tr>' + headers.map(h => '<th>' + inlineMarkdown(h.trim()) + '</th>').join('') + '</tr></thead>';
        let bodyRows = [];
        while (i < lines.length && lines[i].match(/^\|(.+)\|/)) {
          let cells = parseTableRow(lines[i]);
          bodyRows.push('<tr>' + cells.map(c => '<td>' + inlineMarkdown(c.trim()) + '</td>').join('') + '</tr>');
          i++;
        }
        i--;
        html += '<table>' + headerRow + '<tbody>' + bodyRows.join('') + '</tbody></table>\n';
      }
      continue;
    }

    let liMatch = line.match(/^(- |\* |\d+\. )(.+)/);
    if (liMatch) {
      let isOl = !!line.match(/^\d+\. /);
      let listType = isOl ? 'ol' : 'ul';
      if (inList !== listType) {
        flushList();
        inList = listType;
      }
      listItems.push('<li>' + inlineMarkdown(liMatch[2]) + '</li>');
      continue;
    }

    if (line.trim() === '' && inList) {
      flushList();
      continue;
    }

    if (line.trim() === '') {
      flushList();
      continue;
    }

    flushList();
    html += '<p>' + inlineMarkdown(line) + '</p>\n';
  }

  flushList();
  return html.trim();
}

function parseTableRow(line) {
  let s = line.slice(1, -1);
  let cells = [];
  let current = '';
  let inCode = false;
  for (let ch of s) {
    if (ch === '`') inCode = !inCode;
    if (ch === '|' && !inCode) {
      cells.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  cells.push(current);
  return cells;
}

function inlineMarkdown(text) {
  let html = text;

  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  return html;
}

export function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function pluralize(count, singular, plural) {
  return count === 1 ? singular : (plural || `${singular}s`);
}

export function getFeatureLabel(feature) {
  const labels = {
    notes: 'Notes', flashcards: 'Flashcards', quiz: 'Quiz',
    mindmap: 'Mind Map', revision: 'Revision',
  };
  return labels[feature] || feature;
}

export function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
