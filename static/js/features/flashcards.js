import { apiPost } from '../api.js';
import { showToast, hide, show } from '../utils.js';

export async function initFlashcards() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryFlashcards(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const loadingScreen = document.getElementById('loading-screen');
  const downloadBtn = document.getElementById('download-pdf');

  let flashcards = [];
  let isGenerating = false;

  StudyMateUpload.init();

  generateBtn?.addEventListener('click', async () => {
    if (isGenerating) return;
    const fileRecordId = StudyMateUpload.getCurrentFileId();
    if (!fileRecordId) return;

    isGenerating = true;
    generateBtn.disabled = true;
    hide(output);
    show(loadingScreen);

    try {
      const res = await apiPost('/features/flashcards', { fileRecordId });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        hide(loadingScreen);
        showToast(err.detail || 'Generation failed', 'error');
        return;
      }
      const data = await res.json();
      flashcards = data.flashcards || [];
      if (flashcards.length === 0) {
        hide(loadingScreen);
        showToast('No flashcards could be generated from this file', 'warning');
        return;
      }
      hide(loadingScreen);
      show(output);
      show(downloadBtn);
      renderFlashcardGrid();
    } catch (err) {
      hide(loadingScreen);
      showToast(err.message || 'An unexpected error occurred', 'error');
    } finally {
      generateBtn.disabled = false;
      isGenerating = false;
    }
  });

  function renderFlashcardGrid() {
    const grid = document.getElementById('flashcard-grid');
    grid.innerHTML = '';
    const fragment = document.createDocumentFragment();

    flashcards.forEach((fc, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.style.animationDelay = `${i * 50}ms`;
      card.innerHTML = `
        <div class="flashcard-inner">
          <div class="flashcard-front">
            <span class="card-label">Question</span>
            <p class="card-text">${fc.question || 'No question'}</p>
          </div>
          <div class="flashcard-back">
            <span class="card-label">Answer</span>
            <p class="card-text">${fc.answer || 'No answer'}</p>
          </div>
        </div>
      `;
      card.addEventListener('click', () => {
        card.classList.toggle('flipped');
      });
      fragment.appendChild(card);
    });

    grid.appendChild(fragment);
  }

  document.getElementById('shuffle-btn')?.addEventListener('click', () => {
    if (flashcards.length < 2) return;
    for (let i = flashcards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [flashcards[i], flashcards[j]] = [flashcards[j], flashcards[i]];
    }
    renderFlashcardGrid();
    showToast('Cards shuffled', 'info');
  });

  downloadBtn?.addEventListener('click', async () => {
    if (!flashcards.length) return;
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
  });
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
      show(output);
      StudyMateUpload.setFromHistory(fileId);
      show(document.getElementById('download-pdf'));
      const grid = document.getElementById('flashcard-grid');
      grid.innerHTML = '';
      const fragment = document.createDocumentFragment();

      flashcards.forEach((fc, i) => {
        const card = document.createElement('div');
        card.className = 'flashcard';
        card.style.animationDelay = `${i * 50}ms`;
        card.innerHTML = `
          <div class="flashcard-inner">
            <div class="flashcard-front">
              <span class="card-label">Question</span>
              <p class="card-text">${fc.question || 'No question'}</p>
            </div>
            <div class="flashcard-back">
              <span class="card-label">Answer</span>
              <p class="card-text">${fc.answer || 'No answer'}</p>
            </div>
          </div>
        `;
        card.addEventListener('click', () => {
          card.classList.toggle('flipped');
        });
        fragment.appendChild(card);
      });

      grid.appendChild(fragment);

      document.getElementById('download-pdf')?.addEventListener('click', async () => {
        if (!flashcards.length) return;
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
      });
    }
  } catch {}
}
