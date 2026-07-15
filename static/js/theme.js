const THEMES = [
  { id: 'warm-light', name: 'Warm Light', preview: ['#d97706', '#fef9ef'] },
  { id: 'pure-light', name: 'Pure Light', preview: ['#0284c7', '#f0f9ff'] },
  { id: 'warm-dark', name: 'Warm Dark', preview: ['#f59e0b', '#1c1917'] },
  { id: 'slate-dark', name: 'Slate Dark', preview: ['#94a3b8', '#0f172a'] },
  { id: 'midnight-ambient', name: 'Midnight Ambient', preview: ['#6366f1', '#020617'] },
  { id: 'forest-ambient', name: 'Forest Ambient', preview: ['#10b981', '#022c22'] },
];

const STORAGE_KEY = 'studymate-theme';
const CUSTOM_KEY = 'studymate-custom-theme-colors';

export function getThemes() {
  return THEMES;
}

export function loadTheme() {
  const saved = localStorage.getItem(STORAGE_KEY) || 'warm-light';
  applyTheme(saved);
  return saved;
}

export function applyTheme(themeId) {
  document.documentElement.setAttribute('data-theme', themeId);
  localStorage.setItem(STORAGE_KEY, themeId);
}

export function applyCustomTheme(colors) {
  const root = document.documentElement;
  root.setAttribute('data-theme', 'custom');
  root.style.setProperty('--color-primary', colors.primary);
  root.style.setProperty('--color-background', colors.background);
  root.style.setProperty('--color-card', colors.card);
  root.style.setProperty('--color-text', colors.text);
  root.style.setProperty('--color-muted-text', colors.mutedText);
  root.style.setProperty('--color-border', colors.border);
  localStorage.setItem(CUSTOM_KEY, JSON.stringify(colors));
}

export function getCustomColors() {
  const data = localStorage.getItem(CUSTOM_KEY);
  return data ? JSON.parse(data) : null;
}
