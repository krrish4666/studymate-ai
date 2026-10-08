import { showToast, hide, show, errorStateHtml } from '../utils.js?v=8';
import { renderDocHtml, typesetMath, exportDocPdf, decodeStreamChunk } from '../doc-renderer.js?v=1';
import { enterCompletedState } from './generation-state.js?v=8';

const exportNotesPdf = () => exportDocPdf('notes-content', 'Study Notes');

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
  let renderTimer = null;

  const cancelStreamingRender = () => {
    if (renderTimer !== null) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
  };

  const renderStreamingContent = (force = false) => {
    if (!notesContent || !currentContent) return;
    if (!force && renderTimer !== null) return;

    if (force) cancelStreamingRender();
    if (force) {
      notesContent.innerHTML = renderDocHtml(currentContent);
      typesetMath(notesContent);
      return;
    }
    renderTimer = setTimeout(() => {
      renderTimer = null;
      if (!isGenerating) return;
      notesContent.innerHTML = renderDocHtml(currentContent);
      typesetMath(notesContent);
    }, 120);
  };

  const showStreamingOutput = () => {
    show(output, 'block');
    if (output) {
      output.hidden = false;
      output.style.display = 'block';
    }
    hide(loadingScreen);
  };

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
        output.innerHTML = errorStateHtml("We couldn't generate your notes", errDetail);
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
              cancelStreamingRender();
              const errMsg = data.slice(7);
              hide(loadingScreen);
              show(output, 'block');
              if (output) {
                output.hidden = false;
                output.style.display = 'block';
              }
              output.innerHTML = errorStateHtml("We couldn't generate your notes", errMsg);
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
              showStreamingOutput();
            }
            currentContent += decodeStreamChunk(data, !!currentContent);
            renderStreamingContent();
          }
        }
        if (isDone) break;
      }
      clearInterval(stepTimer);
      if (!hadError) renderStreamingContent(true);

      if (!hadError && ((isDone && !output.querySelector('.card p')) || currentContent)) {
        hide(loadingScreen);
        show(output, 'block');
        if (output) {
          output.hidden = false;
          output.style.display = 'block';
        }
        show(downloadBtn, 'inline-block');
        show(relatedActions, 'block');
        if (fileStatus) {
          fileStatus.textContent = 'Notes generated successfully';
          fileStatus.className = 'file-status success';
        }
        showToast('Notes generated successfully!', 'success');
        enterCompletedState();
      }
    } catch (err) {
      cancelStreamingRender();
      hide(loadingScreen);
      show(output, 'block');
      if (output) {
        output.hidden = false;
        output.style.display = 'block';
      }
      const errMsg = err.message || 'Generation error';
      output.innerHTML = errorStateHtml("We couldn't generate your notes", errMsg);
      showToast(errMsg, 'error');
      if (fileStatus) {
        fileStatus.textContent = 'Generation failed';
        fileStatus.className = 'file-status error';
      }
    } finally {
      cancelStreamingRender();
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
      notesContent.innerHTML = renderDocHtml(data.output.outputText);
      typesetMath(notesContent);
      show(downloadBtn, 'inline-block');
      downloadBtn?.addEventListener('click', exportNotesPdf);
      StudyMateUpload.setFromHistory(fileId);
      enterCompletedState(true);
    }
  } catch {
    show(output, 'block');
    output.innerHTML = '<p style="color:var(--color-error)">Failed to load history</p>';
  }
}
