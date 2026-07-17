import { apiPost } from '../api.js';
import { showToast, hide, show } from '../utils.js?v=7';

export async function initMindmap() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryMindmap(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');
  const loadingScreen = document.getElementById('loading-screen');
  const resetViewBtn = document.getElementById('reset-view-btn');

  let currentMindmap = null;
  let isGenerating = false;
  let zoom = 1;

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
    generateBtn.textContent = 'Generating Mindmap...';

    const fileStatus = document.getElementById('file-status') || (document.getElementById('file-info') && document.getElementById('file-info').querySelector('.file-status'));
    if (fileStatus) {
      fileStatus.textContent = 'Generating mind map structure...';
      fileStatus.className = 'file-status info';
    }

    hide(output);
    show(loadingScreen, 'block');
    if (loadingScreen) {
      loadingScreen.hidden = false;
      loadingScreen.style.display = 'block';
    }

    try {
      const res = await apiPost('/features/mindmap', { fileRecordId });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        const errDetail = err.detail || 'Generation failed';
        hide(loadingScreen);
        showToast(errDetail, 'error');
        if (fileStatus) {
          fileStatus.textContent = 'Generation failed';
          fileStatus.className = 'file-status error';
        }
        generateBtn.disabled = false;
        generateBtn.textContent = originalBtnText || 'Generate Mindmap';
        isGenerating = false;
        return;
      }
      const data = await res.json();
      currentMindmap = data.mindmap;
      if (!currentMindmap) {
        hide(loadingScreen);
        showToast('No mindmap could be generated from this file', 'warning');
        if (fileStatus) {
          fileStatus.textContent = 'No mindmap generated';
          fileStatus.className = 'file-status error';
        }
        generateBtn.disabled = false;
        generateBtn.textContent = originalBtnText || 'Generate Mindmap';
        isGenerating = false;
        return;
      }
      hide(loadingScreen);
      show(output, 'block');
      if (output) {
        output.hidden = false;
        output.style.display = 'block';
      }
      if (fileStatus) {
        fileStatus.textContent = 'Mindmap generated successfully';
        fileStatus.className = 'file-status success';
      }
      showToast('Mindmap generated successfully!', 'success');
      renderMindmap(currentMindmap);
      show(downloadBtn);
    } catch (err) {
      hide(loadingScreen);
      const errMsg = err.message || 'Generation error';
      showToast(errMsg, 'error');
      if (fileStatus) {
        fileStatus.textContent = 'Generation failed';
        fileStatus.className = 'file-status error';
      }
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = originalBtnText || 'Generate Mindmap';
      isGenerating = false;
    }
  });

  downloadBtn?.addEventListener('click', async () => {
    if (!currentMindmap) return;
    const token = localStorage.getItem('studymate-token');
    const res = await fetch('/api/v1/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ feature: 'mindmap', outputJson: { mindmap: currentMindmap } }),
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'mindmap.pdf'; a.click();
      URL.revokeObjectURL(url);
    }
  });

  resetViewBtn?.addEventListener('click', () => {
    const tree = document.getElementById('mindmap-tree');
    const wrapper = document.getElementById('mindmap-wrapper');
    if (tree && wrapper) {
      zoom = 1;
      tree.style.transform = 'scale(1)';
      wrapper.scrollTo({ left: 0, top: 0, behavior: 'smooth' });
    }
  });
}

