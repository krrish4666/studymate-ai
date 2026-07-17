import { showToast, markdownToHtml } from './utils.js?v=7';

// Shared document renderer used by the Notes Viewer and Revision Cheat Sheet.
// Renders markdown into the document-style canvas (.notes-document /
// .notes-content) and exports it as a print-parity PDF.

// Render markdown to HTML for the document canvas.
// Math segments ($..$, $$..$$, \(..\), \[..\]) are masked before markdown
// parsing so underscores/asterisks inside TeX aren't eaten as emphasis,
// then restored for KaTeX auto-render to typeset.
export function renderDocHtml(md) {
  if (!md) return '';

  const mathBlocks = [];
  const mask = (m) => `@@MATH${mathBlocks.push(m) - 1}@@`;
  let masked = md
    .replace(/\$\$[\s\S]+?\$\$/g, mask)
    .replace(/\\\[[\s\S]+?\\\]/g, mask)
    .replace(/\\\([\s\S]+?\\\)/g, mask)
    .replace(/\$(?=\S)[^$\n]*?(?<=\S)\$/g, mask);

  let html;
  if (window.marked) {
    // Mask code segments, then neutralize raw HTML from the model in the
    // remaining text (marked escapes code content itself, so restoring the
    // raw code afterwards renders correctly without double-escaping).
    const codeBlocks = [];
    const maskCode = (m) => `@@CODE${codeBlocks.push(m) - 1}@@`;
    masked = masked
      .replace(/```[\s\S]*?```/g, maskCode)
      .replace(/`[^`\n]+`/g, maskCode)
      .replace(/</g, '&lt;')
      .replace(/@@CODE(\d+)@@/g, (_, i) => codeBlocks[+i]);
    html = window.marked.parse(masked, { gfm: true, breaks: false });
  } else {
    html = markdownToHtml(masked);
  }

  // Restore math as escaped text for KaTeX to pick up
  html = html.replace(/@@MATH(\d+)@@/g, (_, i) => {
    const tex = mathBlocks[+i] || '';
    return tex.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  });
  return html;
}

export function typesetMath(el) {
  if (el && window.renderMathInElement) {
    window.renderMathInElement(el, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false },
        { left: '$', right: '$', display: false },
      ],
      throwOnError: false,
    });
  }
}

// Export a rendered document as PDF via the browser's print engine.
// The print document reuses the exact rendered HTML (including KaTeX output)
// and the same stylesheets, so the PDF matches the viewer 1:1.
export function exportDocPdf(contentId, fallbackTitle) {
  const contentEl = document.getElementById(contentId);
  if (!contentEl || !contentEl.innerHTML.trim()) {
    showToast('Nothing to export yet', 'error');
    return;
  }

  const docTitle = (contentEl.querySelector('h1')?.textContent || fallbackTitle || 'Document').trim();

  // Reuse the exact stylesheets the viewer page loaded (fonts, KaTeX, app CSS)
  // so the print document is styled identically to the on-screen viewer.
  const styleLinks = [...document.querySelectorAll('link[rel="stylesheet"]')]
    .map((l) => `<link rel="stylesheet" href="${l.href}">`)
    .join('\n');

  const printHtml = `<!DOCTYPE html>
<html lang="en" data-theme="warm-light">
<head>
<meta charset="utf-8">
<title>${docTitle.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</title>
${styleLinks}
<style>
  @page { size: A4; margin: 16mm 15mm 18mm; }
  /* Force backgrounds (callouts, code, table headers) to print */
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  html, body { background: #ffffff !important; }
  body { margin: 0; }
  .notes-document {
    max-width: none; margin: 0; padding: 0;
    background: #ffffff; border: none; border-radius: 0; box-shadow: none;
  }
  .notes-content { font-size: 11pt; line-height: 1.65; }
  /* Keep headings attached to the content that follows them */
  .notes-content h1, .notes-content h2, .notes-content h3, .notes-content h4 {
    break-after: avoid-page;
  }
  /* Never split these blocks across pages */
  .notes-content table, .notes-content blockquote, .notes-content pre,
  .notes-content .katex-display, .notes-content img {
    break-inside: avoid-page;
  }
  .notes-content tr, .notes-content li { break-inside: avoid; }
  .notes-content a { color: inherit; }
</style>
</head>
<body>
  <div class="notes-document"><div class="notes-content">${contentEl.innerHTML}</div></div>
</body>
</html>`;

  const iframe = document.createElement('iframe');
  iframe.setAttribute('aria-hidden', 'true');
  iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:210mm;height:297mm;border:0;visibility:hidden;';
  document.body.appendChild(iframe);

  iframe.onload = () => {
    const win = iframe.contentWindow;
    if (!win) { iframe.remove(); return; }
    const cleanup = () => setTimeout(() => iframe.remove(), 500);
    win.onafterprint = cleanup;
    setTimeout(cleanup, 120000); // safety net if afterprint never fires

    const fontsReady = win.document.fonts && win.document.fonts.ready
      ? win.document.fonts.ready
      : Promise.resolve();
    fontsReady
      .then(() => new Promise((r) => setTimeout(r, 150)))
      .then(() => { win.focus(); win.print(); })
      .catch(() => { win.focus(); win.print(); });
  };

  iframe.srcdoc = printHtml;
  showToast('Preparing document — choose "Save as PDF" in the print dialog', 'info');
}

// Decode one SSE data payload from the feature streams. New protocol sends
// JSON-encoded string chunks (exact text); legacy servers sent raw lines.
// Returns the text to append.
export function decodeStreamChunk(data, hasContent) {
  if (data.startsWith('"')) {
    try {
      return JSON.parse(data);
    } catch {
      return (hasContent ? '\n' : '') + data;
    }
  }
  return (hasContent ? '\n' : '') + data;
}
