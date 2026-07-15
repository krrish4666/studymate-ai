import { apiPost } from '../api.js';
import { initUpload } from '../upload.js';
import { showToast, $ } from '../utils.js';

export async function initMindmap() {
  const fileId = new URLSearchParams(location.search).get('historyId');
  if (fileId) return loadHistoryMindmap(fileId);

  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const progress = document.getElementById('upload-progress');
  const output = document.getElementById('feature-output');
  const generateBtn = document.getElementById('generate-btn');
  const downloadBtn = document.getElementById('download-pdf');

  let currentFileRecordId = null;
  let currentMindmap = null;

  initUpload(dropzone, fileInput, progress, 'mindmap');

  generateBtn?.addEventListener('click', async () => {
    if (!currentFileRecordId) return;
    generateBtn.disabled = true;
    output.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Generating mind map...</p></div>';

    try {
      const res = await apiPost('/features/mindmap', { fileRecordId: currentFileRecordId });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        output.innerHTML = `<p style="color:var(--color-error)">${err.detail}</p>`;
        return;
      }
      const data = await res.json();
      currentMindmap = data.mindmap;
      renderMindmap(currentMindmap);
      downloadBtn.hidden = false;
    } catch (err) {
      output.innerHTML = `<p style="color:var(--color-error)">${err.message}</p>`;
    } finally {
      generateBtn.disabled = false;
    }
  });

  function renderMindmap(root) {
    output.innerHTML = `
      <canvas id="mindmap-canvas"></canvas>
      <div style="display:flex;justify-content:center;gap:12px;margin-top:16px;">
        <button class="btn btn-primary btn-sm" id="download-mindmap-pdf">Download PDF</button>
      </div>
    `;

    const canvas = document.getElementById('mindmap-canvas');
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = Math.min(800, rect.width - 48);
    canvas.height = 500;

    let offsetX = 0, offsetY = 0;
    let scale = 1;
    let isDragging = false;
    let startX, startY;

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.translate(offsetX, offsetY);
      ctx.scale(scale, scale);
      drawNode(root, canvas.width / 2 / scale, 40, 0);
      ctx.restore();
    }

    function drawNode(node, x, y, depth) {
      const radius = depth === 0 ? 60 : depth === 1 ? 45 : 35;
      const colors = ['#d97706', '#0284c7', '#10b981', '#6366f1', '#f59e0b'];
      const color = colors[depth % colors.length];

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color + '22';
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#1c1917';
      ctx.font = `${depth === 0 ? 14 : 12}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const words = node.label?.split(' ') || [];
      if (words.length <= 2) {
        ctx.fillText(node.label || '', x, y);
      } else {
        const mid = Math.ceil(words.length / 2);
        ctx.fillText(words.slice(0, mid).join(' '), x, y - 8);
        ctx.fillText(words.slice(mid).join(' '), x, y + 8);
      }

      if (node.children && node.children.length > 0) {
        const count = node.children.length;
        const spacing = Math.max(120, Math.min(200, 300 / count));
        const startX = x - ((count - 1) * spacing) / 2;
        const yOffset = depth === 0 ? 100 : 80;

        node.children.forEach((child, i) => {
          const cx = startX + i * spacing;
          const cy = y + yOffset;

          ctx.beginPath();
          ctx.moveTo(x, y + radius);
          ctx.lineTo(cx, cy - (depth === 0 ? 60 : 45));
          ctx.strokeStyle = color + '44';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          drawNode(child, cx, cy, depth + 1);
        });
      }
    }

    draw();

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      startX = e.clientX - offsetX;
      startY = e.clientY - offsetY;
    });

    canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      offsetX = e.clientX - startX;
      offsetY = e.clientY - startY;
      draw();
    });

    canvas.addEventListener('mouseup', () => { isDragging = false; });
    canvas.addEventListener('mouseleave', () => { isDragging = false; });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.max(0.3, Math.min(2, scale * delta));
      draw();
    });

    document.getElementById('download-mindmap-pdf').addEventListener('click', downloadPdf);
  }

  async function downloadPdf() {
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
      document.getElementById('generate-btn').hidden = true;
      output.innerHTML = `<canvas id="mindmap-canvas"></canvas>`;
    }
  } catch {}
}
