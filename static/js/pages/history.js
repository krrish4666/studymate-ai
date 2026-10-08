import { apiGet, apiDelete } from '../api.js?v=8';
import { showToast, formatDate, getFeatureLabel, formatFileSize, $, $$, DOC_ICON, statusPill, emptyStateHtml, errorStateHtml } from '../utils.js?v=8';

const DETAIL_PLACEHOLDER = `
  <div class="empty-state">
    <span class="empty-state-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v5h6"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>
    </span>
    <h3 class="empty-state-title">Select a document</h3>
    <p class="empty-state-text">Choose a document from the list to preview its generated content, download a PDF, or remove it.</p>
  </div>`;

export async function initHistory() {
  await loadHistory();

  const filter = document.getElementById('history-filter');
  filter?.addEventListener('change', () => loadHistory(filter.value));
}

async function loadHistory(feature = '') {
  const list = document.getElementById('history-list');
  const detail = document.getElementById('history-detail');
  if (!list) return;

  detail.innerHTML = DETAIL_PLACEHOLDER;
  list.innerHTML = '<div class="skeleton-block"></div>'.repeat(4);

  try {
    const url = feature ? `/history?feature=${feature}` : '/history';
    const res = await apiGet(url);
    if (!res.ok) throw new Error();

    const items = await res.json();

    if (items.length === 0) {
      list.innerHTML = emptyStateHtml(
        'No sessions yet',
        'Upload a document and StudyMate will generate notes, flashcards, quizzes and more — all saved here.',
        '<a class="btn btn-primary" href="/feature/notes">Upload Document</a>'
      );
      return;
    }

    list.innerHTML = items.map((item, i) => `
      <div class="doc-card" data-id="${item.id}" tabindex="0" role="button" aria-label="Open ${item.originalName}">
        <div class="doc-card-top">
          <span class="doc-card-icon" aria-hidden="true">${DOC_ICON}</span>
          ${statusPill(item.status)}
        </div>
        <h3 class="doc-card-title">${item.originalName}</h3>
        <p class="doc-card-meta">${getFeatureLabel(item.feature)} &middot; ${formatDate(item.createdAt)}</p>
      </div>
    `).join('');

    $$('.doc-card', list).forEach((el) => {
      const open = () => showDetail(el.dataset.id, list);
      el.addEventListener('click', open);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
      });
    });
  } catch {
    list.innerHTML = errorStateHtml(
      'We couldn\'t load your history',
      'Something went wrong while loading your sessions.'
    );
  }
}

async function showDetail(id, list) {
  const detail = document.getElementById('history-detail');
  if (!detail) return;

  if (list) {
    $$('.doc-card', list).forEach((el) => el.classList.toggle('active', el.dataset.id === id));
  }

  detail.innerHTML = '<div class="skeleton-block"></div>';

  try {
    const res = await apiGet(`/history/${id}`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    const fr = data.fileRecord;
    const out = data.output;

    detail.innerHTML = `
      <div class="card detail-card">
        <div class="detail-head">
          <div>
            <h2 class="detail-title">${fr.originalName}</h2>
            <p class="detail-meta">
              ${getFeatureLabel(fr.feature)} &middot; ${formatDate(fr.createdAt)}
              ${fr.fileSize ? ' &middot; ' + formatFileSize(fr.fileSize) : ''}
            </p>
          </div>
          <div class="detail-actions">
            <button class="btn btn-secondary btn-sm" id="download-pdf-detail">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/></svg>
              Download PDF
            </button>
            <button class="btn btn-danger btn-sm" id="delete-session">Delete</button>
          </div>
        </div>
        <div class="detail-body">
          ${out ? (
            out.outputText
              ? `<pre class="detail-preview">${out.outputText}</pre>`
              : '<p class="detail-note">Content preview is only available for notes and revision.</p>'
          ) : '<p class="detail-note">No output generated yet.</p>'}
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
      } else {
        showToast('Failed to generate PDF', 'error');
      }
    });

    document.getElementById('delete-session')?.addEventListener('click', async () => {
      if (!confirm('Delete this session?')) return;
      const res2 = await apiDelete(`/history/${id}`);
      if (res2.ok) {
        showToast('Session deleted', 'success');
        detail.innerHTML = DETAIL_PLACEHOLDER;
        loadHistory(document.getElementById('history-filter')?.value || '');
      } else {
        showToast('Failed to delete', 'error');
      }
    });
  } catch {
    detail.innerHTML = errorStateHtml(
      'We couldn\'t load this session',
      'Something went wrong while loading the details.'
    );
  }
}
