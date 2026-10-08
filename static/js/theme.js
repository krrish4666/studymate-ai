const THEMES = [
  { id: 'warm-light', name: 'Warm Light', preview: ['#0f766e', '#f7f5f1'] },
  { id: 'pure-light', name: 'Pure Light', preview: ['#0369a1', '#f5f8fb'] },
  { id: 'warm-dark', name: 'Warm Dark', preview: ['#2dd4bf', '#1b1917'] },
  { id: 'slate-dark', name: 'Slate Dark', preview: ['#38bdf8', '#0f172a'] },
  { id: 'midnight-ambient', name: 'Midnight Ambient', preview: ['#818cf8', '#0b1020'] },
  { id: 'forest-ambient', name: 'Forest Ambient', preview: ['#34d399', '#071f1a'] },
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