function renderMindmap(root) {
  if (!root || !root.label) {
    showToast('Invalid mind map data', 'error');
    return;
  }
  let wrapper = document.getElementById('mindmap-wrapper');
  let tree = document.getElementById('mindmap-tree');
  const output = document.getElementById('feature-output');

  if (!tree || !wrapper) {
    const oldCanvas = document.getElementById('mindmap-canvas');
    if (oldCanvas) oldCanvas.remove();
    if (!wrapper) {
      wrapper = document.createElement('div');
      wrapper.id = 'mindmap-wrapper';
      wrapper.className = 'mindmap-wrapper';
      if (output) output.appendChild(wrapper);
    }
    if (!tree) {
      tree = document.createElement('div');
      tree.id = 'mindmap-tree';
      tree.className = 'mm-tree';
      wrapper.appendChild(tree);
    }
  }

  tree.innerHTML = '';
  const rootEl = buildNode(root, 0);
  tree.appendChild(rootEl);

  let isDragging = false;
  let startX, startY, scrollLeft, scrollTop;
  let zoom = 1;

  wrapper.onmousedown = (e) => {
    if (e.target.closest('.mm-node-label')) return;
    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    scrollLeft = wrapper.scrollLeft;
    scrollTop = wrapper.scrollTop;
    wrapper.style.cursor = 'grabbing';
  };

  wrapper.onmousemove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    wrapper.scrollLeft = scrollLeft - dx;
    wrapper.scrollTop = scrollTop - dy;
  };

  wrapper.onmouseup = () => { isDragging = false; wrapper.style.cursor = 'grab'; };
  wrapper.onmouseleave = () => { isDragging = false; wrapper.style.cursor = 'grab'; };

  wrapper.onwheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    zoom = Math.max(0.3, Math.min(2, zoom * delta));
    tree.style.transform = `scale(${zoom})`;
  };

  let touchStartX, touchStartY, touchScrollLeft, touchScrollTop;
  wrapper.ontouchstart = (e) => {
    if (e.touches.length === 1) {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      touchScrollLeft = wrapper.scrollLeft;
      touchScrollTop = wrapper.scrollTop;
    }
  };
  wrapper.ontouchmove = (e) => {
    if (e.touches.length !== 1) return;
    e.preventDefault();
    const dx = e.touches[0].clientX - touchStartX;
    const dy = e.touches[0].clientY - touchStartY;
    wrapper.scrollLeft = touchScrollLeft - dx;
    wrapper.scrollTop = touchScrollTop - dy;
  };

  function centerOnNode(nodeEl) {
    const wrapperRect = wrapper.getBoundingClientRect();
    const nodeRect = nodeEl.getBoundingClientRect();
    const padding = 40;
    const targetX = nodeRect.left - wrapperRect.left - (wrapperRect.width - nodeRect.width) / 2;
    const targetY = nodeRect.top - wrapperRect.top - padding;
    wrapper.scrollBy({ left: targetX, top: targetY, behavior: 'smooth' });
  }

  function handleNodeClick(nodeEl) {
    const wasExpanded = nodeEl.classList.contains('expanded');
    toggleNode(nodeEl);
    if (!wasExpanded) {
      setTimeout(() => centerOnNode(nodeEl), 100);
    }
  }

  rootEl.querySelector('.mm-node-label')?.addEventListener('click', (e) => {
    e.stopPropagation();
    handleNodeClick(rootEl);
  });
}

function buildNode(node, depth) {
  const el = document.createElement('div');
  el.className = 'mm-node';
  el.setAttribute('data-depth', depth);

  const label = document.createElement('div');
  label.className = 'mm-node-label';
  label.textContent = node.label || '';

  if (depth === 0) {
    el.classList.add('expanded');
  }

  el.appendChild(label);

  if (node.children && node.children.length > 0) {
    const childrenContainer = document.createElement('div');
    childrenContainer.className = 'mm-children';

    node.children.forEach((child) => {
      const childEl = buildNode(child, depth + 1);
      const childLabel = childEl.querySelector('.mm-node-label');
      childLabel?.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasExpanded = childEl.classList.contains('expanded');
        toggleNode(childEl);
        if (!wasExpanded) {
          const wrapper = document.getElementById('mindmap-wrapper');
          if (wrapper) {
            setTimeout(() => {
              const wrapperRect = wrapper.getBoundingClientRect();
              const nodeRect = childEl.getBoundingClientRect();
              const targetX = nodeRect.left - wrapperRect.left - (wrapperRect.width - nodeRect.width) / 2;
              const targetY = nodeRect.top - wrapperRect.top - 40;
              wrapper.scrollBy({ left: targetX, top: targetY, behavior: 'smooth' });
            }, 100);
          }
        }
      });
      childrenContainer.appendChild(childEl);
    });

    el.appendChild(childrenContainer);
  }

  return el;
}

function toggleNode(nodeEl) {
  const wasExpanded = nodeEl.classList.contains('expanded');
  if (wasExpanded) {
    nodeEl.classList.remove('expanded');
  } else {
    nodeEl.classList.add('expanded');
  }
}

async function loadHistoryMindmap(fileId) {
  const output = document.getElementById('feature-output');
  const token = localStorage.getItem('studymate-token');
  try {
    const res = await fetch(`/api/v1/history/${fileId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await res.json();
    const mindmap = data.output?.outputJson?.mindmap;
    if (mindmap) {
      show(output);
      StudyMateUpload.setFromHistory(fileId);
      renderMindmap(mindmap);
      show(document.getElementById('download-pdf'));
    }
  } catch {}
}
