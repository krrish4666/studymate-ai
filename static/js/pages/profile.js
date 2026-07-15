import { apiGet, apiPost, apiPatch, apiDelete } from '../api.js';
import { showToast, $, $$ } from '../utils.js';
import { loadTheme, applyTheme, applyCustomTheme, getThemes, getCustomColors } from '../theme.js';

export async function initProfile() {
  await loadProfile();
  initThemeSettings();
  initApiKeys();
}

async function loadProfile() {
  try {
    const res = await apiGet('/profile');
    if (!res.ok) throw new Error('Failed to load profile');
    const data = await res.json();

    document.getElementById('profile-name').textContent = data.user.name || 'User';
    document.getElementById('profile-email').textContent = data.user.email;
    document.getElementById('stats-files').textContent = data.stats.totalFiles;
    document.getElementById('stats-sessions').textContent = data.stats.totalSessions;
    document.getElementById('edit-name').value = data.user.name || '';

    const form = document.getElementById('profile-form');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('edit-name').value;
      const res2 = await apiPatch('/profile', { name });
      if (res2.ok) {
        showToast('Profile updated', 'success');
        document.getElementById('profile-name').textContent = name;
      } else {
        showToast('Failed to update profile', 'error');
      }
    });
  } catch {
    showToast('Failed to load profile', 'error');
  }
}

function initThemeSettings() {
  const grid = document.getElementById('theme-grid');
  if (!grid) return;

  const themes = getThemes();
  const current = loadTheme();

  grid.innerHTML = themes.map(t => `
    <div class="theme-option ${t.id === current ? 'active' : ''}" data-theme="${t.id}">
      <div class="preview" style="background: linear-gradient(135deg, ${t.preview[0]} 50%, ${t.preview[1]} 50%);"></div>
      <div>${t.name}</div>
    </div>
  `).join('');

  $$('.theme-option', grid).forEach(el => {
    el.addEventListener('click', () => {
      $$('.theme-option', grid).forEach(o => o.classList.remove('active'));
      el.classList.add('active');
      applyTheme(el.dataset.theme);
      showToast('Theme applied', 'success');
    });
  });
}

async function initApiKeys() {
  const list = document.getElementById('api-keys-list');
  const form = document.getElementById('api-key-form');
  if (!list) return;

  async function loadKeys() {
    try {
      const res = await apiGet('/profile/api-keys');
      if (!res.ok) throw new Error();
      const keys = await res.json();
      if (keys.length === 0) {
        list.innerHTML = '<p style="color:var(--color-muted-text);text-align:center;padding:20px;">No API keys added yet</p>';
        return;
      }
      list.innerHTML = keys.map(k => `
        <div class="card" style="display:flex;justify-content:space-between;align-items:center;padding:16px;">
          <div>
            <strong>${k.provider}</strong>
            ${k.label ? `<span style="color:var(--color-muted-text);font-size:0.85rem;"> - ${k.label}</span>` : ''}
          </div>
          <button class="btn btn-danger btn-sm delete-key" data-id="${k.id}">Delete</button>
        </div>
      `).join('');

      $$('.delete-key', list).forEach(btn => {
        btn.addEventListener('click', async () => {
          const res2 = await apiDelete(`/profile/api-keys/${btn.dataset.id}`);
          if (res2.ok) {
            showToast('API key deleted', 'success');
            loadKeys();
          } else {
            showToast('Failed to delete key', 'error');
          }
        });
      });
    } catch {
      list.innerHTML = '<p style="color:var(--color-error);text-align:center;">Failed to load API keys</p>';
    }
  }

  await loadKeys();

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const provider = document.getElementById('key-provider').value;
    const key = document.getElementById('key-value').value;
    const label = document.getElementById('key-label').value;

    const res = await apiPost('/profile/api-keys', { provider, key, label: label || null });
    if (res.ok) {
      showToast('API key added', 'success');
      document.getElementById('key-value').value = '';
      document.getElementById('key-label').value = '';
      loadKeys();
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed to add key' }));
      showToast(err.detail || 'Failed to add key', 'error');
    }
  });
}
