import { apiGet, apiDelete } from '../api.js';
import { showToast, formatDate, getFeatureLabel, $, $$ } from '../utils.js';

export async function initHistory() {
  await loadHistory();

  const filter = document.getElementById('history-filter');
  filter?.addEventListener('change', () => loadHistory(filter.value));
}

async function loadHistory(feature = '') {
  const list = document.getElementById('history-list');
  const detail = document.getElementById('history-detail');
  if (!list) return;

  list.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

  try {
    const url = feature ? `/history?feature=${feature}` : '/history';
    const res = await apiGet(url);
    if (!res.ok) throw new Error();
    const items = await res.json();

    if (items.length === 0) {
      list.innerHTML = '<div class="card" style="text-align:center;padding:40px;"><p style="color:var(--color-muted-text);">No sessions yet. Upload a file to get started!</p></div>';
      return;
    }

    list.innerHTML = items.map(item => `
      <div class="card history-item" data-id="${item.id}" style="cursor:pointer;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:start;">
          <div>
            <div style="font-weight:600;">${item.originalName}</div>
            <div class="meta" style="font-size:0.85rem;color:var(--color-muted-text);margin-top:4px;">
              ${getFeatureLabel(item.feature)} · ${formatDate(item.createdAt)}
            </div>
          </div>
          <span style="font-size:0.75rem;padding:2px 10px;border-radius:12px;background:${item.status === 'done' ? 'var(--color-success)' : 'var(--color-warning)'};color:white;">
            ${item.status}
          </span>
        </div>
      </div>
    `).join('');

    $$('.history-item', list).forEach(el => {
      el.addEventListener('click', () => showDetail(el.dataset.id));
    });
  } catch {
    list.innerHTML = '<p style="color:var(--color-error);">Failed to load history</p>';
  }
}

async function showDetail(id) {
  const detail = document.getElementById('history-detail');
  if (!detail) return;

  detail.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

  try {
    const res = await apiGet(`/history/${id}`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    const fr = data.fileRecord;
    const out = data.output;

    detail.innerHTML = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:16px;">
          <div>
            <h3>${fr.originalName}</h3>
            <p style="color:var(--color-muted-text);font-size:0.85rem;">
              ${getFeatureLabel(fr.feature)} · ${formatDate(fr.createdAt)}
              · ${fr.fileSize ? (fr.fileSize / 1024).toFixed(1) + ' KB' : ''}
            </p>
          </div>
          <div style="display:flex;gap:8px;">
            <a href="/api/v1/history/${fr.id}/file" class="btn btn-secondary btn-sm" target="_blank">Download File</a>
            <button class="btn btn-primary btn-sm" id="download-pdf-detail">Download PDF</button>
            <button class="btn btn-danger btn-sm" id="delete-session">Delete</button>
          </div>
        </div>
        <div style="border-top:1px solid var(--color-border);padding-top:16px;">
          ${out ? (
            out.outputText
              ? `<div class="streaming-content"><pre style="white-space:pre-wrap;">${out.outputText}</pre></div>`
              : out.outputJson
                ? `<pre style="white-space:pre-wrap;font-size:0.85rem;">${JSON.stringify(out.outputJson, null, 2)}</pre>`
                : '<p style="color:var(--color-muted-text);">No output content</p>'
          ) : '<p style="color:var(--color-muted-text);">No output generated</p>'}
        </div>
      </div>
    `;

    document.getElementById('download-pdf-detail')?.addEventListener('click', async () => {
      const token = localStorage.getItem('studymate-token');
      const res2 = await fetch(`/api/v1/history/${id}/pdf`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res2.ok) {
        const blob = await res2.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${fr.originalName}_${fr.feature}.pdf`; a.click();
        URL.revokeObjectURL(url);
      }
    });

    document.getElementById('delete-session')?.addEventListener('click', async () => {
      if (!confirm('Delete this session?')) return;
      const res2 = await apiDelete(`/history/${id}`);
      if (res2.ok) {
        showToast('Session deleted', 'success');
        detail.innerHTML = '';
        loadHistory();
      } else {
        showToast('Failed to delete', 'error');
      }
    });
  } catch {
    detail.innerHTML = '<p style="color:var(--color-error);">Failed to load details</p>';
  }
}
