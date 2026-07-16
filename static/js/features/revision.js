import { showToast, markdownToHtml, $, hide, show } from '../utils.js';

export async function initRevision() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryRevision(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');
  const loadingScreen = document.getElementById('loading-screen');
  const revisionContent = document.getElementById('revision-content');

  let currentContent = '';
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

    const token = localStorage.getItem('studymate-token');
    const res = await fetch(`/api/v1/features/revision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ fileRecordId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
      hide(loadingScreen);
      show(output);
      output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error)">${err.detail}</p></div>`;
      generateBtn.disabled = false;
      isGenerating = false;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    currentContent = '';

    let stepOrder = ['analyzing', 'generating', 'formatting', 'finalizing'];
    let stepIndex = 0;
    let stepTimer = setInterval(() => {
      if (stepIndex < stepOrder.length - 1) {
        stepIndex++;
        updateLoadingStep(stepOrder[stepIndex]);
      }
    }, 3000);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            clearInterval(stepTimer);
            hide(loadingScreen);
            show(output);
            revisionContent.innerHTML = markdownToHtml(currentContent);
            show(downloadBtn);
            continue;
          }
          if (data.startsWith('[ERROR]')) {
            clearInterval(stepTimer);
            hide(loadingScreen);
            show(output);
            output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error)">${data.slice(7)}</p></div>`;
            generateBtn.disabled = false;
            isGenerating = false;
            continue;
          }
          currentContent += data;
        }
      }
    }
    generateBtn.disabled = false;
    isGenerating = false;
  });

  downloadBtn?.addEventListener('click', async () => {
    if (!currentContent) return;
    const token = localStorage.getItem('studymate-token');
    const res = await fetch('/api/v1/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ feature: 'revision', outputText: currentContent }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'revision.pdf'; a.click();
      URL.revokeObjectURL(url);
    }
  });
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

async function loadHistoryRevision(fileId) {
  const output = document.getElementById('feature-output');
  const downloadBtn = document.getElementById('download-pdf');
  const revisionContent = document.getElementById('revision-content');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await res.json();
    if (data.output?.outputText) {
      show(output);
      revisionContent.innerHTML = markdownToHtml(data.output.outputText);
      show(downloadBtn);
      StudyMateUpload.setFromHistory(fileId);
    }
  } catch {}
}
