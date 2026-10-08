import { loadTheme } from './theme.js?v=8';
import { isAuthenticated, getUser, logout } from './auth.js?v=8';
import { $, $$ } from './utils.js?v=8';

document.addEventListener('DOMContentLoaded', () => {
  loadTheme();
  initNavbar();
  initAuthUI();
  initMobileMenu();
  initDashboard();
});

function initNavbar() {
  const nav = document.querySelector('.navbar');
  if (!nav) return;
}

function initAuthUI() {
  const authContainer = document.getElementById('auth-ui');
  if (!authContainer) return;

  document.body.classList.toggle('is-authenticated', isAuthenticated());

  if (isAuthenticated()) {
    const user = getUser();
    const name = user?.name?.trim() || 'Account';
    const initials = name.split(/\s+/).slice(0, 2)
      .map(part => part.charAt(0).toUpperCase()).join('') || 'A';
    authContainer.innerHTML = `
      <a href="/profile" class="nav-account" aria-label="Account: ${name}" title="${name}">
        <span class="profile-avatar-fallback" aria-hidden="true">${initials}</span>
      </a>
      <button id="logout-btn" class="btn btn-danger btn-sm" type="button">Logout</button>
    `;
    const fallback = authContainer.querySelector('.profile-avatar-fallback');
    if (user?.image && fallback) {
      const image = document.createElement('img');
      image.className = 'profile-avatar';
      image.src = user.image;
      image.alt = `${name} profile photo`;
      image.referrerPolicy = 'no-referrer';
      image.onerror = () => image.replaceWith(fallback);
      fallback.replaceWith(image);
    }
    document.getElementById('logout-btn')?.addEventListener('click', logout);
  } else {
    authContainer.innerHTML = `
      <a href="/login" class="btn btn-ghost btn-sm">Sign In</a>
    `;
  }
}

function initMobileMenu() {
  const toggle = document.querySelector('.mobile-menu-toggle');
  const menu = document.getElementById('nav-menu');
  if (!toggle || !menu) return;

  const setOpen = (open) => {
    menu.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  };

  toggle.addEventListener('click', () => setOpen(!menu.classList.contains('open')));
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });
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

async function initDashboard() {
  const dashboard = document.getElementById('dashboard');
  if (!dashboard || !isAuthenticated()) return;

  const user = getUser();

  const greeting = document.getElementById('dashboard-greeting');
  if (greeting && user?.name) {
    greeting.textContent = `Welcome back, ${user.name.split(' ')[0]}`;
  }

  const eyebrow = document.getElementById('dashboard-eyebrow');
  if (eyebrow) {
    eyebrow.textContent = timeGreeting();
  }
}

function timeGreeting() {
  const h = new Date().getHours();
  if (h < 5) return 'Good night';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  if (h < 21) return 'Good evening';
  return 'Good night';
}
