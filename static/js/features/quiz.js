import { apiPost } from '../api.js';
import { initUpload } from '../upload.js';
import { showToast, $ } from '../utils.js';

export async function initQuiz() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryQuiz(fileId);

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progress = document.getElementById('upload-progress');
  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const difficulty = document.getElementById('quiz-difficulty');
  const count = document.getElementById('quiz-count');

  let currentFileRecordId = null;
  let questions = [];
  let answers = {};
  let submitted = false;

  initUpload(dropzone, fileInput, progress, 'quiz');

  generateBtn?.addEventListener('click', async () => {
    if (!currentFileRecordId) return;
    generateBtn.disabled = true;
    output.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Generating quiz...</p></div>';
    submitted = false;
    answers = {};

    try {
      const res = await apiPost('/features/quiz', {
        fileRecordId: currentFileRecordId,
        difficulty: difficulty?.value || 'medium',
        count: parseInt(count?.value || '10'),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        output.innerHTML = `<p style="color:var(--color-error)">${err.detail}</p>`;
        return;
      }
      const data = await res.json();
      questions = data.questions || [];
      if (questions.length === 0) {
        output.innerHTML = '<p style="color:var(--color-muted-text)">No questions generated</p>';
        return;
      }
      renderQuiz();
    } catch (err) {
      output.innerHTML = `<p style="color:var(--color-error)">${err.message}</p>`;
    } finally {
      generateBtn.disabled = false;
    }
  });

  function renderQuiz() {
    const labels = ['A', 'B', 'C', 'D'];
    output.innerHTML = `
      <h3 style="margin-bottom:16px;">Quiz (${questions.length} questions)</h3>
      <div id="quiz-questions"></div>
      <div style="display:flex;gap:12px;margin-top:20px;">
        <button class="btn btn-primary" id="submit-quiz">Submit Answers</button>
        <button class="btn btn-primary btn-sm" id="download-quiz-pdf">Download PDF</button>
      </div>
      <div id="quiz-results" style="margin-top:20px;"></div>
    `;

    const container = document.getElementById('quiz-questions');
    questions.forEach((q, qi) => {
      const div = document.createElement('div');
      div.style.marginBottom = '24px';
      div.innerHTML = `
        <p style="font-weight:600;margin-bottom:8px;">${qi + 1}. ${q.question}</p>
        <div style="display:flex;flex-direction:column;gap:8px;">
          ${q.options.map((opt, oi) => `
            <button class="quiz-option" data-q="${qi}" data-opt="${oi}">${labels[oi]}. ${opt}</button>
          `).join('')}
        </div>
      `;
      container.appendChild(div);
    });

    container.querySelectorAll('.quiz-option').forEach(btn => {
      btn.addEventListener('click', () => {
        if (submitted) return;
        const qi = parseInt(btn.dataset.q);
        container.querySelectorAll(`[data-q="${qi}"]`).forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        answers[qi] = parseInt(btn.dataset.opt);
      });
    });

    document.getElementById('submit-quiz').addEventListener('click', submitQuiz);
    document.getElementById('download-quiz-pdf').addEventListener('click', downloadPdf);
  }

  function submitQuiz() {
    submitted = true;
    let correct = 0;
    questions.forEach((q, qi) => {
      const opts = document.querySelectorAll(`[data-q="${qi}"]`);
      opts.forEach((btn, oi) => {
        btn.classList.remove('selected', 'correct', 'incorrect');
        if (oi === q.correctAnswer) btn.classList.add('correct');
        if (answers[qi] === oi && oi !== q.correctAnswer) btn.classList.add('incorrect');
      });
      if (answers[qi] === q.correctAnswer) correct++;
    });

    document.getElementById('quiz-results').innerHTML = `
      <div class="card" style="text-align:center;">
        <p style="font-size:1.5rem;font-weight:700;color:var(--color-primary)">${correct}/${questions.length}</p>
        <p style="color:var(--color-muted-text)">${Math.round((correct / questions.length) * 100)}% Correct</p>
      </div>
    `;
  }

  async function downloadPdf() {
    const token = localStorage.getItem('studymate-token');
    const res = await fetch('/api/v1/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ feature: 'quiz', outputJson: { questions } }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'quiz.pdf'; a.click();
      URL.revokeObjectURL(url);
    }
  }
}

async function loadHistoryQuiz(fileId) {
  const output = document.getElementById('feature-output');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await res.json();
    const questions = data.output?.outputJson?.questions || [];
    if (questions.length > 0) {
      document.getElementById('generate-btn').hidden = true;
      const container = document.getElementById('quiz-questions');
      const labels = ['A', 'B', 'C', 'D'];
      questions.forEach((q, qi) => {
        const div = document.createElement('div');
        div.style.marginBottom = '24px';
        div.innerHTML = `
          <p style="font-weight:600;margin-bottom:8px;">${qi + 1}. ${q.question}</p>
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${q.options.map((opt, oi) => `
              <button class="quiz-option correct" data-q="${qi}" data-opt="${oi}" ${oi === q.correctAnswer ? 'style="border-color:var(--color-success)"' : ''}>${labels[oi]}. ${opt}</button>
            `).join('')}
          </div>
        `;
        container.appendChild(div);
      });
    }
  } catch {}
}
