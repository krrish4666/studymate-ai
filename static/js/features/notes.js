import { apiPost, apiGet } from '../api.js';
import { initUpload } from '../upload.js';
import { getAuthHeaders } from '../api.js';
import { showToast, markdownToHtml, $ } from '../utils.js';

export async function initNotes() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryNotes(fileId);

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progress = document.getElementById('upload-progress');
  const output = document.getElementById('feature-output');
  const modeSelect = document.getElementById('notes-mode');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');

  let currentFileRecordId = null;
  let currentContent = '';

  initUpload(dropzone, fileInput, progress, 'notes');

  document.addEventListener('upload-complete', async (e) => {
    currentFileRecordId = e.detail.fileRecordId;
    generateBtn.hidden = false;
  });

  generateBtn?.addEventListener('click', async () => {
    if (!currentFileRecordId) return;
    generateBtn.disabled = true;
    output.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Generating notes...</p></div>';

    const mode = modeSelect?.value || 'detailed';
    const token = localStorage.getItem('studymate-token');
    const res = await fetch(`/api/v1/features/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ fileRecordId: currentFileRecordId, mode }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
      output.innerHTML = `<p style="color:var(--color-error)">${err.detail}</p>`;
      generateBtn.disabled = false;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    output.innerHTML = '<div class="streaming-content"></div>';
    const contentEl = output.querySelector('.streaming-content');
    currentContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            downloadBtn.hidden = false;
            continue;
          }
          currentContent += data;
          contentEl.innerHTML = markdownToHtml(currentContent);
          contentEl.scrollTop = contentEl.scrollHeight;
        }
      }
    }
    generateBtn.disabled = false;
  });

  downloadBtn?.addEventListener('click', async () => {
    if (!currentContent) return;
    const token = localStorage.getItem('studymate-token');
    const res = await fetch('/api/v1/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ feature: 'notes', outputText: currentContent }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'notes.pdf'; a.click();
      URL.revokeObjectURL(url);
    }
  });
}

async function loadHistoryNotes(fileId) {
  const output = document.getElementById('feature-output');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Not found');
    const data = await res.json();
    if (data.output?.outputText) {
      output.innerHTML = `<div class="streaming-content">${markdownToHtml(data.output.outputText)}</div>`;
      document.getElementById('download-pdf').hidden = false;
    }
  } catch {
    output.innerHTML = '<p style="color:var(--color-error)">Failed to load history</p>';
  }
}
