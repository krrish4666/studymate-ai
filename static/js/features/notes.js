import { apiPost, apiGet } from '../api.js';
import { showToast, markdownToHtml, $, hide, show } from '../utils.js?v=7';

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
            currentContent += (currentContent ? '\n' : '') + data;
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
        if (notesContent) notesContent.innerHTML = markdownToHtml(currentContent);
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
      notesContent.innerHTML = markdownToHtml(data.output.outputText);
      show(downloadBtn, 'inline-block');
      StudyMateUpload.setFromHistory(fileId);
    }
  } catch {
    show(output, 'block');
    output.innerHTML = '<p style="color:var(--color-error)">Failed to load history</p>';
  }
}
