import { apiPost, apiGet } from '../api.js';
import { showToast, markdownToHtml, $, hide, show } from '../utils.js?v=7';

// Render markdown to HTML for the Notes Viewer.
// Math segments ($..$, $$..$$, \(..\), \[..\]) are masked before markdown
// parsing so underscores/asterisks inside TeX aren't eaten as emphasis,
// then restored for KaTeX auto-render to typeset.
function renderNotesHtml(md) {
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

function typesetMath(el) {
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

// Export the Notes Viewer as PDF via the browser's print engine.
// The print document reuses the exact rendered HTML (including KaTeX output)
// and the same stylesheet, so the PDF matches the viewer 1:1.
function exportNotesPdf() {
  const contentEl = document.getElementById('notes-content');
  if (!contentEl || !contentEl.innerHTML.trim()) {
    showToast('Nothing to export yet', 'error');
    return;
  }

  const docTitle = (contentEl.querySelector('h1')?.textContent || 'Study Notes').trim();

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

export async function initNotes() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryNotes(fileId);

  const output = document.getElementById('feature-output');
  const modeSelect = document.getElementById('notes-mode');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');
  const loadingScreen = document.getElementById('loading-screen');
  const notesContent = document.getElementById('notes-content');
  const relatedActions = document.getElementById('related-actions');

  let currentContent = '';
  let isGenerating = false;

  generateBtn?.addEventListener('click', async () => {
    if (isGenerating) return;
    const fileRecordId = StudyMateUpload.getCurrentFileId();
    if (!fileRecordId) {
      showToast('Please select a file first', 'error');
      return;
    }

    isGenerating = true;
    generateBtn.disabled = true;
    const originalBtnText = generateBtn.textContent;
    generateBtn.textContent = 'Generating Notes...';

    const fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
    if (fileStatus) {
      fileStatus.textContent = 'Generating study notes...';
      fileStatus.className = 'file-status info';
    }

    hide(output);
    hide(relatedActions);
    show(loadingScreen, 'block');
    if (loadingScreen) {
      loadingScreen.hidden = false;
      loadingScreen.style.display = 'block';
    }
    updateLoadingStep('analyzing');

    const mode = modeSelect?.value || 'detailed';
    const token = localStorage.getItem('studymate-token');
    try {
      const res = await fetch(`/api/v1/features/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ fileRecordId, mode }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        const errDetail = err.detail || 'Generation failed';
        hide(loadingScreen);
        show(output, 'block');
        if (output) {
          output.hidden = false;
          output.style.display = 'block';
        }
        output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error);font-weight:600;font-size:1.1rem;">${errDetail}</p></div>`;
        showToast(errDetail, 'error');
        if (fileStatus) {
          fileStatus.textContent = 'Generation failed';
          fileStatus.className = 'file-status error';
        }
        generateBtn.disabled = false;
        generateBtn.textContent = originalBtnText || 'Generate Notes';
        isGenerating = false;
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      currentContent = '';

      let stepOrder = ['analyzing', 'extracting', 'generating', 'formatting', 'finalizing'];
      let stepIndex = 0;
      let stepTimer = setInterval(() => {
        if (stepIndex < stepOrder.length - 1) {
          stepIndex++;
          updateLoadingStep(stepOrder[stepIndex]);
        }
      }, 3000);

      let buffer = '';
      let isDone = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const trimmed = line.trimRight();
          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6);
            if (data === '[DONE]') {
              isDone = true;
              break;
            }
            if (data.startsWith('[ERROR]')) {
              isDone = true;
              clearInterval(stepTimer);
              const errMsg = data.slice(7);
              hide(loadingScreen);
              show(output, 'block');
              if (output) {
                output.hidden = false;
                output.style.display = 'block';
              }
              output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error);font-weight:600;font-size:1.1rem;">${errMsg}</p></div>`;
              showToast(errMsg, 'error');
              if (fileStatus) {
                fileStatus.textContent = 'Generation failed';
                fileStatus.className = 'file-status error';
              }
              generateBtn.disabled = false;
              generateBtn.textContent = originalBtnText || 'Generate Notes';
              isGenerating = false;
              break;
            }
            if (!currentContent) {
              updateLoadingStep('generating');
              if (fileStatus) fileStatus.textContent = 'Generating study notes...';
            }
            // New protocol: each data payload is a JSON-encoded string chunk
            // (preserves exact newlines). Fall back to legacy line-joining.
            if (data.startsWith('"')) {
              try {
                currentContent += JSON.parse(data);
              } catch {
                currentContent += (currentContent ? '\n' : '') + data;
              }
            } else {
              currentContent += (currentContent ? '\n' : '') + data;
            }
          }
        }
        if (isDone) break;
      }
      clearInterval(stepTimer);

      if ((isDone && !output.querySelector('.card p')) || currentContent) {
        hide(loadingScreen);
        show(output, 'block');
        if (output) {
          output.hidden = false;
          output.style.display = 'block';
        }
        if (notesContent) {
          notesContent.innerHTML = renderNotesHtml(currentContent);
          typesetMath(notesContent);
        }
        show(downloadBtn, 'inline-block');
        show(relatedActions, 'block');
        if (fileStatus) {
          fileStatus.textContent = 'Notes generated successfully';
          fileStatus.className = 'file-status success';
        }
        showToast('Notes generated successfully!', 'success');
      }
    } catch (err) {
      hide(loadingScreen);
      show(output, 'block');
      if (output) {
        output.hidden = false;
        output.style.display = 'block';
      }
      const errMsg = err.message || 'Generation error';
      output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error);font-weight:600;font-size:1.1rem;">${errMsg}</p></div>`;
      showToast(errMsg, 'error');
      if (fileStatus) {
        fileStatus.textContent = 'Generation failed';
        fileStatus.className = 'file-status error';
      }
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = originalBtnText || 'Generate Notes';
      isGenerating = false;
    }
  });

  downloadBtn?.addEventListener('click', exportNotesPdf);
}

function updateLoadingStep(stepId) {
  document.querySelectorAll('.loading-step').forEach(el => {
    if (el.dataset.step === stepId) {
      el.classList.add('active');
      el.classList.remove('done');
    } else if (el.classList.contains('active')) {
      el.classList.remove('active');
      el.classList.add('done');
    }
  });
}

async function loadHistoryNotes(fileId) {
  const output = document.getElementById('feature-output');
  const downloadBtn = document.getElementById('download-pdf');
  const notesContent = document.getElementById('notes-content');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Not found');
    const data = await res.json();
    if (data && data.output) {
      show(output, 'block');
      notesContent.innerHTML = renderNotesHtml(data.output.outputText);
      typesetMath(notesContent);
      show(downloadBtn, 'inline-block');
      downloadBtn?.addEventListener('click', exportNotesPdf);
      StudyMateUpload.setFromHistory(fileId);
    }
  } catch {
    show(output, 'block');
    output.innerHTML = '<p style="color:var(--color-error)">Failed to load history</p>';
  }
}
