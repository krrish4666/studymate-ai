import { apiPost } from '../api.js';
import { showToast, $, hide, show } from '../utils.js';

export async function initFlashcards() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryFlashcards(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const loadingScreen = document.getElementById('loading-screen');
  const downloadBtn = document.getElementById('download-pdf');

  let flashcards = [];
  let currentIndex = 0;
  let isFlipped = false;
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
        show(output);
        output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error)">${err.detail}</p></div>`;
        return;
      }
      const data = await res.json();
      flashcards = data.flashcards || [];
      if (flashcards.length === 0) {
        hide(loadingScreen);
        show(output);
        output.innerHTML = '<p style="color:var(--color-muted-text);text-align:center;padding:40px;">No flashcards generated</p>';
        return;
      }
      currentIndex = 0;
      isFlipped = false;
      hide(loadingScreen);
      show(output);
      show(downloadBtn);
      renderFlashcard();
    } catch (err) {
      hide(loadingScreen);
      show(output);
      output.innerHTML = `<p style="color:var(--color-error)">${err.message}</p>`;
    } finally {
      generateBtn.disabled = false;
      isGenerating = false;
    }
  });

  function renderFlashcard() {
    if (!flashcards.length) return;
    const fc = flashcards[currentIndex];
    if (!fc) return;

    document.getElementById('flashcard-progress').textContent = `Card ${currentIndex + 1} of ${flashcards.length}`;
    document.getElementById('card-question').textContent = fc.question || 'No question';
    document.getElementById('card-answer').textContent = fc.answer || 'No answer';

    const flashcard = document.getElementById('flashcard');
    flashcard.classList.remove('flipped');
    isFlipped = false;

    document.getElementById('prev-card').disabled = currentIndex === 0;
    document.getElementById('next-card').disabled = currentIndex === flashcards.length - 1;
  }

  document.getElementById('flip-card')?.addEventListener('click', () => {
    const flashcard = document.getElementById('flashcard');
    isFlipped = !isFlipped;
    flashcard.classList.toggle('flipped');
  });

  document.getElementById('prev-card')?.addEventListener('click', () => {
    if (currentIndex > 0) {
      currentIndex--;
      renderFlashcard();
    }
  });

  document.getElementById('next-card')?.addEventListener('click', () => {
    if (currentIndex < flashcards.length - 1) {
      currentIndex++;
      renderFlashcard();
    }
  });

  document.getElementById('shuffle-btn')?.addEventListener('click', () => {
    if (flashcards.length < 2) return;
    for (let i = flashcards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [flashcards[i], flashcards[j]] = [flashcards[j], flashcards[i]];
    }
    currentIndex = 0;
    renderFlashcard();
    showToast('Cards shuffled', 'info');
  });

  document.addEventListener('keydown', (e) => {
    if (output.hidden) return;
    if (e.key === 'ArrowLeft' && currentIndex > 0) {
      currentIndex--;
      renderFlashcard();
    }
    if (e.key === 'ArrowRight' && currentIndex < flashcards.length - 1) {
      currentIndex++;
      renderFlashcard();
    }
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      document.getElementById('flip-card')?.click();
    }
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
      let idx = 0;
      const fc = flashcards[idx];
      document.getElementById('flashcard-progress').textContent = `Card 1 of ${flashcards.length}`;
      document.getElementById('card-question').textContent = fc.question || 'No question';
      document.getElementById('card-answer').textContent = fc.answer || 'No answer';
      const flashcard = document.getElementById('flashcard');
      flashcard.classList.remove('flipped');
      document.getElementById('prev-card').disabled = true;
      document.getElementById('next-card').disabled = flashcards.length === 1;
      document.getElementById('flip-card').onclick = () => flashcard.classList.toggle('flipped');
      document.getElementById('prev-card').onclick = () => {
        if (idx > 0) { idx--; showCard(idx); }
      };
      document.getElementById('next-card').onclick = () => {
        if (idx < flashcards.length - 1) { idx++; showCard(idx); }
      };
      function showCard(i) {
        const c = flashcards[i];
        document.getElementById('flashcard-progress').textContent = `Card ${i + 1} of ${flashcards.length}`;
        document.getElementById('card-question').textContent = c.question;
        document.getElementById('card-answer').textContent = c.answer;
        flashcard.classList.remove('flipped');
        document.getElementById('prev-card').disabled = i === 0;
        document.getElementById('next-card').disabled = i === flashcards.length - 1;
      }
    }
  } catch {}
}
