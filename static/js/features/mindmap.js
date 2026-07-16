import { apiPost } from '../api.js';
import { showToast, $, hide, show } from '../utils.js';

export async function initMindmap() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryMindmap(fileId);

  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');
  const loadingScreen = document.getElementById('loading-screen');

  let currentMindmap = null;
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
      const res = await apiPost('/features/mindmap', { fileRecordId });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        hide(loadingScreen);
        show(output);
        output.innerHTML = `<div class="card" style="padding:40px;text-align:center;"><p style="color:var(--color-error)">${err.detail}</p></div>`;
        return;
      }
      const data = await res.json();
      currentMindmap = data.mindmap;
      hide(loadingScreen);
      show(output);
      renderMindmap(currentMindmap);
      show(downloadBtn);
    } catch (err) {
      hide(loadingScreen);
      show(output);
      output.innerHTML = `<p style="color:var(--color-error)">${err.message}</p>`;
    } finally {
      generateBtn.disabled = false;
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
}

function renderMindmap(root) {
  const canvas = document.getElementById('mindmap-canvas');
  if (!canvas) return;

  const wrapper = canvas.parentElement;
  const rect = wrapper.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  const width = Math.max(600, rect.width - 4);
  const height = 560;

  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  canvas.width = width * dpr;
  canvas.height = height * dpr;

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  let offsetX = width / 2;
  let offsetY = 60;
  let scale = 1;
  let isDragging = false;
  let startX, startY;

  function getNodeSize(depth) {
    const sizes = [
      { r: 65, font: 14 },
      { r: 50, font: 12 },
      { r: 38, font: 11 },
      { r: 30, font: 10 },
    ];
    return sizes[Math.min(depth, 3)];
  }

  function layoutTree(node, depth, x, y, availableWidth) {
    const sz = getNodeSize(depth);
    if (!node.children || node.children.length === 0) {
      return { x, y, width: sz.r * 2 };
    }

    const children = node.children;
    const childCount = children.length;
    const spacing = Math.min(availableWidth / (childCount + 1), 180);
    const totalWidth = spacing * (childCount - 1);
    const startX = x - totalWidth / 2;
    const yOffset = depth === 0 ? 120 : 90;

    const childPositions = [];
    children.forEach((child, i) => {
      const cx = startX + i * spacing;
      const cy = y + yOffset;
      const sub = layoutTree(child, depth + 1, cx, cy, spacing * 1.5);
      childPositions.push(sub);
    });

    return { x, y, width: Math.max(totalWidth, sz.r * 2) };
  }

  function drawTree(node, depth, computedPositions, py) {
    const sz = getNodeSize(depth);
    const pos = computedPositions;
    if (!pos) return;

    const x = pos.x * scale + offsetX;
    const y = pos.y * scale + offsetY;

    if (node.children && node.children.length > 0 && depth > 0) {
      node.children.forEach((child, i) => {
        const childPos = computedPositions.children ? computedPositions.children[i] : null;
        if (childPos) {
          const cx = childPos.x * scale + offsetX;
          const cy = childPos.y * scale + offsetY;
          ctx.beginPath();
          ctx.moveTo(x, y + sz.r * scale);
          ctx.lineTo(cx, cy - getNodeSize(depth + 1).r * scale);
          ctx.strokeStyle = getColor(depth, 0.3);
          ctx.lineWidth = 2 * scale;
          ctx.stroke();
        }
      });
    }

    const color = getColor(depth);
    const grad = ctx.createRadialGradient(x, y, 0, x, y, sz.r * scale);
    grad.addColorStop(0, color + '33');
    grad.addColorStop(0.7, color + '22');
    grad.addColorStop(1, color + '11');

    ctx.beginPath();
    ctx.arc(x, y, sz.r * scale, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5 * scale;
    ctx.stroke();

    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#1c1917';
    ctx.font = `${sz.font * scale}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const label = node.label || '';
    const maxChars = Math.floor((sz.r * 1.6) / (sz.font * 0.6));
    if (label.length <= maxChars) {
      ctx.fillText(label, x, y);
    } else {
      const words = label.split(' ');
      const lines = [];
      let line = '';
      for (const word of words) {
        if ((line + ' ' + word).length <= maxChars) {
          line += (line ? ' ' : '') + word;
        } else {
          lines.push(line);
          line = word;
        }
      }
      if (line) lines.push(line);
      lines.forEach((l, i) => {
        ctx.fillText(l, x, y + (i - (lines.length - 1) / 2) * (sz.font * 1.2 * scale));
      });
    }

    if (node.children && node.children.length > 0 && computedPositions.children) {
      node.children.forEach((child, i) => {
        drawTree(child, depth + 1, computedPositions.children[i], null);
      });
    }
  }

  function computeLayout(node, depth, x, y, availableWidth) {
    const sz = getNodeSize(depth);
    const result = { x, y, children: [] };

    if (!node.children || node.children.length === 0) {
      return result;
    }

    const children = node.children;
    const childCount = children.length;
    const spacing = Math.min(availableWidth / Math.max(childCount - 1, 1), 180);
    const totalWidth = spacing * (childCount - 1);
    const startX = x - totalWidth / 2;
    const yOffset = depth === 0 ? 120 : 90;

    children.forEach((child, i) => {
      const cx = startX + i * spacing;
      const cy = y + yOffset;
      const subAvailable = Math.max(spacing * 1.5, 120);
      result.children.push(computeLayout(child, depth + 1, cx, cy, subAvailable));
    });

    return result;
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    const layout = computeLayout(root, 0, 0, 0, width - 100);
    drawTree(root, 0, layout, null);
  }

  draw();

  canvas.onmousedown = (e) => {
    isDragging = true;
    const r = canvas.getBoundingClientRect();
    startX = e.clientX - offsetX;
    startY = e.clientY - offsetY;
    canvas.style.cursor = 'grabbing';
  };

  canvas.onmousemove = (e) => {
    if (!isDragging) return;
    offsetX = e.clientX - startX;
    offsetY = e.clientY - startY;
    draw();
  };

  canvas.onmouseup = () => {
    isDragging = false;
    canvas.style.cursor = 'grab';
  };
  canvas.onmouseleave = () => {
    isDragging = false;
    canvas.style.cursor = 'grab';
  };

  canvas.onwheel = (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const delta = e.deltaY > 0 ? 0.88 : 1.12;
    const newScale = Math.max(0.2, Math.min(2.5, scale * delta));

    offsetX = mx - (mx - offsetX) * (newScale / scale);
    offsetY = my - (my - offsetY) * (newScale / scale);
    scale = newScale;
    draw();
  };

  canvas.ontouchstart = (e) => {
    if (e.touches.length === 1) {
      isDragging = true;
      startX = e.touches[0].clientX - offsetX;
      startY = e.touches[0].clientY - offsetY;
    }
  };
  canvas.ontouchmove = (e) => {
    if (!isDragging || e.touches.length !== 1) return;
    e.preventDefault();
    offsetX = e.touches[0].clientX - startX;
    offsetY = e.touches[0].clientY - startY;
    draw();
  };
  canvas.ontouchend = () => { isDragging = false; };
}

function getColor(depth, alpha = 0.8) {
  const colors = [
    `rgba(217, 119, 6, ${alpha})`,
    `rgba(2, 132, 199, ${alpha})`,
    `rgba(16, 185, 129, ${alpha})`,
    `rgba(99, 102, 241, ${alpha})`,
    `rgba(245, 158, 11, ${alpha})`,
  ];
  return colors[depth % colors.length];
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
