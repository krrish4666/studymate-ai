// Inline markdown test
function inlineMarkdown(text) {
  let html = text;
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return html;
}

// Test full markdownToHtml
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

function markdownToHtml(md) {
  if (!md) return '';
  let lines = md.split('\n');
  let html = '';
  let inList = null;
  let listItems = [];

  function flushList() {
    if (listItems.length === 0) return;
    const tag = inList === 'ul' ? 'ul' : 'ol';
    html += '<' + tag + '>' + listItems.join('') + '</' + tag + '>\n';
    listItems = [];
    inList = null;
  }

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    let hrMatch = line.match(/^---+$/);
    if (hrMatch) { flushList(); html += '<hr>\n'; continue; }

    let codeStart = line.match(/^```(\w*)/);
    if (codeStart) {
      flushList();
      let codeLines = [];
      i++;
      while (i < lines.length && !lines[i].match(/^```/)) {
        codeLines.push(lines[i]);
        i++;
      }
      let code = codeLines.join('\n');
      code = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      html += '<pre><code>' + code + '</code></pre>\n';
      continue;
    }

    let h3Match = line.match(/^### (.+)/);
    let h2Match = line.match(/^## (.+)/);
    let h1Match = line.match(/^# (.+)/);
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
      let headers = parseTableRow(line);
      i++;
      let dividerLine = i < lines.length ? lines[i] : '';
      if (dividerLine.match(/^\|[-:| ]+\|/)) { i++; }
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
      if (inList !== listType) { flushList(); inList = listType; }
      listItems.push('<li>' + inlineMarkdown(liMatch[2]) + '</li>');
      continue;
    }

    if (line.trim() === '') { flushList(); continue; }
    flushList();
    html += '<p>' + inlineMarkdown(line) + '</p>\n';
  }
  flushList();
  return html.trim();
}

// Test
const md = `# Study Notes: JavaScript

## Introduction
JavaScript is a **programming language** used for *web development*.

## Key Concepts
- **Variables**: Use \`let\`, \`const\`, \`var\`
- **Functions**: Reusable blocks of code
- **Objects**: Key-value pairs

### Data Types
1. String
2. Number
3. Boolean

> "JavaScript is the language of the web"

## Comparison Table
| Feature | JS | Python |
|---------|----|--------|
| Typing | Dynamic | Dynamic |
| Speed | Fast | Medium |

---

\`\`\`
console.log("Hello World");
\`\`\`
`;

const output = markdownToHtml(md);
console.log(output);
console.log('\n---\n');
// Verify key elements exist
const checks = [
  ['<h1>', 'heading 1'],
  ['<h2>', 'heading 2'],
  ['<h3>', 'heading 3'],
  ['<strong>', 'bold'],
  ['<em>', 'italic'],
  ['<code>', 'inline code'],
  ['<pre>', 'code block'],
  ['<blockquote>', 'blockquote'],
  ['<ul>', 'unordered list'],
  ['<ol>', 'ordered list'],
  ['<table>', 'table'],
  ['<hr>', 'horizontal rule'],
  ['<li>', 'list item'],
  ['<th>', 'table header'],
  ['<td>', 'table cell'],
];
let allOk = true;
for (const [tag, name] of checks) {
  const ok = output.includes(tag);
  if (!ok) { console.log('MISSING: ' + name + ' (' + tag + ')'); allOk = false; }
}
if (allOk) console.log('All structural elements present!');
