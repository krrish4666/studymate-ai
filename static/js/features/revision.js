import { showToast, hide, show } from '../utils.js?v=7';
import { renderDocHtml, typesetMath, exportDocPdf, decodeStreamChunk } from '../doc-renderer.js?v=1';

const exportRevisionPdf = () => exportDocPdf('revision-content', 'Revision Cheat Sheet');

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
    if (!fileRecordId) {
      showToast('Please select a file first', 'error');
      return;
    }

    isGenerating = true;
    generateBtn.disabled = true;
    const originalBtnText = generateBtn.textContent;
    generateBtn.textContent = 'Generating Sheet...';

    const fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
    if (fileStatus) {
      fileStatus.textContent = 'Generating revision sheet...';
      fileStatus.className = 'file-status info';
    }

    hide(output);
    show(loadingScreen, 'block');
    if (loadingScreen) {
      loadingScreen.hidden = false;
      loadingScreen.style.display = 'block';
    }
    updateLoadingStep('analyzing');

    const showError = (msg) => {
      hide(loadingScreen);
      show(output, 'block');
      if (output) {
        output.hidden = false;
        output.style.display = 'block';
      }
      output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error);font-weight:600;font-size:1.1rem;">${msg}</p></div>`;
      showToast(msg, 'error');
      if (fileStatus) {
        fileStatus.textContent = 'Generation failed';
        fileStatus.className = 'file-status error';
      }
    };

    const token = localStorage.getItem('studymate-token');
    try {
      const res = await fetch(`/api/v1/features/revision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ fileRecordId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        showError(err.detail || 'Generation failed');
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

      let buffer = '';
      let isDone = false;
      let hadError = false;
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
              hadError = true;
              clearInterval(stepTimer);
              showError(data.slice(7));
              break;
            }
            if (!currentContent) {
              updateLoadingStep('generating');
              if (fileStatus) fileStatus.textContent = 'Generating revision sheet...';
            }
            currentContent += decodeStreamChunk(data, !!currentContent);
          }
        }
        if (isDone) break;
      }
      clearInterval(stepTimer);

      if (!hadError && currentContent) {
        hide(loadingScreen);
        show(output, 'block');
        if (output) {
          output.hidden = false;
          output.style.display = 'block';
        }
        if (revisionContent) {
          revisionContent.innerHTML = renderDocHtml(currentContent);
          typesetMath(revisionContent);
        }
        show(downloadBtn, 'inline-block');
        if (fileStatus) {
          fileStatus.textContent = 'Revision sheet generated successfully';
          fileStatus.className = 'file-status success';
        }
        showToast('Revision sheet generated successfully!', 'success');
      } else if (!hadError && !currentContent) {
        showError('No content generated');
      }
    } catch (err) {
      showError(err.message || 'Generation error');
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = originalBtnText || 'Generate Revision Sheet';
      isGenerating = false;
    }
  });

  downloadBtn?.addEventListener('click', exportRevisionPdf);
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
    if (!res.ok) throw new Error('Not found');
    const data = await res.json();
    if (data.output?.outputText) {
      show(output, 'block');
      revisionContent.innerHTML = renderDocHtml(data.output.outputText);
      typesetMath(revisionContent);
      show(downloadBtn, 'inline-block');
      downloadBtn?.addEventListener('click', exportRevisionPdf);
      StudyMateUpload.setFromHistory(fileId);
    }
  } catch {
    show(output, 'block');
    output.innerHTML = '<p style="color:var(--color-error)">Failed to load history</p>';
  }
}
