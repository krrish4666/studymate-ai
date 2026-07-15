import { apiPost } from '../api.js';
import { initUpload } from '../upload.js';
import { showToast, $, $$ } from '../utils.js';

export async function initFlashcards() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryFlashcards(fileId);

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progress = document.getElementById('upload-progress');
  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');

  let currentFileRecordId = null;
  let flashcards = [];
  let currentIndex = 0;

  initUpload(dropzone, fileInput, progress, 'flashcards');

  generateBtn?.addEventListener('click', async () => {
    if (!currentFileRecordId) return;
    generateBtn.disabled = true;
    output.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Generating flashcards...</p></div>';

    try {
      const res = await apiPost('/features/flashcards', { fileRecordId: currentFileRecordId });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        output.innerHTML = `<p style="color:var(--color-error)">${err.detail}</p>`;
        return;
      }
      const data = await res.json();
      flashcards = data.flashcards || [];
      if (flashcards.length === 0) {
        output.innerHTML = '<p style="color:var(--color-muted-text)">No flashcards generated</p>';
        return;
      }
      currentIndex = 0;
      renderFlashcard();
    } catch (err) {
      output.innerHTML = `<p style="color:var(--color-error)">${err.message}</p>`;
    } finally {
      generateBtn.disabled = false;
    }
  });

  function renderFlashcard() {
    const fc = flashcards[currentIndex];
    output.innerHTML = `
      <div style="text-align:center;margin-bottom:16px;">
        <span style="color:var(--color-muted-text);font-size:0.85rem;">Card ${currentIndex + 1} of ${flashcards.length}</span>
      </div>
      <div class="flashcard" onclick="this.classList.toggle('flipped')">
        <div class="flashcard-inner">
          <div class="flashcard-front">
            <span class="label">Question</span>
            <p style="font-size:1.1rem;">${fc.question}</p>
          </div>
          <div class="flashcard-back">
            <span class="label">Answer</span>
            <p style="font-size:1.1rem;">${fc.answer}</p>
          </div>
        </div>
      </div>
      <div style="display:flex;justify-content:center;gap:12px;margin-top:20px;">
        <button class="btn btn-secondary btn-sm" id="prev-card" ${currentIndex === 0 ? 'disabled' : ''}>Previous</button>
        <button class="btn btn-secondary btn-sm" id="next-card" ${currentIndex === flashcards.length - 1 ? 'disabled' : ''}>Next</button>
      </div>
      <div style="display:flex;justify-content:center;gap:12px;margin-top:12px;">
        <button class="btn btn-primary btn-sm" id="download-flashcards-pdf">Download PDF</button>
      </div>
    `;

    document.getElementById('prev-card')?.addEventListener('click', () => {
      if (currentIndex > 0) { currentIndex--; renderFlashcard(); }
    });
    document.getElementById('next-card')?.addEventListener('click', () => {
      if (currentIndex < flashcards.length - 1) { currentIndex++; renderFlashcard(); }
    });
    document.getElementById('download-flashcards-pdf')?.addEventListener('click', downloadPdf);
  }

  async function downloadPdf() {
    const token = localStorage.getItem('studymate-token');
    const res = await fetch('/api/v1/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ feature: 'flashcards', outputJson: { flashcards } }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'flashcards.pdf'; a.click();
      URL.revokeObjectURL(url);
    }
  }
}

async function loadHistoryFlashcards(fileId) {
  const output = document.getElementById('feature-output');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await res.json();
    const flashcards = data.output?.outputJson?.flashcards || [];
    if (flashcards.length > 0) {
      let idx = 0;
      const fc = flashcards[idx];
      output.innerHTML = `
        <div style="text-align:center;margin-bottom:16px;">
          <span style="color:var(--color-muted-text);font-size:0.85rem;">Card 1 of ${flashcards.length}</span>
        </div>
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
          <div class="flashcard-inner">
            <div class="flashcard-front">
              <span class="label">Question</span>
              <p style="font-size:1.1rem;">${fc.question}</p>
            </div>
            <div class="flashcard-back">
              <span class="label">Answer</span>
              <p style="font-size:1.1rem;">${fc.answer}</p>
            </div>
          </div>
        </div>
        <div style="display:flex;justify-content:center;gap:12px;margin-top:20px;">
          <button class="btn btn-secondary btn-sm" id="prev-card2" disabled>Previous</button>
          <button class="btn btn-secondary btn-sm" id="next-card2" ${flashcards.length === 1 ? 'disabled' : ''}>Next</button>
        </div>
      `;
    }
  } catch {}
}
