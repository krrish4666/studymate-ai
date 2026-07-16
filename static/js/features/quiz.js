import { apiPost } from '../api.js';
import { showToast, $, hide, show } from '../utils.js?v=7';

export async function initQuiz() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryQuiz(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const difficulty = document.getElementById('quiz-difficulty');
  const count = document.getElementById('quiz-count');
  const loadingScreen = document.getElementById('loading-screen');
  const downloadBtn = document.getElementById('download-pdf');

  let questions = [];
  let answers = {};
  let submitted = false;
  let isGenerating = false;

  StudyMateUpload.init();

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
    generateBtn.textContent = 'Generating Quiz...';

    const fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
    if (fileStatus) {
      fileStatus.textContent = 'Generating quiz questions...';
      fileStatus.className = 'file-status info';
    }

    hide(output);
    show(loadingScreen, 'block');
    if (loadingScreen) {
      loadingScreen.hidden = false;
      loadingScreen.style.display = 'block';
    }
    submitted = false;
    answers = {};

    try {
      const res = await apiPost('/features/quiz', {
        fileRecordId,
        difficulty: difficulty?.value || 'medium',
        count: parseInt(count?.value || '10'),
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
        generateBtn.textContent = originalBtnText || 'Generate Quiz';
        isGenerating = false;
        return;
      }
      const data = await res.json();
      questions = data.questions || [];
      if (questions.length === 0) {
        hide(loadingScreen);
        show(output, 'block');
        if (output) {
          output.hidden = false;
          output.style.display = 'block';
        }
        output.innerHTML = '<p style="color:var(--color-muted-text);text-align:center;padding:40px;">No questions generated</p>';
        if (fileStatus) {
          fileStatus.textContent = 'No questions generated';
          fileStatus.className = 'file-status error';
        }
        generateBtn.disabled = false;
        generateBtn.textContent = originalBtnText || 'Generate Quiz';
        isGenerating = false;
        return;
      }
      hide(loadingScreen);
      show(output, 'block');
      if (output) {
        output.hidden = false;
        output.style.display = 'block';
      }
      document.getElementById('quiz-question-count').textContent = `${questions.length} questions`;
      hide(downloadBtn);
      if (fileStatus) {
        fileStatus.textContent = 'Quiz generated successfully';
        fileStatus.className = 'file-status success';
      }
      showToast('Quiz generated successfully!', 'success');
      renderQuiz();
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
      generateBtn.textContent = originalBtnText || 'Generate Quiz';
      isGenerating = false;
    }
  });

  function renderQuiz() {
    const labels = ['A', 'B', 'C', 'D'];
    const container = document.getElementById('quiz-questions');
    const resultsDiv = document.getElementById('quiz-results');
    resultsDiv.hidden = true;

    container.innerHTML = '';
    questions.forEach((q, qi) => {
      const div = document.createElement('div');
      div.className = 'quiz-question';
      const type = q.type || 'mcq';
      const typeLabel = { mcq: 'Multiple Choice', 'true-false': 'True / False', 'fill-blank': 'Fill in the Blank', 'short-answer': 'Short Answer' };
      div.innerHTML = `
        <div class="quiz-question-type">${typeLabel[type] || 'Multiple Choice'}</div>
        <div class="quiz-question-text">${qi + 1}. ${q.question}</div>
        <div class="quiz-options" data-q="${qi}">
          ${q.options.map((opt, oi) => `
            <button class="quiz-option" data-q="${qi}" data-opt="${oi}">${q.options.length > 2 ? labels[oi] + '. ' : ''}${opt}</button>
          `).join('')}
        </div>
      `;
      container.appendChild(div);
    });

    container.querySelectorAll('.quiz-option').forEach(btn => {
      btn.addEventListener('click', () => {
        if (submitted) return;
        const qi = parseInt(btn.dataset.q);
        container.querySelectorAll(`[data-q="${qi}"] .quiz-option`).forEach(b => b.classList.remove('selected'));
        document.querySelectorAll(`.quiz-options[data-q="${qi}"] .quiz-option`).forEach(b => b.classList.remove('selected'));
        btn.closest('.quiz-options').querySelectorAll('.quiz-option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        answers[qi] = parseInt(btn.dataset.opt);
      });
    });

    document.getElementById('submit-quiz').onclick = submitQuiz;
    document.getElementById('download-pdf').onclick = downloadPdf;
  }

  function submitQuiz() {
    if (Object.keys(answers).length === 0) {
      showToast('Please answer at least one question', 'error');
      return;
    }
    submitted = true;
    let correct = 0;

    document.querySelectorAll('.quiz-question').forEach((qDiv, qi) => {
      const q = questions[qi];
      if (!q) return;
      const opts = qDiv.querySelectorAll('.quiz-option');
      opts.forEach((btn) => {
        btn.classList.add('disabled');
        btn.classList.remove('selected');
        const oi = parseInt(btn.dataset.opt);
        if (oi === q.correctAnswer) btn.classList.add('correct');
        if (answers[qi] === oi && oi !== q.correctAnswer) btn.classList.add('incorrect');
      });
      if (answers[qi] === q.correctAnswer) correct++;

      if (q.explanation) {
        const expDiv = document.createElement('div');
        expDiv.className = 'quiz-explanation';
        expDiv.textContent = '💡 ' + q.explanation;
        qDiv.appendChild(expDiv);
      }
    });

    document.getElementById('submit-quiz').disabled = true;
    const resultsDiv = document.getElementById('quiz-results');
    resultsDiv.hidden = false;

    const pct = Math.round((correct / questions.length) * 100);
    let message = 'Keep practicing!';
    if (pct >= 90) message = 'Excellent work! You mastered this topic!';
    else if (pct >= 70) message = 'Good job! Review the ones you missed.';
    else if (pct >= 50) message = 'Not bad, but needs more review.';

    resultsDiv.innerHTML = `
      <div class="quiz-result-card">
        <div class="quiz-score">${correct}/${questions.length}</div>
        <div class="quiz-percentage">${pct}% Correct</div>
        <div class="quiz-message">${message}</div>
      </div>
    `;
    show(document.getElementById('download-pdf'));
  }

  async function downloadPdf() {
    if (!questions.length) return;
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
      show(output);
      StudyMateUpload.setFromHistory(fileId);
      document.getElementById('quiz-question-count').textContent = `${questions.length} questions`;
      const container = document.getElementById('quiz-questions');
      const labels = ['A', 'B', 'C', 'D'];
      questions.forEach((q, qi) => {
        const div = document.createElement('div');
        div.className = 'quiz-question';
        const type = q.type || 'mcq';
        const typeLabel = { mcq: 'Multiple Choice', 'true-false': 'True / False', 'fill-blank': 'Fill in the Blank', 'short-answer': 'Short Answer' };
        div.innerHTML = `
          <div class="quiz-question-type">${typeLabel[type] || 'Multiple Choice'}</div>
          <div class="quiz-question-text">${qi + 1}. ${q.question}</div>
          <div class="quiz-options" data-q="${qi}">
            ${q.options.map((opt, oi) => `
              <button class="quiz-option correct disabled" data-q="${qi}" data-opt="${oi}">${q.options.length > 2 ? labels[oi] + '. ' : ''}${opt}</button>
            `).join('')}
          </div>
          ${q.explanation ? `<div class="quiz-explanation">💡 ${q.explanation}</div>` : ''}
        `;
        container.appendChild(div);
      });
      document.getElementById('submit-quiz').disabled = true;
      document.getElementById('submit-quiz').textContent = 'Viewing History';
      const resultsDiv = document.getElementById('quiz-results');
      resultsDiv.hidden = false;
      const correct = questions.filter((q, i) => q.correctAnswer === 0).length;
      resultsDiv.innerHTML = `
        <div class="quiz-result-card">
          <div class="quiz-question-text" style="margin-bottom:0;">Historical session — answers shown</div>
        </div>
      `;
    }
  } catch {}
}
