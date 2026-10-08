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

export const DOC_ICON =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
  '<path d="M14 2v5h6"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>';

export function statusPill(status) {
  const done = status === 'done';
  const failed = status === 'failed' || status === 'error';
  const cls = failed ? 'status-failed' : done ? 'status-done' : 'status-processing';
  const label = failed ? 'Failed' : done ? 'Processed' : 'Processing';
  return `<span class="status-pill ${cls}">${label}</span>`;
}

export function errorStateHtml(title, detail) {
  return `<div class="error-state">
    <span class="error-state-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
    </span>
    <h3 class="error-state-title">${title}</h3>
    <p class="error-state-text">${detail}</p>
    <p class="error-state-hint">Try uploading your file again, or use different settings.</p>
  </div>`;
}

export function emptyStateHtml(title, text, cta) {
  return `<div class="empty-state">
    <span class="empty-state-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>
    </span>
    <h3 class="empty-state-title">${title}</h3>
    <p class="empty-state-text">${text}</p>
    ${cta || ''}
  </div>`;
}
