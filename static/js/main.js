import { loadTheme } from './theme.js';
import { isAuthenticated, getUser, logout } from './auth.js';
import { $, $$ } from './utils.js';

document.addEventListener('DOMContentLoaded', () => {
  loadTheme();
  initNavbar();
  initAuthUI();
  initMobileMenu();
});

function initNavbar() {
  const nav = document.querySelector('.navbar');
  if (!nav) return;
}

function initAuthUI() {
  const authContainer = document.getElementById('auth-ui');
  if (!authContainer) return;

  if (isAuthenticated()) {
    const user = getUser();
    authContainer.innerHTML = `
      <a href="/profile" class="btn btn-ghost btn-sm">${user?.name || 'Profile'}</a>
      <button id="logout-btn" class="btn btn-ghost btn-sm">Logout</button>
    `;
    document.getElementById('logout-btn')?.addEventListener('click', logout);
  } else {
    authContainer.innerHTML = `
      <a href="/login" class="btn btn-ghost btn-sm">Sign In</a>
      <a href="/register" class="btn btn-primary btn-sm">Get Started</a>
    `;
  }
}

function initMobileMenu() {
  const toggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => navLinks.classList.toggle('open'));
  }
}

export function updateHistorySidebar(items) {
  const list = document.getElementById('history-list');
  if (!list) return;
  if (!items || items.length === 0) {
    list.innerHTML = '<p style="color:var(--color-muted-text);font-size:0.85rem;text-align:center;padding:20px;">No sessions yet</p>';
    return;
  }
  const labels = { notes: 'Notes', flashcards: 'Flashcards', quiz: 'Quiz', mindmap: 'Mind Map', revision: 'Revision' };
  list.innerHTML = items.map(item => `
    <div class="history-item" data-id="${item.id}" data-feature="${item.feature}">
      <div class="title">${item.originalName}</div>
      <div class="meta">${labels[item.feature] || item.feature} · ${new Date(item.createdAt).toLocaleDateString()}</div>
    </div>
  `).join('');

  $$('.history-item', list).forEach(el => {
    el.addEventListener('click', () => {
      window.location.href = `/feature/${el.dataset.feature}?historyId=${el.dataset.id}`;
    });
  });
}
